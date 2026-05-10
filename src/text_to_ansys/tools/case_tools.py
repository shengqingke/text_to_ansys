from __future__ import annotations

from pathlib import Path

from text_to_ansys.runtime import CaseManager
from text_to_ansys.schema import SimulationSpec, cantilever_beam_example


def create_case_from_template(template: str, *, cases_dir: str | Path = "cases") -> dict[str, object]:
    if template != "cantilever":
        raise ValueError(f"unknown template: {template}")
    manager = CaseManager(cases_dir)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever_beam")
    return manager.inspect_case(case.case_id)


def create_case_from_spec(spec: SimulationSpec, *, cases_dir: str | Path = "cases") -> dict[str, object]:
    manager = CaseManager(cases_dir)
    case = manager.create_case(spec)
    return manager.inspect_case(case.case_id)


def generate_apdl(case_id: str, *, cases_dir: str | Path = "cases") -> dict[str, object]:
    manager = CaseManager(cases_dir)
    result = manager.build_case(case_id)
    info = manager.inspect_case(case_id)
    info["required_outputs"] = result.required_outputs
    info["warnings"] = result.warnings
    return info


def inspect_case(case_id: str, *, cases_dir: str | Path = "cases") -> dict[str, object]:
    return CaseManager(cases_dir).inspect_case(case_id)

