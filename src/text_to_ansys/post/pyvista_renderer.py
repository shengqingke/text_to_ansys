from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from text_to_ansys.runtime import CaseManager


@dataclass(frozen=True)
class PyVistaRenderResult:
    status: str
    case_id: str
    message: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    def to_json_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_pyvista_runtime() -> Dict[str, Any]:
    return {
        "pyvista_available": importlib.util.find_spec("pyvista") is not None,
        "mapdl_reader_available": _module_available("ansys.mapdl.reader"),
        "will_render": False,
        "message": "This check only verifies optional visualization imports; it does not read RST files.",
    }


class PyVistaRenderer:
    def __init__(
        self,
        manager: CaseManager,
        *,
        read_binary_func: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.manager = manager
        self._read_binary_func = read_binary_func

    def render_displacement(
        self,
        case_id: str,
        *,
        rst_path: str | Path | None = None,
        result_index: int = 0,
        component: str = "NORM",
        show_displacement: bool = True,
        displacement_factor: float = 1.0,
    ) -> PyVistaRenderResult:
        case_dir = self.manager.case_dir(case_id).resolve()
        selected_rst = Path(rst_path).resolve() if rst_path else self._find_rst(case_dir)
        plots_dir = case_dir / "results" / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = plots_dir / f"displacement_{component.lower()}.png"

        if selected_rst is None:
            return PyVistaRenderResult(
                status="failed",
                case_id=case_id,
                message="No RST file found for this case.",
                artifacts={"plots_dir": str(plots_dir)},
                diagnostics=["Run MAPDL first, or pass an explicit RST path."],
            )
        if not selected_rst.exists():
            return PyVistaRenderResult(
                status="failed",
                case_id=case_id,
                message=f"RST file does not exist: {selected_rst}",
                artifacts={"rst": str(selected_rst)},
                diagnostics=[],
            )

        try:
            read_binary = self._read_binary_func or self._load_read_binary()
            result = read_binary(str(selected_rst))
            result.plot_nodal_displacement(
                result_index,
                comp=component,
                show_displacement=show_displacement,
                displacement_factor=displacement_factor,
                off_screen=True,
                interactive=False,
                screenshot=str(screenshot_path),
                background="white",
                show_edges=True,
            )
            return PyVistaRenderResult(
                status="success",
                case_id=case_id,
                message="Rendered displacement plot with PyVista.",
                artifacts={"rst": str(selected_rst), "screenshot": str(screenshot_path)},
                diagnostics=[],
            )
        except ImportError as exc:
            return PyVistaRenderResult(
                status="not_available",
                case_id=case_id,
                message="PyVista rendering dependencies are not available.",
                artifacts={"rst": str(selected_rst)},
                diagnostics=[str(exc)],
            )
        except Exception as exc:
            return PyVistaRenderResult(
                status="failed",
                case_id=case_id,
                message="PyVista rendering failed.",
                artifacts={"rst": str(selected_rst), "screenshot": str(screenshot_path)},
                diagnostics=[str(exc)],
            )

    def _find_rst(self, case_dir: Path) -> Optional[Path]:
        candidates = sorted(case_dir.glob("*.rst")) + sorted((case_dir / "raw").glob("*.rst"))
        if not candidates:
            return None
        return candidates[0]

    def _load_read_binary(self) -> Callable[[str], Any]:
        try:
            from ansys.mapdl import reader as pymapdl_reader
        except ImportError as exc:
            raise ImportError("Could not import ansys.mapdl.reader.") from exc
        return pymapdl_reader.read_binary


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False

