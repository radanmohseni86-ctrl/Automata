<div dir="rtl">

# جزوه اتوماتا

جزوه کامل درس **نظریه زبان‌ها و ماشین‌ها** (Theory of Formal Languages and Automata)، بر اساس اسلایدهای درس دکتر مهدی دولتی در دانشکده مهندسی کامپیوتر دانشگاه صنعتی شریف.

- 🌐 **نسخه وب:** <https://radanmohseni86-ctrl.github.io/Automata/>
- 📄 **نسخه PDF:** [Jozve-Automata.pdf](Jozve-Automata.pdf)
- 🗂️ **گالری پروژه‌ها:** <https://radanmohseni86-ctrl.github.io/>

## ویژگی‌ها

- ۲۴ فصل در ۵ بخش، از مقدمات ریاضی تا NP-تمامیت.
- تعریف‌ها، قضیه‌ها، اثبات‌ها، مثال‌ها و نکته‌ها در کادرهای رنگی جدا.
- اثبات کامل قضیه‌ها، حتی جاهایی که اسلایدها فقط ایده اثبات را داشتند یا اثبات را به عنوان تمرین گذاشته بودند.
- نمودار همه ماشین‌ها با TikZ.
- راست‌چین کامل با متن فارسی و انگلیسی و فرمول‌ها.

## فهرست

| بخش | فصل‌ها |
|---|---|
| ۱. پیش‌نیازهای ریاضی | منطق، مجموعه، تابع، گراف · رشته، زبان و روش‌های اثبات |
| ۲. زبان‌های منظم | DFA · NFA · بستاری · عبارات منظم · گرامرهای منظم · لم تزریق |
| ۳. زبان‌های مستقل از متن | CFG و ابهام · فرم‌های نرمال · CYK · PDA · بستاری · لم تزریق · DPDA و LL |
| ۴. محاسبه‌پذیری | ماشین تورینگ · گونه‌ها · تز چرچ–تورینگ · تصمیم‌ناپذیری · کاهش · PCP |
| ۵. پیچیدگی | کلاس P · کلاس NP · NP-تمامیت و کوک–لوین |

## ساختار مخزن

- `src/` متن LaTeX جزوه (XePersian با فونت وزیرمتن)
- `web/` اسکریپت ساخت نسخه وب از همان متن LaTeX
- `docs/` نسخه وب ساخته‌شده (برای GitHub Pages)
- `fonts/` فونت وزیرمتن (مجوز OFL)

## ساختن از روی متن

نیازمندی‌ها: TeX Live با `xetex`، `texlive-lang-arabic`، `texlive-pictures`، `texlive-latex-extra`؛ و برای نسخه وب Python 3، Node.js و `pdftocairo` (از poppler-utils).

```bash
make pdf   # ساخت Jozve-Automata.pdf
make web   # ساخت سایت در docs/
```

## منابع

- Michael Sipser, *Introduction to the Theory of Computation*
- Peter Linz, *An Introduction to Formal Languages and Automata*
- اسلایدهای Costas Busch (مثال‌های لم تزریق)

اگر اشتباهی دیدید، یک Issue باز کنید یا Pull Request بفرستید.

</div>
