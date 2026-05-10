from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from text_to_ansys.builders import APDLBuildResult, StaticStructuralBuilder
from text_to_ansys.schema import SimulationSpec


@dataclass(frozen=True)
class CaseInfo:
    case_id: str
    case_dir: Path
    spec_path: Path
    apdl_path: Path
    status: str


class CaseManager:
    def __init__(self, cases_dir: str | Path = "cases") -> None:
        self.cases_dir = Path(cases_dir)
        self.cases_dir.mkdir(parents=True, exist_ok=True)

    def create_case(self, spec: SimulationSpec, *, slug: str | None = None) -> CaseInfo:
        case_id = self._new_case_id(slug or spec.title)
        case_dir = self.cases_dir / case_id
        (case_dir / "logs").mkdir(parents=True)
        (case_dir / "raw").mkdir()
        (case_dir / "results" / "plots").mkdir(parents=True)
        (case_dir / "reports").mkdir()

        spec_path = case_dir / "simulation_spec.json"
        spec_path.write_text(spec.model_dump_json(indent=2), encoding="utf-8")

        case_yaml = self._case_yaml(case_id=case_id, spec=spec, status="created")
        (case_dir / "case.yaml").write_text(case_yaml, encoding="utf-8")
        (case_dir / "simulation_spec.history.jsonl").write_text(
            json.dumps({"version": 1, "reason": "initial creation", "spec_path": "simulation_spec.json"}) + "\n",
            encoding="utf-8",
        )

        return CaseInfo(
            case_id=case_id,
            case_dir=case_dir,
            spec_path=spec_path,
            apdl_path=case_dir / "input.apdl",
            status="created",
        )

    def load_spec(self, case_id: str) -> SimulationSpec:
        spec_path = self.case_dir(case_id) / "simulation_spec.json"
        return SimulationSpec.model_validate_json(spec_path.read_text(encoding="utf-8"))

    def build_case(self, case_id: str) -> APDLBuildResult:
        spec = self.load_spec(case_id)
        builder = StaticStructuralBuilder()
        result = builder.build(spec)
        case_dir = self.case_dir(case_id)
        (case_dir / "input.apdl").write_text(result.script, encoding="utf-8")
        (case_dir / "input.preview.md").write_text(f"```apdl\n{result.script}```\n", encoding="utf-8")
        self._update_status(case_id, "built")
        return result

    def inspect_case(self, case_id: str) -> dict[str, object]:
        case_dir = self.case_dir(case_id)
        spec = self.load_spec(case_id)
        apdl_path = case_dir / "input.apdl"
        return {
            "case_id": case_id,
            "case_dir": str(case_dir),
            "title": spec.title,
            "analysis_type": spec.analysis_type,
            "unit_system": spec.unit_system,
            "geometry": spec.geometry.model_dump(),
            "element": spec.element.model_dump(),
            "mesh": spec.mesh.model_dump(),
            "materials": [material.model_dump() for material in spec.materials],
            "outputs": list(spec.outputs),
            "has_apdl": apdl_path.exists(),
            "apdl_path": str(apdl_path),
        }

    def case_dir(self, case_id: str) -> Path:
        path = self.cases_dir / case_id
        if not path.exists():
            raise FileNotFoundError(f"case not found: {case_id}")
        return path

    def _new_case_id(self, seed: str) -> str:
        timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d_%H%M%S")
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", seed.lower()).strip("_")
        slug = slug[:48] or "ansys_case"
        candidate = f"{timestamp}_{slug}"
        index = 2
        while (self.cases_dir / candidate).exists():
            candidate = f"{timestamp}_{slug}_{index}"
            index += 1
        return candidate

    def _case_yaml(self, *, case_id: str, spec: SimulationSpec, status: str) -> str:
        now = datetime.now(timezone.utc).astimezone().isoformat()
        return "\n".join(
            [
                f"id: {case_id}",
                f'title: "{spec.title}"',
                f"status: {status}",
                f'created_at: "{now}"',
                f'updated_at: "{now}"',
                f"analysis_type: {spec.analysis_type}",
                "solver: mapdl",
                f"unit_system: {spec.unit_system}",
                "",
            ]
        )

    def _update_status(self, case_id: str, status: str) -> None:
        case_dir = self.case_dir(case_id)
        spec = self.load_spec(case_id)
        (case_dir / "case.yaml").write_text(self._case_yaml(case_id=case_id, spec=spec, status=status), encoding="utf-8")

