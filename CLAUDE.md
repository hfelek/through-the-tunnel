# CLAUDE.md — Through the Tunnel

Simulator for estimating a car's position in a GPS-denied tunnel (Pointr case study).
Python core (`sim/`), FastAPI (`sim/api/`), React + Vite in plain JavaScript (`web/`).
Everything in English: replies, code, comments, commit messages, docs.

## Where things are (read only what the task needs)

- `PLAN.md` is long. Never read it whole. Read only the current task:
  `grep -n -A 10 '\*\*T2.1 ' PLAN.md` (replace T2.1; read more lines if the task continues).
- `docs/CONTRACTS.md`: list sections with `grep -n '^###' docs/CONTRACTS.md`,
  then read only the sections the task touches.
- Fresh cloud environment: run `pip install -q -e '.[dev]'` once at session start.
  Always run tests as `python -m pytest -q`.
- `docs/ASSUMPTIONS.md`: numbered assumptions (A1, A2, ...). Read when the task mentions one.
- `docs/CODE_TOUR.md`: where every part of the code lives, how data flows, and recipes for
  common changes. Read only the section of the module you touch.

## Budget rules (credit is limited)

- One phase per session, one commit per task. After each task, stop and wait for "next".
- For tasks that create or change 3 or more files: first reply with a short plan
  (max 8 lines: files, main functions, tests) and wait for "ok". Smaller tasks: just do them.
- Never read: `data/`, `out/`, `docs/figures/`, `web/node_modules/`, `web/dist/`, lock files.
  For any large file use `head`, `wc -l` or `grep`.
- Do not re-read a file already in context unless it changed.
- Edit with minimal diffs. Never rewrite a whole file to change a few lines.
- Keep command output short: `python -m pytest -q -x`, `ruff check -q`, pipe long output to `tail -n 30`.
- Do not start long-running processes (`make dev`, `uvicorn`, `npm run dev`).
  The user runs and checks the app in the browser.
- Stay inside the task. No refactors or "improvements" to finished tasks.
  Ideas go into one "Suggestions" line in the final reply.
- If the same error survives 2 fix attempts: stop, summarize in max 5 lines, ask.
- No dependencies beyond those listed in task T0.1 without asking.
- Final reply per task: max 10 lines (what changed, test result, suggestions).
- Acceptance thresholds are targets. When one is missed, report the numbers with one
  diagnosis and stop. Do not run extra experiments or try alternative fixes unless asked.
  One-off tables only on the scenarios named in the task. Keep reports short.

## Tasks done outside Claude Code

Tasks tagged `[claude.ai]` in PLAN.md are done by the user in Claude.ai. Do not do them.
If asked to, reply "This task is tagged [claude.ai]." and stop.

## Contracts (never change without asking)

- If a task seems to need a change to `docs/CONTRACTS.md`: STOP and ask.
  After approval: update `docs/CONTRACTS.md` first, then the code.
- Units: SI (s, m, m/s, m/s², rad, rad/s). Pressure hPa, magnetic field µT.
  Human-facing JSON fields carry suffixes: `_kmh`, `_deg`, `_pct`.
- World frame: local ENU, origin at road start. Position along road: arc length `s` (m).
- Vehicle frame: x forward, y left, z up.
- Phone frame: Android convention (x right, y up the screen, z out of the screen).
  Accelerometer = specific force: phone flat, face up, reads z = +9.81.
  iOS conversion happens only in `sim/realdata/`.
- Trace JSON is columnar (one list per field). Missing sensor = field absent, never nulls.

## Hard rules

- Estimators never see truth. Code under `sim/estimators/` may use `RoadMap` and the
  `Measurement`/`Estimate` types, but must not import vehicle motion, sensor generation
  or anything that reads `trace.truth`.
- Estimators are causal: state changes only through `update(m)`, in time order.
- Determinism: all randomness via a seeded `numpy.random.Generator` passed in. No global `np.random`.
- Physical sensor and environment parameters need a source: in Python a comment
  (datasheet, paper, `# A7`), in JSON a `source` field. Estimator tuning parameters
  only need to live in config, not in code.
- New estimators register via the registry decorator. Never hardcode estimator names in `web/`.

## Code style

- Python 3.11+, type hints, Pydantic v2 for contracts, NumPy vectorized where it matters.
  Small pure functions. One-line docstrings unless the math needs more.
- Explainability: the user must be able to explain and change every line in an interview.
  Prefer straightforward code over clever code. Short functions with one job.
  A short comment explaining WHY on every non-obvious line; formulas cite the design
  note or the A-number. No new abstraction unless it removes real duplication.
- JavaScript only (no TypeScript). React function components + hooks.
  CSS modules or inline styles. Charts with Recharts. No other UI framework.
- Tests stay light: per task 1–3 short smoke tests in one file (runs, right
  shape, one key sanity check). Check remaining acceptance criteria with a
  one-off command and report the result in one line. Frontend is checked
  manually by the user.

## Definition of done (every task)

1. Acceptance criteria met; `python -m pytest -q` green; `ruff check -q` clean.
2. One commit: `T2.1: short description` (task ID first).
3. Update the relevant section of `docs/CODE_TOUR.md` in the same commit (new or moved
   functions, changed line references, new recipes or tests).
4. End your final reply with one line: `AI log: <what you generated>`.

## Git
- Push the task commit to your working branch. Never open a pull request;
  the user merges into main.
