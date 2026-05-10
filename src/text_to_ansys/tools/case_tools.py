from __future__ import annotations

from pathlib import Path

from text_to_ansys.parser import parse_text_to_spec
from text_to_ansys.runtime import CaseManager, MapdlExecutor, MapdlRuntimeConfig, check_mapdl_runtime
from text_to_ansys.schema import SimulationSpec, cantilever_beam_example


def create_case_from_text(text: str, *, cases_dir: str | Path = "cases", build: bool = False) -> dict[str, object]:
    parse_result = parse_text_to_spec(text)
    manager = CaseManager(cases_dir)
    case = manager.create_case(parse_result.spec, slug="text_case")
    build_result = None
    if build:
        build_result = manager.build_case(case.case_id)
    info = manager.inspect_case(case.case_id)
    info["assumptions"] = parse_result.assumptions
    info["warnings"] = parse_result.warnings
    if build_result is not None:
        info["required_outputs"] = build_result.required_outputs
        info["build_warnings"] = build_result.warnings
    return info


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


def check_mapdl() -> dict[str, object]:
    return check_mapdl_runtime()


def run_case(
    case_id: str,
    *,
    cases_dir: str | Path = "cases",
    exec_file: str | None = None,
    jobname: str = "text_to_ansys",
) -> dict[str, object]:
    manager = CaseManager(cases_dir)
    executor = MapdlExecutor(manager, MapdlRuntimeConfig(exec_file=exec_file, jobname=jobname))
    return executor.run_case(case_id).to_json_dict()
