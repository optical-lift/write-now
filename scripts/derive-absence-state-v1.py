#!/usr/bin/env python3
"""Reference derivation for Absence-State Model v1.

Reads one JSON object from stdin containing:
  instantiation_evidence
  opportunity_status
  observability_status
  compatibility_status
  coverage_status

Prints the derived absence state.
"""
from __future__ import annotations
import json, sys

def derive(a: dict[str, str]) -> str:
    if a["instantiation_evidence"] == "OBSERVED_PRESENT":
        return "PRESENT"
    if a["observability_status"] == "NOT_PRESERVED":
        return "NOT_PRESERVED"
    if a["observability_status"] in {"UNMEASURED", "INADEQUATE"}:
        return "MEASUREMENT_UNRESOLVED"
    if a["opportunity_status"] == "OUTSIDE_EXPOSED_REGION":
        return "OUTSIDE_EXPOSED_REGION"
    if (
        a["instantiation_evidence"] == "NOT_OBSERVED"
        and a["opportunity_status"] == "DEMONSTRATED"
        and a["compatibility_status"] == "PROHIBITED"
        and a["observability_status"] == "ADEQUATE"
    ):
        return "OPPORTUNITY_PRESENT_PROHIBITED"
    if (
        a["instantiation_evidence"] == "NOT_OBSERVED"
        and a["compatibility_status"] == "STRUCTURALLY_INCOMPATIBLE"
        and a["observability_status"] == "ADEQUATE"
    ):
        return "STRUCTURALLY_INCOMPATIBLE"
    if (
        a["instantiation_evidence"] == "NOT_OBSERVED"
        and a["opportunity_status"] == "DEMONSTRATED"
        and a["compatibility_status"] == "COMPATIBLE"
        and a["observability_status"] == "ADEQUATE"
        and a["coverage_status"] == "ADEQUATE"
    ):
        return "OPPORTUNITY_PRESENT_NO_INSTANCE"
    if (
        a["instantiation_evidence"] == "NOT_OBSERVED"
        and a["opportunity_status"] in {"POSSIBLE", "NONE"}
        and a["compatibility_status"] == "COMPATIBLE"
        and a["coverage_status"] == "ADEQUATE"
    ):
        return "COMPATIBLE_UNUSED"
    if (
        a["instantiation_evidence"] != "OBSERVED_PRESENT"
        and (
            a["opportunity_status"] == "POSSIBLE"
            or a["coverage_status"] in {"PARTIAL", "NOT_SAMPLED"}
            or (
                a["opportunity_status"] == "DEMONSTRATED"
                and a["coverage_status"] != "ADEQUATE"
            )
        )
    ):
        return "NOT_YET_OBSERVED"
    return "UNKNOWN_ABSENCE"

def main() -> None:
    payload=json.load(sys.stdin)
    print(derive(payload))

if __name__ == "__main__":
    main()
