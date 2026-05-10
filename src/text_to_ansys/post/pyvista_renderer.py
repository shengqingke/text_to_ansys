from __future__ import annotations

import importlib.util
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from text_to_ansys.runtime import CaseManager


FIELD_COMPONENTS = {
    "disp": {"norm": "NORM", "x": "X", "y": "Y", "z": "Z"},
    "stress": {
        "x": "X",
        "y": "Y",
        "z": "Z",
        "xy": "XY",
        "yz": "YZ",
        "xz": "XZ",
        "eqv": "VON_MISES",
        "von_mises": "VON_MISES",
        "von-mises": "VON_MISES",
        "mises": "VON_MISES",
    },
}


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
        plotter_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.manager = manager
        self._read_binary_func = read_binary_func
        self._plotter_factory = plotter_factory

    def render_displacement(
        self,
        case_id: str,
        *,
        rst_path: str | Path | None = None,
        result_index: int = 0,
        component: str = "NORM",
        show_displacement: bool = True,
        displacement_factor: float = 1.0,
        interactive: bool = False,
    ) -> PyVistaRenderResult:
        return self.render_result(
            case_id,
            rst_path=rst_path,
            field="disp",
            component=component,
            result_index=result_index,
            show_displacement=show_displacement,
            displacement_factor=displacement_factor,
            interactive=interactive,
        )

    def render_result(
        self,
        case_id: str,
        *,
        rst_path: str | Path | None = None,
        field: str = "disp",
        component: str = "norm",
        result_index: int = 0,
        show_displacement: bool = True,
        displacement_factor: float = 1.0,
        interactive: bool = False,
    ) -> PyVistaRenderResult:
        case_dir = self.manager.case_dir(case_id).resolve()
        selected_rst = Path(rst_path).resolve() if rst_path else self._find_rst(case_dir)
        plots_dir = case_dir / "results" / "plots"
        plots_dir.mkdir(parents=True, exist_ok=True)
        try:
            normalized_field, normalized_component, pyansys_component = self._normalize_render_request(field, component)
        except ValueError as exc:
            return PyVistaRenderResult(
                status="failed",
                case_id=case_id,
                message="Invalid render request.",
                artifacts={"plots_dir": str(plots_dir)},
                diagnostics=[str(exc)],
            )
        screenshot_path = plots_dir / f"{normalized_field}_{normalized_component}.png"

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
            screenshot = None if interactive else str(screenshot_path)
            if normalized_field == "stress" and pyansys_component == "VON_MISES":
                self._plot_von_mises(
                    result,
                    result_index=result_index,
                    screenshot=screenshot,
                    show_displacement=show_displacement,
                    displacement_factor=displacement_factor,
                    interactive=interactive,
                )
            else:
                plot_method = self._plot_method(result, normalized_field)
                plot_method(
                    result_index,
                    comp=pyansys_component,
                    show_displacement=show_displacement,
                    displacement_factor=displacement_factor,
                    off_screen=not interactive,
                    interactive=interactive,
                    screenshot=screenshot,
                    background="white",
                    show_edges=True,
                )
            artifacts = {"rst": str(selected_rst)}
            if not interactive:
                artifacts["screenshot"] = str(screenshot_path)
            return PyVistaRenderResult(
                status="success",
                case_id=case_id,
                message=(
                    f"Opened interactive PyVista {normalized_field} plot."
                    if interactive
                    else f"Rendered {normalized_field} plot with PyVista."
                ),
                artifacts=artifacts,
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

    def _normalize_render_request(self, field: str, component: str) -> tuple[str, str, str]:
        normalized_field = field.strip().lower()
        if normalized_field in {"displacement", "u"}:
            normalized_field = "disp"
        if normalized_field not in FIELD_COMPONENTS:
            raise ValueError(f"Unsupported field {field!r}. Supported fields: disp, stress.")

        normalized_component = component.strip().lower()
        if normalized_component not in FIELD_COMPONENTS[normalized_field]:
            supported = ", ".join(sorted(FIELD_COMPONENTS[normalized_field]))
            raise ValueError(f"Unsupported {normalized_field} component {component!r}. Supported components: {supported}.")
        pyansys_component = FIELD_COMPONENTS[normalized_field][normalized_component]
        if normalized_field == "stress" and pyansys_component == "VON_MISES":
            normalized_component = "von_mises"
        return normalized_field, normalized_component, pyansys_component

    def _plot_method(self, result: Any, field: str) -> Callable[..., Any]:
        if field == "disp":
            return result.plot_nodal_displacement
        if field == "stress":
            return result.plot_nodal_stress
        raise ValueError(f"Unsupported field: {field}")

    def _plot_von_mises(
        self,
        result: Any,
        *,
        result_index: int,
        screenshot: Optional[str],
        show_displacement: bool,
        displacement_factor: float,
        interactive: bool,
    ) -> None:
        try:
            import numpy as np
            import pyvista as pv
        except ImportError as exc:
            raise ImportError("Could not import numpy/pyvista for von Mises rendering.") from exc

        node_numbers, stress = result.nodal_stress(result_index)
        stress = np.asarray(stress, dtype=float)
        if stress.ndim != 2 or stress.shape[1] < 6:
            raise ValueError("nodal_stress must return an array with columns X, Y, Z, XY, YZ, XZ.")

        sx, sy, sz, txy, tyz, txz = stress[:, 0], stress[:, 1], stress[:, 2], stress[:, 3], stress[:, 4], stress[:, 5]
        von_mises = np.sqrt(
            0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
            + 3.0 * (txy**2 + tyz**2 + txz**2)
        )

        grid = result.grid.copy()
        if len(von_mises) != grid.number_of_points:
            mapped = np.full(grid.number_of_points, np.nan)
            grid_node_numbers = grid.point_data.get("ansys_node_num")
            if grid_node_numbers is None:
                raise ValueError("Result grid is missing point_data['ansys_node_num']; cannot map von Mises values.")
            index_by_node = {int(node): index for index, node in enumerate(grid_node_numbers)}
            for stress_index, node in enumerate(node_numbers):
                grid_index = index_by_node.get(int(node))
                if grid_index is not None:
                    mapped[grid_index] = von_mises[stress_index]
            von_mises = mapped

        if show_displacement:
            _, displacement = result.nodal_displacement(result_index)
            displacement = np.asarray(displacement, dtype=float)
            if len(displacement) == grid.number_of_points:
                grid.points = grid.points + displacement[:, :3] * displacement_factor

        grid.point_data["von_mises"] = von_mises
        plotter_factory = self._plotter_factory or pv.Plotter
        plotter = plotter_factory(off_screen=not interactive)
        plotter.add_mesh(
            grid,
            scalars="von_mises",
            show_edges=True,
            cmap="jet",
            scalar_bar_args={"title": "Von Mises\nStress"},
            nan_color="white",
        )
        plotter.set_background("white")
        plotter.add_axes()
        plotter.show(interactive=interactive, screenshot=screenshot, auto_close=True)


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False
