from text_to_ansys.parser import parse_text_to_spec


def test_parse_chinese_cantilever_prompt() -> None:
    result = parse_text_to_spec(
        "创建一个钢制悬臂梁，长1m，宽50mm，高100mm，右端向下1000N，使用SOLID186，网格20mm。"
    )
    spec = result.spec

    assert spec.geometry.parameters["length"] == 1.0
    assert spec.geometry.parameters["width"] == 0.05
    assert spec.geometry.parameters["height"] == 0.1
    assert spec.mesh.global_size == 0.02
    assert spec.loads[0].value == -1000.0
    assert spec.element.type == "SOLID186"
    assert spec.materials[0].name == "steel"


def test_parse_aluminum_kn_prompt() -> None:
    result = parse_text_to_spec("铝合金悬臂梁 长度=500mm 宽度=40mm 高度=20mm 向下 2kN 网格 10mm solid185")
    spec = result.spec

    assert spec.geometry.parameters["length"] == 0.5
    assert spec.geometry.parameters["width"] == 0.04
    assert spec.geometry.parameters["height"] == 0.02
    assert spec.loads[0].value == -2000.0
    assert spec.element.type == "SOLID185"
    assert spec.materials[0].name == "aluminum"

