from __future__ import annotations

from dataclasses import dataclass, field

from text_to_ansys.schema import SimulationSpec


@dataclass(frozen=True)
class APDLBuildResult:
    script: str
    warnings: list[str] = field(default_factory=list)
    required_outputs: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)


class BaseAPDLBuilder:
    analysis_type: str

    def supports(self, spec: SimulationSpec) -> bool:
        return spec.analysis_type == self.analysis_type

    def build(self, spec: SimulationSpec) -> APDLBuildResult:
        raise NotImplementedError

