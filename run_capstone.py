#!/usr/bin/env python3
"""
Run the five capstone criteria (criteria.md → "Capstone criteria (Unit 9)")
against the deployed service, one trial per invocation. ← UNIT 9

    python run_capstone.py --label before --trial 1
    python run_capstone.py --label before --trial 2 --url http://localhost:5000

Each trial sends the exact requests criteria.md names, then reads the service's
own structured log back from GET /logs and scores each criterion by the pass
rule written in criteria.md. Everything it saw — every HTTP status, every
response request_id, every log record — is written to
results/capstone_<label>_trial<N>.json, and a readable summary to the matching
.md, so each verdict can be re-checked by hand.

Uses only the standard library, so it runs from any Python 3.11+.
"""

import argparse
import datetime as dt
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent
DEFAULT_URL = "https://fitfindr-v2026.onrender.com"

LOG_FIELDS = [
    "ts", "request_id", "route", "status", "query", "search_method",
    "keyword_results", "semantic_results", "selected_id", "selected_title",
    "selected_price", "similarity", "fit_card_chars", "error", "duration_ms",
    "model_calls", "cache_hits", "prompt_tokens", "output_tokens",
]

C1_QUERIES = ["black boots", "oversized hoodie", "sweater", "summer dress", "laptop charger"]
C2_QUERIES = {
    "retro t-shirt": "tops",
    "slacks": "bottoms",
    "rain coat": "outerwear",
    "trainers": "shoes",
    "handbag": "accessories",
}
C3_QUERIES = [
    "vintage graphic tee under $30", "denim jacket under $50", "graphic tee",
    "vintage denim", "leather", "jacket", "streetwear", "retro t-shirt",
    "oversized hoodie", "sweater",
]


# ── HTTP ─────────────────────────────────────────────────────────────────────

def http(method, url, body=None, raw=None, timeout=180):
    """Return (status, parsed JSON or None, seconds). Never raises on HTTP errors."""
    data, headers = None, {}
    if raw is not None:
        data = raw.encode()
        headers["Content-Type"] = "text/plain"
    elif body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, text = resp.status, resp.read().decode()
    except urllib.error.HTTPError as exc:
        status, text = exc.code, exc.read().decode(errors="replace")
    except Exception as exc:  # noqa: BLE001 — a timeout or reset is a result too
        return None, {"client_error": f"{type(exc).__name__}: {exc}"}, time.perf_counter() - started
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"raw_text": text[:300]}
    return status, parsed, time.perf_counter() - started


def ask(base, query=None, raw=None, body=None):
    if raw is None and body is None:
        body = {"query": query}
    status, payload, secs = http("POST", f"{base}/ask", body=body, raw=raw)
    sent = raw if raw is not None else body
    rid = payload.get("request_id") if isinstance(payload, dict) else None
    print(f"    {status} {secs:6.1f}s  {json.dumps(sent)[:60]}", flush=True)
    return {"sent": sent, "http_status": status, "client_seconds": round(secs, 2),
            "request_id": rid}


def fetch_logs(base):
    _, records, _ = http("GET", f"{base}/logs?n=500")
    return records if isinstance(records, list) else []


def attach(requests_sent, records):
    """Attach the log record(s) whose request_id matches each response."""
    for r in requests_sent:
        matches = [rec for rec in records if r["request_id"] and rec.get("request_id") == r["request_id"]]
        r["log_matches"] = len(matches)
        r["log"] = matches[0] if matches else None


# ── criteria ─────────────────────────────────────────────────────────────────

def c1(base):
    sent = [ask(base, q) for q in C1_QUERIES]
    return sent


def c2(base):
    return [ask(base, q) for q in C2_QUERIES]


def c3(base):
    status, payload, secs = http("GET", f"{base}/health")
    health = {"http_status": status, "seconds": round(secs, 3)}
    print(f"    /health {status} {secs:.3f}s", flush=True)
    return health, [ask(base, q) for q in C3_QUERIES]


def c4(base):
    return [
        ask(base, "vintage graphic tee under $30"),
        ask(base, "retro t-shirt"),
        ask(base, "laptop charger"),
        ask(base, ""),
        ask(base, raw="this is not json"),
    ]


def c5(base):
    return [
        ask(base, ""),
        ask(base, ""),
        ask(base, raw="this is not json"),
        ask(base, raw="{broken json"),
        ask(base, body={"query": 123}),
    ]


