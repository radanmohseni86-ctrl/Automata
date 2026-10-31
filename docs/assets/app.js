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
