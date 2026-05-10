from pathlib import Path

from text_to_ansys.runtime import CaseManager
from text_to_ansys.schema import cantilever_beam_example


def test_case_manager_creates_case_and_builds_apdl(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")

    assert case.case_dir.exists()
    assert case.spec_path.exists()
    assert (case.case_dir / "case.yaml").exists()
    assert (case.case_dir / "logs").is_dir()
    assert (case.case_dir / "raw").is_dir()
    assert (case.case_dir / "results" / "plots").is_dir()

    result = manager.build_case(case.case_id)

    assert "SOLVE" in result.script
    assert (case.case_dir / "input.apdl").exists()
    assert (case.case_dir / "input.preview.md").exists()


def test_case_manager_inspect_reports_apdl_state(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")

    before = manager.inspect_case(case.case_id)
    assert before["has_apdl"] is False

    manager.build_case(case.case_id)
    after = manager.inspect_case(case.case_id)

    assert after["has_apdl"] is True
    assert after["analysis_type"] == "static_structural"
    assert after["element"]["type"] == "SOLID186"

