# PaperBanana-Pro

> 面向中文用户的科研插图与统计图生成系统。当前提供 Streamlit 图形界面、CLI 批处理、结果回放与评估可视化工具。

![PaperBanana-Pro 示例](assets/teaser_figure.jpg)

## 项目简介

`PaperBanana-Pro` 是这个仓库当前的独立项目名称。它已经不再是原始 `PaperBanana` 或 `PaperBanana-CN` README 的简单延续，而是围绕本仓库的真实代码、中文工作流和个人产品化方向持续演化的版本。

这个项目保留了多 Agent 科研绘图流水线的核心思路，同时把重心放在当前真正可用的产品能力上：中文 GUI、后台候选生成、历史 Bundle 回放、plot 代码重渲染、图像精修，以及更稳定的结果导出与可视化审阅流程。

## 相比原始 PaperBanana，我们新增了哪些实用功能

以下对比以当前仓库 git 中 `origin/main` 指向的早期上游快照 `b644e51` 为基线。关注点不是内部重构，而是中文用户今天真正能直接用到的功能差异。

### 实用升级摘要

- GUI 已经产品化：支持后台候选生成、停止未开始候选、刷新后重新连接任务、候选实时阶段和实时日志展示。
- 生成闭环更完整：历史 `.bundle.json` 可以直接回放，候选图可以一键“送去精修”，精修本身也支持后台执行。
- 候选筛选更像真实工作台：支持收藏、淘汰、设为最终候选，并按决策范围筛选展示与批量导出。
- `plot` 不再只是代码仓里的附带能力，而是正式进入 GUI 主流程，支持结构化数据解析预览、Matplotlib 代码查看和重渲染工作台。
- 精修链路更适合连续打磨：精修结果会自动进入版本历史，可从任意历史版本继续精修、回退父版本并保留编辑指令。
- 结果产物更适合真实使用：除了 legacy JSON，还会稳定生成 `.bundle.json`、`.summary.json`、`.failures.json`，并保留 `candidate_id` 与 `input_index`。
- GUI 导出能力更强：除了单候选下载，还支持“最终候选 ZIP”和“全流程总览 ZIP”，便于归档、分享和审阅。
- 安装和运行入口更统一：当前公开主命令是 `paperbanana`，`paperbanana-pro` 保留为兼容别名，并提供 `paperbanana run`、`uv sync --locked` 和提交入库的 `uv.lock`。
- Provider 与运行时更实用：当前正式公开支持 `gemini` 与 `evolink`，CLI / GUI / viewer 共用更一致的元数据和结果合同。
- 稳定性增强直接体现在体验上：dataset-aware 路径、`curated` fixed few-shot profile、并发后的稳定排序，以及 viewer 对 legacy JSON / bundle 的兼容查看。

### 和原始 PaperBanana 的精简对照

| 能力 | 原始 PaperBanana | 当前 PaperBanana-Pro |
| --- | --- | --- |
| GUI 产品面 | 以研究演示为主，没有完整的后台任务视角 | 中文 GUI，支持后台生成、停止未开始候选、刷新后重连、候选实时阶段和流式日志 |
| 生成闭环 | 生成与精修之间衔接有限 | 历史 bundle 回放、候选直送精修、精修后台化、失败信息可见 |
| Plot 产品化 | README 中仍把统计图代码作为待补内容 | `plot` 已进入 GUI 主流程，支持结构化输入预览、Matplotlib 代码查看与重渲染 |
| 结果产物 | 以单次结果 JSON 为主 | legacy JSON + `.bundle.json` + `summary/failures`，并稳定写入 `candidate_id` / `input_index` |
| 安装与运行 | 以仓库内脚本运行和论文复现语境为主 | repo-first editable 合同、全局 `paperbanana` 主命令、`paperbanana-pro` 兼容别名、`paperbanana run`、`uv sync --locked`、`uv.lock`、Evolink 接入 |
| 稳定性与兼容 | 对路径、阶段、结果格式的假设更强 | dataset-aware 路径、`curated` profile、稳定排序、viewer 兼容 legacy 与 bundle |

## 功能实拍

