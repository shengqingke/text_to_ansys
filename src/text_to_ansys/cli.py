from __future__ import annotations

import argparse
import json
from pathlib import Path

from text_to_ansys.interactive import run_interactive
from text_to_ansys.runtime import CaseManager
from text_to_ansys.schema import cantilever_beam_example
from text_to_ansys.tools import check_mapdl, check_pyvista, create_case_from_text, render_displacement, run_case


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="text-to-ansys")
    parser.add_argument("--cases-dir", default="cases", help="Directory used for generated cases.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_example = subparsers.add_parser("create-example", help="Create a built-in example case.")
    create_example.add_argument("template", choices=["cantilever"])
    create_example.add_argument("--build", action="store_true", help="Generate input.apdl immediately.")

    create_from_text = subparsers.add_parser("create-from-text", help="Create a case from a natural-language prompt.")
    create_from_text.add_argument("text")
    create_from_text.add_argument("--build", action="store_true", help="Generate input.apdl immediately.")

    build = subparsers.add_parser("build", help="Generate input.apdl for a case.")
    build.add_argument("case_id")

    inspect = subparsers.add_parser("inspect", help="Print case summary as JSON.")
    inspect.add_argument("case_id")

    run = subparsers.add_parser("run", help="Run a generated APDL case with PyMAPDL.")
    run.add_argument("case_id")
    run.add_argument("--exec-file", help="Explicit MAPDL executable path. No path is guessed automatically.")
    run.add_argument("--jobname", default="text_to_ansys")

    subparsers.add_parser("check-mapdl", help="Check whether PyMAPDL is importable without launching MAPDL.")

    render = subparsers.add_parser("render", help="Render an RST displacement plot with PyVista.")
    render.add_argument("case_id")
    render.add_argument("--rst-path", help="Optional explicit RST path. Defaults to the first RST in the case.")
    render.add_argument("--component", default="NORM", help="Displacement component, for example NORM, X, Y, or Z.")
    render.add_argument("--result-index", type=int, default=0)
    render.add_argument("--displacement-factor", type=float, default=1.0)

    subparsers.add_parser("check-pyvista", help="Check optional PyVista rendering imports without reading RST files.")

    subparsers.add_parser("interactive", help="Start a basic interactive shell.")

    args = parser.parse_args(argv)
    manager = CaseManager(Path(args.cases_dir))

    if args.command == "create-example":
        spec = cantilever_beam_example()
        case = manager.create_case(spec, slug="cantilever_beam")
        if args.build:
            manager.build_case(case.case_id)
        print(json.dumps(manager.inspect_case(case.case_id), indent=2))
        return 0

    if args.command == "create-from-text":
        print(json.dumps(create_case_from_text(args.text, cases_dir=Path(args.cases_dir), build=args.build), indent=2))
        return 0

    if args.command == "build":
        result = manager.build_case(args.case_id)
        print(json.dumps({"case_id": args.case_id, "warnings": result.warnings, "required_outputs": result.required_outputs}, indent=2))
        return 0

    if args.command == "inspect":
        print(json.dumps(manager.inspect_case(args.case_id), indent=2))
        return 0

    if args.command == "check-mapdl":
        print(json.dumps(check_mapdl(), indent=2))
        return 0

    if args.command == "check-pyvista":
        print(json.dumps(check_pyvista(), indent=2))
        return 0

    if args.command == "run":
        print(
            json.dumps(
                run_case(args.case_id, cases_dir=Path(args.cases_dir), exec_file=args.exec_file, jobname=args.jobname),
                indent=2,
            )
        )
        return 0

    if args.command == "render":
        print(
            json.dumps(
                render_displacement(
                    args.case_id,
                    cases_dir=Path(args.cases_dir),
                    rst_path=args.rst_path,
                    component=args.component,
                    result_index=args.result_index,
                    displacement_factor=args.displacement_factor,
                ),
                indent=2,
            )
        )
        return 0

    if args.command == "interactive":
        return run_interactive(Path(args.cases_dir))

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
