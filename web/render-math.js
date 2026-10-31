const fs = require("fs");
const katex = require("katex");

const macros = {
  "\\eps": "\\varepsilon",
  "\\blank": "\\sqcup",
  "\\enc": "\\langle #1\\rangle",
  "\\st": "\\mid",
  "\\cP": "\\mathrm{P}",
  "\\cNP": "\\mathrm{NP}",
  "\\prob": "\\mathit{#1}",
  "\\lng": "\\mathit{#1}_{\\mathsf{#2}}",
  "\\ATM": "\\mathit{A}_{\\mathsf{TM}}",
  "\\der": "\\overset{*}{\\Rightarrow}",
  "\\ra": "\\rightarrow",
  "\\pre": "\\mathit{Prefix}",
  "\\suf": "\\mathit{Suffix}",
  "\\qacc": "q_{\\mathrm{accept}}",
  "\\qrej": "q_{\\mathrm{reject}}",
  "\\qstart": "q_{\\mathrm{start}}",
  "\\txt": "\\text{#1}",
  "\\abs": "\\lvert #1\\rvert",
  "\\dom": "\\left[\\genfrac{}{}{0pt}{}{\\mathtt{#1}}{\\mathtt{#2}}\\right]",
  "\\textsc": "\\textsf{#1}",
  "\\qedhere": "",
};

console.warn = () => {};
const items = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = [];
const errors = [];
const base = {
  output: "html",
  strict: "ignore",
  trust: (ctx) => ctx.command === "\\htmlClass",
};
for (const it of items) {
  try {
    out.push(katex.renderToString(it.tex, { ...base, displayMode: it.display, macros: { ...macros }, throwOnError: true }));
  } catch (e) {
    errors.push({ tex: it.tex, msg: e.message });
    out.push(katex.renderToString(it.tex, { ...base, displayMode: it.display, macros: { ...macros }, throwOnError: false }));
  }
}
fs.writeFileSync(process.argv[3], JSON.stringify({ out, errors }));