def score(results, categories):
    out = {}

    # 1 — keyword_results 0 and model_calls >= 1 (the embedding call)
    rows = []
    for r in results["c1"]:
        log = r["log"] or {}
        ok = r["log"] is not None and log.get("keyword_results") == 0 and (log.get("model_calls") or 0) >= 1
        rows.append(ok)
    out["c1"] = {"passed": sum(rows), "of": len(rows), "met": sum(rows) == 5, "per_request": rows}

    # 2 — selected listing's category matches, or nothing returned
    rows, detail = [], []
    for r, (q, expected) in zip(results["c2"], C2_QUERIES.items()):
        log = r["log"] or {}
        sid = log.get("selected_id")
        got = categories.get(sid) if sid else None
        ok = r["log"] is not None and (log.get("search_method") is None or got == expected)
        rows.append(ok)
        detail.append({"query": q, "expected": expected, "selected_id": sid,
                       "selected_title": log.get("selected_title"), "category": got,
                       "similarity": log.get("similarity"), "pass": ok})
    out["c2"] = {"passed": sum(rows), "of": len(rows), "met": sum(rows) >= 3, "detail": detail}

    # 3 — mean duration_ms of matched runs <= 15000, after a /health under 1s
    health = results["c3_health"]
    matched = [r["log"]["duration_ms"] for r in results["c3"]
               if r["log"] and r["log"].get("search_method") is not None]
    excluded = [r["sent"]["query"] for r in results["c3"]
                if not (r["log"] and r["log"].get("search_method") is not None)]
    mean_ms = statistics.mean(matched) if matched else None
    warm = health["http_status"] == 200 and health["seconds"] < 1.0
    out["c3"] = {"warm": warm, "health_seconds": health["seconds"], "matched_runs": len(matched),
                 "excluded": excluded, "mean_s": round(mean_ms / 1000, 2) if mean_ms else None,
                 "max_s": round(max(matched) / 1000, 2) if matched else None,
                 "met": bool(warm and mean_ms is not None and mean_ms <= 15000)}

    # 4 — each response's request_id matches exactly one record with all 19 fields
    rows = []
    for r in results["c4"]:
        log = r["log"] or {}
        ok = (r["log_matches"] == 1 and all(k in log for k in LOG_FIELDS)
              and log.get("request_id") is not None)
        rows.append(ok)
    out["c4"] = {"passed": sum(rows), "of": len(rows), "met": sum(rows) == 5, "per_request": rows}

    # 5 — HTTP 400 and a log record with status 400
    rows = []
    for r in results["c5"]:
        ok = r["http_status"] == 400 and r["log"] is not None and r["log"].get("status") == 400
        rows.append(ok)
    out["c5"] = {"passed": sum(rows), "of": len(rows), "met": sum(rows) == 5, "per_request": rows}
    return out


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--trial", type=int, required=True)
    ap.add_argument("--url", default=DEFAULT_URL)
    args = ap.parse_args()
    base = args.url.rstrip("/")

    listings = json.loads((ROOT / "data" / "listings.json").read_text(encoding="utf-8"))
    listings = listings if isinstance(listings, list) else listings.get("listings", [])
    categories = {l["id"]: l["category"] for l in listings}

    started = dt.datetime.now(dt.timezone.utc)
    print(f"Trial {args.trial} ({args.label}) against {base}", flush=True)
    results = {}
    print("  criterion 1", flush=True); results["c1"] = c1(base)
    print("  criterion 2", flush=True); results["c2"] = c2(base)
    print("  criterion 3", flush=True); results["c3_health"], results["c3"] = c3(base)
    print("  criterion 4", flush=True); results["c4"] = c4(base)
    print("  criterion 5", flush=True); results["c5"] = c5(base)

    records = fetch_logs(base)
    for key in ("c1", "c2", "c3", "c4", "c5"):
        attach(results[key], records)
    scores = score(results, categories)

    out = ROOT / "results" / f"capstone_{args.label}_trial{args.trial}"
    out.with_suffix(".json").write_text(json.dumps({
        "label": args.label, "trial": args.trial, "url": base,
        "started": started.isoformat(timespec="seconds"),
        "finished": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "scores": scores, "results": results,
    }, indent=2, ensure_ascii=False))

    s = scores
    lines = [
        f"# Capstone run — {args.label}, trial {args.trial}",
        "",
        f"- Produced by: `run_capstone.py::main` against {base}",
        f"- Started: {started.isoformat(timespec='seconds')}",
        f"- Raw responses and log records: `{out.with_suffix('.json').name}`",
        "",
        "| Criterion | Target | Result | Met |",
        "|---|---|---|---|",
        f"| 1. semantic_search runs after empty keyword search | 5 of 5 | {s['c1']['passed']}/5 | {s['c1']['met']} |",
        f"| 2. semantic pick is in the expected category (or nothing) | 3 of 5 | {s['c2']['passed']}/5 | {s['c2']['met']} |",
        f"| 3. warm mean duration_ms of matched runs | ≤ 15.0 s | {s['c3']['mean_s']} s over {s['c3']['matched_runs']} (health {s['c3']['health_seconds']} s) | {s['c3']['met']} |",
        f"| 4. every request has one complete log record | 5 of 5 | {s['c4']['passed']}/5 | {s['c4']['met']} |",
        f"| 5. bad input → 400 and logged | 5 of 5 | {s['c5']['passed']}/5 | {s['c5']['met']} |",
        "",
        "## Criterion 2 detail",
        "",
        "| Query | Expected | Selected | Category | Similarity | Pass |",
        "|---|---|---|---|---|---|",
    ]
    for d in s["c2"]["detail"]:
        lines.append(f"| {d['query']} | {d['expected']} | {d['selected_title']} | {d['category']} | {d['similarity']} | {d['pass']} |")
    lines += ["", f"Criterion 3: excluded (no match): {s['c3']['excluded'] or 'none'}; max {s['c3']['max_s']} s", ""]
    out.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines[6:13]))
    print(f"\nWrote {out.with_suffix('.md').relative_to(ROOT)} and .json")


if __name__ == "__main__":
    main()
