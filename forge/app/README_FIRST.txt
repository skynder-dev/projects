MERCH FORGE 068 Merch Forge REVIEW FIXES RC

ПО-РУССКИ
1. Распакуйте всю папку: правый клик по ZIP -> «Извлечь все».
2. Запустите START_068_MERCH_FORGE.vbs двойным щелчком.
3. Как пользоваться (1 страница): HOW_TO_USE_RU.txt

START
1. Extract the whole folder.
2. Run START_068_MERCH_FORGE.vbs.

WHAT IS NEW (068)
- FIX (old, since before 054): local image generation could never start - the code assigned to the
  read-only $pid variable right after the worker was launched, then deleted the job file. A running
  generation also showed as "ambiguous" and the app offered to start another paid request.
  A new automatic check rejects any assignment to read-only PowerShell variables.
- Performance: "no sales for 30 days" is said only when the imported sales data is recent;
  otherwise it says the sales data is missing or old.
- Sales CSV: amounts like "1,50", "1.234,56 EUR", "$1,234.56", "(0.35)" and dates in ISO, US (M/d/yyyy)
  or d.M.yyyy are read correctly; unclear dates are not guessed (counted as undated).
- Amazon profile form: you must paste the Amazon page you took the values from; your own accepted
  design is refused as a "template".
- Saving a research draft asks before discarding unsaved listing text (like server ideas).
- Portfolio: if you keep unsaved edits instead of opening another idea, you stay on Portfolio.
- Forms never close the app on an unexpected error; the profile import cannot freeze the window.
- Russian one-page guide HOW_TO_USE_RU.txt next to START; README_FIRST starts in Russian.
- Includes 067 and earlier (055-066).
