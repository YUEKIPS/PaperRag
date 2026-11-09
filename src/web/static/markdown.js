/**
 * Safe Markdown → DOM for assistant answers (marked lexer, no raw HTML execution).
 */
(function (global) {
  const markedLib = global.marked;
  if (!markedLib) {
    global.PaperRagMarkdown = {
      render(md, el) {
        const p = document.createElement("p");
        p.textContent = String(md || "");
        el.appendChild(p);
      },
    };
    return;
  }

  markedLib.setOptions({ gfm: true, breaks: false });

  function safeHref(href) {
    if (!href) return null;
    const trimmed = String(href).trim();
    if (/^\s*(javascript|data|vbscript):/i.test(trimmed)) return null;
    try {
      const u = new URL(trimmed, "https://invalid.example");
      if (u.protocol === "http:" || u.protocol === "https:") return u.href;
    } catch {
      /* ignore */
    }
    return null;
  }

  function appendInlines(parent, tokens) {
    if (!tokens || !tokens.length) return;
    tokens.forEach((tok) => {
      switch (tok.type) {
        case "text":
        case "escape":
          parent.appendChild(document.createTextNode(tok.text || ""));
          break;
        case "strong": {
          const el = document.createElement("strong");
          appendInlines(el, tok.tokens);
          parent.appendChild(el);
          break;
        }
        case "em": {
          const el = document.createElement("em");
          appendInlines(el, tok.tokens);
          parent.appendChild(el);
          break;
        }
        case "del": {
          const el = document.createElement("del");
          appendInlines(el, tok.tokens);
          parent.appendChild(el);
          break;
        }
        case "codespan": {
          const el = document.createElement("code");
          el.textContent = tok.text || "";
          parent.appendChild(el);
          break;
        }
        case "br":
          parent.appendChild(document.createElement("br"));
          break;
        case "link": {
          const href = safeHref(tok.href);
          if (href) {
            const a = document.createElement("a");
            a.href = href;
            a.rel = "noopener noreferrer";
            a.target = "_blank";
            appendInlines(a, tok.tokens);
            if (!a.textContent) a.textContent = tok.text || href;
            parent.appendChild(a);
          } else {
            appendInlines(parent, tok.tokens);
          }
          break;
        }
        case "image": {
          const alt = tok.text || tok.alt || "";
          if (alt) parent.appendChild(document.createTextNode(alt));
          break;
        }
        case "html":
          break;
        default:
          if (tok.text) parent.appendChild(document.createTextNode(tok.text));
          else if (tok.tokens) appendInlines(parent, tok.tokens);
          break;
      }
    });
  }

  function paragraphEl(tokens) {
    const p = document.createElement("p");
    appendInlines(p, tokens);
    return p;
  }

  function renderList(token) {
    const tag = token.ordered ? "ol" : "ul";
    const list = document.createElement(tag);
    if (token.ordered && token.start != null && token.start !== 1) {
      list.start = token.start;
    }
    (token.items || []).forEach((item) => {
      const li = document.createElement("li");
      const blocks = item.tokens || [];
      if (blocks.length === 1 && blocks[0].type === "paragraph") {
        appendInlines(li, blocks[0].tokens);
      } else {
        blocks.forEach((blk) => {
          const child = renderBlock(blk);
          if (child) li.appendChild(child);
        });
      }
      list.appendChild(li);
    });
    return list;
  }

  function renderTable(token) {
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    (token.header || []).forEach((cell) => {
      const th = document.createElement("th");
      appendInlines(th, cell.tokens);
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
    const tbody = document.createElement("tbody");
    (token.rows || []).forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((cell) => {
        const td = document.createElement("td");
        appendInlines(td, cell.tokens);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    const wrap = document.createElement("div");
    wrap.className = "markdown-table-wrap";
    wrap.appendChild(table);
    return wrap;
  }

  function renderCodeBlock(token) {
    const wrap = document.createElement("div");
    wrap.className = "code-block";
    const toolbar = document.createElement("div");
    toolbar.className = "code-block-toolbar";
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "code-copy-btn";
    btn.textContent = "复制";
    btn.dataset.copyText = token.text || "";
    toolbar.appendChild(btn);
    const pre = document.createElement("pre");
    const code = document.createElement("code");
    if (token.lang) code.dataset.lang = token.lang;
    code.textContent = token.text || "";
    pre.appendChild(code);
    wrap.appendChild(toolbar);
    wrap.appendChild(pre);
    return wrap;
  }

  function renderBlock(token) {
    switch (token.type) {
      case "space":
        return null;
      case "hr": {
        const hr = document.createElement("hr");
        return hr;
      }
      case "heading": {
        const level = Math.min(6, Math.max(1, token.depth || 1));
        const h = document.createElement(`h${level}`);
        appendInlines(h, token.tokens);
        return h;
      }
      case "paragraph":
        return paragraphEl(token.tokens);
      case "blockquote": {
        const el = document.createElement("blockquote");
        (token.tokens || []).forEach((inner) => {
          const child = renderBlock(inner);
          if (child) el.appendChild(child);
        });
        return el;
      }
      case "code":
        return renderCodeBlock(token);
      case "list":
        return renderList(token);
      case "table":
        return renderTable(token);
      case "html":
        return null;
      case "text":
        return paragraphEl([{ type: "text", text: token.text }]);
      default:
        return null;
    }
  }

  function bindCopyButtons(root) {
    root.querySelectorAll(".code-copy-btn").forEach((btn) => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", async () => {
        const text = btn.dataset.copyText || "";
        try {
          await navigator.clipboard.writeText(text);
          const prev = btn.textContent;
          btn.textContent = "已复制";
          setTimeout(() => {
            btn.textContent = prev;
          }, 1200);
        } catch {
          btn.textContent = "失败";
        }
      });
    });
  }

  function render(markdown, container) {
    container.innerHTML = "";
    const src = String(markdown ?? "").trim();
    if (!src) {
      const p = document.createElement("p");
      p.textContent = "(无回答)";
      container.appendChild(p);
      return;
    }
    const tokens = markedLib.lexer(src);
    tokens.forEach((t) => {
      const el = renderBlock(t);
      if (el) container.appendChild(el);
    });
    bindCopyButtons(container);
  }

  global.PaperRagMarkdown = { render, bindCopyButtons };
})(typeof window !== "undefined" ? window : globalThis);