以下截图均来自本地 `demo.py` 的真实界面，并通过 Playwright 在 2026-03-11 实拍。

### 1. 历史回放与批量导出

![历史回放与批量导出](assets/readme/01-history-replay-and-export.png)

历史 `.bundle.json` 可以直接在 GUI 里回放；结果区同时展示 Bundle 路径、候选卡片，以及“最终候选 ZIP / 全流程总览 ZIP”下载入口。

### 2. 流水线演化时间线

![流水线演化时间线](assets/readme/02-evolution-timeline.png)

生成结果不是黑盒。你可以展开“查看演化时间线”，按阶段回看 `规划器`、`评审第 1 轮` 等中间产物与描述。

### 3. 候选方案直送精修

![候选方案直送精修](assets/readme/03-refine-handoff.png)

候选图不需要额外下载再上传，直接从结果卡片送去精修页；界面会明确标出图像来源、原始图像和编辑指令入口。

### 4. Plot 结构化输入预览

![Plot 结构化输入预览](assets/readme/04-plot-structured-input.png)

`plot` 已是正式 GUI 任务。输入 CSV 或表格数据后，界面会先解析出结构化预览，再进入代码生成和渲染流程。

### 5. 低成本真实生成中的实时状态

![低成本真实生成中的实时状态](assets/readme/05-live-generation-stream.png)

这张图来自一次真实运行：`gemini + demo_planner_critic + retrieval=none + candidate=1 + max_critic_rounds=1`。界面会持续显示任务状态、候选实时阶段和最近日志，而不是只在全部结束后给出最终图。

## 当前能力概览

- 面向中文用户：主界面、主要运行日志和导出说明以中文为主。
- 双任务支持：`diagram` 用于科研方法图 / 流程图，`plot` 用于统计图。
- GUI 为主：主产品入口是 `demo.py` 的 Streamlit 界面。
- CLI 可批处理：支持数据集批量运行、稳定排序、结果增量保存。
- Viewer 可审阅：支持流程演化查看与带参考结果的评估查看。
- 后台候选生成：支持多候选并发、流式阶段展示、停止未开始候选、刷新后重新连接后台任务。
- 图像精修：候选图可直接送入精修页做修改、放大与批量导出。
- Plot 工作台：可查看最终 Matplotlib 代码，并在 GUI 中直接重渲染预览。
- 结果打包：支持 legacy JSON、`.bundle.json`、CLI 摘要报告，以及 GUI 全流程 ZIP 导出。
- Provider 说明：当前对外公开文档只覆盖 `gemini` 与 `evolink` 两条正式运行路径。

## 命名说明

