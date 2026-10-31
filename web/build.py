#!/usr/bin/env python3
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
WEB = ROOT / "web"
BUILD = WEB / "build"

SITE_TITLE = "جزوه اتوماتا"
SITE_SUBTITLE = "نظریه زبان‌ها و ماشین‌ها"
REPO_URL = "https://github.com/radanmohseni86-ctrl/Automata"
PDF_URL = "https://github.com/radanmohseni86-ctrl/Automata/raw/main/Jozve-Automata.pdf"
GALLERY_URL = "https://radanmohseni86-ctrl.github.io/"

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
ORDINALS = ["اول", "دوم", "سوم", "چهارم", "پنجم", "ششم", "هفتم", "هشتم"]


def fa(s):
    return s.translate(FA_DIGITS)


def esc(s):
    return html.escape(s, quote=False)


CMD_ARGS = {
    "textbf": 1, "emph": 1, "textcolor": 2, "term": 2, "lr": 1, "rl": 1, "en": 1,
    "ref": 1, "label": 1, "chapter": 1, "section": 1, "subsection": 1, "subsubsection": 1,
    "textmd": 1, "addcontentsline": 3, "textsc": 1, "part": 1, "input": 1, "hspace": 1,
    "vspace": 1, "texttt": 1, "url": 1, "href": 2, "underline": 1, "textit": 1, "mbox": 1,
    "gterm": 2, "fbox": 1, "renewcommand": 2, "setlength": 2, "newcommand": 2, "arraystretch": 0,
}
CMD_OPT = {"item", "chapter", "section"}
ENV_ARGS = {"algo": 2, "tabular": 1, "minipage": 1, "multicols": 1}
RAW_ENVS = {"automaton", "ltrfig", "align*", "align", "equation*", "tikzpicture", "tabular", "array"}
MATH_ENVS = {"align*", "align", "equation*"}
SIMPLE_SYMBOLS = {
    "%": "%", "&": "&", "#": "#", "_": "_", "{": "{", "}": "}", "$": "$",
    ",": "\u2009", " ": " ", "-": "", ";": " ", ":": " ", "!": "",
}
WORD_SYMBOLS = {
    "ldots": "…", "dots": "…", "textbackslash": "\\", "quad": "\u2003", "qquad": "\u2003\u2003",
    "LaTeX": "LaTeX", "TeX": "TeX", "textvisiblespace": "␣",
}
IGNORED = {
    "small", "normalsize", "large", "Large", "LARGE", "huge", "Huge", "footnotesize", "scriptsize",
    "tiny", "noindent", "smallskip", "medskip", "bigskip", "centering", "nobreak", "tableofcontents",
    "newpage", "clearpage", "bfseries", "mdseries", "normalfont", "selectfont", "relax", "qedhere",
    "frontmatter", "mainmatter", "backmatter", "toprule", "midrule", "bottomrule", "hline",
}
BOX_KIND = {
    "definition": ("تعریف", "def"), "theorem": ("قضیه", "thm"), "lemma": ("لم", "lem"),
    "corollary": ("نتیجه", "cor"), "example": ("مثال", "ex"),
}
COLOR_CLASS = {
    "jzMain": "c-main", "jzAccent": "c-accent", "warnFrame": "c-bad", "exFrame": "c-good",
    "defFrame": "c-def", "thmFrame": "c-thm", "noteFrame": "c-note", "proofFrame": "c-muted",
}
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")


class TexError(Exception):
    pass


