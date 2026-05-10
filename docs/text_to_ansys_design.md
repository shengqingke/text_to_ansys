# Text-to-Ansys(APDL) 工程设计文档

## 1. 目标

本项目目标是实现一个面向 Ansys MAPDL/APDL 的对话式仿真自动化系统，使用户可以在自然语言对话中完成类似 `text_to_abaqus` / `text-to-cae` 的工作流：

```text
自然语言需求
  -> 结构化仿真意图
  -> APDL / PyMAPDL 可执行脚本
  -> MAPDL 求解
  -> 结果抽取与可视化
  -> 对话式修改、重跑、对比和解释
```

系统的核心不是让大模型直接“自由生成 APDL”，而是建立一个可校验、可复现、可扩展的工程闭环：

```text
LLM 负责理解需求和辅助修复
Schema/DSL 负责约束仿真意图
Builder 负责生成 APDL
PyMAPDL 负责执行求解
Postprocess 负责提取和展示结果
Case Workspace 负责保存全流程上下文
```

## 2. 借鉴 text-to-CAE / text-to-Abaqus 的内容

`text-to-cae` 和 `abaqus-mcp` 类项目对本项目的参考价值主要在工程闭环，而不是具体求解器代码。

### 2.1 强借鉴部分

1. **Case 工作区**

   每次仿真都保存为一个独立 case，包括输入脚本、结构化 spec、日志、结果文件、报告、图片和运行元数据。这样可以支持复现、继续修改、结果对比和问题追踪。

2. **Solver Bridge**

   Abaqus 项目通过 Python 脚本或 MCP 控制 Abaqus/CAE；本项目通过 PyMAPDL 控制 MAPDL。二者角色相同，都是 AI 和工程求解器之间的执行桥。

3. **结果导出**

   Abaqus 项目从 ODB 导出 JSON 和可视化数据；本项目从 RST、PyMAPDL post_processing 或 Ansys DPF 导出 JSON、表格和云图数据。

4. **对话式迭代**

   用户可以继续提出“网格加密”“材料换成铝”“把载荷改成压力”“对比两次最大应力”等修改。系统不重新丢弃上下文，而是在已有 case/spec 基础上更新、重跑和解释。

5. **MCP 工具化**

   将创建 case、生成 APDL、运行 MAPDL、读取结果、查看日志、对比结果等能力包装为工具，使 Codex/LLM 能在对话中显式调用，而不是凭空回答。

6. **错误反馈闭环**

   求解失败时保存 `.err`、`.out`、stdout/stderr 和 APDL 输入，交给修复模块判断错误来源，并尝试修复 spec 或 APDL。

### 2.2 不照搬部分

Abaqus 和 Ansys MAPDL 的脚本模型差异很大：

```text
Abaqus: Python object model, mdb/model/part/job
MAPDL: 命令流式 APDL, /PREP7 -> /SOLU -> /POST1
```

因此不建议照搬 Abaqus 的建模对象结构和代码生成方式。本项目应围绕以下链路重新设计：

```text
SimulationSpec
  -> APDLBuilder
  -> PyMAPDLExecutor
  -> ResultExtractor
  -> Report/Viewer
```

## 3. 总体架构

```text
┌─────────────────────────────────────────────┐
│ Conversation / Agent Layer                  │
│ Codex, OpenAI API, local LLM, MCP client     │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ Intent Parser Layer                         │
│ text -> SimulationSpec draft                │
│ ambiguity detection                         │
│ spec repair / completion                    │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ Simulation DSL / Schema Layer               │
│ Pydantic models                             │
│ units, material, geometry, load validation  │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ APDL Builder Layer                          │
│ static/modal/thermal builders               │
│ reusable snippets                           │
│ generated input.apdl                        │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ MAPDL Runtime Layer                         │
│ PyMAPDL launch/connect/run                  │
│ input execution, timeout, logs, artifacts   │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ Postprocess / Report Layer                  │
│ RST, PyMAPDL post_processing, DPF           │
│ result.json, plots, report.md               │
└──────────────────────┬──────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│ Case Workspace                              │
│ spec, APDL, logs, result files, metadata    │
└─────────────────────────────────────────────┘
```

