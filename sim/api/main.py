import json
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sim.contracts.scenario import Scenario
from sim.contracts.trace import decimate
from sim.estimators import EstimatorFailed, list_estimators, validate_params
from sim.runner import run_scenario

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "scenarios"
PRESETS = ROOT / "presets"
ID_RE = re.compile(r"^[a-z0-9_]+$")

app = FastAPI(title="Through the Tunnel")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["GET", "POST"])


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class SimulateRequest(BaseModel):
    scenario: Scenario
    estimators: dict[str, dict] = Field(default_factory=lambda: {"baseline": {}})
    decimate_hz: float = Field(default=10.0, gt=0)
    callout_k: float = 1.0


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, str]]:
    out = []
    for path in sorted(SCENARIOS.glob("*.json")):
        data = json.loads(path.read_text())
        out.append({"id": data["id"], "title": data.get("title") or data["id"], "description": data.get("description", "")})
    return sorted(out, key=lambda x: x["id"])


@app.get("/api/scenarios/{scenario_id}")
def scenario(scenario_id: str) -> dict:
    if not ID_RE.fullmatch(scenario_id):
        raise HTTPException(422, f"invalid scenario id: {scenario_id!r}")
    path = SCENARIOS / f"{scenario_id}.json"
    if not path.is_file():
        raise HTTPException(404, f"unknown scenario: {scenario_id}")
    return json.loads(path.read_text())


@app.get("/api/estimators")
def estimators() -> list[dict]:
    return list_estimators()


@app.get("/api/presets")
def presets() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(PRESETS.glob("*.json"))}


@app.post("/api/simulate")
def simulate(req: SimulateRequest) -> Response:
    known = {e["id"] for e in list_estimators()}
    for key in req.estimators:
        if key not in known:
            raise HTTPException(422, f"unknown estimator: {key}")
    for key, params in req.estimators.items():
        try:
            validate_params(key, params)
        except (ValueError, TypeError) as e:
            raise HTTPException(422, str(e)) from None
    try:
        trace = run_scenario(req.scenario, req.estimators, callout_k=req.callout_k)
    except EstimatorFailed as e:
        raise HTTPException(422, str(e)) from None
    body = decimate(trace, req.decimate_hz).model_dump_json(exclude_none=True)
    return Response(body, media_type="application/json")
