from text_to_ansys.builders import StaticStructuralBuilder
from text_to_ansys.schema import cantilever_beam_example


def test_static_builder_generates_expected_apdl_sections() -> None:
    spec = cantilever_beam_example()
    result = StaticStructuralBuilder().build(spec)
    script = result.script

    assert "/PREP7" in script
    assert "ET,1,SOLID186" in script
    assert "MP,EX,1,210000000000" in script
    assert "BLOCK,0,1,0,0.05,0,0.1" in script
    assert "ESIZE,0.02" in script
    assert "NSEL,S,LOC,X,0" in script
    assert "D,ALL,UX,0" in script
    assert "NSEL,S,LOC,X,1" in script
    assert "F,ALL,FY,FEACH1" in script
    assert "ANTYPE,STATIC" in script
    assert "SOLVE" in script


def test_static_builder_records_required_outputs() -> None:
    spec = cantilever_beam_example()
    result = StaticStructuralBuilder().build(spec)

    assert result.required_outputs == ["max_total_displacement", "max_von_mises_stress"]

