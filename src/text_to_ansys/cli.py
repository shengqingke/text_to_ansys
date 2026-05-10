from __future__ import annotations

import argparse
import json
from pathlib import Path

from text_to_ansys.runtime import CaseManager
from text_to_ansys.schema import cantilever_beam_example


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="text-to-ansys")
    parser.add_argument("--cases-dir", default="cases", help="Directory used for generated cases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_example = subparsers.add_parser("create-example", help="Create a built-in example case.")
    create_example.add_argument("template", choices=["cantilever"])
    create_example.add_argument("--build", action="store_true", help="Generate input.apdl immediately.")

    build = subparsers.add_parser("build", help="Generate input.apdl for a case.")
    build.add_argument("case_id")

    inspect = subparsers.add_parser("inspect", help="Print case summary as JSON.")
    inspect.add_argument("case_id")

    args = parser.parse_args(argv)
    manager = CaseManager(Path(args.cases_dir))

    if args.command == "create-example":
        spec = cantilever_beam_example()
        case = manager.create_case(spec, slug="cantilever_beam")
        if args.build:
            manager.build_case(case.case_id)
        print(json.dumps(manager.inspect_case(case.case_id), indent=2))
        return 0

    if args.command == "build":
        result = manager.build_case(args.case_id)
        print(json.dumps({"case_id": args.case_id, "warnings": result.warnings, "required_outputs": result.required_outputs}, indent=2))
        return 0

    if args.command == "inspect":
        print(json.dumps(manager.inspect_case(args.case_id), indent=2))
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

