#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Re-run gemma4_31b_or on the 141 weapon H-Full GT pairs against the CURRENT feature DB,
then annotate the explanations with the original claude_annotate.py pipeline.

Mirrors exactly what was done for claude-sonnet-4-6:
  - same V6 weapon system prompt (verbatim from generate_gpt4_explanations.py)
  - same user template, temperature 0.1, max_tokens 2000
  - same 0/1/2/3 thresholds
  - annotation by claude-opus-4-7 with the SYSTEM_PROMPT + JSON schema from claude_annotate.py

Run:  python3 rerun_gemma.py
Needs: OPENROUTER_API_KEY in new_try/experiments/.env
       ANTHROPIC_API_KEY  in Thesis!!!/.env
       pip install openai anthropic pandas tqdm
"""
from __future__ import annotations
import json, re, time, csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from openai import OpenAI
import anthropic
from tqdm import tqdm

ROOT = Path("<WORKSPACE>")
WEAPON_DB = ROOT / "new_try/weapon/similarity_database_hybrid_full_gpt.csv"
OLD_FILE = ROOT / "new_try/experiments/old/results_1_similarity/explainability/hybrid_full/explainability_weapon_gemma4_31b_or.csv"
OUT = ROOT / "new_try/experiments/old/results_1_similarity/explainability/hybrid_full/final_labels"
OUT.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUT / "explainability_weapon_gemma4_31b_or_RERUN.csv"

GEN_MODEL = "google/gemma-4-31b-it"      # same id as run_score_only_all_models.py
ANN_MODEL = "claude-opus-4-7"            # same as claude_annotate.py


def _env(path: Path, *names):
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            if k.strip().lower() in names:
                return v.strip().strip('"').strip("'")
    raise RuntimeError(f"key {names} not found in {path}")


OR_KEY = _env(ROOT / "new_try/experiments/.env", "openrouter_api_key")
AN_KEY = _env(ROOT / ".env", "anthropic_api_key", "antropic_api_key")

# ---------------------------------------------------------------- generation
SYSTEM_WEAPON = """את/ה מומחית לדין הפלילי בישראל. מוצגים בפנייך **פיצ'רים מובנים** של שני תיקים פליליים.

המשימה: הערכת דמיון מהותי — עד כמה תיק אחד יכול לשמש כתקדים ענייני לשני?

נתחי כל ממד בנפרד:
1. **סוג העבירה וחומרתה** — האם מדובר באותו סוג עבירה? באותה רמת חומרה?
2. **תפקיד הנאשם ומעורבותו** — יזם/סוחר לעומת שליח/מחזיק? מעורבות פעילה לעומת פסיבית?
3. **שיטת הביצוע (MO)** — דפוס דומה? אמצעים דומים?
4. **נסיבות הליבה** — כמות תחמושת (סדר גודל), שימוש בנשק, תכנון, נסיבות מחמירות/מקלות?
5. **ישימות כתקדים** — האם בית משפט יראה את שני התיקים כרלוונטיים זה לזה לצורכי ענישה?

חשוב:
- התמקדי בפרמטרים המשפטיים המהותיים, לא בפרטים טכניים/ביורוקרטיים.
- השתייכות לאותו תחום (סמים/נשק) לבדה **לא מספיקה** לדמיון מהותי.
- הבחנה בין 144(א) (החזקה בלבד) ל-144(ב) (נשיאה/הובלה) היא מהותית — תיק שהוא 144(א) לבדו כמעט אף פעם לא מהווה תקדים לתיק 144(ב).


פורמט תשובה:
1. ניתוח קצר (2-3 משפטים) של כל ממד
2. שורה אחרונה בדיוק בפורמט: SIMILARITY_SCORE: X
   כאשר X הוא מספר שלם בין 0 ל-100.
   0 = שונים לחלוטין, 100 = זהים כמעט. ציון מעל 50 = תקדים רלוונטי."""

USER_TEMPLATE = """להלן שני תיקים פליליים עם פיצ'רים מובנים:

תיק 1:
{fv1}

תיק 2:
{fv2}

