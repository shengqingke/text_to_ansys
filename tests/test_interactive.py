from pathlib import Path

from text_to_ansys.interactive import InteractiveShell
from text_to_ansys.runtime import CaseManager


def test_interactive_create_build_show_apdl(tmp_path: Path) -> None:
    shell = InteractiveShell(CaseManager(tmp_path))

    created = shell.execute("create cantilever build")
    assert created.should_exit is False
    assert "Created case" in created.message
    assert shell.current_case_id is not None

    listed = shell.execute("list")
    assert shell.current_case_id in listed.message
    assert "built" in listed.message
    assert "apdl" in listed.message

    apdl = shell.execute("show apdl")
    assert "ET,1,SOLID186" in apdl.message
    assert "SOLVE" in apdl.message


def test_interactive_requires_current_case_for_build(tmp_path: Path) -> None:
    shell = InteractiveShell(CaseManager(tmp_path))

    result = shell.execute("build")

    assert "no current case" in result.message


def test_interactive_exit() -> None:
    shell = InteractiveShell(CaseManager("cases"))

    result = shell.execute("exit")

    assert result.should_exit is True
    assert result.message == "Bye."
