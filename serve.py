#!/usr/bin/env python3
"""
FitFindr over HTTP. ← UNIT 9

    python serve.py                       run it on your machine
    gunicorn serve:app                    run it the way a host runs it

Everything else in this repo exits after one command. A host has nothing to
keep running, so a command line cannot be deployed. This file is the smallest
thing that can: it starts a web server, waits, and hands each request to the
same `run_agent()` your CLI calls. **No new agent logic lives here.** If your
loop works from `python app.py ask`, it works from here; if it doesn't, fix it
there, not in this file.

Two routes:

    POST /ask       {"query": "vintage graphic tee under $30",
                     "wardrobe": {...}}     ← wardrobe is optional
    GET  /health    is it awake?

`/ask` returns the session dict from `run_agent()` as JSON, unchanged — the
same keys you print from the command line, including `error`. Read
`session["error"]` first, exactly as you do everywhere else.

It runs **one request at a time**, and one route is deliberately slower than a
web server has to be. The reason is worth reading before you deploy: see the
note above `_one_at_a_time` below — it also decides which gunicorn worker you
can use.

UNIT 9 (capstone): structured logging now added — see "structured request
log" below, and GET /logs.

⚠️ (Original starter note) There is deliberately NO logging, NO timing and NO
request counting in this file. That is unit 9's follow-along: you instrument this yourself, first, and
then deploy it. A structured log you were handed teaches you nothing about
what belongs in one — and the timing field is the one everybody skips.
"""

import datetime as dt
import json
import os
import sys
import threading
import time
import uuid
from pathlib import Path

# config first, and before anything that talks to the model: it loads your .env
# and fixes the Windows console encoding for every module that imports it.
import config  # noqa: F401

from flask import Flask, jsonify, request

import generate
from agent import run_agent
from utils.data_loader import get_example_wardrobe

app = Flask(__name__)


# ── structured request log ← UNIT 9 (capstone) ───────────────────────────────
# One JSON object per line, one line per /ask request — including rejected
# (400) and crashed (500) ones. Written to logs/requests.jsonl AND printed to
# stdout, because a free host wipes the disk when it sleeps but keeps stdout in
# its dashboard. GET /logs reads the file back.

LOG_FILE = Path(os.getenv("FITFINDR_LOG", Path(__file__).parent / "logs" / "requests.jsonl"))
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
_log_lock = threading.Lock()


def _usage_snapshot() -> dict:
    tokens = generate.token_counts()
    timing = generate.timing_counters()
    return {
        "calls": generate.call_count(),
        "cache_hits": generate._cache_hits,
        "prompt": tokens["prompt"],
        "output": tokens["output"],
        **timing,
    }


def _write_log(record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False)
    with _log_lock:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    print(f"[request] {line}", flush=True)


def _log_record(request_id, started, query, status, session=None,
                error=None, before=None) -> dict:
    """Build one log record from whatever the request got as far as."""
    after = _usage_snapshot()
    before = before or after
    selected = (session or {}).get("selected_item") or {}
    return {
        "ts": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
        "request_id": request_id,
        "route": "/ask",
        "status": status,
        "query": query,
        "search_method": (session or {}).get("search_method"),
        "keyword_results": len((session or {}).get("search_results") or []),
        "semantic_results": len((session or {}).get("semantic_results") or []),
        "selected_id": selected.get("id"),
        "selected_title": selected.get("title"),
        "selected_price": selected.get("price"),
        "similarity": selected.get("similarity"),
        "fit_card_chars": len((session or {}).get("fit_card") or ""),
        "error": error if error is not None else (session or {}).get("error"),
        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        "model_calls": after["calls"] - before["calls"],
        "cache_hits": after["cache_hits"] - before["cache_hits"],
        "prompt_tokens": after["prompt"] - before["prompt"],
        "output_tokens": after["output"] - before["output"],
        # UNIT 9 latency breakdown: per-stage wall clock, and how much of it
        # was our own limiter sleeping vs. the service answering
        "stages_ms": (session or {}).get("timings_ms") or {},
        "limiter_wait_ms": round((after["limiter_wait_s"] - before["limiter_wait_s"]) * 1000, 1),
        "backoff_ms": round((after["backoff_s"] - before["backoff_s"]) * 1000, 1),
        "api_ms": round((after["api_s"] - before["api_s"]) * 1000, 1),
        "retries": after["retries"] - before["retries"],
    }