## 4. 推荐工程目录

```text
text_to_ansys/
  pyproject.toml
  README.md
  .env.example

  src/
    text_to_ansys/
      __init__.py

      agent/
        __init__.py
        chat_orchestrator.py
        tool_registry.py
        prompts/
          system_prompt.md
          intent_extraction.md
          spec_update.md
          repair_apdl.md
          result_explanation.md

      schema/
        __init__.py
        simulation_spec.py
        geometry.py
        material.py
        mesh.py
        loads.py
        boundary_conditions.py
        outputs.py
        units.py
        validators.py

      parser/
        __init__.py
        text_to_spec.py
        spec_repair.py
        spec_update.py
        ambiguity_detector.py

      builders/
        __init__.py
        base.py
        static_structural.py
        modal.py
        thermal.py
        transient.py
        snippets/
          prep7.py
          geometry.py
          material.py
          mesh.py
          solution.py
          post1.py
          components.py

      runtime/
        __init__.py
        mapdl_session.py
        executor.py
        case_manager.py
        logs.py
        errors.py
        artifact_store.py

      post/
        __init__.py
        result_extractor.py
        rst_reader.py
        dpf_reader.py
        plots.py
        report.py
        compare.py

      library/
        examples/
          cantilever_beam.yaml
          plate_with_hole.yaml
          bracket_static.yaml
          modal_beam.yaml
        materials/
          steel.yaml
          aluminum.yaml
        elements/
          solid185.yaml
          solid186.yaml
          shell181.yaml
          beam188.yaml

      tools/
        __init__.py
        create_case.py
        update_case.py
        run_case.py
        inspect_case.py
        compare_cases.py
        export_apdl.py
        explain_result.py

      mcp/
        __init__.py
        server.py
        tools.py

      cli.py

  cases/
    .gitkeep

  tests/
    test_schema_validation.py
    test_static_builder.py
    test_case_manager.py
    test_post_extract.py
    test_apdl_snapshots.py

  docs/
    architecture.md
    simulation_spec.md
    examples.md
    text_to_ansys_design.md
```

## 5. Case 工作区设计

每次仿真创建一个独立 case 目录：

```text
cases/
  2026-05-10_153012_cantilever_beam/
    case.yaml
    simulation_spec.json
    simulation_spec.history.jsonl
    input.apdl
    input.preview.md
    run.json
    logs/
      mapdl_stdout.txt
      mapdl_stderr.txt
      job.out
      job.err
    raw/
      job.db
      job.rst
      job.full
    results/
      result_summary.json
      nodal_displacement.json
      element_stress.json
      mesh.json
      plots/
        displacement.png
        von_mises.png
    reports/
      summary.md
      comparison.md
```

### 5.1 `case.yaml`

保存 case 级别元数据：

```yaml
id: 2026-05-10_153012_cantilever_beam
title: Cantilever beam static analysis
status: solved
created_at: "2026-05-10T15:30:12+08:00"
updated_at: "2026-05-10T15:32:10+08:00"
parent_case_id: null
analysis_type: static_structural
solver: mapdl
jobname: cantilever
unit_system: SI
```

### 5.2 `simulation_spec.history.jsonl`

每次对话修改都追加一条记录：

```json
{"version": 1, "reason": "initial creation", "spec_path": "simulation_spec.json"}
{"version": 2, "reason": "mesh size changed from 0.02 to 0.01", "spec_path": "simulation_spec.v2.json"}
```

这使得“网格加密后再跑”“对比上一版”成为一等能力。

## 6. SimulationSpec 设计

第一版建议使用 Pydantic 定义强约束 schema。

