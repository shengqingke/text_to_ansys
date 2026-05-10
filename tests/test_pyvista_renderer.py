from pathlib import Path

from text_to_ansys.post import PyVistaRenderer, check_pyvista_runtime
from text_to_ansys.runtime import CaseManager
from text_to_ansys.schema import cantilever_beam_example


def test_check_pyvista_runtime_does_not_render() -> None:
    info = check_pyvista_runtime()

    assert "pyvista_available" in info
    assert "mapdl_reader_available" in info
    assert info["will_render"] is False


def test_render_displacement_requires_rst(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    renderer = PyVistaRenderer(manager)

    result = renderer.render_displacement(case.case_id)

    assert result.status == "failed"
    assert "No RST file" in result.message


def test_render_displacement_with_fake_reader(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    rst_path = case.case_dir / "text_to_ansys.rst"
    rst_path.write_text("fake rst", encoding="utf-8")
    calls = {}

    class FakeResult:
        def plot_nodal_displacement(self, *args, **kwargs):
            calls["args"] = args
            calls["kwargs"] = kwargs
            Path(kwargs["screenshot"]).write_text("png placeholder", encoding="utf-8")
            return []

    def fake_read_binary(path: str):
        calls["rst_path"] = path
        return FakeResult()

    renderer = PyVistaRenderer(manager, read_binary_func=fake_read_binary)
    result = renderer.render_displacement(case.case_id, component="NORM", displacement_factor=2.0)

    assert result.status == "success"
    assert calls["rst_path"] == str(rst_path.resolve())
    assert calls["args"] == (0,)
    assert calls["kwargs"]["comp"] == "NORM"
    assert calls["kwargs"]["off_screen"] is True
    assert calls["kwargs"]["interactive"] is False
    assert calls["kwargs"]["displacement_factor"] == 2.0
    assert Path(result.artifacts["screenshot"]).exists()


def test_render_result_supports_stress_von_mises(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    rst_path = case.case_dir / "text_to_ansys.rst"
    rst_path.write_text("fake rst", encoding="utf-8")
    calls = {}

    class FakeResult:
        def plot_nodal_stress(self, *args, **kwargs):
            calls["args"] = args
            calls["kwargs"] = kwargs
            Path(kwargs["screenshot"]).write_text("png placeholder", encoding="utf-8")
            return []

    renderer = PyVistaRenderer(manager, read_binary_func=lambda path: FakeResult())
    result = renderer.render_result(case.case_id, field="stress", component="von_mises")

    assert result.status == "success"
    assert "stress" in result.message
    assert calls["args"] == (0,)
    assert calls["kwargs"]["comp"] == "EQV"
    assert result.artifacts["screenshot"].endswith("stress_von_mises.png")


def test_render_result_supports_directional_displacement(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    rst_path = case.case_dir / "text_to_ansys.rst"
    rst_path.write_text("fake rst", encoding="utf-8")
    calls = {}

    class FakeResult:
        def plot_nodal_displacement(self, *args, **kwargs):
            calls["kwargs"] = kwargs
            Path(kwargs["screenshot"]).write_text("png placeholder", encoding="utf-8")
            return []

    renderer = PyVistaRenderer(manager, read_binary_func=lambda path: FakeResult())
    result = renderer.render_result(case.case_id, field="disp", component="y")

    assert result.status == "success"
    assert calls["kwargs"]["comp"] == "Y"
    assert result.artifacts["screenshot"].endswith("disp_y.png")


def test_render_result_rejects_invalid_component(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    rst_path = case.case_dir / "text_to_ansys.rst"
    rst_path.write_text("fake rst", encoding="utf-8")
    renderer = PyVistaRenderer(manager, read_binary_func=lambda path: None)

    result = renderer.render_result(case.case_id, field="stress", component="norm")

    assert result.status == "failed"
    assert "Unsupported stress component" in result.diagnostics[0]


def test_render_displacement_interactive_mode(tmp_path: Path) -> None:
    manager = CaseManager(tmp_path)
    case = manager.create_case(cantilever_beam_example(), slug="cantilever")
    rst_path = case.case_dir / "text_to_ansys.rst"
    rst_path.write_text("fake rst", encoding="utf-8")
    calls = {}

    class FakeResult:
        def plot_nodal_displacement(self, *args, **kwargs):
            calls["kwargs"] = kwargs
            return []

    renderer = PyVistaRenderer(manager, read_binary_func=lambda path: FakeResult())
    result = renderer.render_displacement(case.case_id, interactive=True)

    assert result.status == "success"
    assert "interactive" in result.message
    assert calls["kwargs"]["off_screen"] is False
    assert calls["kwargs"]["interactive"] is True
    assert calls["kwargs"]["screenshot"] is None
    assert "screenshot" not in result.artifacts
