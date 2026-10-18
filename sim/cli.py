"""Command-line entry point: python -m sim run scenarios/x.json -o out.json [--estimators baseline,ekf]."""
from __future__ import annotations

import argparse
import sys

from sim.contracts.scenario import load_scenario
from sim.contracts.trace import write_trace
from sim.runner import run_scenario


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="python -m sim")
    sub = p.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="simulate a scenario and write the trace JSON")
    run.add_argument("scenario")
    run.add_argument("-o", "--output", required=True)
    run.add_argument("--estimators", default="", help="comma-separated registry ids (default parameters)")
    args = p.parse_args(argv)
    ids = [i for i in args.estimators.split(",") if i]
    try:
        trace = run_scenario(load_scenario(args.scenario), {i: {} for i in ids})
    except KeyError as e:
        sys.exit(f"unknown estimator id: {e}")
    write_trace(trace, args.output)