# ── one request at a time ─────────────────────────────────────────────────────
# Here's why this exists.
#
# A web server will happily run two requests at once. Two things in this repo
# assume otherwise:
#
#   • If you moved a tool onto MCP in unit 4, `mcp_client.call_tool` starts
#     `mcp_server.py` as a separate process over stdio, one per call. Two
#     overlapping requests means two extra Python interpreters, and the free
#     tier you're deploying to has 512 MB for all of it. That is the reason
#     that would still be here even if everything else were perfect.
#   • `generate.py`'s pacing window and its call counter are plain module
#     globals — deliberately, because that file is teaching pacing and quota,
#     not locking. Two threads sharing them means the per-minute limiter is
#     counting something that isn't true.
#
# What the lock covers is exactly the agent run: the part that spawns
# processes and calls the model. Reading the request, rejecting a bad one, and
# turning the answer into JSON all happen outside it — so a request with a
# malformed body comes straight back with a 400 instead of queueing behind
# somebody else's agent.
#
# Serialising the runs costs you nothing here — this is one user asking one
# question — and it keeps the deployed behaviour identical to the CLI's. When
# that stops being an acceptable trade, the fix is a real queue, not a bigger
# lock.
#
# The same constraint decides your start command, and this is the part that
# bites in deployment rather than on your machine. `mcp_client.call_tool`
# wraps `asyncio.run()`, and `asyncio.run()` refuses to start when an event
# loop is already running. An async worker always has one running. So under
# `gunicorn -k gevent` (or `-k eventlet`, or `serve:app` wrapped for an ASGI
# server like uvicorn) EVERY MCP call fails with "asyncio.run() cannot be
# called from a running event loop" — not some of them under load, all of
# them, every time, in a place your laptop never showed you.
#
#     gunicorn serve:app              ← right: the DEFAULT sync worker
#     gunicorn -k gevent serve:app    ← breaks every MCP call you make

_one_at_a_time = threading.Lock()


@app.get("/health")
def health():
    """Is the server awake? A host pings something like this to find out."""
    return jsonify({"status": "ok"})


@app.post("/ask")
def ask():
    """
    Run the agent on one query.

    In:   {"query": "...", "wardrobe": {...}}   wardrobe optional — leave it
                                                out and you get the same
                                                example wardrobe the CLI uses.
    Out:  the session dict from run_agent(), as JSON.
    """
    started = time.perf_counter()
    request_id = uuid.uuid4().hex[:8]

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        payload = {}
    raw_query = payload.get("query")
    query = raw_query.strip() if isinstance(raw_query, str) else ""
    if not query:
        # 400 rather than a stack trace: the caller can act on this one.
        message = ("Send JSON with a 'query' field, e.g. "
                   '{"query": "vintage graphic tee under $30"}')
        _write_log(_log_record(request_id, started, raw_query, 400, error=message))
        return jsonify({"error": message, "request_id": request_id}), 400

    wardrobe = payload.get("wardrobe")
    if not isinstance(wardrobe, dict):
        wardrobe = get_example_wardrobe()

    # A queued request should look like a queued request. Without this the
    # second caller just sits there, and "slow" and "waiting its turn" are
    # indistinguishable from the outside — which is how people conclude the
    # deployment is broken when it is behaving exactly as designed.
    #
    # This is NOT the logging you add in the follow-along. It prints nothing
    # on the normal path, carries no timing and counts nothing; it says only
    # that this request had to wait. `locked()` can be a moment out of date,
    # so the note is occasionally missed — which costs nothing, because
    # nothing depends on it.
    if _one_at_a_time.locked():
        print(
            "  [serve] another request is still running. This one is waiting "
            "its turn — serve.py handles one at a time, on purpose.",
            file=sys.stderr,
            flush=True,
        )

    failure = None
    session = None
    with _one_at_a_time:
        # Snapshot inside the lock so the counter deltas belong to this run only
        before = _usage_snapshot()
        try:
            session = run_agent(query, wardrobe)
        except Exception as exc:  # noqa: BLE001 — a 500 with a sentence beats a hang
            failure = f"{type(exc).__name__}: {exc}"
        record = _log_record(request_id, started, query,
                             500 if failure else 200,
                             session=session, error=failure, before=before)

    # Outside the lock: building a response is not work the next caller should
    # be waiting on.
    _write_log(record)
    if failure is not None:
        return jsonify({"error": failure, "request_id": request_id}), 500

    return jsonify({**session, "request_id": request_id})


@app.get("/logs")
def logs():
    """The last N log records (default 50) — the disk copy, while it lasts."""
    n = request.args.get("n", default=50, type=int)
    if not LOG_FILE.exists():
        return jsonify([])
    with _log_lock:
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
    return jsonify([json.loads(line) for line in lines[-max(n, 0):] if line.strip()])


if __name__ == "__main__":
    # PORT and 0.0.0.0 are not decoration. A host tells you which port to
    # listen on through PORT, and it reaches your process from outside the
    # container — bind 127.0.0.1 and nothing but the container itself can
    # connect, which looks exactly like a broken app from the browser.
    port = int(os.getenv("PORT", "5000"))

    # Never on by default. Flask's debugger executes code typed into a browser,
    # and a deployed app with it on is a stranger's shell. Set AI201_DEBUG=1 in
    # your own terminal when you want the reloader.
    debug = os.getenv("AI201_DEBUG", "0") == "1"

    print(f"\nFitFindr is listening on http://localhost:{port}")
    print("It runs one request at a time — a second one waits for the first.")
    print("Ask it something (single quotes, as always):\n")
    print(
        f"  curl -X POST http://localhost:{port}/ask \\\n"
        f"    -H 'Content-Type: application/json' \\\n"
        f"    -d '{{\"query\": \"vintage graphic tee under $30\"}}'\n"
    )
    print("Ctrl-C to stop.\n")

    app.run(host="0.0.0.0", port=port, debug=debug)
