# Gunicorn reads this file automatically when started from the repo root,
# so the start command stays `gunicorn serve:app`. ← UNIT 9 (capstone)

# Default is 30 s. One /ask run (MCP search + up to two Gemini calls, plus an
# embedding call on the semantic path) measured 25–31 s on Render's free tier,
# so the default killed the worker mid-request: the caller got a 500 and the
# run never reached the structured log. 120 s leaves room for generate.py's
# rate-limit waits.
timeout = 120

# Keep the default sync worker — an async worker breaks every MCP call (see serve.py).
worker_class = "sync"
workers = 1
