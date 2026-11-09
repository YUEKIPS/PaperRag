(function () {
  const tokenMeta = document.querySelector('meta[name="session-token"]');
  const token = tokenMeta ? tokenMeta.getAttribute("content") : "";

  const healthEl = document.getElementById("health");
  const messagesEl = document.getElementById("messages");
  const citationsEl = document.getElementById("citations");
  const citationsEmpty = document.getElementById("citations-empty");
  const gradeMeta = document.getElementById("grade-meta");
  const traceList = document.getElementById("trace-list");
  const queryInput = document.getElementById("query-input");
  const askBtn = document.getElementById("ask-btn");
  const loadingEl = document.getElementById("loading");

  function apiHeaders() {
    return {
      "Content-Type": "application/json",
      "X-Session-Token": token,
    };
  }

  function setBusy(busy) {
    askBtn.disabled = busy;
    queryInput.disabled = busy;
    loadingEl.classList.toggle("hidden", !busy);
  }

  function appendMessage(role, text) {
    const div = document.createElement("div");
    div.className = "msg " + role;
    const label = document.createElement("div");
    label.className = "role";
    label.textContent = role === "user" ? "你" : "助手";
    const body = document.createElement("div");
    body.textContent = text;
    div.appendChild(label);
    div.appendChild(body);
    messagesEl.appendChild(div);
    div.scrollIntoView({ behavior: "smooth", block: "end" });
  }

  function renderCitations(list) {
    citationsEl.innerHTML = "";
    if (!list || list.length === 0) {
      citationsEmpty.classList.remove("hidden");
      return;
    }
    citationsEmpty.classList.add("hidden");
    list.forEach((c) => {
      const li = document.createElement("li");
      const paper = c.paper_id ?? c.paper ?? "?";
      const page = c.page ?? "?";
      const chunk = c.chunk_id ?? c.chunk ?? "";
      li.textContent = `${paper} · 第 ${page} 页 · ${chunk}`;
      citationsEl.appendChild(li);
    });
  }

  function renderGradeMeta(result) {
    gradeMeta.innerHTML = "";
    const rows = [
      ["原始问题", result.query],
      ["Working query", result.working_query],
      [
        "Grade",
        result.grade_passed ? "通过" : "未通过",
      ],
      ["原因", result.grade_reason || "—"],
      ["Rewrite 次数", String(result.iterations ?? 0)],
      ["Generator", result.generator || "—"],
      ["检索 chunks", String(result.num_chunks ?? 0)],
    ];
    rows.forEach(([k, v]) => {
      const dt = document.createElement("dt");
      dt.textContent = k;
      const dd = document.createElement("dd");
      if (k === "Grade") {
        dd.className = result.grade_passed ? "grade-pass" : "grade-fail";
      }
      dd.textContent = v;
      gradeMeta.appendChild(dt);
      gradeMeta.appendChild(dd);
    });
  }

  function renderTrace(trace) {
    traceList.innerHTML = "";
    if (!trace || !trace.length) {
      const li = document.createElement("li");
      li.textContent = "（无 trace 事件）";
      traceList.appendChild(li);
      return;
    }
    trace.forEach((ev) => {
      const li = document.createElement("li");
      const node = ev.event || ev.node || ev.step || "event";
      const rest = { ...ev };
      delete rest.event;
      delete rest.node;
      const detail =
        Object.keys(rest).length === 0
          ? ""
          : typeof rest === "object"
            ? JSON.stringify(rest)
            : String(rest);
      li.textContent = detail ? `${node}: ${detail}` : node;
      traceList.appendChild(li);
    });
  }

  async function refreshHealth() {
    try {
      const res = await fetch("/api/health", { headers: apiHeaders() });
      const data = await res.json();
      if (!res.ok) {
        healthEl.textContent = data.error || "健康检查失败";
        healthEl.className = "health warn";
        return;
      }
      const parts = [];
      parts.push(data.index_present ? "索引：已就绪" : "索引：未构建（请先 build_index）");
      parts.push(`生成器：${data.generator_mode}`);
      parts.push(data.llm_mode_hint);
      healthEl.textContent = parts.join(" · ");
      healthEl.className = "health " + (data.index_present ? "ok" : "warn");
    } catch (err) {
      healthEl.textContent = "无法连接 API：" + err.message;
      healthEl.className = "health warn";
    }
  }

  async function ask() {
    const query = queryInput.value.trim();
    if (!query) return;

    setBusy(true);
    appendMessage("user", query);
    queryInput.value = "";

    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: apiHeaders(),
        body: JSON.stringify({ query }),
      });
      const data = await res.json();
      if (!res.ok || !data.ok) {
        const msg = data.error || "请求失败";
        appendMessage("assistant", msg);
        return;
      }
      const result = data.result;
      appendMessage("assistant", result.answer || "（无回答文本）");
      renderCitations(result.citations);
      renderGradeMeta(result);
      renderTrace(result.trace);
      document.getElementById("trace-panel").open = true;
    } catch (err) {
      appendMessage("assistant", "网络错误：" + err.message);
    } finally {
      setBusy(false);
    }
  }

  askBtn.addEventListener("click", ask);
  queryInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      ask();
    }
  });

  refreshHealth();
})();
