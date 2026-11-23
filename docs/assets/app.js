(function () {
  var root = document.documentElement;
  var btn = document.getElementById("theme-toggle");

  function currentTheme() {
    var t = root.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }

  function label() {
    if (btn) btn.textContent = currentTheme() === "dark" ? "تم روشن" : "تم تاریک";
  }

  if (btn) {
    label();
    btn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("jz-theme", next); } catch (e) {}
      label();
    });
  }

  var toc = document.querySelector(".side-toc");
  if (toc && window.matchMedia && window.matchMedia("(max-width: 1000px)").matches) {
    toc.removeAttribute("open");
  }

  var links = toc ? Array.prototype.slice.call(toc.querySelectorAll("a[href^='#']")) : [];
  if (links.length && "IntersectionObserver" in window) {
    var map = {};
    links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var heads = Object.keys(map).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          links.forEach(function (a) { a.classList.remove("active"); });
          var a = map[en.target.id];
          if (a) a.classList.add("active");
        }
      });
    }, { rootMargin: "-15% 0px -75% 0px" });
    heads.forEach(function (h) { obs.observe(h); });
  }
})();

(function () {
  var terms = document.querySelectorAll(".gl");
  if (!terms.length) return;
  var tip = document.createElement("div");
  tip.className = "gl-tip";
  tip.setAttribute("role", "tooltip");
  tip.hidden = true;
  document.body.appendChild(tip);
  var current = null;
  var pinned = false;

  terms.forEach(function (el) {
    el.setAttribute("aria-label", el.textContent + ": " + el.getAttribute("data-en"));
    el.removeAttribute("title");
  });

  function show(el, pin) {
    current = el;
    pinned = !!pin;
    var en = el.getAttribute("data-en");
    var g = el.getAttribute("data-g");
    tip.textContent = "";
    var t = document.createElement("span");
    t.className = "gl-en";
    t.setAttribute("dir", "ltr");
    t.setAttribute("lang", "en");
    t.textContent = en;
    tip.appendChild(t);
    if (pin) {
      var a = document.createElement("a");
      a.href = "glossary.html#" + g;
      a.textContent = "واژه‌نامه";
      a.className = "gl-more";
      tip.appendChild(a);
    }
    tip.hidden = false;
    var r = el.getBoundingClientRect();
    var tw = tip.offsetWidth, th = tip.offsetHeight;
    var left = r.left + r.width / 2 - tw / 2;
    left = Math.max(8, Math.min(left, document.documentElement.clientWidth - tw - 8));
    var top = r.top - th - 8;
    if (top < 8) top = r.bottom + 8;
    tip.style.left = left + window.scrollX + "px";
    tip.style.top = top + window.scrollY + "px";
  }

  function hide() {
    tip.hidden = true;
    current = null;
    pinned = false;
  }

  document.addEventListener("mouseover", function (e) {
    var el = e.target.closest && e.target.closest(".gl");
    if (el && !pinned) show(el, false);
  });
  document.addEventListener("mouseout", function (e) {
    var el = e.target.closest && e.target.closest(".gl");
    if (el && !pinned) hide();
  });
  document.addEventListener("click", function (e) {
    var el = e.target.closest && e.target.closest(".gl");
    if (el) {
      if (pinned && current === el) hide(); else show(el, true);
      return;
    }
    if (!(e.target.closest && e.target.closest(".gl-tip"))) hide();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") hide();
    if ((e.key === "Enter" || e.key === " ") && e.target.classList && e.target.classList.contains("gl")) {
      e.preventDefault();
      show(e.target, true);
    }
  });
  window.addEventListener("scroll", function () { if (!pinned) hide(); }, { passive: true });
})();