```json
{
  "analysis_type": "static_structural",
  "unit_system": "SI",
  "geometry": {
    "kind": "block",
    "name": "beam",
    "parameters": {
      "length": 1.0,
      "width": 0.05,
      "height": 0.1
    }
  },
  "materials": [
    {
      "id": 1,
      "name": "steel",
      "model": "linear_isotropic",
      "youngs_modulus": 210000000000.0,
      "poisson_ratio": 0.3,
      "density": 7850
    }
  ],
  "element": {
    "type": "SOLID186",
    "material_id": 1,
    "real_constant_id": null
  },
  "mesh": {
    "global_size": 0.02,
    "method": "free"
  },
  "boundary_conditions": [
    {
      "kind": "fixed_support",
      "target": {
        "selector": "face",
        "expression": "x=0"
      },
      "dofs": ["UX", "UY", "UZ"]
    }
  ],
  "loads": [
    {
      "kind": "force",
      "target": {
        "selector": "face",
        "expression": "x=length"
      },
      "direction": "Y",
      "value": -1000.0
    }
  ],
  "outputs": [
    "max_total_displacement",
    "max_von_mises_stress"
  ]
}
```

### 6.1 为什么需要 DSL

直接 `text -> APDL` 的问题：

- 缺少单位检查
- 难以判断材料、载荷、边界条件是否完整
- 错误 APDL 难以定位源头
- 不方便对话式修改
- 不方便把一个仿真迁移到其他 solver 或 viewer

采用 `text -> SimulationSpec -> APDL` 后：

- LLM 输出先被校验
- Builder 可以稳定生成 APDL
- Case 可以保存和版本化
- 后续可支持 PyMAPDL、Workbench、Mechanical scripting 或其他后端

## 7. APDL Builder 设计

Builder 输入 `SimulationSpec`，输出 `input.apdl` 和可读预览。

### 7.1 Builder 接口

```python
class BaseAPDLBuilder:
    analysis_type: str

    def supports(self, spec: SimulationSpec) -> bool:
        ...

    def build(self, spec: SimulationSpec) -> APDLBuildResult:
        ...
```

`APDLBuildResult`：

```python
class APDLBuildResult:
    script: str
    warnings: list[str]
    required_outputs: list[str]
    metadata: dict
```

### 7.2 静力结构分析 APDL 模板

```text
/CLEAR
/PREP7
! element type
ET,1,SOLID186

! material
MP,EX,1,2.1E11
MP,PRXY,1,0.3

! geometry
BLOCK,0,1,0,0.05,0,0.1

! mesh
ESIZE,0.02
VMESH,ALL

! boundary conditions
NSEL,S,LOC,X,0
D,ALL,ALL,0
ALLSEL,ALL

! load
NSEL,S,LOC,X,1
F,ALL,FY,-1000
ALLSEL,ALL

/SOLU
ANTYPE,STATIC
SOLVE
FINISH

/POST1
SET,LAST
```

注意：以上是 MVP 级示意。正式 Builder 需要处理选择容差、面载荷分配、单位、组件命名、结果提取命令和失败回退。

## 8. PyMAPDL Runtime 设计

Runtime 层负责执行，不负责理解仿真语义。

### 8.1 主要职责

- 启动或连接 MAPDL
- 指定 run_location 和 jobname
- 写入 `input.apdl`
- 执行 APDL
- 设置超时
- 捕获 stdout/stderr
- 归档 `.out`、`.err`、`.rst`、`.db`
- 返回结构化运行状态

### 8.2 Runtime 接口

```python
class MapdlExecutor:
    def run_case(self, case_dir: Path, apdl_script: str) -> RunResult:
        ...
```

`RunResult`：

```python
class RunResult:
    status: Literal["success", "failed", "timeout"]
    case_dir: Path
    jobname: str
    elapsed_seconds: float
    stdout_path: Path
    stderr_path: Path
    err_path: Path | None
    out_path: Path | None
    rst_path: Path | None
    diagnostics: list[str]
```

### 8.3 MAPDL 连接策略

第一阶段支持本地 MAPDL：