מהו ציון הדמיון המהותי (0-100)?"""

_or = OpenAI(api_key=OR_KEY, base_url="https://openrouter.ai/api/v1")


def parse_score(t: str):
    m = re.search(r"SIMILARITY_SCORE:\s*(\d+)", t)
    return int(m.group(1)) if m else None


def scale(s):  # identical thresholds to generate_gpt4_explanations.py
    return 0 if s < 25 else 1 if s < 50 else 2 if s < 75 else 3


def generate(row, tries=5):
    user = USER_TEMPLATE.format(fv1=row["feature_vector_1"], fv2=row["feature_vector_2"])
    last = None
    for i in range(tries):
        try:
            r = _or.chat.completions.create(
                model=GEN_MODEL,
                messages=[{"role": "system", "content": SYSTEM_WEAPON},
                          {"role": "user", "content": user}],
                temperature=0.1, max_tokens=2000)
            return r.choices[0].message.content or ""
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


# ---------------------------------------------------------------- annotation
ANN_SYSTEM = """את/ה משמש/ת כמתייג/ת אנושי/ת מומחה/ית בתחום המשפט הפלילי הישראלי (גזרי דין בעבירות סמים ונשק).

המשימה: בכל זוג של גזרי דין, המודל קיבל שני feature vectors (מיצוי מובנה של עובדות) וניסח הסבר השוואתי של דמיון בעברית, עם ציון דמיון מספרי (0–100). תפקידך להעריך את איכות ההסבר של המודל על סקאלה 1–3 בשלושה ממדים, ולהוסיף הערה מילולית קצרה.

### שלושה ממדי הערכה (סקאלה 1–3):

**1) נאמנות_עובדתית** — האם ההסבר מציג נכונה את העובדות מה-feature vectors?
  - 3 = ההסבר מדויק עובדתית לחלוטין. כל טענה ניתנת לאימות מול ה-vectors. אין הזיות, אין סילוף, אין הכללות לא מבוססות.
  - 2 = רוב הטענות נכונות, אך יש שגיאה עובדתית קטנה אחת, סילוף קל, או הכללה יתרה של פרט אחד. לא פוגע מהותית בהבנה.
  - 1 = שגיאות עובדתיות מהותיות. ההסבר כולל הזיות, סילוף חמור של פרטים, או טענות שסותרות את ה-vectors.

**2) רלוונטיות_משפטית** — האם ההסבר מתמקד בגורמים בעלי משקל משפטי-עונשי בתחום הספציפי (סמים/נשק)?
  ממדים רלוונטיים נפוצים: סוג העבירה וסעיף החוק, חומרה, תפקיד הנאשם (עיקרי/שולי), סוג וכמות החומר (סם/נשק), שיטת ביצוע (MO), נסיבות מחמירות/מקלות, עבירות נלוות, שימוש.
  - 3 = ההסבר מתמקד כמעט כולו בממדים בעלי משקל משפטי מובהק. אין משקל לפרטים זניחים או "רעש".
  - 2 = ההסבר כולל ממדים רלוונטיים, אך גם פרטים פחות רלוונטיים משפטית (למשל: תאריכים מדויקים, שמות שותפים) שמקבלים משקל מוגזם.
  - 1 = ההסבר מתמקד בעיקר בפרטים חסרי משקל משפטי או מפספס את הממדים המהותיים שהיו צריכים להוביל את ההשוואה.

**3) שלמות** — האם ההסבר מכסה את כל ממדי הדמיון/ההבדל המשמעותיים שעולים מה-vectors?
  - 3 = ההסבר מכסה את כל הממדים המשמעותיים. לא הוחמץ גורם משפטי משמעותי שעולה מה-vectors.
  - 2 = מרבית הממדים מכוסים, אך הוחמץ ממד משני אחד או שניים.
  - 1 = הוחמצו ממדים מרכזיים. ההסבר שטחי, חלקי, או מתרכז בהיבט אחד תוך התעלמות מהיתר.

### הערה מילולית (הערות):
טקסט חופשי קצר בעברית (1–3 משפטים): הצדק/י את הציונים — מה עבד טוב, מה חסר או שגוי. התייחס/י לדוגמה קונקרטית מההסבר אם אפשר.

### עקרונות עבודה:
- את/ה מתייג/ת את **איכות ההסבר** בלבד — לא את נכונות ציון הדמיון של המודל ולא את הדמיון האמיתי בין התיקים.
- ה-GT (סקייל 1/2/3) ניתן לך כאינפורמציה — אבל אל תתני לו להטות את הציון שלך להסבר. הסבר טוב יכול לתאר נכונה למה שני תיקים דומים גם אם בפועל הציון של המודל שגוי.
- בעת קריאת feature vectors: שים/י לב להעדר שדות (לא כל תיק כולל את כל השדות), ולקודי עבירה (144 לנשק, 19/13 לסמים).
- החזר/י JSON תקני לפי הסכמה שתסופק, ללא טקסט נוסף.
"""

ANN_SCHEMA = {
    "type": "object",
    "properties": {
        "נאמנות_עובדתית": {"type": "integer", "enum": [1, 2, 3]},
        "רלוונטיות_משפטית": {"type": "integer", "enum": [1, 2, 3]},
        "שלמות": {"type": "integer", "enum": [1, 2, 3]},
        "הערות": {"type": "string", "minLength": 1},
    },
    "required": ["נאמנות_עובדתית", "רלוונטיות_משפטית", "שלמות", "הערות"],
    "additionalProperties": False,
}

_an = anthropic.Anthropic(api_key=AN_KEY)


def annotate(r, tries=5):
    user = f"""להלן זוג גזרי דין בתחום נשק שההסבר של המודל עליהם דורש תיוג.

