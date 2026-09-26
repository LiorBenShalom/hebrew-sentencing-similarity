# RUBRIC — feature hierarchies, dominance evidence, and corpus-specific traps

This file tells you which features are **dominant/important** and which are **marginal**, per domain. The hierarchy comes from the human-annotator guides in `guides/` (primary authority — the `GT` labels were produced with them), cross-checked against an empirical measurement on this very dataset.

---

## DRUGS

### The guide's explicit weights (`guides/Tagging_Plan_drugs.csv`)

| Feature | Weight | Share |
|---|---|---|
| `סוג הסם` — which drug | 5 | 26.3% |
| `כמות הסם` — quantity | 5 | 26.3% |
| `מעבדה` — lab yes/no | 4 | 21.1% |
| `מכירה לסוכן` — sale to undercover agent | 3 | 15.8% |
| `תפקיד` — owner / lab owner / neither | 2 | 10.5% |

The guide adds in prose: *"לגבי סעיפי העבירה – הייתי מתמקד ב**סוג העבירה**: האם החזקה שלא לצריכה עצמית, גידול, או סחר"* — so **`עבירה` as the three-way category** (possession-not-for-personal-use / cultivation / trade) is also a legitimate dominant anchor.

The guide also states substantive equivalences: **חשיש ≈ קנבוס** and **הרואין ≈ קוקאין**, "מבחינת חומרה". Similarity is defined as *"לסם זהה, ובנוסף…"* — same drug is the baseline, everything else modifies it.

### Empirical cross-check (Spearman of per-feature similarity vs `GT`, n=300 pooled rows)

| Feature | r | p |
|---|---|---|
| כמות הסם | **+0.604** | <.001 |
| תפקיד | **+0.505** | <.001 |
| מכירה לסוכן | **+0.440** | <.001 |
| עבירה (סוג) | **+0.391** | <.001 |
| סוג הסם (זהות) | +0.264 | <.001 |
| מעבדה | +0.199 | .001 |
| **עבירות נלוות** | **−0.040** | .49 (not significant) |

Guide and data agree on the top tier and agree that `עבירות נלוות` is noise. They disagree on the relative rank of `תפקיד` (guide lowest, data 2nd) and `מעבדה` (guide 3rd, data lowest significant). **Where they conflict, the guide wins** — but treat both `תפקיד` and `מעבדה` as genuinely important.

### Tiers to apply

