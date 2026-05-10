# Text-to-Ansys(APDL)

Text-to-Ansys is a conversation-friendly automation toolkit for generating and managing Ansys MAPDL/APDL simulation cases.

The MVP focuses on a controlled path:

```text
natural language or template
  -> SimulationSpec
  -> input.apdl
  -> case workspace
```

Real PyMAPDL execution and result extraction are planned after the first stable `spec -> APDL` loop.

## MVP Quick Start

Create a cantilever beam example case and generate APDL:

```powershell
python -m text_to_ansys.cli create-example cantilever --build
```

Inspect the generated case:

```powershell
python -m text_to_ansys.cli inspect <case_id>
```

Generate APDL for an existing case:

```powershell
python -m text_to_ansys.cli build <case_id>
```

Run tests:

```powershell
pytest
```

## Current Scope

Supported in the first MVP:

- static structural analysis
- block/cantilever beam geometry
- linear isotropic materials
- `SOLID185` and `SOLID186`
- global mesh size
- fixed support on a selected face
- force on a selected face, distributed across selected nodes
- APDL generation and case persistence

