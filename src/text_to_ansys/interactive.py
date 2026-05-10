from __future__ import annotations

import json
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from text_to_ansys.runtime import CaseManager
from text_to_ansys.schema import cantilever_beam_example


HELP_TEXT = """Commands:
  help                         Show this help.
  create cantilever [build]    Create the built-in cantilever case.
  list                         List existing cases.
  use <case_id>                Set the current case.
  current                      Show the current case.
  inspect [case_id]            Show a compact case summary.
  build [case_id]              Generate input.apdl for a case.
  show apdl [case_id]          Print generated APDL.
  exit                         Leave the interactive shell.
"""


@dataclass
class CommandResult:
    message: str
    should_exit: bool = False


class InteractiveShell:
    def __init__(self, manager: CaseManager) -> None:
        self.manager = manager
        self.current_case_id: Optional[str] = None

    def execute(self, line: str) -> CommandResult:
        stripped = line.strip()
        if not stripped:
            return CommandResult("")

        try:
            args = shlex.split(stripped)
        except ValueError as exc:
            return CommandResult(f"Could not parse command: {exc}")

        command = args[0].lower()
        rest = args[1:]

        try:
            if command in {"exit", "quit"}:
                return CommandResult("Bye.", should_exit=True)
            if command == "help":
                return CommandResult(HELP_TEXT.rstrip())
            if command == "create":
                return CommandResult(self._create(rest))
            if command == "list":
                return CommandResult(self._list_cases())
            if command == "use":
                return CommandResult(self._use(rest))
            if command == "current":
                return CommandResult(self._current())
            if command == "inspect":
                return CommandResult(self._inspect(rest))
            if command == "build":
                return CommandResult(self._build(rest))
            if command == "show":
                return CommandResult(self._show(rest))
        except Exception as exc:
            return CommandResult(f"Error: {exc}")

        return CommandResult(f"Unknown command: {command}. Type 'help' for available commands.")

    def _create(self, args: list[str]) -> str:
        if not args or args[0] != "cantilever":
            return "Usage: create cantilever [build]"
        build_now = "build" in args[1:]
        case = self.manager.create_case(cantilever_beam_example(), slug="cantilever_beam")
        self.current_case_id = case.case_id
        if build_now:
            self.manager.build_case(case.case_id)
        suffix = " and generated input.apdl" if build_now else ""
        return f"Created case {case.case_id}{suffix}."

    def _list_cases(self) -> str:
        cases = self.manager.list_cases()
        if not cases:
            return "No cases found."
        lines = ["Cases:"]
        for case in cases:
            marker = "*" if case["case_id"] == self.current_case_id else " "
            apdl = "apdl" if case["has_apdl"] else "no-apdl"
            lines.append(f"{marker} {case['case_id']}  {case['status']}  {apdl}  {case['title']}")
        return "\n".join(lines)

    def _use(self, args: list[str]) -> str:
        if len(args) != 1:
            return "Usage: use <case_id>"
        self.manager.case_dir(args[0])
        self.current_case_id = args[0]
        return f"Current case set to {args[0]}."

    def _current(self) -> str:
        if self.current_case_id is None:
            return "No current case. Create or use a case first."
        return f"Current case: {self.current_case_id}"

    def _inspect(self, args: list[str]) -> str:
        case_id = self._resolve_case_id(args)
        info = self.manager.inspect_case(case_id)
        compact = {
            "case_id": info["case_id"],
            "title": info["title"],
            "analysis_type": info["analysis_type"],
            "element": info["element"],
            "mesh": info["mesh"],
            "has_apdl": info["has_apdl"],
            "apdl_path": info["apdl_path"],
        }
        return json.dumps(compact, indent=2)

    def _build(self, args: list[str]) -> str:
        case_id = self._resolve_case_id(args)
        result = self.manager.build_case(case_id)
        self.current_case_id = case_id
        outputs = ", ".join(result.required_outputs) or "none"
        return f"Generated input.apdl for {case_id}. Required outputs: {outputs}."

    def _show(self, args: list[str]) -> str:
        if not args or args[0] != "apdl":
            return "Usage: show apdl [case_id]"
        case_id = self._resolve_case_id(args[1:])
        apdl = self.manager.read_apdl(case_id)
        return apdl.rstrip()

    def _resolve_case_id(self, args: list[str]) -> str:
        if len(args) > 1:
            raise ValueError("expected zero or one case id")
        if args:
            return args[0]
        if self.current_case_id is None:
            raise ValueError("no current case; pass a case id or create/use a case first")
        return self.current_case_id


def run_interactive(
    cases_dir: str | Path = "cases",
    *,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> int:
    shell = InteractiveShell(CaseManager(cases_dir))
    output_func("Text-to-Ansys interactive shell. Type 'help' for commands.")
    while True:
        try:
            line = input_func("text-to-ansys> ")
        except (EOFError, KeyboardInterrupt):
            output_func("")
            output_func("Bye.")
            return 0
        result = shell.execute(line)
        if result.message:
            output_func(result.message)
        if result.should_exit:
            return 0

