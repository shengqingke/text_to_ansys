from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AnalysisType = Literal["static_structural"]
GeometryKind = Literal["block", "cantilever_beam"]
ElementType = Literal["SOLID185", "SOLID186"]
UnitSystem = Literal["SI"]
Axis = Literal["X", "Y", "Z"]
ForceDirection = Literal["X", "Y", "Z"]
TargetSelector = Literal["face", "nodes"]
BoundaryKind = Literal["fixed_support", "displacement"]
LoadKind = Literal["force", "pressure"]
OutputRequest = Literal[
    "max_total_displacement",
    "max_directional_displacement",
    "max_von_mises_stress",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GeometrySpec(StrictModel):
    kind: GeometryKind
    name: str = "geometry"
    parameters: Dict[str, float]

    @model_validator(mode="after")
    def validate_geometry_parameters(self) -> "GeometrySpec":
        required = {"length", "width", "height"}
        missing = sorted(required.difference(self.parameters))
        if missing:
            raise ValueError(f"geometry.parameters missing: {', '.join(missing)}")
        for key in required:
            if self.parameters[key] <= 0:
                raise ValueError(f"geometry.parameters.{key} must be positive")
        return self


class MaterialSpec(StrictModel):
    id: int = Field(ge=1)
    name: str
    model: Literal["linear_isotropic"] = "linear_isotropic"
    youngs_modulus: float = Field(gt=0)
    poisson_ratio: float = Field(gt=-1.0, lt=0.5)
    density: Optional[float] = Field(default=None, gt=0)


class ElementSpec(StrictModel):
    type: ElementType
    material_id: int = Field(ge=1)
    real_constant_id: Optional[int] = Field(default=None, ge=1)


class MeshSpec(StrictModel):
    global_size: float = Field(gt=0)
    method: Literal["free"] = "free"


class TargetSpec(StrictModel):
    selector: TargetSelector
    expression: str

    @field_validator("expression")
    @classmethod
    def expression_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target expression must not be empty")
        return value.strip()


class BoundaryConditionSpec(StrictModel):
    kind: BoundaryKind
    target: TargetSpec
    dofs: List[Literal["UX", "UY", "UZ"]] = Field(default_factory=lambda: ["UX", "UY", "UZ"])
    value: float = 0.0

    @model_validator(mode="after")
    def validate_bc(self) -> "BoundaryConditionSpec":
        if self.kind == "fixed_support":
            self.dofs = ["UX", "UY", "UZ"]
            self.value = 0.0
        if not self.dofs:
            raise ValueError("boundary condition requires at least one DOF")
        return self


class LoadSpec(StrictModel):
    kind: LoadKind
    target: TargetSpec
    direction: Optional[ForceDirection] = None
    value: float

    @model_validator(mode="after")
    def validate_load(self) -> "LoadSpec":
        if self.kind == "force" and self.direction is None:
            raise ValueError("force load requires direction")
        if self.kind == "pressure" and self.direction is not None:
            raise ValueError("pressure load does not use direction")
        return self


class SimulationSpec(StrictModel):
    title: str = "Untitled Ansys case"
    analysis_type: AnalysisType = "static_structural"
    unit_system: UnitSystem = "SI"
    geometry: GeometrySpec
    materials: List[MaterialSpec]
    element: ElementSpec
    mesh: MeshSpec
    boundary_conditions: List[BoundaryConditionSpec]
    loads: List[LoadSpec]
    outputs: List[OutputRequest] = Field(default_factory=lambda: ["max_total_displacement"])
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_references(self) -> "SimulationSpec":
        material_ids = {material.id for material in self.materials}
        if self.element.material_id not in material_ids:
            raise ValueError(f"element.material_id {self.element.material_id} is not defined")
        if not self.boundary_conditions:
            raise ValueError("at least one boundary condition is required")
        if not self.loads:
            raise ValueError("at least one load is required")
        return self

    @property
    def primary_material(self) -> MaterialSpec:
        for material in self.materials:
            if material.id == self.element.material_id:
                return material
        raise ValueError(f"material {self.element.material_id} not found")


def cantilever_beam_example(
    *,
    length: float = 1.0,
    width: float = 0.05,
    height: float = 0.1,
    force_y: float = -1000.0,
    mesh_size: float = 0.02,
    element_type: ElementType = "SOLID186",
) -> SimulationSpec:
    return SimulationSpec(
        title="Cantilever beam static analysis",
        analysis_type="static_structural",
        unit_system="SI",
        geometry=GeometrySpec(
            kind="cantilever_beam",
            name="beam",
            parameters={"length": length, "width": width, "height": height},
        ),
        materials=[
            MaterialSpec(
                id=1,
                name="steel",
                model="linear_isotropic",
                youngs_modulus=210_000_000_000.0,
                poisson_ratio=0.3,
                density=7850.0,
            )
        ],
        element=ElementSpec(type=element_type, material_id=1),
        mesh=MeshSpec(global_size=mesh_size),
        boundary_conditions=[
            BoundaryConditionSpec(
                kind="fixed_support",
                target=TargetSpec(selector="face", expression="x=0"),
            )
        ],
        loads=[
            LoadSpec(
                kind="force",
                target=TargetSpec(selector="face", expression="x=length"),
                direction="Y",
                value=force_y,
            )
        ],
        outputs=["max_total_displacement", "max_von_mises_stress"],
        metadata={"source": "built-in example"},
    )