- 对外品牌名是 `PaperBanana-Pro`。
- 当前主 CLI 命令是 `paperbanana`。
- `paperbanana-pro` 仍然保留为兼容别名，方便旧命令过渡。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/elpsykongloo/PaperBanana-Pro.git
cd PaperBanana-Pro
```

### 2. 准备数据集

完整体验建议准备默认数据集 `PaperBananaBench`，并放到 `data/PaperBananaBench/` 下。当前仓库默认使用这个目录结构。

- 数据集：[`dwzhu/PaperBananaBench`](https://huggingface.co/datasets/dwzhu/PaperBananaBench)
- 可选原始 PDF：[`dwzhu/PaperBananaDiagramPDFs`](https://huggingface.co/datasets/dwzhu/PaperBananaDiagramPDFs)

如果你只是做低依赖试跑，也可以把检索设置为 `none`，但参考驱动能力、评估查看和大多数默认流程仍建议配套数据集使用。

### 3. 配置 API Key

推荐先复制配置模板：

```bash
Copy-Item configs\model_config.template.yaml configs\model_config.yaml
```

运行时读取优先级如下：

1. 环境变量
2. `configs/local/*.txt`
3. `configs/model_config.yaml`

推荐的本地 secret 文件名：

- `configs/local/google_api_key.txt`
- `configs/local/evolink_api_key.txt`
- `configs/local/openai_api_key.txt`
- `configs/local/anthropic_api_key.txt`

说明：

- `gemini` 默认模型字段在 `defaults.model_name` 与 `defaults.image_model_name`
- `evolink` 默认模型字段在 `evolink.model_name` 与 `evolink.image_model_name`
- 模板里保留了 `OpenAI` / `Anthropic` 的兼容配置位，但当前正式文档化的主生成入口仍是 `gemini` 与 `evolink`

### 4. 安装方式

#### 当前正式支持：repo-first editable

当前公开发布只支持“仓库内运行 + editable 全局命令”。推荐流程如下：

```bash
git clone https://github.com/elpsykongloo/PaperBanana-Pro.git
cd PaperBanana-Pro
uv python install 3.12
uv sync --locked
uv tool install --editable . --force
```

安装完成后，你可以在任意目录直接调用：

```bash
paperbanana
paperbanana gui
paperbanana viewer evolution
paperbanana viewer eval
paperbanana run --help
paperbanana-pro
```

如果 `paperbanana-pro` 或 `paperbanana` 没有进入 PATH，可按 `uv` 提示执行一次 `uv tool update-shell`。

说明：

- 当前版本仍依赖已 checkout 的仓库源码，以及仓库内 `data/`、`configs/` 等路径。
- `uv sync --locked` 会基于 `pyproject.toml` 与已提交的 `uv.lock` 创建可复现环境。
- README 中所有全局命令示例都以 `paperbanana` 为主；`paperbanana-pro` 仅保留为兼容别名。

#### 未来路线（暂未支持）

以下能力已经列入 TODO，但不属于本次发布支持范围：

- 非 editable 的 `uv tool install .`
- 显式入口安装 `uv tool install --from . paperbanana-pro`
- 发布到可访问索引后执行 `uv tool install paperbanana-pro`

#### 仓库内直接调试

如果你暂时不需要全局命令，也可以继续直接从仓库执行：

```bash
streamlit run demo.py
python main.py --help
```

### 5. 启动项目

```bash
paperbanana
```

或者直接从仓库启动 GUI：

```bash
streamlit run demo.py
```

## 运行方式

兼容别名：`paperbanana-pro`

### GUI：`paperbanana` / `paperbanana-pro` / `streamlit run demo.py`

GUI 是当前主产品面，适合绝大多数中文用户。它提供两个核心工作区：

#### 生成候选方案

- `diagram`：输入方法描述与图注，生成科研插图候选。
- `plot`：输入结构化数据与可视化意图，生成 Matplotlib 代码并渲染统计图。
- 支持后台生成、多候选并发、流式预览、停止未开始候选。
- 支持历史 `.bundle.json` 回放。
- 支持把候选图或“最终候选”直接送入精修页。
- 支持对候选执行收藏、淘汰、设为最终，并按当前决策范围筛选展示与导出。
- `plot` 任务支持查看最终代码、在 GUI 中重渲染预览，再把预览送去精修。
- 支持下载单候选、批量最终候选 ZIP、全流程总览 ZIP。

#### 精修图像

- 支持上传任意图像，或直接使用上一页送来的候选结果。
- 支持多张并发精修。
- 支持分辨率、宽高比和 provider 独立设置。
- 支持版本历史：每轮精修都会形成版本链，可从任意历史版本继续精修、回退到父版本。
- 支持后台执行、停止后续重试、批量 ZIP 下载。

### CLI：`paperbanana run` / `paperbanana-pro run` / `python main.py`

CLI 适合数据集批处理、回归测试和产物归档。

最短示例：

```bash
paperbanana run --task_name diagram --exp_mode demo_full --provider gemini
```

等价仓库内调用：

```bash
python main.py --task_name diagram --exp_mode demo_full --provider gemini
```

核心参数：

- `--dataset_name`：切换数据集根目录名，默认 `PaperBananaBench`
- `--task_name`：`diagram` 或 `plot`
- `--exp_mode`：流水线模式，例如 `vanilla`、`demo_planner_critic`、`demo_full`、`dev_full`
- `--retrieval_setting`：`auto`、`auto-full`、`curated`、`manual`、`random`、`none`
- `--curated_profile`：固定 few-shot profile 名称
- `--max_critic_rounds`：最大 critic 轮数，可设为 `0`
- `--provider`：当前公开支持 `gemini` / `evolink`
- `--max_concurrent`：并发上限
- `--resume`：按当前输出路径自动恢复最近一次 checkpoint / bundle
- `--resume_from`：显式指定 checkpoint、bundle 或 legacy 结果文件作为恢复源

完整参数与支持的 `exp_mode` 以如下帮助输出为准：

```bash
paperbanana run --help
```

### Viewer：结果审阅与评估查看

查看单次运行的流程演化：

```bash
paperbanana viewer evolution
```

查看带参考结果的评估内容：

```bash
paperbanana viewer eval
```

如果你仍在仓库中直接调试，也可以继续使用：

```bash
streamlit run visualize/show_pipeline_evolution.py
streamlit run visualize/show_referenced_eval.py
```

如果你要查看带 GT / reference 的结果，请确保对应数据集目录仍然存在于本地。

## 数据与配置说明

### 默认数据目录

默认数据集根目录为：

```text
data/PaperBananaBench/
```

当前目录合同如下：

```text
data/PaperBananaBench/
├── diagram/
│   ├── test.json
│   ├── ref.json
│   ├── images/
│   └── manual_profiles/      # 可选
└── plot/
    ├── test.json
    ├── ref.json
    ├── images/
    └── manual_profiles/      # 可选
```

说明：

- `test.json`：当前任务的输入样本
- `ref.json`：参考样例池
- `images/`：对应图片资产
- `manual_profiles/<profile>.json`：固定 few-shot profile，可选

你也可以通过 `--dataset_name` 使用自定义数据集，例如：

```bash
paperbanana run --dataset_name MyDataset --task_name plot --exp_mode dev_full
```

只要目录结构与默认合同一致，相关路径解析逻辑会自动切换到 `data/MyDataset/`。

### `curated` few-shot profile 说明

当前仓库已经把旧的“manual retrieval”对外收口为更明确的 `curated` 固定 few-shot 流程。

- 优先读取：`data/<dataset>/<task>/manual_profiles/<profile>.json`
- 默认 profile：`default`
- 向后兼容：当 `default` profile 不存在时，仍会兼容旧文件 `agent_selected_12.json`
- profile 可以直接存完整样例，也可以只存参考 ID，再回连到 `ref.json`

这意味着：

- 旧命令中的 `manual` 仍可用，但它是对 `curated` 的 legacy alias
- 新项目说明中更推荐你直接使用 `curated + curated_profile`

### 配置文件要点

`configs/model_config.template.yaml` 当前的关键位置如下：

```yaml
defaults:
  model_name: ""
  image_model_name: ""

api_keys:
  google_api_key: ""
  openai_api_key: ""
  anthropic_api_key: ""

evolink:
  api_key: ""
  base_url: "https://api.evolink.ai"
  model_name: "gemini-2.5-flash"
  image_model_name: "nano-banana-2-lite"
```

README 层面的默认建议是：

- `gemini` 作为日常主路径
- `evolink` 作为另一条正式公开路径
- 其余兼容代码与配置位不作为当前首页主入口来介绍

## 结果产物与可视化工具

### CLI 产物

CLI 运行结束后，当前仓库会围绕一次运行保存多类结果：

- legacy 结果 JSON
- companion `.bundle.json`
- `.summary.json`
- `.failures.json`

其中 Bundle 是当前仓库推荐的可移植结果封装，公开字段合同如下：

```json
{
  "schema": "paperbanana.result_bundle",
  "schema_version": 1,
  "manifest": {},
  "summary": {},
  "failures": [],
  "results": []
}
```

当前 Bundle / 结果记录会尽量携带这些稳定元信息：

- `dataset_name`
- `task_name`
- `exp_mode`
- `retrieval_setting`
- `curated_profile`
- `provider`
- `candidate_id`
- `input_index`

这保证了批处理结果在并发执行下仍然能稳定排序、稳定导出和稳定回放。

### GUI 导出能力

GUI 当前支持导出：

- 单候选图片
- 单候选代码文件（`plot`）
- 运行 JSON
- 运行 Bundle
- 最终候选 ZIP
- 全流程总览 ZIP

其中“全流程总览 ZIP”会按照中文目录整理每个候选的：

- 最终图像
- 最终描述 / 最终代码
- 中间阶段图像
- critic 建议
- 原始结果 JSON

### 可视化审阅

- `visualize/show_pipeline_evolution.py`：按阶段查看候选演化过程
- `visualize/show_referenced_eval.py`：查看带参考图与 GT 的评估展示

如果你希望跨机器共享结果，优先共享 `.bundle.json`；如果需要查看 reference / GT 资产，本地仍要保留对应数据集目录。

## 项目结构

下面是当前最值得关心的目录与入口：

```text
PaperBanana/
├── agents/                 # 多 Agent 阶段实现
├── configs/                # 模型与本地密钥配置
├── data/                   # 默认数据集目录
├── docs/                   # 维护记录与路线图
├── results/                # CLI / smoke / demo 结果
├── scripts/                # live smoke 等辅助脚本
├── tests/                  # 单元测试与回归测试
├── utils/                  # 运行时、路径、bundle、registry 等共享逻辑
├── visualize/              # Streamlit viewer
├── cli.py                  # 全局 paperbanana / paperbanana-pro 命令入口
├── demo.py                 # 主 GUI
├── main.py                 # CLI 批处理入口
├── pyproject.toml          # 项目元数据
├── uv.lock                 # 锁定依赖
└── README.md
```

## 架构与流水线

![PaperBanana-Pro 流水线](assets/method_diagram.png)

### 核心阶段

| 阶段 | 作用 |
| --- | --- |
| Retriever | 从参考池中检索 few-shot 样例 |
| Planner | 生成结构化较强的可视化描述 |
| Stylist | 优化学术表达和风格一致性 |
| Visualizer | 生成图像，或在 plot 路径生成 Matplotlib 代码 |
| Critic | 进行多轮评审和修订建议 |
| Polish | 作为可选后处理阶段进一步精修 |

### 当前实现上的关键点

- `diagram` 路径主要围绕描述生成与图像生成展开。
- `plot` 路径当前不是“图像模型直接出图”，而是先生成 Matplotlib 代码，再在本地执行与渲染。
- 当前流水线模式由 registry 统一声明，CLI / GUI / viewer 会共享相同的阶段元信息。
- 结果文件会写入稳定的运行元数据，减少 viewer 对历史硬编码假设的依赖。

## 技术路线图 / TODO

下面是短期内计划进行支持的功能清单。

- [ ] 多语言支持：在保持中文产品面稳定的前提下，补齐英文等多语言 UI / README / 提示词支持
- [ ] 扩展数据集：由于原始的PaperBananaBench 的定位是 benchmark，导致其图片数量覆盖范围不够大，后续计划扩展更多会议如ICML、ACL等的数据集，为few shot提供更加可靠的结果
- [ ] Plot correctness / `PlotSpec`：增强统计图的结构化合同、诊断与自动修复能力
- [ ] `FigureSpec` / structured IR：让 diagram 与 plot 都逐步从自由文本串联迁移到结构化中间表示
- [ ] No-reference QA：在没有 GT 的真实使用场景里也能给出自动质量反馈
- [ ] Bundle / Viewer 产品化：继续提升 bundle 便携性与 viewer 的可审阅能力
- [ ] Provider / runtime 收口：进一步减少 provider 配置和运行时逻辑的分散状态
- [ ] 发布到可访问索引：让 `uv tool install paperbanana-pro` 成为真正可直接联网安装的默认路径

## 致谢 / 参考资料

`PaperBanana-Pro` 已经按当前仓库的独立产品方向持续演化，但项目发展过程中仍参考了以下工作与仓库：

- 原始仓库：[`dwzhu-pku/PaperBanana`](https://github.com/dwzhu-pku/PaperBanana)
- 中文参考仓库：[`Mylszd/PaperBanana-CN`](https://github.com/Mylszd/PaperBanana-CN)
- 原始论文：[`PaperBanana: Automating Academic Illustration for AI Scientists`](https://huggingface.co/papers/2601.23265)

同时也感谢原始数据集与相关科研绘图探索工作，为这个仓库后续的独立演化提供了出发点。

## License

Apache-2.0
