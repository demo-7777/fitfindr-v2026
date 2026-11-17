# Capstone run — after, trial 3

- Produced by: `run_capstone.py::main` against https://fitfindr-v2026.onrender.com
- Started: 2026-11-17T20:41:56+00:00
- Raw responses and log records: `capstone_after_trial3.json`

| Criterion | Target | Result | Met |
|---|---|---|---|
| 1. semantic_search runs after empty keyword search | 5 of 5 | 5/5 | True |
| 2. semantic pick is in the expected category (or nothing) | 3 of 5 | 5/5 | True |
| 3. warm mean duration_ms of matched runs | ≤ 15.0 s | 12.67 s over 10 (health 0.071 s) | True |
| 4. every request has one complete log record | 5 of 5 | 5/5 | True |
| 5. bad input → 400 and logged | 5 of 5 | 5/5 | True |

## Criterion 2 detail

| Query | Expected | Selected | Category | Similarity | Pass |
|---|---|---|---|---|---|
| retro t-shirt | tops | Graphic Tee — 2003 Tour Bootleg Style | tops | 0.6175 | True |
| slacks | bottoms | None | None | None | True |
| rain coat | outerwear | None | None | None | True |
| trainers | shoes | None | None | None | True |
| handbag | accessories | None | None | None | True |

Criterion 3: excluded (no match): none; max 52.94 s