class Parser:
    def __init__(self, s, where=""):
        self.s = s
        self.i = 0
        self.where = where

    def err(self, msg):
        line = self.s.count("\n", 0, self.i) + 1
        raise TexError(f"{self.where}:{line}: {msg}")

    def peek(self, k=0):
        j = self.i + k
        return self.s[j] if j < len(self.s) else ""

    def skip_ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\n":
            self.i += 1

    def read_balanced(self, open_ch, close_ch):
        if self.peek() != open_ch:
            self.err(f"expected {open_ch}")
        depth = 0
        start = self.i + 1
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return self.s[start:self.i - 1]
            self.i += 1
        self.err(f"unbalanced {open_ch}")

    def read_opt(self):
        save = self.i
        while self.peek() in " \t":
            self.i += 1
        if self.peek() == "[":
            return self.read_balanced("[", "]")
        self.i = save
        return None

    def read_arg(self):
        save = self.i
        self.skip_ws()
        if self.peek() != "{":
            self.i = save
            self.err("expected {")
        return self.read_balanced("{", "}")

    def read_name(self):
        j = self.i
        while j < len(self.s) and self.s[j].isalpha():
            j += 1
        name = self.s[self.i:j]
        self.i = j
        return name

    def raw_until_end(self, name):
        pat = re.compile(r"\\(begin|end)\{" + re.escape(name) + r"\}")
        depth = 1
        pos = self.i
        while True:
            m = pat.search(self.s, pos)
            if not m:
                self.err(f"missing \\end{{{name}}}")
            if m.group(1) == "begin":
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    body = self.s[self.i:m.start()]
                    self.i = m.end()
                    return body
            pos = m.end()

    def read_inline_math(self):
        start = self.i
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "\\":
                self.i += 2
                continue
            if c == "{":
                self.read_balanced("{", "}")
                continue
            if c == "$":
                body = self.s[start:self.i]
                self.i += 1
                return body
            self.i += 1
        self.err("unterminated $")

    def parse(self, end_env=None, end_brace=False):
        nodes = []
        buf = []

        def flush():
            if buf:
                nodes.append(("text", "".join(buf)))
                buf.clear()

        while self.i < len(self.s):
            c = self.s[self.i]
            if c == "%":
                nl = self.s.find("\n", self.i)
                self.i = len(self.s) if nl < 0 else nl + 1
                continue
            if c == "}":
                if end_brace:
                    self.i += 1
                    flush()
                    return nodes
                self.err("unexpected }")
            if c == "{":
                self.i += 1
                flush()
                nodes.append(("group", self.parse(end_brace=True)))
                continue
            if c == "$":
                self.i += 1
                flush()
                nodes.append(("math", self.read_inline_math(), False))
                continue
            if c == "~":
                buf.append("\u00a0")
                self.i += 1
                continue
            if c == "\n":
                m = re.compile(r"\n[ \t]*\n\s*").match(self.s, self.i)
                if m:
                    flush()
                    nodes.append(("par",))
                    self.i = m.end()
                    continue
                buf.append(" ")
                self.i += 1
                continue
            if c != "\\":
                buf.append(c)
                self.i += 1
                continue
            nxt = self.peek(1)
            if nxt == "\\":
                self.i += 2
                flush()
                self.read_opt()
                nodes.append(("nl",))
                continue
            if nxt == "[":
                self.i += 2
                end = self.s.find("\\]", self.i)
                if end < 0:
                    self.err("unterminated \\[")
                flush()
                nodes.append(("math", self.s[self.i:end], True))
                self.i = end + 2
                continue
            if not nxt.isalpha():
                self.i += 2
                buf.append(SIMPLE_SYMBOLS.get(nxt, nxt))
                continue
            self.i += 1
            name = self.read_name()
            star = False
            if self.peek() == "*":
                star = True
                self.i += 1
            if name == "begin":
                env = self.read_arg()
                flush()
                nodes.append(self.parse_env(env))
                continue
            if name == "end":
                env = self.read_arg()
                if env != end_env:
                    self.err(f"unexpected \\end{{{env}}}")
                flush()
                return nodes
            if name in WORD_SYMBOLS:
                buf.append(WORD_SYMBOLS[name])
                continue
            flush()
            opt = self.read_opt() if name in CMD_OPT else None
            nargs = CMD_ARGS.get(name, 0)
            args = []
            for _ in range(nargs):
                raw = self.read_arg()
                if name in ("label", "ref", "input", "url", "hspace", "vspace") or (name == "textcolor" and not args):
                    args.append(raw)
                else:
                    args.append(Parser(raw, self.where).parse_all())
            nodes.append(("cmd", name, star, opt, args))
            if nargs == 0 and name not in ("item",) and self.peek() == " ":
                self.i += 1
        if end_env:
            self.err(f"missing \\end{{{end_env}}}")
        if end_brace:
            self.err("missing }")
        flush()
        return nodes

    def parse_all(self):
        return self.parse()

    def parse_env(self, env):
        if env in RAW_ENVS:
            opt = None
            args = []
            if env == "automaton":
                opt = self.read_opt()
            if env in ("tabular", "array"):
                args.append(self.read_arg())
            body = self.raw_until_end(env)
            if env in MATH_ENVS:
                return ("math", f"\\begin{{{env}}}{body}\\end{{{env}}}", True)
            return ("env", env, opt, args, body)
        opt = self.read_opt()
        args = [self.read_arg() for _ in range(ENV_ARGS.get(env, 0))]
        body = self.parse(end_env=env)
        return ("env", env, opt, args, body)


def split_top(s, sep):
    parts = []
    depth = 0
    cur = []
    i = 0
    in_math = False
    while i < len(s):
        c = s[i]
        if c == "\\":
            if s.startswith(sep, i) and depth == 0 and not in_math:
                parts.append("".join(cur))
                cur = []
                i += len(sep)
                continue
            cur.append(s[i:i + 2])
            i += 2
            continue
        if c == "$":
            in_math = not in_math
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if s.startswith(sep, i) and depth == 0 and not in_math:
            parts.append("".join(cur))
            cur = []
            i += len(sep)
            continue
        cur.append(c)
        i += 1
    parts.append("".join(cur))
    return parts


class Site:
    def __init__(self):
        self.labels = {}
        self.math = []
        self.figures = []
        self.chapters = []
        self.parts = []
        self.current = None

    def add_math(self, tex, display):
        self.math.append((tex, display))
        return f"\x00M{len(self.math) - 1}\x00"


def prep_math(tex):
    tex = re.sub(r"\\text\{\s*\\rl\{", r"\\text{\\rl{", tex)
    out = []
    i = 0
    while i < len(tex):
        if tex.startswith("\\text{", i):
            j = i + len("\\text")
            p = Parser(tex, "math")
            p.i = j
            inner = p.read_balanced("{", "}")
            inner2 = re.sub(r"\\(rl|lr)\{", "{", inner)
            inner2 = prep_math_inner(inner2)
            if ARABIC_RE.search(inner2):
                out.append("\\htmlClass{rtl}{\\text{" + inner2 + "}}")
            else:
                out.append("\\text{" + inner2 + "}")
            i = p.i
            continue
        out.append(tex[i])
        i += 1
    tex = "".join(out)
    tex = re.sub(r"\\(lr|rl|en)\{", "{", tex)
    return tex


