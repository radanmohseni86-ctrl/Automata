import re
from pathlib import Path

PERSIAN = "\u0600-\u06ff"
ZWNJ = "\u200c"

NO_LINK = {
    "حالت", "ورودی", "خروجی", "نماد", "طول", "اندازه", "زمان", "جمله", "نتیجه", "رد", "خالی",
    "بند", "دور", "جدول", "مجاز", "پایه", "فصل", "تعریف", "معنی", "مجموعه", "رابطه", "تشخیص",
    "تولید", "توصیف", "مسیر", "قطعی", "بسته", "تعریف", "تابع",
}

SKIP_TAGS = {"script", "style", "svg", "code", "a", "bdi", "h1", "h2", "h3", "h4", "button", "summary",
             "title", "head", "figure", "table"}
SKIP_CLASS = {"katex", "math-display", "term", "term-en", "box-title", "lead", "subtitle", "chip", "pager",
              "toc", "side-toc", "topbar", "site-foot", "kicker", "hlink", "xref", "tn", "num"}
VOID = {"br", "img", "hr", "meta", "link", "input", "path", "line", "circle", "rect", "use", "wbr"}
BLOCK_RESET = {"p", "li", "td", "th", "div"}


def load_terms(glossary_tex):
    text = Path(glossary_tex).read_text(encoding="utf-8")
    first = text.split(r"\section*{انگلیسی به فارسی}")[0]
    rows = re.findall(r"\\gterm\{([^{}]*)\}\{([^{}]*)\}", first)
    terms = []
    for i, (fa, en) in enumerate(rows, start=1):
        terms.append((fa.strip(), en.replace("\\&", "&").strip(), f"g{i}"))
    return terms


SUFFIX = f"(?:{ZWNJ}(?:ها|های|هایی|ای))?"


def term_pattern(fa):
    words = fa.split(" ")
    parts = []
    for k, w in enumerate(words):
        p = re.escape(w)
        if k == 0 or k == len(words) - 1:
            p += SUFFIX
        parts.append(p)
    return " ".join(parts)


class Linker:
    def __init__(self, glossary_tex):
        terms = [t for t in load_terms(glossary_tex) if "$" not in t[0] and t[0] not in NO_LINK
                 and re.search(f"[{PERSIAN}]", t[0])]
        terms.sort(key=lambda t: -len(t[0]))
        self.info = {}
        pats = []
        for i, (fa, en, gid) in enumerate(terms):
            name = f"t{i}"
            self.info[name] = (fa, en, gid)
            pats.append(f"(?P<{name}>{term_pattern(fa)})")
        self.rx = re.compile(f"(?<![{PERSIAN}{ZWNJ}])(?:" + "|".join(pats) + f")(?![{PERSIAN}{ZWNJ}])")

    @staticmethod
    def esc(s):
        return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

    def link_text(self, text, seen):
        def rep(m):
            name = m.lastgroup
            fa, en, gid = self.info[name]
            if fa in seen:
                return m.group(0)
            seen.add(fa)
            return (f'<span class="gl" tabindex="0" role="button" title="{self.esc(en)}" '
                    f'data-en="{self.esc(en)}" data-g="{gid}">{m.group(0)}</span>')
        return self.rx.sub(rep, text)

    def annotate(self, html):
        start = html.find('<main class="content"')
        end = html.find("</main>")
        if start < 0 or end < 0:
            return html
        head, body, tail = html[:start], html[start:end], html[end:]
        out = []
        stack = []
        seen = set()
        for tok in re.split(r"(<[^>]+>)", body):
            if not tok:
                continue
            if tok.startswith("<"):
                m = re.match(r"<(/?)([a-zA-Z0-9]+)([^>]*)>", tok)
                if m:
                    closing, name, rest = m.group(1) == "/", m.group(2).lower(), m.group(3)
                    if closing:
                        for k in range(len(stack) - 1, -1, -1):
                            if stack[k][0] == name:
                                del stack[k:]
                                break
                    elif name not in VOID and not rest.rstrip().endswith("/"):
                        cls = set()
                        cm = re.search(r'class="([^"]*)"', rest)
                        if cm:
                            cls = set(cm.group(1).split())
                        skip = name in SKIP_TAGS or bool(cls & SKIP_CLASS)
                        stack.append((name, skip))
                        if name in BLOCK_RESET:
                            seen = set()
                out.append(tok)
                continue
            if any(s for _, s in stack):
                out.append(tok)
            else:
                out.append(self.link_text(tok, seen))
        return head + "".join(out) + tail
