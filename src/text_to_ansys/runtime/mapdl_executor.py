from __future__ import annotations

import importlib.util
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from text_to_ansys.runtime.case_manager import CaseManager


@dataclass(frozen=True)
class MapdlRuntimeConfig:
    exec_file: Optional[str] = None
    jobname: str = "text_to_ansys"
    start_timeout: int = 120
    additional_launch_kwargs: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunResult:
    status: str
    case_id: str
    elapsed_seconds: float
    message: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    diagnostics: list[str] = field(default_factory=list)

    def to_json_dict(self) -> Dict[str, Any]:
        return asdict(self)


def check_mapdl_runtime() -> Dict[str, Any]:
    try:
        package_available = importlib.util.find_spec("ansys.mapdl.core") is not None
    except ModuleNotFoundError:
        package_available = False
    return {
        "pymapdl_available": package_available,
        "package": "ansys-mapdl-core",
        "will_launch_mapdl": False,
        "message": (
            "PyMAPDL Python package is available. This check does not launch MAPDL."
            if package_available
            else "PyMAPDL Python package is not installed in this Python environment."
        ),
    }


class MapdlExecutor:
    def __init__(
        self,
        manager: CaseManager,
        config: Optional[MapdlRuntimeConfig] = None,
        launch_mapdl_func: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.manager = manager
        self.config = config or MapdlRuntimeConfig()
        self._launch_mapdl_func = launch_mapdl_func

    def run_case(self, case_id: str) -> RunResult:
        case_dir = self.manager.case_dir(case_id).resolve()
        apdl_path = case_dir / "input.apdl"
        if not apdl_path.exists():
            result = RunResult(
                status="failed",
                case_id=case_id,
                elapsed_seconds=0.0,
                message="input.apdl not found. Build the case before running MAPDL.",
                artifacts={"apdl": str(apdl_path)},
                diagnostics=["Run `build` for this case first."],
            )
            self._write_run_json(case_dir, result)
            return result

        start = time.perf_counter()
        logs_dir = case_dir / "logs"
        raw_dir = case_dir / "raw"
        logs_dir.mkdir(exist_ok=True)
        raw_dir.mkdir(exist_ok=True)

        mapdl = None
        stdout_path = logs_dir / "mapdl_stdout.txt"
        error_path = logs_dir / "mapdl_error.txt"

        try:
            launch_mapdl = self._launch_mapdl_func or self._load_launch_mapdl()
            launch_kwargs = {
                "run_location": str(case_dir),
                "jobname": self.config.jobname,
                "override": True,
                "start_timeout": self.config.start_timeout,
            }
            if self.config.exec_file:
                launch_kwargs["exec_file"] = self.config.exec_file
            launch_kwargs.update(self.config.additional_launch_kwargs)

            mapdl = launch_mapdl(**launch_kwargs)
            output = mapdl.input("input.apdl")
            stdout_path.write_text(str(output), encoding="utf-8")

            elapsed = time.perf_counter() - start
            result = RunResult(
                status="success",
                case_id=case_id,
                elapsed_seconds=elapsed,
                message="MAPDL run completed.",
                artifacts=self._collect_artifacts(case_dir, stdout_path=stdout_path),
                diagnostics=[],
            )
            self._write_run_json(case_dir, result)
            self.manager.update_status(case_id, "solved")
            return result
        except ImportError as exc:
            elapsed = time.perf_counter() - start
            message = "PyMAPDL is not installed. Install ansys-mapdl-core before running MAPDL."
            error_path.write_text(str(exc), encoding="utf-8")
            result = RunResult(
                status="not_available",
                case_id=case_id,
                elapsed_seconds=elapsed,
                message=message,
                artifacts=self._collect_artifacts(case_dir, stdout_path=stdout_path, error_path=error_path),
                diagnostics=[str(exc)],
            )
            self._write_run_json(case_dir, result)
            return result
        except Exception as exc:
            elapsed = time.perf_counter() - start
            error_path.write_text(str(exc), encoding="utf-8")
            result = RunResult(
                status="failed",
                case_id=case_id,
                elapsed_seconds=elapsed,
                message="MAPDL run failed.",
                artifacts=self._collect_artifacts(case_dir, stdout_path=stdout_path, error_path=error_path),
                diagnostics=[str(exc)],
            )
            self._write_run_json(case_dir, result)
            self.manager.update_status(case_id, "failed")
            return result
        finally:
            if mapdl is not None:
                try:
                    mapdl.exit()
                except Exception:
                    pass

    def _load_launch_mapdl(self) -> Callable[..., Any]:
        try:
            from ansys.mapdl.core import launch_mapdl
        except ImportError as exc:
            raise ImportError("Could not import ansys.mapdl.core.launch_mapdl.") from exc
        return launch_mapdl

    def _collect_artifacts(
        self,
        case_dir: Path,
        *,
        stdout_path: Optional[Path] = None,
        error_path: Optional[Path] = None,
    ) -> Dict[str, str]:
        artifacts: Dict[str, str] = {"apdl": str(case_dir / "input.apdl")}
        if stdout_path and stdout_path.exists():
            artifacts["stdout"] = str(stdout_path)
        if error_path and error_path.exists():
            artifacts["error"] = str(error_path)

        for suffix in ("out", "err", "rst", "db", "full"):
            candidate = case_dir / f"{self.config.jobname}.{suffix}"
            if candidate.exists():
                artifacts[suffix] = str(candidate)
        return artifacts

    def _write_run_json(self, case_dir: Path, result: RunResult) -> None:
        (case_dir / "run.json").write_text(json.dumps(result.to_json_dict(), indent=2), encoding="utf-8")