def prep_math_inner(s):
    return s


class Renderer:
    def __init__(self, site, chap):
        self.site = site
        self.chap = chap

    def inline(self, nodes, ltr=False):
        out = []
        for n in nodes:
            out.append(self.inline_node(n, ltr))
        return "".join(out)

    def text(self, s, ltr):
        s = re.sub(r"\s+", " ", s)
        s = s.replace("---", "—").replace("--", "–")
        s = esc(s)
        return s if ltr else fa(s)

    def inline_node(self, n, ltr):
        kind = n[0]
        if kind == "text":
            return self.text(n[1], ltr)
        if kind == "group":
            return self.inline(n[1], ltr)
        if kind == "math":
            if n[2]:
                return self.display_math(n[1])
            return self.site.add_math(prep_math(n[1]), False)
        if kind == "nl":
            return "<br>"
        if kind == "par":
            return " "
        if kind == "cmd":
            return self.cmd(n, ltr)
        if kind == "env":
            return self.block_env(n)
        return ""

    def display_math(self, tex):
        return '<div class="math-display">' + self.site.add_math(prep_math(tex), True) + "</div>"

    def cmd(self, n, ltr):
        _, name, star, opt, args = n
        if name in ("textbf", "emph"):
            return "<strong>" + self.inline(args[0], ltr) + "</strong>"
        if name == "textit":
            return "<em>" + self.inline(args[0], ltr) + "</em>"
        if name == "textmd":
            return '<span class="md">' + self.inline(args[0], ltr) + "</span>"
        if name == "textcolor":
            cls = COLOR_CLASS.get(args[0].split("!")[0], "c-main")
            return f'<span class="{cls}">' + self.inline(args[1], ltr) + "</span>"
        if name == "term":
            return ('<strong class="term">' + self.inline(args[0], ltr) + '</strong> <span class="term-en">(<bdi dir="ltr" lang="en">'
                    + self.inline(args[1], True) + "</bdi>)</span>")
        if name in ("lr", "en"):
            return '<bdi dir="ltr" lang="en">' + self.inline(args[0], True) + "</bdi>"
        if name == "rl":
            return '<bdi dir="rtl">' + self.inline(args[0], False) + "</bdi>"
        if name == "texttt":
            return '<code dir="ltr">' + self.inline(args[0], True) + "</code>"
        if name == "textsc":
            return '<span class="sc">' + self.inline(args[0], ltr) + "</span>"
        if name in ("underline", "mbox", "fbox"):
            return self.inline(args[0], ltr)
        if name == "ref":
            key = args[0]
            if key not in self.site.labels:
                print(f"warning: undefined ref {key} in {self.chap['file']}", file=sys.stderr)
                return "؟؟"
            page, anchor, num = self.site.labels[key]
            href = f"#{anchor}" if page == self.chap["page"] else f"{page}#{anchor}"
            return f'<a class="xref" href="{href}">{num}</a>'
        if name == "label":
            return ""
        if name == "hfill":
            return '<span class="hfill"></span>'
        if name in ("url",):
            return f'<a href="{html.escape(args[0])}" dir="ltr">{esc(args[0])}</a>'
        if name == "href":
            return f'<a href="{html.escape(self.inline(args[0], True))}">{self.inline(args[1], ltr)}</a>'
        if name in IGNORED or name in ("addcontentsline", "hspace", "vspace", "input", "part", "par", "setlength", "renewcommand", "newcommand", "arraystretch"):
            return ""
        if name == "item":
            return ""
        print(f"warning: unknown command \\{name} in {self.chap['file']}", file=sys.stderr)
        return ""

    def blocks(self, nodes):
        out = []
        para = []

        def flush():
            if para:
                h = self.inline(para).strip()
                h = re.sub(r"^(<br>\s*)+|(\s*<br>)+$", "", h)
                if h:
                    out.append("<p>" + h + "</p>")
                para.clear()

        for n in nodes:
            k = n[0]
            if k == "par":
                flush()
            elif k == "math" and n[2]:
                flush()
                out.append(self.display_math(n[1]))
            elif k == "env":
                flush()
                out.append(self.block_env(n))
            elif k == "cmd" and n[1] in ("section", "subsection", "subsubsection", "chapter"):
                flush()
                out.append(self.heading(n))
            elif k == "cmd" and n[1] == "label":
                anchor = self.chap["label_anchor"].get(id(n))
                if anchor and anchor.startswith("lbl-"):
                    out.append(f'<span id="{anchor}"></span>')
            else:
                para.append(n)
        flush()
        return "\n".join(out)

    def heading(self, n):
        _, name, star, opt, args = n
        info = self.chap["headings"].get(id(n))
        title = self.inline(args[0]).strip()
        if name == "chapter":
            return ""
        tag = {"section": "h2", "subsection": "h3", "subsubsection": "h4"}[name]
        if info is None:
            return f"<{tag}>{title}</{tag}>"
        anchor, num = info
        numhtml = f'<span class="num">{num}</span>' if num else ""
        return f'<{tag} id="{anchor}">{numhtml}<span class="htext">{title}</span><a class="hlink" href="#{anchor}" aria-label="پیوند به این بخش">#</a></{tag}>'

    def block_env(self, n):
        _, env, opt, args, body = n
        if env in ("automaton", "ltrfig"):
            return self.figure(n)
        if env in ("itemize", "enumerate"):
            return self.listing(n)
        if env in BOX_KIND:
            return self.box(n)
        if env in ("note", "warning", "proofidea", "proof", "algo", "summary"):
            return self.box(n)
        if env == "center":
            inner = self.blocks(body)
            return '<div class="center">' + inner + "</div>"
        if env in ("tabular",):
            return self.table(args[0], body)
        if env == "array":
            return self.display_math("\\begin{array}{" + args[0] + "}" + body + "\\end{array}")
        if env in ("latin", "LTR"):
            return '<div dir="ltr">' + self.blocks(body) + "</div>"
        if env in ("glossary", "jzglossary"):
            return self.glossary(body)
        if env in ("multicols", "minipage", "titlepage"):
            return self.blocks(body)
        print(f"warning: unknown env {env} in {self.chap['file']}", file=sys.stderr)
        return self.blocks(body)

    def listing(self, n):
        _, env, opt, args, body = n
        items = []
        cur = None
        for x in body:
            if x[0] == "cmd" and x[1] == "item":
                cur = []
                items.append(cur)
            elif cur is not None:
                cur.append(x)
        tag = "ul" if env == "itemize" else "ol"
        attrs = ""
        if env == "enumerate":
            start = self.chap["enum_start"].get(id(n), 1)
            if start != 1:
                attrs = f' start="{start}"'
        lis = []
        for it in items:
            h = self.blocks(it)
            m = re.fullmatch(r"<p>(.*)</p>", h, re.S)
            if m and "<p>" not in m.group(1):
                h = m.group(1)
            lis.append("<li>" + h + "</li>")
        return f"<{tag}{attrs}>" + "".join(lis) + f"</{tag}>"

    def box(self, n):
        _, env, opt, args, body = n
        opt_html = self.inline(Parser(opt, self.chap["file"]).parse_all()).strip() if opt else ""
        bid = self.chap["box_ids"].get(id(n))
        idattr = f' id="{bid}"' if bid else ""
        inner = self.blocks(body)
        if env in BOX_KIND:
            word, cls = BOX_KIND[env]
            num = self.chap["box_nums"][id(n)]
            label = f"{word} {num}"
            if env == "example":
                lead = f'<span class="lead">{label}{" (" + opt_html + ")" if opt_html else ""}.</span> '
                return f'<div class="box box-{cls}"{idattr}>' + self.prepend(inner, lead) + "</div>"
            title = f'<span class="bt-kind">{label}</span>' + (f'<span class="bt-name">{opt_html}</span>' if opt_html else "")
            return f'<div class="box box-{cls}"{idattr}><div class="box-title">{title}</div><div class="box-body">{inner}</div></div>'
        if env == "note":
            lead = f'<span class="lead">{opt_html or "نکته"}.</span> '
            return '<div class="box box-note">' + self.prepend(inner, lead) + "</div>"
        if env == "warning":
            lead = f'<span class="lead">{opt_html or "دقت کنید"}!</span> '
            return '<div class="box box-warn">' + self.prepend(inner, lead) + "</div>"
        if env == "proofidea":
            lead = f'<span class="lead">ایده اثبات{" (" + opt_html + ")" if opt_html else ""}.</span> '
            return '<div class="box box-idea">' + self.prepend(inner, lead) + "</div>"
        if env == "proof":
            lead = f'<span class="lead">اثبات{" (" + opt_html + ")" if opt_html else ""}.</span> '
            return '<div class="box box-proof">' + self.prepend(inner, lead) + '<div class="qed" aria-hidden="true">∎</div></div>'
        if env == "algo":
            a0 = self.inline(Parser(args[0], self.chap["file"]).parse_all())
            a1 = self.inline(Parser(args[1], self.chap["file"]).parse_all())
            return f'<div class="box box-algo"><div class="box-title">{a0} = «{a1}»</div><div class="box-body">{inner}</div></div>'
        if env == "summary":
            return f'<div class="box box-summary"><div class="box-title">جمع‌بندی فصل</div><div class="box-body">{inner}</div></div>'
        return inner

    def prepend(self, inner, lead):
        if inner.startswith("<p>"):
            return "<p>" + lead + inner[3:]
        return "<p>" + lead + "</p>" + inner

    def figure(self, n):
        fid = self.chap["fig_ids"][id(n)]
        return f'\x00F{fid}\x00'

    def table(self, spec, body):
        body = re.sub(r"\\renewcommand\{\\arraystretch\}\{[^}]*\}", "", body)
        rows = split_top(body, "\\\\")
        header_rows = 0
        cleaned = []
        for r in rows:
            has_mid = bool(re.search(r"\\(midrule|hline)", r))
            r2 = re.sub(r"\\(toprule|midrule|bottomrule|hline)", "", r).strip()
            if has_mid and cleaned and header_rows == 0:
                header_rows = len(cleaned)
            if r2:
                cleaned.append(r2)
        out = ['<div class="table-wrap"><table>']
        for ri, r in enumerate(cleaned):
            cells = split_top(r, "&")
            tag = "th" if ri < header_rows else "td"
            out.append("<tr>" + "".join(f"<{tag}>" + self.inline(Parser(c.strip(), self.chap["file"]).parse_all()).strip() + f"</{tag}>" for c in cells) + "</tr>")
        out.append("</table></div>")
        return "".join(out)

    def glossary(self, body):
        rows = []
        for x in body:
            if x[0] == "cmd" and x[1] == "gterm":
                rows.append((self.inline(x[4][0]), self.inline(x[4][1], True)))
        out = ['<div class="table-wrap"><table class="glossary"><tr><th>فارسی</th><th>English</th></tr>']
        for a, b in rows:
            out.append(f'<tr><td>{a}</td><td><bdi dir="ltr" lang="en">{b}</bdi></td></tr>')
        out.append("</table></div>")
        return "".join(out)


