# Mode A — blind labeling

Give the model this whole folder and paste `PROMPT.md`.
Tell it: **Mode A**, input `data_blind/`, output JSON into `output/`.

It must read `RUBRIC.md` and `KNOWN_ISSUES.md` before starting — `PROMPT.md` says so.
`guides/` holds the original human-annotator guides.

723 rows total. Suggested chunking: 47-50 rows per call (`df.iloc[start:end]`),
one JSON per chunk, full coverage — every row read in full, no sampling.

When results are in:

    python3 scripts/agreement.py

prints Cohen's κ per dimension vs our labels and writes `output/disagreements.csv`.
(`data_current/` holds our labels — it exists ONLY for that comparison.
Do NOT show it to the reviewing model; it would break the blindness.)