- **Dominant:** סוג הסם · כמות הסם · מעבדה · מכירה לסוכן · תפקיד · סוג העבירה
- **Marginal (zero weight — never penalize their omission, and their carrying a verdict is a defect):** עבירות נלוות · MO ושיטת הסתרה · גיאוגרפיה, מדינות, מסלולי טיסה · תאריכים ומשך · סכומי כסף · אפליקציות תקשורת · שמות ומספר שותפים · מספר נאשמים · זהות/עיסוק הנאשם · "תחכום" · נסיבות התפיסה (מרדף, מבצע סוכן, תפיסה בנתב"ג)

### Trap specific to this corpus

Explanations repeatedly invent a statutory drug grading — `"סם מסוג א'"` vs `"סם מסוג ב'"`, `"לוח א'/ב'"`, `"מסוג A/B/C"`. **No such grading exists** in the Dangerous Drugs Ordinance in the form they use, and the same model is inconsistent across rows (MDMA is "לוח א'" in one row and "מסוג ב'" in another). Policy:
- If the invented class **materially supports** the verdict → `רלוונטיות_משפטית` capped at 2.
- If it **alone carries** the verdict → 1.
- A decorative mention outside the operative conclusion → no penalty.

The other recurring trap: the verdict resting on **the false-walled-suitcase-from-Europe MO** while a drug-class or order-of-magnitude quantity gap is waved away.

---

## WEAPONS

### The guide's staged protocol (`guides/Entity_recipe_weapons.csv`)

This guide is a **procedure**, not just a weight list. Annotators were told:

**Ordered stages (שלבי תיוג):**
1. `סוג הנשק`, `סוג עבירה`, `מספר עבירה` (144א / 144ב)
2. `שימוש`, `מטרה`
3. `סטטוס הנשק`, `אופן החזקת הנשק`
4. *optional, only for cases still sitting at 3:* `בריחה`, `תכנון`

**Hard gates stated outright:**
- Overall similarity is necessarily **< 3** if `סוג הנשק` < 3, **or** `סוג עבירה` < 3, **or** `שימוש` < 3.
- To award **5**, you need `סוג הנשק` ≥ 4 **and** `מספר עבירה` ≥ 4.
- `סטטוס` + `אופן החזקה` are a **balancer**: both high → raise to 4; both low → lower to 2; one high one low, or both 3 → they cancel.
- `מטרה` adjusts against the mean of (`סוג הנשק`, `עבירה`, `מספר עבירה`), rounded down: above → round up; equal → no change; below → round down.

**The guide even scores the section pairs numerically:** 144א/144א = 5 · 144ב/144ב = 5 · **144א/144ב = 2** ("כשמדובר בהחזקה ונשיאה") · "144א+ב"/144ב = 4 · "144א+ב"/144א = 3. It supplies weapon-type pairs too: רובה צייד/רובה סער = 1 · תת מקלע/תת מקלע מאולתר = 4 · אקדח/מטען = 1 · "2 נשקים מסוג X"/"נשק אחד מסוג X" = 4.

### Empirical cross-check (Spearman vs `GT`, n=423 pooled rows)

| Feature | r | p |
|---|---|---|
| מספר עבירה 144(א)/(ב) | **+0.259** | <.001 |
| סוג עבירה | **+0.258** | <.001 |
| סטטוס הנשק | +0.209 | <.001 |
| עבירות נוספות | +0.193 | <.001 |
| שימוש | +0.183 | <.001 |
| סוג הנשק | +0.121 | .079 |
| כמות תחמושת | +0.108 | .47 |
| מטרה | +0.105 | .031 |
| תכנון | +0.102 | .036 |
| אופן החזקת הנשק | +0.042 | .39 |
| אופן קבלת הנשק | −0.026 | .59 |

> **Warning from our own experience.** An earlier pass computed `מספר עבירה` as a *numeric* field, so `"144 א"` and `"144 ב"` both parsed to the number 144, every pair looked identical, and it came out at r≈.05 — "marginal". That was a parsing bug. Compared as categorical strings it is r=.259, the strongest single predictor in the domain. We then wrongly penalized dozens of explanations for reasoning about 144(א)/(ב). **Do not repeat this: the section distinction is a first-class criterion, and a verdict resting on it is a 3.**

### Tiers to apply

- **Dominant (stages 1-2):** סוג הנשק · סוג עבירה · מספר עבירה 144(א)/(ב) · שימוש · מטרה
- **Important but secondary (stage 3, balancers):** סטטוס הנשק · אופן החזקת הנשק · כמות תחמושת · עבירות נוספות · אופן קבלת הנשק — legitimate as *adjusters*, a defect when they are the **sole** load-bearer
- **Marginal (stage 4 or off-protocol):** תכנון · בריחה · גיאוגרפיה · תאריכים · מספרים סידוריים · מספר מעורבים · "רמת ארגון" · נסיבות המעצר ומרדפים · עבירות סמים נלוות

### Uniform policy for hard-gate overrides

When a hard gate points clearly against the verdict (weapon types sharply different, offense types sharply different, or use-vs-no-use) and the explanation asserts the verdict anyway by leaning elsewhere → `רלוונטיות_משפטית` = **2**, *whether or not it acknowledges the gap*. Acknowledging and then overriding is not better than ignoring; earlier passes treated these inconsistently and 2 is the settled answer.

### Traps specific to this corpus

- **The Honda / femur-fracture case.** Several explanations assert actual shooting in a case whose vector records no shooting field at all and whose only injury is `שבר בפמור`. This is a genuine invention → faithfulness 1 when it drives the analysis (it usually does), 2 at minimum.
- **The Tirat HaCarmel case.** Explanations invent `רובה סער` / a third weapon where the vector says only `נשק`. Genuine invention.
- **Invented `סכסוך`.** A conflict motive attributed to a case whose vector has no such field. Single invented detail → 2.
- **`שימוש: לא` alongside recorded firing.** Extremely common. This is the vector contradicting itself — **not** an invention. See the CRITICAL RULE in `PROMPT.md`.

---

## Applies to both domains

- Judge each dimension independently. A row can legitimately be 1 / 3 / 3.
- Do not let `GT` or `model_score` influence any label. Well-anchored explanations sometimes land on the wrong number, and badly-anchored ones sometimes land on the right one.
- The fixed 5-section template every model uses forces an MO section into every explanation. Its mere presence costs nothing.
- Depth is not required for `שלמות` — a one-clause mention of a feature counts as addressing it.