def walk(nodes, fn):
    for n in nodes:
        fn(n)
        if n[0] == "group":
            walk(n[1], fn)
        elif n[0] == "env" and isinstance(n[4], list):
            walk(n[4], fn)
        elif n[0] == "cmd":
            for a in n[4]:
                if isinstance(a, list):
                    walk(a, fn)


def number_chapter(site, chap):
    chap["headings"] = {}
    chap["box_nums"] = {}
    chap["box_ids"] = {}
    chap["fig_ids"] = {}
    chap["enum_start"] = {}
    chap["label_anchor"] = {}
    chap["toc"] = []
    num = chap["num"]
    state = {"sec": 0, "sub": 0, "box": 0, "fig": 0, "last": None, "boxstack": [], "enum_last": 0}

    def visit(nodes):
        for n in nodes:
            k = n[0]
            if k == "cmd":
                name = n[1]
                if name in ("section", "subsection", "subsubsection") and num is not None:
                    star = n[2]
                    title_nodes = n[4][0]
                    if name == "section":
                        if not star:
                            state["sec"] += 1
                            state["sub"] = 0
                            label = fa(f"{num}.{state['sec']}")
                            anchor = f"s{state['sec']}"
                        else:
                            label = ""
                            anchor = f"x{len(chap['toc'])}"
                        chap["headings"][id(n)] = (anchor, label)
                        chap["toc"].append((2, label, title_nodes, anchor))
                        state["last"] = (anchor, label)
                    elif name == "subsection":
                        if not star:
                            state["sub"] += 1
                            label = fa(f"{num}.{state['sec']}.{state['sub']}")
                            anchor = f"s{state['sec']}-{state['sub']}"
                        else:
                            label = ""
                            anchor = f"x{len(chap['toc'])}"
                        chap["headings"][id(n)] = (anchor, label)
                        chap["toc"].append((3, label, title_nodes, anchor))
                        state["last"] = (anchor, label)
                    else:
                        anchor = f"x{len(chap['toc'])}"
                        chap["headings"][id(n)] = (anchor, "")
                elif name == "section" and num is None:
                    anchor = f"x{len(chap['toc'])}"
                    chap["headings"][id(n)] = (anchor, "")
                    chap["toc"].append((2, "", n[4][0], anchor))
                elif name == "label":
                    key = n[4][0]
                    if state["boxstack"]:
                        anchor, label = state["boxstack"][-1]
                    elif state["last"]:
                        anchor, label = state["last"]
                    else:
                        anchor, label = "top", ""
                    site.labels[key] = (chap["page"], anchor, label)
                for a in n[4]:
                    if isinstance(a, list):
                        visit(a)
            elif k == "group":
                visit(n[1])
            elif k == "env":
                env = n[1]
                if env in BOX_KIND and num is not None:
                    state["box"] += 1
                    lab = fa(f"{num}.{state['box']}")
                    bid = f"b{state['box']}"
                    chap["box_nums"][id(n)] = lab
                    chap["box_ids"][id(n)] = bid
                    state["boxstack"].append((bid, lab))
                    visit(n[4])
                    state["boxstack"].pop()
                    continue
                if env in BOX_KIND:
                    chap["box_nums"][id(n)] = ""
                if env in ("automaton", "ltrfig"):
                    state["fig"] += 1
                    fid = f"{chap['slug']}-{state['fig']:02d}"
                    chap["fig_ids"][id(n)] = fid
                    site.figures.append((fid, n))
                    continue
                if env == "enumerate":
                    resume = (n[2] or "").strip() == "resume"
                    count = sum(1 for x in n[4] if x[0] == "cmd" and x[1] == "item")
                    start = state["enum_last"] + 1 if resume else 1
                    chap["enum_start"][id(n)] = start
                    state["enum_last"] = start + count - 1
                if isinstance(n[4], list):
                    visit(n[4])

    visit(chap["nodes"])


