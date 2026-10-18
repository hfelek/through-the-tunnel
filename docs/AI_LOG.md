# AI usage log
| Task | What Claude Code generated | What I corrected or overruled |
| --- | --- | --- |
| T0.1 | Repo skeleton: pyproject, sim/ packages, /api/health + test, Vite React app with recharts and proxy, Makefile, .gitignore, doc/test-policy edits | Approved httpx (needed by TestClient, not in the original list). Overrode the test policy: 1–3 smoke tests per task instead of one test per criterion. Told it to keep the existing .gitignore line. Local setup: macOS system Python 3.9 was too old, switched to a Python 3.12 venv. |