```text
launch_mapdl(run_location=case_dir, jobname=jobname)
```

第二阶段支持连接已有 MAPDL 实例：

```text
Mapdl(ip="127.0.0.1", port=50052)
```

第三阶段再考虑远程求解服务器、队列系统或容器化环境。

## 9. 后处理设计

后处理层负责把 MAPDL 结果转成对话和 viewer 都能消费的数据。

### 9.1 数据来源

优先级建议：

1. PyMAPDL `mapdl.post_processing`
2. Ansys DPF
3. APDL `/POST1` 命令导出文本
4. 直接读取 RST

### 9.2 输出文件

```text
results/
  result_summary.json
  mesh.json
  nodal_displacement.json
  element_stress.json
  plots/
    displacement.png
    von_mises.png
reports/
  summary.md
```

`result_summary.json` 示例：

```json
{
  "status": "success",
  "analysis_type": "static_structural",
  "max_total_displacement": {
    "value": 0.00342,
    "unit": "m",
    "node_id": 1284
  },
  "max_von_mises_stress": {
    "value": 185000000.0,
    "unit": "Pa",
    "element_id": 96
  },
  "warnings": []
}
```

## 10. MCP / 对话工具设计

为了在和 Codex 的对话中达到 `text_to_ansys` 效果，建议提供 MCP server 或等价工具接口。

### 10.1 第一批工具

```text
create_case_from_text(text: str) -> case_id
inspect_case(case_id: str) -> case_summary
generate_apdl(case_id: str) -> apdl_path
run_case(case_id: str) -> run_result
extract_results(case_id: str) -> result_summary
update_case_from_text(case_id: str, text: str) -> new_case_id | updated_case_id
compare_cases(case_ids: list[str]) -> comparison_summary
export_case(case_id: str) -> artifact_paths
```

### 10.2 对话示例

```text
用户：创建一个 1m 长、50mm 宽、100mm 高的钢悬臂梁，左端固定，右端向下 1000N。
Agent：
  - create_case_from_text
  - generate_apdl
  - run_case
  - extract_results
  - 总结最大位移和最大等效应力

用户：把网格尺寸改成 10mm，再跑一次，并和上一版对比。
Agent：
  - update_case_from_text
  - generate_apdl
  - run_case
  - extract_results
  - compare_cases
```

## 11. 错误修复闭环

求解失败后不应只返回失败，而应进入诊断流程。

```text
MAPDL failed
  -> 收集 input.apdl, job.err, job.out, stdout/stderr
  -> Runtime 生成 diagnostics
  -> Repair 模块判断错误类型
  -> 必要时修改 SimulationSpec 或 APDL
  -> 重新生成/运行
  -> 保存修复历史
```

### 11.1 常见错误分类

```text
schema_error: spec 缺字段或字段冲突
builder_error: 当前 builder 不支持该需求
selection_error: NSEL/ASEL/VSEL 没选中目标
mesh_error: 几何无法网格化
material_error: 材料参数缺失或非法
load_error: 载荷目标或方向非法
solver_error: 约束不足、刚体运动、非收敛
post_error: 结果文件缺失或结果项不可用
environment_error: MAPDL 未安装、license 不可用、启动失败
```

### 11.2 修复策略

第一阶段只做保守修复：

- 选择集为空时增加容差或改用组件
- 缺单位时要求用户确认，不盲猜
- 材料库中找不到材料时使用候选材料并提示
- 网格失败时尝试增大尺寸或改用更简单单元
- 约束不足时给出诊断，不自动添加虚假约束

## 12. MVP 范围

第一版建议只做静力结构分析，降低不确定性。

### 12.1 支持能力

```text
analysis_type:
  - static_structural

geometry:
  - block
  - cylinder
  - cantilever_beam template
  - plate_with_hole template

material:
  - linear isotropic
  - built-in steel
  - built-in aluminum

element:
  - SOLID185
  - SOLID186

mesh:
  - global element size
  - free mesh

boundary conditions:
  - fixed support by face expression
  - displacement constraint by DOF

loads:
  - nodal/face equivalent force
  - pressure

outputs:
  - max total displacement
  - max directional displacement
  - max von Mises stress
```