def read_structure():
    main = (SRC / "main.tex").read_text(encoding="utf-8")
    body = main[main.index("\\frontmatter"):]
    parts = []
    entries = []
    cur_part = None
    for m in re.finditer(r"\\part\{([^}]*)\}|\\input\{chapters/([^}]*)\}", body):
        if m.group(1):
            cur_part = {"title": m.group(1), "chapters": []}
            parts.append(cur_part)
        else:
            entries.append((m.group(2), cur_part))
    return parts, entries


def load_chapters(site):
    parts, entries = read_structure()
    site.parts = parts
    chapter_no = 0
    for fname, part in entries:
        path = SRC / "chapters" / f"{fname}.tex"
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            continue
        m = re.search(r"\\chapter(\*?)\{", text)
        if not m:
            continue
        star = m.group(1) == "*"
        p = Parser(text, f"{fname}.tex")
        p.i = m.end() - 1
        title_raw = p.read_balanced("{", "}")
        rest = text[p.i:]
        nodes = Parser(rest, f"{fname}.tex").parse_all()
        if fname.startswith("00"):
            num, page, slug = None, "index.html", "preface"
        elif fname.startswith("99"):
            num, page, slug = None, "glossary.html", "glossary"
        else:
            chapter_no += 1
            num, page, slug = chapter_no, f"ch{chapter_no:02d}.html", f"ch{chapter_no:02d}"
        chap = {"file": f"{fname}.tex", "title_raw": title_raw, "nodes": nodes, "num": num,
                "page": page, "slug": slug, "part": part, "star": star}
        site.chapters.append(chap)
        if part is not None and num is not None:
            part["chapters"].append(chap)
    for chap in site.chapters:
        number_chapter(site, chap)


