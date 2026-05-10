from pathlib import Path

from text_to_ansys.tools import create_case_from_text


def test_create_case_from_text_builds_apdl(tmp_path: Path) -> None:
    info = create_case_from_text(
        "创建一个钢制悬臂梁，长1m，宽50mm，高100mm，右端向下1000N，使用SOLID186，网格20mm。",
        cases_dir=tmp_path,
        build=True,
    )

    assert info["has_apdl"] is True
    assert info["geometry"]["parameters"]["width"] == 0.05
    assert info["mesh"]["global_size"] == 0.02
    assert info["required_outputs"] == ["max_total_displacement", "max_von_mises_stress"]

