(function () {
  const TOKEN =
    document.querySelector('meta[name="paper-rag-token"]')?.getAttribute("content") || "";

  const PIPELINE_STEPS = [
    { key: "decide", label: "路由" },
    { key: "retrieve", label: "检索" },
    { key: "grade", label: "评分" },
    { key: "rewrite", label: "改写" },
    { key: "generate", label: "生成" },
  ];

  const els = {
    sessionList: document.getElementById("session-list"),
    messages: document.getElementById("messages"),
    mainTitle: document.getElementById("main-title"),
    mainPane: document.getElementById("main-pane"),
    composerForm: document.getElementById("composer-form"),
    queryInput: document.getElementById("query-input"),
    btnSend: document.getElementById("btn-send"),
    btnNew: document.getElementById("btn-new-session"),
    btnArchive: document.getElementById("btn-archive"),
    btnDelete: document.getElementById("btn-delete"),
    progressDock: document.getElementById("progress-dock"),
    progressLabel: document.getElementById("progress-label"),
    progressSteps: document.getElementById("progress-steps"),
    healthDot: document.getElementById("health-dot"),
    healthText: document.getElementById("health-text"),
    themeSelect: document.getElementById("theme-select"),
    inspector: document.getElementById("inspector"),
    inspectorBody: document.getElementById("inspector-body"),
    inspectorClose: document.getElementById("inspector-close"),
    confirmDialog: document.getElementById("confirm-dialog"),
    confirmDialogTitle: document.getElementById("confirm-dialog-title"),
    confirmDialogMessage: document.getElementById("confirm-dialog-message"),
    confirmDialogCancel: document.getElementById("confirm-dialog-cancel"),
    confirmDialogOk: document.getElementById("confirm-dialog-ok"),
    renameDialog: document.getElementById("rename-dialog"),
    renameDialogForm: document.getElementById("rename-dialog-form"),
    renameDialogInput: document.getElementById("rename-dialog-input"),
    renameDialogCancel: document.getElementById("rename-dialog-cancel"),
    tabSessions: document.getElementById("tab-sessions"),
    tabPapers: document.getElementById("tab-papers"),
    panelSessions: document.getElementById("panel-sessions"),
    panelPapers: document.getElementById("panel-papers"),
    paperList: document.getElementById("paper-list"),
    paperDrawer: document.getElementById("paper-drawer"),
    paperDrawerTitle: document.getElementById("paper-drawer-title"),
    paperDrawerId: document.getElementById("paper-drawer-id"),
    paperDrawerEmpty: document.getElementById("paper-drawer-empty"),
    paperDrawerStatus: document.getElementById("paper-drawer-status"),
    paperDrawerToolbar: document.getElementById("paper-drawer-toolbar"),
    paperDrawerPage: document.getElementById("paper-drawer-page"),
    paperPages: document.getElementById("paper-drawer-pages"),
    btnPdfPrev: document.getElementById("btn-pdf-prev"),
    btnPdfNext: document.getElementById("btn-pdf-next"),
    btnPdfZoomIn: document.getElementById("btn-pdf-zoom-in"),
    btnPdfZoomOut: document.getElementById("btn-pdf-zoom-out"),
    btnInsertPaperQuery: document.getElementById("btn-insert-paper-query"),
    btnClosePaperPreview: document.getElementById("btn-close-paper-preview"),
  };

  let confirmDialogResolve = null;
  let renameDialogResolve = null;
  let sessionActionBusy = false;

  let currentSessionId = null;
  let sessionDetail = null;
  let asking = false;
  let progressTimer = null;
  let progressIndex = 0;
  let sessionContextMenu = null;
  let contextMenuSessionId = null;
  let papersCatalog = [];
  let selectedPaperId = null;
  let previewGen = 0;
  let sidebarMode = "sessions";

  function api(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${TOKEN}`,
      ...(options.headers || {}),
    };
    return fetch(path, { ...options, headers }).then(async (res) => {
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const err = new Error(data.message || data.error || res.statusText);
        err.status = res.status;
        err.payload = data;
        throw err;
      }
      return data;
    });
  }

  function updateSessionActionButtons() {
    const disabled = !currentSessionId || sessionActionBusy;
    els.btnArchive.disabled = disabled;
    els.btnDelete.disabled = disabled;
  }

  function setSessionActionBusy(busy) {
    sessionActionBusy = busy;
    updateSessionActionButtons();
    const on = !busy;
    els.confirmDialogOk.disabled = !on;
    els.confirmDialogCancel.disabled = !on;
  }

  const DELETE_CONFIRM = {
    title: "删除对话",
    message: "删除后无法恢复，对话记录将从列表中移除。",
    confirmLabel: "删除",
    danger: true,
  };

  const ARCHIVE_CONFIRM = {
    title: "归档对话",
    message: "归档后该对话将从侧栏列表中隐藏，记录仍保留。确定归档？",
    confirmLabel: "归档",
    danger: false,
  };

  function openConfirmDialog({
    title = DELETE_CONFIRM.title,
    message = DELETE_CONFIRM.message,
    confirmLabel = DELETE_CONFIRM.confirmLabel,
    danger = true,
  } = {}) {
    return new Promise((resolve) => {
      confirmDialogResolve = resolve;
      els.confirmDialogTitle.textContent = title;
      els.confirmDialogMessage.textContent = message;
      els.confirmDialogOk.textContent = confirmLabel;
      els.confirmDialogOk.classList.toggle("btn-danger-fill", danger);
      els.confirmDialogOk.classList.toggle("btn-primary", !danger);
      els.confirmDialogOk.disabled = false;
      els.confirmDialogCancel.disabled = false;
      if (typeof els.confirmDialog.showModal === "function") {
        els.confirmDialog.showModal();
      }
      els.confirmDialogCancel.focus();
    });
  }

  function finishConfirmDialog(confirmed) {
    if (typeof els.confirmDialog.close === "function") {
      els.confirmDialog.close();
    }
    if (confirmDialogResolve) {
      confirmDialogResolve(confirmed);
      confirmDialogResolve = null;
    }
  }

  function openRenameDialog({ defaultValue = "新对话" } = {}) {
    return new Promise((resolve) => {
      renameDialogResolve = resolve;
      els.renameDialogInput.value = defaultValue;
      if (typeof els.renameDialog.showModal === "function") {
        els.renameDialog.showModal();
      }
      els.renameDialogInput.focus();
      els.renameDialogInput.select();
    });
  }

  function finishRenameDialog(value) {
    if (typeof els.renameDialog.close === "function") {
      els.renameDialog.close();
    }
    if (renameDialogResolve) {
      renameDialogResolve(value);
      renameDialogResolve = null;
    }
  }

  function wireSessionDialogs() {
    els.confirmDialogOk.addEventListener("click", () => finishConfirmDialog(true));
    els.confirmDialogCancel.addEventListener("click", () => finishConfirmDialog(false));
    els.confirmDialog.addEventListener("cancel", (e) => {
      e.preventDefault();
      finishConfirmDialog(false);
    });
    els.confirmDialog.addEventListener("click", (e) => {
      if (e.target === els.confirmDialog) finishConfirmDialog(false);
    });

    els.renameDialogCancel.addEventListener("click", () => finishRenameDialog(null));
    els.renameDialog.addEventListener("cancel", (e) => {
      e.preventDefault();
      finishRenameDialog(null);
    });
    els.renameDialog.addEventListener("click", (e) => {
      if (e.target === els.renameDialog) finishRenameDialog(null);
    });
    els.renameDialogForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const title = els.renameDialogInput.value.trim();
      if (!title) return;
      finishRenameDialog(title);
    });
  }

  function showToast(message, { variant = "error" } = {}) {
    const toast = document.createElement("div");
    toast.className = `app-toast app-toast--${variant}`;
    toast.setAttribute("role", "alert");
    toast.textContent = message;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("visible"));
    setTimeout(() => {
      toast.classList.remove("visible");
      setTimeout(() => toast.remove(), 280);
    }, 4200);
  }

  async function fetchPaperPdf(paperId) {
    const res = await fetch(`/api/papers/${encodeURIComponent(paperId)}/pdf`, {
      headers: { Authorization: `Bearer ${TOKEN}` },
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      const err = new Error(data.error || data.message || res.statusText);
      err.status = res.status;
      throw err;
    }
    return res.blob();
  }

  function resetPdfSurface() {
    if (window.PaperPdfView) window.PaperPdfView.clear();
    if (els.paperPages) els.paperPages.innerHTML = "";
    if (els.paperDrawerToolbar) els.paperDrawerToolbar.hidden = true;
    if (els.paperDrawerStatus) els.paperDrawerStatus.hidden = true;
    if (els.paperDrawerPage) els.paperDrawerPage.textContent = "—";
  }

  function revealPaperDrawer() {
    const drawer = els.paperDrawer;
    if (!drawer) return;
    drawer.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    els.mainPane.classList.add("drawer-open");
    requestAnimationFrame(() => drawer.classList.add("is-open"));
  }

  function concealPaperDrawer() {
    const drawer = els.paperDrawer;
    if (!drawer || drawer.hidden) return;
    drawer.classList.remove("is-open");
    drawer.setAttribute("aria-hidden", "true");
    els.mainPane.classList.remove("drawer-open");
    const finish = () => {
      if (!drawer.classList.contains("is-open")) drawer.hidden = true;
    };
    const onEnd = (event) => {
      if (event.target !== drawer || event.propertyName !== "transform") return;
      drawer.removeEventListener("transitionend", onEnd);
      finish();
    };
    drawer.addEventListener("transitionend", onEnd);
    setTimeout(finish, 320);
  }

  function setSidebarTab(mode) {
    sidebarMode = mode === "papers" ? "papers" : "sessions";
    const sessionsOn = sidebarMode === "sessions";
    const pairs = [
      [els.tabSessions, els.panelSessions, sessionsOn],
      [els.tabPapers, els.panelPapers, !sessionsOn],
    ];
    pairs.forEach(([tab, panel, on]) => {
      if (tab) {
        tab.classList.toggle("active", on);
        tab.setAttribute("aria-selected", on ? "true" : "false");
        tab.tabIndex = on ? 0 : -1;
      }
      if (panel) {
        panel.classList.toggle("is-active", on);
        panel.hidden = !on;
      }
    });
  }

  function activateSidebarTab(btn) {
    if (!btn) return;
    const mode = btn.id === "tab-papers" ? "papers" : "sessions";
    setSidebarTab(mode);
    if (mode === "papers") {
      loadPapers().catch((err) => showToast((err && err.message) || "无法加载论文列表"));
    }
  }

  function bindSidebarTabs() {
    const tabList = document.querySelector(".sidebar-tabs");
    if (!tabList) return;
    tabList.addEventListener("click", (event) => {
      const btn = event.target.closest("button.sidebar-tab");
      if (!btn || !tabList.contains(btn)) return;
      activateSidebarTab(btn);
    });
    tabList.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight" && event.key !== "Home" && event.key !== "End") {
        return;
      }
      const tabs = [...tabList.querySelectorAll('[role="tab"]')];
      const current = tabs.indexOf(document.activeElement);
      if (current < 0) return;
      event.preventDefault();
      let next = current;
      if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (current - 1 + tabs.length) % tabs.length;
      else if (event.key === "Home") next = 0;
      else next = tabs.length - 1;
      tabs[next].focus();
      activateSidebarTab(tabs[next]);
    });
  }

  function paperDisplayTitle(paper) {
    if (paper.title) return paper.title;
    return paper.id;
  }

  function renderPaperList() {
    if (!els.paperList) return;
    els.paperList.innerHTML = "";
    if (!papersCatalog.length) {
      els.paperList.innerHTML =
        '<p class="session-item-meta" style="padding:8px">暂无论文条目</p>';
      return;
    }
    papersCatalog.forEach((paper) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "paper-item" + (paper.id === selectedPaperId ? " active" : "");
      btn.dataset.id = paper.id;
      const badgeClass = paper.has_pdf ? "ok" : "missing";
      const badgeText = paper.has_pdf ? "PDF" : "缺失";
      const sub =
        paper.title && paper.title !== paper.id
          ? `<span class="paper-item-title">${escapeHtml(paper.title)}</span>`
          : "";
      btn.innerHTML = `
        <span class="paper-badge ${badgeClass}">${badgeText}</span>
        <span class="paper-item-body">
          <span class="paper-item-id">${escapeHtml(paper.id)}</span>
          ${sub}
        </span>`;
      btn.addEventListener("click", () => openPaperPreview(paper));
      els.paperList.appendChild(btn);
    });
  }

  async function loadPapers() {
    try {
      const data = await api("/api/papers");
      papersCatalog = data.papers || [];
      renderPaperList();
    } catch (err) {
      if (!papersCatalog.length && els.paperList) {
        els.paperList.innerHTML =
          `<p class="paper-library-error">${escapeHtml((err && err.message) || "无法加载论文列表")}</p>`;
      }
      throw err;
    }
  }

  function closePaperPreview() {
    previewGen += 1;
    resetPdfSurface();
    selectedPaperId = null;
    if (els.paperDrawerEmpty) els.paperDrawerEmpty.hidden = true;
    concealPaperDrawer();
    renderPaperList();
    if (els.queryInput) els.queryInput.focus();
  }

  function showDrawerMessage(which, text) {
    if (els.paperDrawerEmpty) {
      els.paperDrawerEmpty.hidden = which !== "empty";
      if (which === "empty" && text) els.paperDrawerEmpty.textContent = text;
    }
    if (els.paperDrawerStatus) {
      els.paperDrawerStatus.hidden = which !== "status";
      if (which === "status" && text) els.paperDrawerStatus.textContent = text;
    }
  }

  async function openPaperPreview(paper) {
    const gen = ++previewGen;
    selectedPaperId = paper.id;
    renderPaperList();
    revealPaperDrawer();
    const label = paperDisplayTitle(paper);
    els.paperDrawerTitle.textContent = label;
    els.paperDrawerId.textContent = paper.id;
    els.btnInsertPaperQuery.disabled = false;
    resetPdfSurface();

    if (!paper.has_pdf) {
      showDrawerMessage("empty", "本地暂无 PDF，可先运行 download_pdfs.py。");
      return;
    }

    showDrawerMessage("status", "正在打开 PDF…");
    try {
      const blob = await fetchPaperPdf(paper.id);
      if (gen !== previewGen) return;
      const buffer = await blob.arrayBuffer();
      if (gen !== previewGen) return;
      if (!window.PaperPdfView) throw new Error("PDF 查看器未加载");
      await window.PaperPdfView.show(buffer, els.paperPages, {
        onChange(info) {
          if (!els.paperDrawerPage) return;
          const total = info.total || 0;
          els.paperDrawerPage.textContent = total ? `${info.page} / ${total}` : "—";
          if (els.btnPdfPrev) els.btnPdfPrev.disabled = info.page <= 1;
          if (els.btnPdfNext) els.btnPdfNext.disabled = !total || info.page >= total;
        },
      });
      if (gen !== previewGen) return;
      showDrawerMessage("none");
      if (els.paperDrawerToolbar) els.paperDrawerToolbar.hidden = false;
    } catch (e) {
      if (gen !== previewGen) return;
      resetPdfSurface();
      showDrawerMessage("empty", `无法加载 PDF：${e.message || e}`);
    }
  }

  function insertPaperIntoComposer(paperId) {
    const tag = `[${paperId}]`;
    const cur = els.queryInput.value.trim();
    if (!cur) {
      els.queryInput.value = `关于论文 ${tag}：`;
    } else if (!cur.includes(tag)) {
      const sep = cur.endsWith(" ") ? "" : " ";
      els.queryInput.value = `${cur}${sep}${tag} `;
    }
    setSidebarTab("sessions");
    els.queryInput.focus();
  }

  function loadTheme() {
    const saved = localStorage.getItem("paper-rag-theme") || "ink";
    document.documentElement.setAttribute("data-theme", saved);
    els.themeSelect.value = saved;
  }

  function setTheme(name) {
    document.documentElement.setAttribute("data-theme", name);
    localStorage.setItem("paper-rag-theme", name);
  }

  async function refreshHealth() {
    try {
      const h = await api("/api/health");
      const dot = els.healthDot;
      dot.classList.remove("ok", "warn");
      if (h.index_ok) {
        dot.classList.add("ok");
        els.healthText.textContent = `索引就绪 · ${h.generator_mode}${h.api_key_set ? "" : " (无 API key)"}`;
      } else {
        dot.classList.add("warn");
        els.healthText.textContent = "索引缺失 · 先运行 build_index.py";
      }
    } catch {
      els.healthDot.classList.add("warn");
      els.healthText.textContent = "无法连接服务";
    }
  }

  function renderSessionList(sessions) {
    els.sessionList.innerHTML = "";
    if (!sessions.length) {
      els.sessionList.innerHTML = '<p class="session-item-meta" style="padding:8px">暂无对话</p>';
      return;
    }
    sessions.forEach((s) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "session-item" + (s.id === currentSessionId ? " active" : "");
      btn.dataset.id = s.id;
      btn.innerHTML = `<span class="session-item-title">${escapeHtml(s.title)}</span>
        <span class="session-item-meta">${s.turn_count || 0} 轮</span>`;
      btn.addEventListener("click", () => switchSession(s.id));
      btn.addEventListener("contextmenu", (e) => showSessionContextMenu(e, s));
      els.sessionList.appendChild(btn);
    });
  }

  async function loadSessionList() {
    const data = await api("/api/sessions");
    renderSessionList(data.sessions || []);
  }

  async function switchSession(id) {
    if (id === currentSessionId && sessionDetail) return;
    els.mainPane.classList.add("switching");
    await new Promise((r) => setTimeout(r, 120));
    currentSessionId = id;
    updateSessionActionButtons();
    sessionDetail = await api(`/api/sessions/${encodeURIComponent(id)}`);
    els.mainTitle.textContent = sessionDetail.title || "新对话";
    renderMessages(sessionDetail.turns || []);
    await loadSessionList();
    els.mainPane.classList.remove("switching");
  }

  async function createNewSession() {
    const session = await api("/api/sessions", { method: "POST", body: "{}" });
    currentSessionId = session.id;
    updateSessionActionButtons();
    sessionDetail = session;
    els.mainTitle.textContent = session.title || "新对话";
    renderMessages([]);
    await loadSessionList();
    els.queryInput.focus();
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderAnswerMarkdown(bubble, text) {
    bubble.innerHTML = "";
    const body = document.createElement("div");
    body.className = "markdown-body";
    bubble.appendChild(body);
    if (window.PaperRagMarkdown) {
      window.PaperRagMarkdown.render(text, body);
    } else {
      body.textContent = text || "(无回答)";
    }
  }

  function ensureSessionContextMenu() {
    if (sessionContextMenu) return sessionContextMenu;
    const menu = document.createElement("div");
    menu.id = "session-context-menu";
    menu.className = "session-context-menu";
    menu.setAttribute("role", "menu");
    menu.hidden = true;
    menu.innerHTML = `
      <button type="button" data-action="rename" role="menuitem">重命名</button>
      <button type="button" data-action="archive" role="menuitem">归档</button>
      <button type="button" data-action="delete" class="danger" role="menuitem">删除</button>
    `;
    document.body.appendChild(menu);
    menu.addEventListener("click", (e) => {
      e.stopPropagation();
      const btn = e.target.closest("button[data-action]");
      if (!btn || !contextMenuSessionId) return;
      const action = btn.dataset.action;
      const id = contextMenuSessionId;
      const title = btn.dataset.sessionTitle || "";
      hideSessionContextMenu();
      if (action === "rename") renameSession(id, title);
      else if (action === "archive") archiveSession(id);
      else if (action === "delete") deleteSession(id);
    });
    document.addEventListener("click", (e) => {
      if (!sessionContextMenu || sessionContextMenu.hidden) return;
      if (!sessionContextMenu.contains(e.target)) hideSessionContextMenu();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") hideSessionContextMenu();
    });
    document.addEventListener(
      "scroll",
      () => {
        if (!sessionContextMenu?.hidden) hideSessionContextMenu();
      },
      true
    );
    sessionContextMenu = menu;
    return menu;
  }

  function hideSessionContextMenu() {
    if (sessionContextMenu) sessionContextMenu.hidden = true;
    contextMenuSessionId = null;
  }

  function showSessionContextMenu(e, session) {
    e.preventDefault();
    e.stopPropagation();
    const menu = ensureSessionContextMenu();
    contextMenuSessionId = session.id;
    menu.querySelectorAll("button[data-action]").forEach((btn) => {
      btn.dataset.sessionTitle = session.title || "";
    });
    menu.hidden = false;
    const pad = 8;
    let x = e.clientX;
    let y = e.clientY;
    menu.style.left = `${x}px`;
    menu.style.top = `${y}px`;
    const rect = menu.getBoundingClientRect();
    if (rect.right > window.innerWidth - pad) {
      x = Math.max(pad, window.innerWidth - rect.width - pad);
      menu.style.left = `${x}px`;
    }
    if (rect.bottom > window.innerHeight - pad) {
      y = Math.max(pad, window.innerHeight - rect.height - pad);
      menu.style.top = `${y}px`;
    }
  }

  async function renameSession(id, currentTitle) {
    if (sessionActionBusy || !id) return;
    hideSessionContextMenu();
    const next = await openRenameDialog({ defaultValue: currentTitle || "新对话" });
    if (next === null) return;
    const title = next.trim();
    if (!title || title === currentTitle) return;
    try {
      await api(`/api/sessions/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: JSON.stringify({ title }),
      });
      if (id === currentSessionId) {
        els.mainTitle.textContent = title;
        if (sessionDetail) sessionDetail.title = title;
      }
      await loadSessionList();
    } catch (e) {
      showToast(e.message || "重命名失败");
    }
  }

  async function navigateAfterCurrentSessionRemoved() {
    currentSessionId = null;
    sessionDetail = null;
    updateSessionActionButtons();
    const data = await api("/api/sessions");
    const sessions = data.sessions || [];
    renderSessionList(sessions);
    if (sessions.length) {
      await switchSession(sessions[0].id);
      return;
    }
    els.mainTitle.textContent = "新对话";
    renderMessages([]);
    await createNewSession();
  }

  async function archiveSession(id) {
    if (sessionActionBusy || !id) return;
    hideSessionContextMenu();
    const ok = await openConfirmDialog(ARCHIVE_CONFIRM);
    if (!ok) return;
    setSessionActionBusy(true);
    try {
      await api(`/api/sessions/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: JSON.stringify({ archived: true }),
      });
      if (id === currentSessionId) {
        await navigateAfterCurrentSessionRemoved();
      } else {
        await loadSessionList();
      }
    } catch (e) {
      showToast(e.message || "归档失败");
    } finally {
      setSessionActionBusy(false);
    }
  }

  async function deleteSession(id) {
    if (sessionActionBusy || !id) return;
    hideSessionContextMenu();
    const ok = await openConfirmDialog(DELETE_CONFIRM);
    if (!ok) return;
    setSessionActionBusy(true);
    try {
      await api(`/api/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
      if (id === currentSessionId) {
        await navigateAfterCurrentSessionRemoved();
      } else {
        await loadSessionList();
      }
    } catch (e) {
      showToast(e.message || "删除失败");
    } finally {
      setSessionActionBusy(false);
    }
  }

  function renderMessages(turns) {
    els.messages.innerHTML = "";
    if (!turns.length) {
      els.messages.innerHTML =
        '<p class="empty-state">输入问题开始检索论文库。<br>回答会附带页码级引用与 Agent 轨迹。</p>';
      return;
    }
    turns.forEach((turn, idx) => {
      appendTurnToDom(turn, { animate: false, skipUser: false });
    });
  }

  function appendUserBubble(text, { pending = false } = {}) {
    const wrap = document.createElement("div");
    wrap.className = "msg msg-user" + (pending ? " pending" : "");
    wrap.innerHTML = `<div class="msg-bubble">${escapeHtml(text)}</div>`;
    els.messages.appendChild(wrap);
    els.messages.scrollTop = els.messages.scrollHeight;
    return wrap;
  }

  function appendTurnToDom(turn, opts = {}) {
    const { animate = true, skipUser = false } = opts;
    const result = turn.result || {};
    if (!skipUser) {
      appendUserBubble(turn.query, { pending: false });
    }
    const assist = document.createElement("div");
    assist.className = "msg msg-assistant";
    assist.dataset.turnId = turn.id;

    const bubble = document.createElement("div");
    bubble.className = "msg-bubble";
    let answerSpan = null;
    if (animate) {
      answerSpan = document.createElement("span");
      answerSpan.className = "answer-typed";
      bubble.appendChild(answerSpan);
    }
    assist.appendChild(bubble);

    const actions = document.createElement("div");
    actions.className = "msg-actions";
    const gradeOk = result.grade_passed;
    actions.innerHTML = `
      <span class="msg-meta">generator: ${escapeHtml(result.generator || "stub")} · ${result.num_chunks || 0} chunks</span>
      <button type="button" class="btn btn-ghost btn-sm btn-detail">详情</button>
    `;
    assist.appendChild(actions);

    const chips = document.createElement("div");
    chips.className = "citation-chips";
    (result.citations || []).forEach((c, i) => {
      const chip = document.createElement("span");
      chip.className = "citation-chip";
      chip.style.animationDelay = `${i * 0.08}s`;
      chip.textContent = `${c.paper_id || "?"} p.${c.page ?? "?"} · ${c.chunk_id || ""}`;
      chips.appendChild(chip);
    });
    assist.appendChild(chips);

    els.messages.appendChild(assist);
    assist.querySelector(".btn-detail").addEventListener("click", () => openInspector(turn));

    const answerText = result.answer || "";
    if (animate && answerSpan) {
      revealAnswer(answerSpan, answerText, () => {
        renderAnswerMarkdown(bubble, answerText);
        requestAnimationFrame(() => chips.classList.add("revealed"));
      });
    } else {
      renderAnswerMarkdown(bubble, answerText);
      chips.classList.add("revealed");
    }

    els.messages.scrollTop = els.messages.scrollHeight;
    return assist;
  }

  function revealAnswer(el, text, onDone) {
    const chars = text.length;
    if (chars === 0) {
      el.textContent = "(无回答)";
      if (onDone) onDone();
      return;
    }
    const ms = Math.min(2400, Math.max(400, chars * 12));
    const start = performance.now();
    function tick(now) {
      const t = Math.min(1, (now - start) / ms);
      const n = Math.floor(t * chars);
      el.textContent = text.slice(0, n);
      if (t < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = text;
        if (onDone) onDone();
      }
    }
    requestAnimationFrame(tick);
  }

  function startProgress() {
    els.progressDock.hidden = false;
    els.composerForm.classList.add("busy");
    els.queryInput.disabled = true;
    els.btnSend.disabled = true;
    els.progressSteps.innerHTML = "";
    PIPELINE_STEPS.forEach((s) => {
      const li = document.createElement("li");
      li.className = "progress-step";
      li.dataset.key = s.key;
      li.textContent = s.label;
      els.progressSteps.appendChild(li);
    });
    progressIndex = 0;
    setProgressStep(0);
    progressTimer = setInterval(() => {
      if (progressIndex < PIPELINE_STEPS.length - 1) {
        progressIndex += 1;
        setProgressStep(progressIndex);
      }
    }, 900);
  }

  function setProgressStep(idx) {
    const steps = els.progressSteps.querySelectorAll(".progress-step");
    const labels = [
      "解析意图…",
      "混合检索与重排…",
      "评估检索质量…",
      "必要时改写查询…",
      "生成带引用回答…",
    ];
    els.progressLabel.textContent = labels[Math.min(idx, labels.length - 1)];
    steps.forEach((el, i) => {
      el.classList.remove("active", "done");
      if (i < idx) el.classList.add("done");
      else if (i === idx) el.classList.add("active");
    });
  }

  function stopProgress(success) {
    clearInterval(progressTimer);
    progressTimer = null;
    if (success) {
      els.progressSteps.querySelectorAll(".progress-step").forEach((el) => {
        el.classList.remove("active");
        el.classList.add("done");
      });
      els.progressLabel.textContent = "完成";
    }
    setTimeout(() => {
      els.progressDock.hidden = true;
    }, success ? 400 : 100);
    els.composerForm.classList.remove("busy");
    els.queryInput.disabled = false;
    els.btnSend.disabled = false;
  }

  async function submitQuery(query) {
    if (asking || !query.trim()) return;
    asking = true;
    if (!currentSessionId) {
      await createNewSession();
    }

    const pending = appendUserBubble(query, { pending: true });
    els.queryInput.value = "";
    startProgress();

    try {
      const data = await api("/api/ask", {
        method: "POST",
        body: JSON.stringify({ query, session_id: currentSessionId }),
      });
      pending.remove();
      sessionDetail = data.session;
      if (data.session?.title) els.mainTitle.textContent = data.session.title;
      const turn = data.turn;
      if (turn) {
        stagedRevealFromTrace(turn);
        const empty = els.messages.querySelector(".empty-state");
        if (empty) empty.remove();
        appendUserBubble(turn.query, { pending: false });
        appendTurnToDom(turn, { animate: true, skipUser: true });
      }
      stopProgress(true);
      await loadSessionList();
    } catch (e) {
      pending.classList.remove("pending");
      stopProgress(false);
      const err = document.createElement("div");
      err.className = "msg msg-assistant";
      err.innerHTML = `<div class="msg-bubble" style="border-color:var(--danger)">错误: ${escapeHtml(e.message || String(e))}</div>`;
      els.messages.appendChild(err);
    } finally {
      asking = false;
      els.queryInput.focus();
    }
  }

  function stagedRevealFromTrace(turn) {
    const trace = (turn.result && turn.result.trace) || [];
    const keys = new Set(trace.map((t) => t.event));
    let idx = 0;
    PIPELINE_STEPS.forEach((s, i) => {
      if (keys.has(s.key) || (s.key === "generate" && turn.result?.answer)) {
        idx = i;
      }
    });
    progressIndex = idx;
    setProgressStep(idx);
  }

  function openInspector(turn) {
    const r = turn.result || {};
    const gradeClass = r.grade_passed ? "pass" : "fail";
    const trace = r.trace || [];

    let timelineHtml = "";
    trace.forEach((item, i) => {
      const delay = i * 0.06;
      const detail = { ...item };
      delete detail.event;
      timelineHtml += `<li style="animation-delay:${delay}s">
        <span class="timeline-event">${escapeHtml(item.event || "?")}</span>
        <pre style="margin:4px 0 0;font-size:0.75rem;white-space:pre-wrap;color:var(--text-muted)">${escapeHtml(JSON.stringify(detail, null, 0))}</pre>
      </li>`;
    });

    let cites = "";
    (r.citations || []).forEach((c) => {
      cites += `<li>${escapeHtml(c.paper_id)} · page ${c.page} · ${escapeHtml(c.chunk_id || "")}</li>`;
    });

    els.inspectorBody.innerHTML = `
      <div class="inspector-section">
        <h3>查询</h3>
        <p>${escapeHtml(turn.query)}</p>
        <p style="color:var(--text-muted);font-size:0.82rem">Working: ${escapeHtml(r.working_query || "")}</p>
      </div>
      <div class="inspector-section">
        <h3>Grade</h3>
        <span class="grade-badge ${gradeClass}">${r.grade_passed ? "通过" : "未通过"}</span>
        <span style="margin-left:8px">${escapeHtml(r.grade_reason || "")}</span>
        <p style="margin:8px 0 0;font-size:0.82rem">Rewrite 迭代: ${r.iterations ?? 0}</p>
      </div>
      <div class="inspector-section">
        <h3>Trace</h3>
        <ul class="timeline">${timelineHtml || "<li>无轨迹</li>"}</ul>
      </div>
      <div class="inspector-section">
        <h3>Citations</h3>
        <ul class="citations-list">${cites || "<li>无引用</li>"}</ul>
      </div>
    `;
    if (typeof els.inspector.showModal === "function") {
      els.inspector.showModal();
    }
  }

  bindSidebarTabs();

  els.composerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitQuery(els.queryInput.value);
  });

  els.queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submitQuery(els.queryInput.value);
    }
  });

  els.btnNew.addEventListener("click", () => createNewSession());
  els.btnArchive.addEventListener("click", async () => {
    if (!currentSessionId) return;
    await archiveSession(currentSessionId);
  });

  els.btnDelete.addEventListener("click", async () => {
    if (!currentSessionId) return;
    await deleteSession(currentSessionId);
  });

  els.themeSelect.addEventListener("change", () => setTheme(els.themeSelect.value));
  if (els.btnClosePaperPreview) {
    els.btnClosePaperPreview.addEventListener("click", () => closePaperPreview());
  }
  if (els.btnInsertPaperQuery) {
    els.btnInsertPaperQuery.addEventListener("click", () => {
      if (!selectedPaperId) return;
      insertPaperIntoComposer(selectedPaperId);
    });
  }
  if (els.btnPdfPrev) {
    els.btnPdfPrev.addEventListener("click", () => window.PaperPdfView && window.PaperPdfView.go(-1));
  }
  if (els.btnPdfNext) {
    els.btnPdfNext.addEventListener("click", () => window.PaperPdfView && window.PaperPdfView.go(1));
  }
  if (els.btnPdfZoomIn) {
    els.btnPdfZoomIn.addEventListener("click", () => window.PaperPdfView && window.PaperPdfView.zoomBy(0.15));
  }
  if (els.btnPdfZoomOut) {
    els.btnPdfZoomOut.addEventListener("click", () => window.PaperPdfView && window.PaperPdfView.zoomBy(-0.15));
  }
  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!els.paperDrawer || els.paperDrawer.hidden) return;
    if (document.querySelector("dialog[open]")) return;
    event.preventDefault();
    closePaperPreview();
  });
  els.inspectorClose.addEventListener("click", () => els.inspector.close());
  els.inspector.addEventListener("click", (e) => {
    if (e.target === els.inspector) els.inspector.close();
  });

  async function init() {
    wireSessionDialogs();
    updateSessionActionButtons();
    loadTheme();
    refreshHealth();
    setInterval(refreshHealth, 45000);
    setSidebarTab("sessions");
    await loadSessionList();
    await loadPapers().catch((err) => showToast((err && err.message) || "无法加载论文列表"));
    const data = await api("/api/sessions");
    if (data.sessions && data.sessions.length) {
      await switchSession(data.sessions[0].id);
    } else {
      await createNewSession();
    }
  }

  init().catch((e) => {
    els.healthText.textContent = String(e.message || e);
  });
})();