FIG_PREAMBLE = r"""\documentclass[multi=jzfig,border=4pt]{standalone}
\usepackage{fontspec}
\setmainfont{Vazirmatn}[Path=%FONTS%/,Extension=.ttf,UprightFont=*-Regular,BoldFont=*-Bold,ItalicFont=*-Regular,Scale=0.93]
\usepackage{jozve-base}
\usepackage{array,booktabs}
\newcommand{\lr}[1]{#1}
\newcommand{\rl}[1]{#1}
\newcommand{\en}[1]{#1}
\begin{document}
"""


def build_figures(site, out_dir):
    fig_dir = out_dir / "fig"
    fig_dir.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    pieces = [FIG_PREAMBLE.replace("%FONTS%", str(ROOT / "fonts"))]
    for fid, n in site.figures:
        _, env, opt, args, body = n
        if env == "automaton":
            content = f"\\begin{{tikzpicture}}[jzaut,{opt or ''}]{body}\\end{{tikzpicture}}"
        else:
            content = body.strip()
        pieces.append(f"\\begin{{jzfig}}{content}\\end{{jzfig}}\n")
    pieces.append("\\end{document}\n")
    tex = BUILD / "figures.tex"
    tex.write_text("".join(pieces), encoding="utf-8")
    cmd = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={BUILD}", str(tex)]
    r = subprocess.run(cmd, cwd=SRC, capture_output=True, text=True)
    if r.returncode != 0:
        log = (BUILD / "figures.log").read_text(errors="replace")
        idx = log.find("\n!")
        print(log[idx:idx + 1500] if idx >= 0 else log[-1500:], file=sys.stderr)
        raise SystemExit("figure compilation failed")
    pdf = BUILD / "figures.pdf"
    sizes = {}
    for k, (fid, _) in enumerate(site.figures, start=1):
        svg = fig_dir / f"{fid}.svg"
        subprocess.run(["pdftocairo", "-svg", "-f", str(k), "-l", str(k), str(pdf), str(svg)], check=True)
        head = svg.read_text(encoding="utf-8")[:600]
        w = re.search(r'width="([\d.]+)(pt)?"', head)
        h = re.search(r'height="([\d.]+)(pt)?"', head)
        sizes[fid] = (float(w.group(1)), float(h.group(1)))
    return sizes


def render_math(site):
    BUILD.mkdir(parents=True, exist_ok=True)
    src = BUILD / "math-in.json"
    dst = BUILD / "math-out.json"
    src.write_text(json.dumps([{"tex": t, "display": d} for t, d in site.math], ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(WEB / "render-math.js"), str(src), str(dst)], check=True)
    data = json.loads(dst.read_text(encoding="utf-8"))
    for e in data["errors"]:
        print(f"katex error: {e['msg']}\n    in: {e['tex'][:200]}", file=sys.stderr)
    return data["out"], len(data["errors"])


def page_shell(title, body, extra_class="", for_artifact=False):
    head = f"""<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<meta name="description" content="جزوه کامل درس نظریه زبان‌ها و ماشین‌ها با اثبات‌ها و مثال‌ها">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800;900&display=swap">
<link rel="stylesheet" href="assets/katex/katex.min.css">
<link rel="stylesheet" href="assets/style.css">
<script>try{{var t=localStorage.getItem('jz-theme');if(t)document.documentElement.setAttribute('data-theme',t);}}catch(e){{}}</script>"""
    tail = '<script src="assets/app.js"></script>'
    if for_artifact:
        return f"{head}\n<div class=\"page {extra_class}\" dir=\"rtl\" lang=\"fa\">\n{body}\n</div>\n{tail}\n"
    return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
{head}
</head>
<body>
<div class="page {extra_class}">
{body}
</div>
{tail}
</body>
</html>
"""


def topbar(crumb=""):
    crumb_html = f'<span class="crumb">{crumb}</span>' if crumb else ""
    return f"""<header class="topbar">
  <div class="topbar-in">
    <a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true">δ</span><span>{SITE_TITLE}</span></a>
    {crumb_html}
    <div class="tools">
      <a class="tool" href="index.html#toc">فهرست</a>
      <button class="tool theme-toggle" type="button" id="theme-toggle" aria-label="تغییر تم روشن و تاریک">تم</button>
    </div>
  </div>
