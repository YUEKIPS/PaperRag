/**
 * Canvas PDF viewer (vendored PDF.js 4.8.69). No browser PDF plugin.
 * Loaded as a classic script; the library itself is an ES module.
 */
(function () {
  const PDFJS_URL = "/static/vendor/pdfjs/pdf.min.mjs";
  const WORKER_URL = "/static/vendor/pdfjs/pdf.worker.min.mjs";
  const ZOOM_MIN = 0.7;
  const ZOOM_MAX = 2.4;

  let pdfjsLib = null;
  let pdfjsPromise = null;
  let loadingTask = null;
  let doc = null;
  let token = 0;
  let pagesRoot = null;
  let slots = [];
  let observer = null;
  let resizeObserver = null;
  let zoom = 1;
  let baseFit = 1;
  let currentPage = 1;
  let onChange = null;
  let scrollHandler = null;

  function loadPdfjs() {
    if (!pdfjsPromise) {
      pdfjsPromise = import(PDFJS_URL).then((lib) => {
        lib.GlobalWorkerOptions.workerSrc = WORKER_URL;
        pdfjsLib = lib;
        return lib;
      });
    }
    return pdfjsPromise;
  }

  function emit() {
    if (!onChange) return;
    onChange({
      page: currentPage,
      total: doc ? doc.numPages : 0,
    });
  }

  function detachScroll() {
    if (pagesRoot && scrollHandler) {
      pagesRoot.removeEventListener("scroll", scrollHandler);
    }
    scrollHandler = null;
  }

  function destroyDoc() {
    token += 1;
    if (observer) {
      observer.disconnect();
      observer = null;
    }
    if (resizeObserver) {
      resizeObserver.disconnect();
      resizeObserver = null;
    }
    detachScroll();
    slots.forEach((slot) => {
      if (slot.task) {
        try {
          slot.task.cancel();
        } catch {
          /* already settled */
        }
      }
    });
    slots = [];
    if (pagesRoot) pagesRoot.innerHTML = "";
    if (loadingTask) {
      try {
        loadingTask.destroy();
      } catch {
        /* ignore */
      }
      loadingTask = null;
    }
    if (doc) {
      try {
        doc.destroy();
      } catch {
        /* ignore */
      }
      doc = null;
    }
    currentPage = 1;
    zoom = 1;
    baseFit = 1;
  }

  function clear() {
    const cb = onChange;
    destroyDoc();
    onChange = cb;
    emit();
  }

  function scaleFor() {
    return Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, baseFit * zoom));
  }

  function measureFit(pageWidth) {
    const width = pagesRoot ? pagesRoot.clientWidth : 0;
    const inner = Math.max(0, width - 32);
    if (!pageWidth || inner < 40) return 1;
    return inner / pageWidth;
  }

  async function renderSlot(slot, my) {
    if (!doc || my !== token) return;
    const scale = scaleFor();
    if (slot.done && Math.abs(slot.renderedScale - scale) < 0.02) return;
    if (slot.task) {
      try {
        slot.task.cancel();
      } catch {
        /* ignore */
      }
      slot.task = null;
    }
    const page = await doc.getPage(slot.num);
    if (my !== token) return;
    const viewport = page.getViewport({ scale });
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const canvas = slot.canvas;
    canvas.width = Math.floor(viewport.width * dpr);
    canvas.height = Math.floor(viewport.height * dpr);
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;
    slot.el.style.width = `${Math.floor(viewport.width)}px`;
    slot.el.style.height = `${Math.floor(viewport.height)}px`;
    const ctx = canvas.getContext("2d", { alpha: false });
    const params = { canvasContext: ctx, viewport };
    if (dpr !== 1) params.transform = [dpr, 0, 0, dpr, 0, 0];
    const task = page.render(params);
    slot.task = task;
    try {
      await task.promise;
      if (my !== token) return;
      slot.renderedScale = scale;
      slot.done = true;
    } catch (err) {
      if (err && err.name === "RenderingCancelledException") return;
      throw err;
    } finally {
      if (slot.task === task) slot.task = null;
    }
  }

  function updateCurrentFromScroll() {
    if (!pagesRoot || !slots.length) return;
    const mark = pagesRoot.scrollTop + 24;
    let page = 1;
    slots.forEach((slot) => {
      if (slot.el.offsetTop <= mark) page = slot.num;
    });
    if (page !== currentPage) {
      currentPage = page;
      emit();
    }
  }

  function go(delta) {
    if (!doc || !pagesRoot) return;
    const next = Math.min(doc.numPages, Math.max(1, currentPage + delta));
    const slot = slots[next - 1];
    if (!slot) return;
    currentPage = next;
    pagesRoot.scrollTo({ top: Math.max(0, slot.el.offsetTop - 8), behavior: "smooth" });
    emit();
  }

  function zoomBy(delta) {
    const my = token;
    zoom = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round((zoom + delta) * 100) / 100));
    slots.forEach((slot) => {
      slot.done = false;
    });
    slots.forEach((slot) => {
      const visible = slot.el.getBoundingClientRect();
      const rootBox = pagesRoot.getBoundingClientRect();
      const near =
        visible.bottom >= rootBox.top - 200 && visible.top <= rootBox.bottom + 200;
      if (near || slot.num === currentPage) renderSlot(slot, my);
    });
  }

  async function show(buffer, root, hooks) {
    if (!root) throw new Error("PDF 容器缺失");
    clear();
    pagesRoot = root;
    onChange = hooks && hooks.onChange;
    const my = token;
    const lib = await loadPdfjs();
    if (my !== token) return;
    const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
    loadingTask = lib.getDocument({ data: bytes, disableRange: true, disableStream: true });
    const opened = await loadingTask.promise;
    if (my !== token) {
      opened.destroy();
      return;
    }
    doc = opened;
    loadingTask = null;
    const first = await doc.getPage(1);
    if (my !== token) return;
    const natural = first.getViewport({ scale: 1 });
    for (let i = 0; i < 30; i += 1) {
      if (my !== token) return;
      if (pagesRoot.clientWidth > 40) break;
      await new Promise((resolve) => requestAnimationFrame(resolve));
    }
    baseFit = measureFit(natural.width);
    const aspect = natural.height / natural.width;
    const layoutWidth = Math.max(120, (pagesRoot.clientWidth || 320) - 32);

    for (let num = 1; num <= doc.numPages; num += 1) {
      const el = document.createElement("div");
      el.className = "pdf-page";
      el.dataset.page = String(num);
      el.style.width = `${Math.floor(layoutWidth)}px`;
      el.style.height = `${Math.floor(layoutWidth * aspect)}px`;
      const canvas = document.createElement("canvas");
      canvas.setAttribute("role", "img");
      canvas.setAttribute("aria-label", `第 ${num} 页`);
      el.appendChild(canvas);
      pagesRoot.appendChild(el);
      slots.push({ num, el, canvas, task: null, renderedScale: 0, done: false });
    }

    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          const num = Number(entry.target.dataset.page);
          const slot = slots[num - 1];
          if (slot) renderSlot(slot, my);
        });
      },
      { root: pagesRoot, rootMargin: "240px 0px" }
    );
    slots.forEach((slot) => observer.observe(slot.el));

    scrollHandler = () => updateCurrentFromScroll();
    pagesRoot.addEventListener("scroll", scrollHandler, { passive: true });

    resizeObserver = new ResizeObserver(() => {
      if (my !== token || !doc) return;
      const nextFit = measureFit(natural.width);
      if (Math.abs(nextFit - baseFit) < 0.03) return;
      baseFit = nextFit;
      slots.forEach((slot) => {
        slot.done = false;
      });
      const visible = slots.filter((slot) => {
        const box = slot.el.getBoundingClientRect();
        const rootBox = pagesRoot.getBoundingClientRect();
        return box.bottom >= rootBox.top - 80 && box.top <= rootBox.bottom + 80;
      });
      (visible.length ? visible : slots.slice(0, 1)).forEach((slot) => renderSlot(slot, my));
    });
    resizeObserver.observe(pagesRoot);

    currentPage = 1;
    emit();
    await renderSlot(slots[0], my);
  }

  window.PaperPdfView = {
    show,
    clear,
    go,
    zoomBy,
  };
})();