### 12.2 暂不支持

```text
非线性接触
大变形
复杂装配
Workbench Mechanical 原生工程
拓扑优化
复杂 CAD 导入修复
显式动力学
疲劳
流固耦合
电磁/热结构耦合
```

## 13. 实施路线

### Phase 0: 文档与约束确认

- 审核本设计文档
- 确认 MVP 分析类型
- 确认本机 MAPDL / PyMAPDL 环境
- 确认是否优先 MCP 接入 Codex

### Phase 1: Core CLI 原型

- 建立 Python 项目结构
- 实现 SimulationSpec schema
- 实现静力结构 APDL Builder
- 实现 CaseManager
- 实现 CLI：

```text
text-to-ansys create "..."
text-to-ansys build <case_id>
text-to-ansys run <case_id>
text-to-ansys results <case_id>
```

### Phase 2: PyMAPDL 执行闭环

- 接入 `ansys-mapdl-core`
- 支持本地 `launch_mapdl`
- 保存日志和结果文件
- 实现基础结果抽取
- 生成 `summary.md`

### Phase 3: 对话/MCP 接入

- 实现 MCP server
- 暴露 case 工具
- 支持在 Codex 对话中创建、运行、修改和对比 case

### Phase 4: 可视化与对比

- 导出 mesh/result JSON
- 生成静态云图
- 可选 React/Three.js viewer
- 支持 case 间对比

### Phase 5: 扩展分析类型

- modal
- thermal
- transient structural
- contact/nonlinear static

## 14. 风险与设计取舍

### 14.1 最大风险

1. **LLM 生成不可靠仿真意图**

   解决：强制经过 schema 校验和 ambiguity detector。

2. **APDL 选择集脆弱**

   解决：Builder 使用组件、选择容差和命名约定，避免大量裸 `NSEL,S,LOC`。

3. **环境差异**

   MAPDL 安装路径、license、版本、图形环境都可能不同。

   解决：Runtime 层集中处理环境检测和错误解释。

4. **结果后处理复杂**

   解决：MVP 只抽取少量关键指标，后续再接 DPF 和 viewer。

5. **自动修复可能引入错误假设**

   解决：只自动修复低风险问题；涉及物理假设时要求用户确认。

### 14.2 关键取舍

```text
不用纯 LLM 直接生成 APDL
优先 text -> spec -> APDL 的可控路线

不用一开始做大而全 viewer
优先 result_summary.json + summary.md + 基础图片

不用一开始支持所有 Ansys 物理场
优先静力结构闭环跑通

不把 PyMAPDL 逻辑塞进 Agent
Agent 只调用工具，Runtime 统一管理 MAPDL
```

## 15. 近期可审核决策点

需要确认的设计决策：

1. 第一版是否只做 `static_structural`？
2. 第一版是否采用 Pydantic 作为 schema 基础？
3. 第一版是否先做 CLI，再做 MCP？
4. Case 是否默认保存在仓库内 `cases/`？
5. 是否要求每次运行都生成 `input.apdl`，方便人工审核？
6. 后处理第一版是否只输出 summary JSON/Markdown，不做 Web viewer？
7. 是否允许 LLM 在失败时自动尝试一次低风险修复？

## 16. 推荐结论

推荐采用如下路线：

```text
text-to-cae/text-to-abaqus 原型闭环
  + PyMAPDL/MAPDL 作为 Ansys 后端
  + SimulationSpec 作为中间 DSL
  + APDL Builder 作为确定性生成层
  + Case Workspace 作为记忆和复现基础
  + MCP tools 作为 Codex 对话接入口
```

这样可以最大化借鉴已有 `text_to_abaqus` 原型的产品形态，同时避免把 Abaqus 的对象模型错误迁移到 Ansys APDL 体系中。