</header>"""


def chapter_title_html(r, chap):
    return r.inline(Parser(chap["title_raw"], chap["file"]).parse_all()).strip()


def toc_side(r, chap):
    items = []
    for level, label, tnodes, anchor in chap["toc"]:
        t = r.inline(tnodes).strip()
        n = f'<span class="tn">{label}</span>' if label else ""
        items.append(f'<li class="l{level}"><a href="#{anchor}">{n}{t}</a></li>')
    return '<details class="side-toc" open><summary>در این فصل</summary><nav aria-label="بخش‌های این فصل"><ol>' + "".join(items) + "</ol></nav></details>"


def build_pages(site, out_dir, for_artifact_index=False):
    pages = {}
    numbered = [c for c in site.chapters if c["num"] is not None]
    glossary = next((c for c in site.chapters if c["slug"] == "glossary"), None)
    seq = numbered + ([glossary] if glossary else [])
    for chap in site.chapters:
        r = Renderer(site, chap)
        chap["title_html"] = chapter_title_html(r, chap)
    for chap in site.chapters:
        r = Renderer(site, chap)
        content = r.blocks(chap["nodes"])
        if chap["slug"] == "preface":
            continue
        idx = seq.index(chap)
        prev_c = seq[idx - 1] if idx > 0 else None
        next_c = seq[idx + 1] if idx + 1 < len(seq) else None
        nav = ['<nav class="pager">']
        if prev_c:
            nav.append(f'<a class="pg prev" href="{prev_c["page"]}"><span class="pg-k">فصل قبل</span><span class="pg-t">{prev_c["title_html"]}</span></a>')
        else:
            nav.append('<a class="pg prev" href="index.html"><span class="pg-k">بازگشت</span><span class="pg-t">صفحه اصلی و فهرست</span></a>')
        if next_c:
            nav.append(f'<a class="pg next" href="{next_c["page"]}"><span class="pg-k">فصل بعد</span><span class="pg-t">{next_c["title_html"]}</span></a>')
        nav.append("</nav>")
        if chap["num"] is not None:
            kicker = f'<div class="kicker"><span class="chip">فصل {fa(str(chap["num"]))}</span><span class="part-name">{chap["part"]["title"] if chap["part"] else ""}</span></div>'
            crumb = f"فصل {fa(str(chap['num']))}"
        else:
            kicker = '<div class="kicker"><span class="chip">پیوست</span></div>'
            crumb = "واژه‌نامه"
        body = f"""{topbar(crumb)}
<div class="layout">
  {toc_side(r, chap) if chap["toc"] else '<div></div>'}
  <main class="content" id="top">
    <header class="chapter-head">{kicker}<h1>{chap["title_html"]}</h1></header>
{content}
    {"".join(nav)}
  </main>
</div>
{footer()}"""
        title = f'{chap["title_html"]} | {SITE_TITLE}'
        title = re.sub(r"<[^>]+>", "", title)
        pages[chap["page"]] = page_shell(title, body, "chapter")
    preface = next(c for c in site.chapters if c["slug"] == "preface")
    pr = Renderer(site, preface)
    pages["index.html"] = index_page(site, pr, preface, numbered, glossary)
    return pages


def footer():
    return f"""<footer class="site-foot"><div class="foot-in">
<p>این جزوه بر اساس اسلایدهای درس نظریه زبان‌ها و ماشین‌ها (دکتر مهدی دولتی، دانشگاه صنعتی شریف) نوشته شده است.</p>
<p><a href="{REPO_URL}">کد منبع در گیت‌هاب</a> · <a href="{PDF_URL}">نسخه PDF</a> · <a href="{GALLERY_URL}">گالری پروژه‌ها</a></p>
</div></footer>"""


HERO_SVG = """<svg class="hero-art" viewBox="0 0 420 150" role="img" aria-label="یک ماشین متناهی سه‌حالته">
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="currentColor"/></marker></defs>
<g fill="none" stroke="currentColor" stroke-width="2">
<line x1="18" y1="95" x2="62" y2="95" marker-end="url(#ah)"/>
<circle cx="88" cy="95" r="24"/><circle cx="210" cy="95" r="24"/><circle cx="332" cy="95" r="24"/><circle cx="332" cy="95" r="18"/>
<line x1="112" y1="95" x2="184" y2="95" marker-end="url(#ah)"/>
<path d="M228,78 C260,44 290,44 318,76" marker-end="url(#ah)"/>
<path d="M314,114 C290,140 255,140 228,112" marker-end="url(#ah)"/>
<path d="M76,73 C64,38 112,38 100,73" marker-end="url(#ah)"/>
<path d="M198,73 C186,38 234,38 222,73" marker-end="url(#ah)"/>
</g>
<g fill="currentColor" font-family="KaTeX_Math, Times New Roman, serif" font-style="italic" font-size="20" text-anchor="middle">
<text x="88" y="102">q₀</text><text x="210" y="102">q₁</text><text x="332" y="102">q₂</text>
</g>
<g fill="currentColor" font-family="KaTeX_Main, Times New Roman, serif" font-size="17" text-anchor="middle">
<text x="88" y="32">0</text><text x="148" y="86">1</text><text x="210" y="32">1</text><text x="272" y="44">0</text><text x="272" y="148">0,1</text>
</g>
</svg>"""


def index_page(site, r, preface, numbered, glossary):
    pre = r.blocks(preface["nodes"])
    toc = ['<section class="toc" id="toc"><h2 class="toc-h">فهرست مطالب</h2>']
    for pi, part in enumerate(site.parts):
        toc.append(f'<div class="toc-part"><div class="toc-part-head"><span class="toc-part-k">بخش {ORDINALS[pi]}</span><span class="toc-part-t">{part["title"]}</span></div><div class="toc-grid">')
        for chap in part["chapters"]:
            secs = [Renderer(site, chap).inline(t).strip() for lvl, lab, t, a in chap["toc"] if lvl == 2]
            sec_html = "".join(f"<li>{s}</li>" for s in secs[:6])
            more = f'<li class="more">و {fa(str(len(secs) - 6))} بخش دیگر</li>' if len(secs) > 6 else ""
            toc.append(f'<a class="toc-card" href="{chap["page"]}"><span class="toc-n">{fa(str(chap["num"]))}</span><span class="toc-t">{chap["title_html"]}</span><ul>{sec_html}{more}</ul></a>')
        toc.append("</div></div>")
    if glossary:
        toc.append(f'<div class="toc-part"><div class="toc-part-head"><span class="toc-part-k">پیوست</span><span class="toc-part-t">{glossary["title_html"]}</span></div><div class="toc-grid"><a class="toc-card" href="{glossary["page"]}"><span class="toc-n">ا</span><span class="toc-t">{glossary["title_html"]}</span><ul><li>معادل انگلیسی اصطلاحات درس</li></ul></a></div></div>')
    toc.append("</section>")
    first = numbered[0]["page"] if numbered else "#toc"
    body = f"""{topbar()}
