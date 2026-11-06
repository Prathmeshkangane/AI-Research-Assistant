/* ResearchAI front-end helpers. No dependencies. */
(function () {
  "use strict";

  /* ---- 1. tiny, safe Markdown renderer (builds DOM nodes, never uses innerHTML) ---- */
  function inline(parent, text, cite) {
    var re = /(\*\*[^*\n]+\*\*|`[^`\n]+`|\[\d+\])/g, last = 0, m;
    while ((m = re.exec(text))) {
      if (m.index > last) parent.appendChild(document.createTextNode(text.slice(last, m.index)));
      var tok = m[0], el;
      if (tok.startsWith("**")) { el = document.createElement("strong"); el.textContent = tok.slice(2, -2); }
      else if (tok[0] === "`") { el = document.createElement("code"); el.textContent = tok.slice(1, -1); }
      else if (cite) {
        var n = tok.slice(1, -1);
        el = document.createElement("a"); el.className = "cite"; el.href = "#src-" + n; el.textContent = n;
        el.setAttribute("aria-label", "Source " + n);
      } else { el = document.createTextNode(tok); }
      parent.appendChild(el); last = m.index + tok.length;
    }
    if (last < text.length) parent.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderMarkdown(box) {
    var cite = box.hasAttribute("data-cite");
    var lines = box.textContent.replace(/\r/g, "").split("\n");
    var frag = document.createDocumentFragment(), para = [], list = null, listType = null;
    function flushPara() {
      if (!para.length) return;
      var p = document.createElement("p"); inline(p, para.join(" "), cite); frag.appendChild(p); para = [];
    }
    function flushList() { if (list) { frag.appendChild(list); list = null; listType = null; } }
    lines.forEach(function (raw) {
      var line = raw.trimEnd(), h = line.match(/^\s*(#{1,4})\s+(.*)$/),
          ul = line.match(/^\s*[-*•]\s+(.*)$/), ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
      if (!line.trim()) { flushPara(); flushList(); return; }
      if (h) { flushPara(); flushList(); var hx = document.createElement(h[1].length > 2 ? "h4" : "h3"); inline(hx, h[2], false); frag.appendChild(hx); return; }
      if (ul || ol) {
        flushPara(); var type = ul ? "ul" : "ol";
        if (listType !== type) { flushList(); list = document.createElement(type); listType = type; }
        var li = document.createElement("li"); inline(li, (ul || ol)[1], cite); list.appendChild(li); return;
      }
      flushList(); para.push(line.trim());
    });
    flushPara(); flushList();
    box.textContent = ""; box.appendChild(frag); box.classList.add("rendered");
  }
  document.querySelectorAll(".md[data-md]").forEach(renderMarkdown);

  /* ---- 2. citation click -> highlight the matching source ---- */
  document.addEventListener("click", function (e) {
    var a = e.target.closest("a.cite");
    if (!a) return;
    var t = document.querySelector(a.getAttribute("href"));
    if (!t) return;
    e.preventDefault(); t.scrollIntoView({ behavior: "smooth", block: "center" });
    t.classList.add("hl"); setTimeout(function () { t.classList.remove("hl"); }, 1600);
  });

  /* ---- 3. keyboard shortcut: "/" focuses the search / question box ---- */
  document.addEventListener("keydown", function (e) {
    var tag = (document.activeElement && document.activeElement.tagName) || "";
    if (e.key === "/" && !/INPUT|TEXTAREA|SELECT/.test(tag)) {
      var box = document.querySelector("[data-focus]");
      if (box) { e.preventDefault(); box.focus(); box.select && box.select(); }
    }
  });

  /* ---- 4. buttons that show progress while a slow request (AI call) runs ---- */
  document.querySelectorAll("form[data-loading]").forEach(function (f) {
    f.addEventListener("submit", function () {
      var b = f.querySelector("button[type=submit]");
      if (!b || b.disabled) return;
      b.dataset.label = b.textContent; b.disabled = true;
      b.innerHTML = '<span class="spinner"></span> ' + f.getAttribute("data-loading");
    });
  });
  window.addEventListener("pageshow", function () {     // back button: undo the spinner
    document.querySelectorAll("form[data-loading] button[type=submit]").forEach(function (b) {
      if (b.dataset.label) { b.textContent = b.dataset.label; b.disabled = false; }
    });
  });

  /* ---- 5. example chips fill the input ---- */
  document.querySelectorAll("[data-fill]").forEach(function (c) {
    c.addEventListener("click", function () {
      var box = document.querySelector("[data-focus]"); if (!box) return;
      box.value = c.getAttribute("data-fill"); box.focus();
    });
  });

  /* ---- 6. copy button ---- */
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var src = document.querySelector(b.getAttribute("data-copy")); if (!src) return;
      navigator.clipboard.writeText(src.innerText).then(function () {
        var old = b.textContent; b.textContent = "Copied"; setTimeout(function () { b.textContent = old; }, 1400);
      });
    });
  });
})();
