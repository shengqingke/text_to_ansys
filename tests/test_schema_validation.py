import pytest
from pydantic import ValidationError

from text_to_ansys.schema import ElementSpec, SimulationSpec, cantilever_beam_example


def test_cantilever_example_is_valid() -> None:
    spec = cantilever_beam_example()

    assert spec.analysis_type == "static_structural"
    assert spec.geometry.parameters["length"] == 1.0
    assert spec.primary_material.name == "steel"


def test_rejects_unknown_material_reference() -> None:
    spec = cantilever_beam_example()
    data = spec.model_dump()
    data["element"] = ElementSpec(type="SOLID186", material_id=2).model_dump()

    with pytest.raises(ValidationError, match="material_id 2"):
        SimulationSpec.model_validate(data)


def test_rejects_invalid_force_without_direction() -> None:
    data = cantilever_beam_example().model_dump()
    data["loads"][0]["direction"] = None

    with pytest.raises(ValidationError, match="force load requires direction"):
        SimulationSpec.model_validate(data)

