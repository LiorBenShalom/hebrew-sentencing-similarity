# KNOWN ISSUES — data bugs you must not mistake for model errors

## 1. Feature vectors contradict themselves (very common)

The vectors were auto-extracted and frequently disagree with themselves:

- `"שימוש": "לא"` alongside `"מספר כדורים שנורו": 11`, `"תרמילים"`, `"כיוון ירי"`, `"מרחק ירי"`, or a `340א` conviction under `"עבירות נוספות"`.
- `"מעבדה": "לא"` alongside `"תפקיד": "בעל המעבדה"`, `"מיקום המעבדה"`, `"כמות חדרים במעבדה": 7`, or 700 seedlings.
- `"כמות תחמושת": "ללא"` alongside `"סוג תחמושת": "מחסניות ותחמושת"`.
- `"מספר עסקאות": 2` alongside four documented transaction dates.

**An explanation relying on either side is using real case data. Never score it as an invention.** This is the single most consequential rule in the pack — an earlier pass got it wrong and produced ~25 unfair downgrades.

## 2. `model_pred_scale` is not comparable across models

- Claude and Gemma use a **1-3** scale whose value is a separate model judgment (score ranges overlap between bins).
- GPT-4 uses a **0-3** scale produced by deterministic binning of `model_score` (10-20→0, 25-48→1, 55-72→2, 75-95→3). `GT` never contains 0, so 21 drug rows and 32 weapon rows are automatically counted wrong.

Naive accuracy from this column reads GPT-4 at 53% / 55% versus ~80% for the others. After collapsing GPT-4's 0→1 it is 72% / 78%; after re-binning all three from `model_score` with a common rule it is ~73-79% for all. Scale-free Spearman of `model_score` vs `GT` is **.776 / .775 / .757** (drugs) and **.770 / .768 / .770** (weapons) — the three models are statistically indistinguishable at ranking similarity.

**Do not use this column, and do not let it influence any label.**

## 3. Multi-value categorical fields

Fields like `"מספר עבירה": "144 א, 144 ב"` and `"עבירה": "יבוא/סחר, 19"` hold comma-separated sets. If you compute anything on them, compare as sets — parsing them as numbers silently destroys the signal (see the warning in `RUBRIC.md`).

## 4. The `הערות` column

Free-text notes from the original annotation pass. Several are themselves factually or legally wrong — one inverts the severity of 144(א) vs 144(ב) (in fact 144(ב), נשיאה/הובלה, is the more severe). Others justify a downgrade with a claim the vector contradicts. **Treat as commentary, never as authority.**

## 5. Escaped-JSON edge cases

A handful of `feature_vector_*` cells fail a strict `json.loads` because of backslash escaping. Fall back to a lenient parse rather than dropping the row.
