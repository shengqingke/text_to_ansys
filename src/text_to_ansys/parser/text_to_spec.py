from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from text_to_ansys.schema import SimulationSpec, cantilever_beam_example
from text_to_ansys.schema.simulation_spec import ElementType


@dataclass(frozen=True)
class TextParseResult:
    spec: SimulationSpec
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_text_to_spec(text: str) -> TextParseResult:
    normalized = _normalize_text(text)
    warnings: list[str] = []
    assumptions: list[str] = []

    if not _looks_like_cantilever(normalized):
        warnings.append("Only cantilever beam static examples are supported by the MVP parser.")
        assumptions.append("Using the built-in cantilever beam template.")

    length = _find_dimension(normalized, ("长", "长度", "length", "long"))
    width = _find_dimension(normalized, ("宽", "宽度", "width", "wide"))
    height = _find_dimension(normalized, ("高", "高度", "height", "tall"))
    mesh_size = _find_mesh_size(normalized)
    force_y = _find_force_y(normalized)
    element_type = _find_element_type(normalized)
    material = _find_material(normalized)

    if length is None:
        length = 1.0
        assumptions.append("Length not found; using 1.0 m.")
    if width is None:
        width = 0.05
        assumptions.append("Width not found; using 0.05 m.")
    if height is None:
        height = 0.1
        assumptions.append("Height not found; using 0.1 m.")
    if mesh_size is None:
        mesh_size = 0.02
        assumptions.append("Mesh size not found; using 0.02 m.")
    if force_y is None:
        force_y = -1000.0
        assumptions.append("Y force not found; using -1000 N at the free end.")
    if element_type is None:
        element_type = "SOLID186"
        assumptions.append("Element type not found; using SOLID186.")

    spec = cantilever_beam_example(
        length=length,
        width=width,
        height=height,
        force_y=force_y,
        mesh_size=mesh_size,
        element_type=element_type,
    )

    if material == "aluminum":
        spec.materials[0].name = "aluminum"
        spec.materials[0].youngs_modulus = 70_000_000_000.0
        spec.materials[0].poisson_ratio = 0.33
        spec.materials[0].density = 2700.0
    elif material == "steel":
        spec.materials[0].name = "steel"

    spec.metadata.update(
        {
            "source": "text parser",
            "original_text": text,
            "assumptions": assumptions,
            "warnings": warnings,
        }
    )
    return TextParseResult(spec=spec, assumptions=assumptions, warnings=warnings)


def _normalize_text(text: str) -> str:
    return (
        text.strip()
        .replace("，", ",")
        .replace("。", ".")
        .replace("、", ",")
        .replace("－", "-")
        .replace("向下", "down")
        .replace("向上", "up")
        .lower()
    )


def _looks_like_cantilever(text: str) -> bool:
    return any(token in text for token in ("悬臂", "cantilever", "beam", "梁"))


def _find_dimension(text: str, names: tuple[str, ...]) -> Optional[float]:
    for name in sorted(names, key=len, reverse=True):
        patterns = [rf"{re.escape(name)}\s*(?:为|是|=|:)?\s*({_NUMBER})\s*({_LENGTH_UNIT})"]
        if name.isascii():
            patterns.append(rf"({_NUMBER})\s*({_LENGTH_UNIT})\s*(?:的)?\s*{re.escape(name)}")
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return _length_to_m(value, unit)
    return None


def _find_mesh_size(text: str) -> Optional[float]:
    patterns = [
        rf"(?:网格|mesh)(?:尺寸|大小|size)?\s*(?:为|是|=|:)?\s*({_NUMBER})\s*({_LENGTH_UNIT})",
        rf"({_NUMBER})\s*({_LENGTH_UNIT})\s*(?:网格|mesh)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _length_to_m(float(match.group(1)), match.group(2))
    return None


def _find_force_y(text: str) -> Optional[float]:
    patterns = [
        rf"(?:down|up)\s*(-?{_NUMBER})\s*({_FORCE_UNIT})",
        rf"(?:fy|y\s*方向力|y向力|竖向力|载荷|力|force)\s*(?:为|是|=|:)?\s*(-?{_NUMBER})\s*({_FORCE_UNIT})",
        rf"(-?{_NUMBER})\s*({_FORCE_UNIT})\s*(?:的)?\s*(?:载荷|力|force)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = _force_to_n(float(match.group(1)), match.group(2))
            if "down" in text or "向下" in text:
                return -abs(value)
            if "up" in text or "向上" in text:
                return abs(value)
            return value
    return None


def _find_element_type(text: str) -> Optional[ElementType]:
    if "solid185" in text:
        return "SOLID185"
    if "solid186" in text:
        return "SOLID186"
    return None


def _find_material(text: str) -> Optional[str]:
    if any(token in text for token in ("铝", "aluminum", "aluminium")):
        return "aluminum"
    if any(token in text for token in ("钢", "steel")):
        return "steel"
    return None


def _length_to_m(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit in {"m", "meter", "meters", "米"}:
        return value
    if unit in {"cm", "厘米"}:
        return value / 100.0
    if unit in {"mm", "毫米"}:
        return value / 1000.0
    raise ValueError(f"unsupported length unit: {unit}")


def _force_to_n(value: float, unit: str) -> float:
    unit = unit.lower()
    if unit in {"n", "牛", "牛顿"}:
        return value
    if unit in {"kn", "千牛"}:
        return value * 1000.0
    raise ValueError(f"unsupported force unit: {unit}")


_NUMBER = r"\d+(?:\.\d+)?"
_LENGTH_UNIT = r"mm|毫米|cm|厘米|m|米|meter|meters"
_FORCE_UNIT = r"kn|千牛|n|牛顿|牛"