**GT (סקייל 1–3, תיוג אנושי של דמיון אמיתי):** {r['GT']}
**ציון דמיון שהמודל חזה (0–100):** {r['model_score']}
**תחזית סקייל של המודל לפי thresholds (1–3):** {r['model_pred_scale']}

---
**feature_vector_1** (תיק {r['verdict_1']}):
{r['feature_vector_1']}

---
**feature_vector_2** (תיק {r['verdict_2']}):
{r['feature_vector_2']}

---
**הסבר המודל לדמיון בין השניים:**
{r['explanation']}

---
הערך/י את איכות ההסבר בשלושה ממדים (1–3) וכתוב/י הערה קצרה. החזר/י JSON בלבד."""
    last = None
    for i in range(tries):
        try:
            resp = _an.messages.create(
                model=ANN_MODEL, max_tokens=4096,
                thinking={"type": "adaptive"},
                output_config={"effort": "xhigh",
                               "format": {"type": "json_schema", "schema": ANN_SCHEMA}},
                system=[{"type": "text", "text": ANN_SYSTEM,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}])
            return json.loads(next(b.text for b in resp.content if b.type == "text"))
        except Exception as e:
            last = e
            time.sleep(4 * (i + 1))
    raise last


# ---------------------------------------------------------------- main
def main():
    db = pd.read_csv(WEAPON_DB)
    old = pd.read_csv(OLD_FILE)
    pid = {(r["verdict_1"], r["verdict_2"]): int(r["pair_id"]) for _, r in old.iterrows()}

    rows = []
    for _, r in db.iterrows():
        rows.append({"pair_id": pid[(r["verdict_1"], r["verdict_2"])],
                     "verdict_1": r["verdict_1"], "verdict_2": r["verdict_2"],
                     "GT": int(r["similarity_scale"]),
                     "feature_vector_1": r["feature_vector_1"],
                     "feature_vector_2": r["feature_vector_2"]})
    rows.sort(key=lambda x: x["pair_id"])
    print(f"pairs: {len(rows)}")

    print(f"\n[1/2] generating explanations — {GEN_MODEL}")
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(generate, r): r for r in rows}
        for fu in tqdm(as_completed(futs), total=len(rows)):
            r = futs[fu]
            try:
                txt = fu.result()
            except Exception as e:
                txt = ""
                print(f"  !! gen failed pair {r['pair_id']}: {e!r}"[:160])
            r["explanation"] = txt
            r["model_score"] = parse_score(txt)
            r["model_pred_scale"] = scale(r["model_score"]) if r["model_score"] is not None else ""

    bad = [r["pair_id"] for r in rows if r["model_score"] is None]
    if bad:
        print(f"  !! no score parsed for pairs: {bad}")

    print(f"\n[2/2] annotating — {ANN_MODEL}")
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = {ex.submit(annotate, r): r for r in rows}
        for fu in tqdm(as_completed(futs), total=len(rows)):
            r = futs[fu]
            try:
                a = fu.result()
            except Exception as e:
                a = {"נאמנות_עובדתית": "", "רלוונטיות_משפטית": "", "שלמות": "", "הערות": f"ERR {e!r}"[:200]}
            r.update(a)

    cols = ["pair_id", "verdict_1", "verdict_2", "GT", "feature_vector_1", "feature_vector_2",
            "model_score", "model_pred_scale", "explanation",
            "נאמנות_עובדתית", "רלוונטיות_משפטית", "שלמות", "הערות"]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([str(r.get(c, "")) for c in cols])

    df = pd.DataFrame(rows)
    print(f"\nwrote {OUT_CSV}")
    for d in ["נאמנות_עובדתית", "רלוונטיות_משפטית", "שלמות"]:
        s = pd.to_numeric(df[d], errors="coerce")
        print(f"  {d}: mean={s.mean():.2f}  {dict(sorted(s.value_counts().items()))}")


if __name__ == "__main__":
    main()
