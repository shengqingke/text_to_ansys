import json
from pathlib import Path

from text_to_ansys.runtime import CaseManager, MapdlExecutor, MapdlRuntimeConfig, check_mapdl_runtime
from text_to_ansys.schema import cantilever_beam_example


def test_check_mapdl_runtime_does_not_launch_mapdl() -> None:
    info = check_mapdl_runtime()

    assert info["package"] == "ansys-mapdl-core"
    assert info["will_launch_mapdl"] is False
    assert "pymapdl_available" in info


def test_run_case_requires_built_apdl(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    executor = MapdlExecutor(manager)

    result = executor.run_case(case.case_id)

    assert result.status == "failed"
    assert "input.apdl not found" in result.message
    assert (case.case_dir / "run.json").exists()


def test_run_case_records_not_available_when_pymapdl_missing(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    manager.build_case(case.case_id)

    def missing_launch_mapdl(**kwargs):
        raise ImportError("missing PyMAPDL")

    executor = MapdlExecutor(manager, launch_mapdl_func=missing_launch_mapdl)
    result = executor.run_case(case.case_id)

    assert result.status == "not_available"
    assert "PyMAPDL is not installed" in result.message
    assert (case.case_dir / "logs" / "mapdl_error.txt").exists()


def test_run_case_success_with_fake_mapdl(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    manager.build_case(case.case_id)
    exits = []

    class FakeMapdl:
        def input(self, path: str) -> str:
            assert path == "input.apdl"
            return "fake MAPDL output"

        def exit(self) -> None:
            exits.append(True)

    def fake_launch_mapdl(**kwargs):
        assert kwargs["run_location"] == str(case.case_dir.resolve())
        assert kwargs["jobname"] == "unit_test_job"
        return FakeMapdl()

    executor = MapdlExecutor(
        manager,
        MapdlRuntimeConfig(jobname="unit_test_job"),
        launch_mapdl_func=fake_launch_mapdl,
    )
    result = executor.run_case(case.case_id)

    assert result.status == "success"
    assert exits == [True]
    assert (case.case_dir / "logs" / "mapdl_stdout.txt").read_text(encoding="utf-8") == "fake MAPDL output"

    run_json = json.loads((case.case_dir / "run.json").read_text(encoding="utf-8"))
    assert run_json["status"] == "success"