<section class="hero">
  <div class="hero-in">
    <div class="hero-text">
      <p class="hero-k">{SITE_SUBTITLE} · <bdi dir="ltr" lang="en">Theory of Formal Languages and Automata</bdi></p>
      <h1 class="hero-t">{SITE_TITLE}</h1>
      <p class="hero-d">از زبان‌های منظم تا ماشین تورینگ، تصمیم‌ناپذیری و <bdi dir="ltr">NP</bdi>-تمامیت؛ همراه با اثبات کامل قضیه‌ها به زبان ساده. بر اساس اسلایدهای درس دکتر مهدی دولتی، دانشگاه صنعتی شریف.</p>
      <div class="hero-actions">
        <a class="btn primary" href="{first}">شروع از فصل ۱</a>
        <a class="btn" href="#toc">فهرست مطالب</a>
        <a class="btn" href="{PDF_URL}">نسخه PDF</a>
      </div>
      <p class="hero-meta">{fa(str(len(numbered)))} فصل · ۵ بخش · تعریف، قضیه، اثبات و مثال در کادرهای جدا</p>
    </div>
    {HERO_SVG}
  </div>
</section>
<div class="layout single">
  <main class="content">
{toc_html(toc)}
    <section class="preface">
      <h2 class="toc-h">{preface["title_html"]}</h2>
{pre}
    </section>
  </main>
</div>
{footer()}"""
    return page_shell(SITE_TITLE, body, "home")


def toc_html(toc):
    return "\n".join(toc)


def main():
    out_dir = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else (ROOT / "docs")
    site = Site()
    load_chapters(site)
    if out_dir.exists():
        for p in out_dir.iterdir():
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
    out_dir.mkdir(parents=True, exist_ok=True)
    sizes = build_figures(site, out_dir)
    pages = build_pages(site, out_dir)
    math_html, nerr = render_math(site)
    fig_alt = "شکل"

    def fill(h):
        h = re.sub("\x00M(\\d+)\x00", lambda m: math_html[int(m.group(1))], h)

        def fig(m):
            fid = m.group(1)
            w, hh = sizes[fid]
            pw = round(w * 1.333)
            ph = round(hh * 1.333)
            return f'<figure class="fig"><img src="fig/{fid}.svg" width="{pw}" height="{ph}" alt="{fig_alt}" loading="lazy" decoding="async"></figure>'

        return re.sub("\x00F([\\w-]+)\x00", fig, h)

    for name, h in pages.items():
        (out_dir / name).write_text(fill(h), encoding="utf-8")
    full = (out_dir / "index.html").read_text(encoding="utf-8")
    head = full[full.index("<title>"):full.index("</head>")]
    bodyc = full[full.index("<body>") + len("<body>"):full.index("</body>")]
    (BUILD / "artifact-index.html").write_text(head.strip() + "\n" + bodyc.strip() + "\n", encoding="utf-8")
    assets = out_dir / "assets"
    (assets / "katex").mkdir(parents=True, exist_ok=True)
    kdist = WEB / "node_modules" / "katex" / "dist"
    shutil.copy(kdist / "katex.min.css", assets / "katex" / "katex.min.css")
    shutil.copytree(kdist / "fonts", assets / "katex" / "fonts", dirs_exist_ok=True)
    for f in (assets / "katex" / "fonts").iterdir():
        if not f.name.endswith(".woff2"):
            f.unlink()
    shutil.copy(WEB / "assets" / "style.css", assets / "style.css")
    shutil.copy(WEB / "assets" / "app.js", assets / "app.js")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")
    print(f"pages: {len(pages)}, figures: {len(site.figures)}, math: {len(site.math)}, katex errors: {nerr}")
    if nerr:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
