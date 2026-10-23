"""Real recordings (T10.5a): list them and replay one with a GNSS outage (docs/CONTRACTS.md 3.6)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from sim.contracts.trace import decimate
from sim.estimators import EstimatorFailed, list_estimators
from sim.realdata.replay import REAL_DEFAULTS, replay
from sim.realdata.sensor_logger import DEFAULT_SPAN_S, list_recordings, load_recording

router = APIRouter()
DEFAULT_OUTAGE_S = (515.0, 625.0)  # recording time; turns and hills, the car speeds up from 52 to 90 km/h
MIN_GNSS_BEFORE_S = 60.0  # the filters need this long with GNSS to calibrate the phone and learn the bias


class RealRunRequest(BaseModel):
    outage_start_s: float = DEFAULT_OUTAGE_S[0]
    outage_end_s: float = DEFAULT_OUTAGE_S[1]
    estimators: dict[str, dict] = Field(default_factory=lambda: {"baseline": {}})
    decimate_hz: float = Field(default=10.0, gt=0)


def _known(rec_id: str) -> str:
    if rec_id not in list_recordings():
        raise HTTPException(404, f"unknown recording: {rec_id}")
    return rec_id


@router.get("/api/real")
def recordings() -> list[dict]:
    return [
        {"id": r, "title": r.replace("_", " "), "span_s": list(DEFAULT_SPAN_S), "default_outage_s": list(DEFAULT_OUTAGE_S),
         "default_params": REAL_DEFAULTS}
        for r in list_recordings()
    ]


@router.get("/api/real/{rec_id}")
def recording(rec_id: str) -> Response:
    trace = load_recording(_known(rec_id))
    return Response(decimate(trace, 10.0).model_dump_json(exclude_none=True), media_type="application/json")


@router.post("/api/real/{rec_id}/run")
def run(rec_id: str, req: RealRunRequest) -> Response:
    from sim.api.main import check_estimators  # late import: main includes this router

    t0, t1 = DEFAULT_SPAN_S
    a, b = req.outage_start_s, req.outage_end_s
    if a < t0 + MIN_GNSS_BEFORE_S or b > t1 or b <= a:
        raise HTTPException(422, f"outage must satisfy {t0 + MIN_GNSS_BEFORE_S:g} <= start < end <= {t1:g} s (recording time)")
    check_estimators(req.estimators)
    # the recording's defaults, only for the estimators that have the parameter; values in the request win
    known = {e["id"]: e["params"] for e in list_estimators()}
    estimators = {k: {**{n: v for n, v in REAL_DEFAULTS.items() if n in known[k]}, **p} for k, p in req.estimators.items()}
    trace = load_recording(_known(rec_id))
    try:  # trace time counts from the start of the span
        out = replay(trace, a - t0, b - t0, estimators)
    except EstimatorFailed as e:
        raise HTTPException(422, str(e)) from None
    return Response(decimate(out, req.decimate_hz).model_dump_json(exclude_none=True), media_type="application/json")
