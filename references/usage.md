# 通用天文学论文图表工具：使用说明

本工具服务各类天体和天文学研究；原有各种双星、三星入口保持兼容。新增天球/WCS、测光、光谱、星系、宇宙学和多信使专题见 [astronomy-scope.md](astronomy-scope.md) 与 [astronomy-usage.md](astronomy-usage.md)。图形来自调用者提供的观测、计算结果或明确标注的示例，不因系统类型自动选择物理模型。

下面保留原有 49 个基础与双星/三星 recipe 名称，其中部分是别名或共享实现。目录用于快速选择，也允许用通用 Matplotlib／Plotly 接口制作新的图型；数量不等于已穷尽所有科研图或已验证所有天体领域。

## 快速运行

在本项目根目录执行。以下变量只指向本工具的 Python 和项目副本；安装后的技能副本也可作为 `PLOT_SKILL` 使用。

```sh
PLOT_PY=".venv/bin/python"
PLOT_SKILL="."

"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" list
"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" journals
```

`list` 输出实际登记的名称、必需字段和说明；以当前程序输出为准。`journals` 输出有日期的期刊资料、建议值和未确认项。

运行包内明确标注的合成示例，输出到新的目录：

```sh
"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" render \
  "$PLOT_SKILL/examples/synthetic_radial_velocity.json" \
  --output "figures/tool-example/rv" --journal mnras --width double

"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" table \
  "$PLOT_SKILL/examples/synthetic_parameter_table.json" \
  --output "figures/tool-example/parameters" --journal mnras --preview
```

这些文件演示工具，不应充作项目观测结果或模型验证证据。真实研究使用自己的 spec 与数据路径。

```sh
"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" render \
  spec.json --output "figures/rv" --journal aas \
  --width single --formats pdf,svg,png

"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" inspect "figures/rv.pdf"
```

`--width` 可为 `single`、`double` 或毫米数。数值宽度仍受已知期刊最大宽度约束。`--dpi` 可显式指定位图分辨率；低于已知门槛会进入检查记录，不能据此声明达到投稿要求。输出参数使用**不带文件扩展名的基名**。默认拒绝覆盖；只有确定需要替换已有结果时使用 `--force`。

## 49 个 recipe 名称索引

下表中的数据量均由调用者提供。`N` 为数据点数，`K` 为系列数，`P` 为参数数；二维系列通常按 `[N,K]` 排列。

| 名称 | 用途与主要输入 |
| --- | --- |
| `line`、`scatter`、`errorbar` | 通用曲线、散点和误差棒；`x`、`y`，可加 `xerr`／`yerr` |
| `bar` | 分组类别比较；类别 `x` 与数量 `y` |
| `histogram` | 原始样本分布；`values`，可指定共同分箱 |
| `boxplot`、`violin` | 多组样本分布；`groups` 与可选标签 |
| `heatmap`、`image` | 数值矩阵或图像；`z`，可加真实坐标；图像也接受 RGB(A) |
| `contour`、`stability_map` | 等高线、稳定性诊断网格；`x`、`y`、`z` |
| `quiver` | 已计算的矢量场；`x`、`y`、`u`、`v` |
| `envelope` | 估计曲线与区间带；`x`、`y`、`lower`、`upper` |
| `timeseries_fit`、`light_curve`、`radial_velocity` | 观测、模型及观测减模型残差；`x`、`observed`、`model`，可加 `sigma` |
| `phase_curve` | 按给定周期折叠观测；`x`、`y`、`period`，可给 `t0` 和误差 |
| `orbit2d`、`astrometry` | 平面轨道或天测投影；`x`、`y`，可加误差与坐标约定 |
| `orbit3d` | 二／三颗星的空间轨迹；`x`、`y`、`z`，各轴使用一致空间单位 |
| `oc`、`eclipse_timing`、`etv` | 已计算的 O−C／食时变化；`x`、`y`，可加误差；绘图器不拟合星历 |
| `periodogram`、`power_spectrum` | 已计算的频率与功率；`x`、`y`，可给明确来源的阈值 |
| `secular_evolution` | 多种轨道要素随时间变化；`x`、多列 `y`，可给各面板标签 |
| `transfer_history` | 质量、质量交换率、半径、自旋等历史；`x`、多列 `y`、带单位的 `ylabels` |
| `roche_map` | 已计算的有效势网格；`x`、`y`、`z`，明确给出等势值；可标临界点 |
| `eclipse_geometry` | 二／三颗星的投影圆盘位置；`centers`、`radii`，可给前后顺序；不计算光通量 |
| `streamlines` | 已计算速度场的流线；等距递增 `x`／`y` 与 `u`／`v` 网格 |
| `dynamic_spectrum` | 时变频谱或谱线图；时间 `x`、频率／光谱坐标 `y`、网格 `z` |
| `visibility`、`uv_coverage` | 干涉可见度／采样覆盖；`x`、`y`，可见度可加误差；不补造共轭点 |
| `polarimetry` | 已计算的 Stokes 或偏振观测；`x`、多列 `y`、`labels` |
| `selection_function` | 检出／选择概率；`x`、`y`、范围为 `[0,1]` 的网格 `z` |
| `phase_portrait`、`poincare` | 相空间投影或预先提取的截面穿越点；`x`、`y` |
| `hr_diagram`、`mass_radius` | 恒星性质与演化对照；`x`、`y`，可加误差与方向设定 |
| `spectrum`、`sed` | 提供的光谱坐标及相应通量量；`x`、`y`，坐标变换显式指定 |
| `corner` | 真实后验样本及参数相关性；`samples[draw,P]` |
| `trace`、`autocorrelation` | 样本轨迹与自相关；`samples[draw,P]` 或 `[draw,chain,P]` |
| `forest` | 多参数／方法的估计与区间；`estimate`、`lower`、`upper`、`labels` |
| `correlation` | 参数相关矩阵；`matrix[P,P]` 或真实样本 `samples[draw,P]` |
| `residual_diagnostics` | 已有残差的分布和诊断；`residuals`，可给 `x` 和标准化所需 `sigma` |
| `convergence`、`benchmark` | 容差／步长—误差、耗时—误差等对照；`x`、`y`；可比条件另行记录 |

质量交换、Roche、食几何、稳定性、后验和功率谱等名称描述绘图对象，不提供相应完整物理求解器或统计推断器。相空间截面、参数后验和频谱显著性不能由图形外观推断。专题范围见 [coverage.md](coverage.md)。

## 数据与 spec

支持 JSON、CSV、TSV、ECSV；具体限制、缺测编码、来源记录及现有工作台适配器见 [data-contract.md](data-contract.md)。

渲染 spec 的基本形式：

```json
{
  "kind": "radial_velocity",
  "data_path": "selected_star_rv.csv",
  "mapping": {
    "x": "time_day",
    "observed": "observed_km_s",
    "model": "predicted_km_s",
    "sigma": "sigma_km_s"
  },
  "journal": "mnras",
  "width": "single",
  "units": {"x": "day", "observed": "km/s"},
  "options": {"xlabel": "Time (day)", "ylabel": "RV (km/s)"},
  "caption": "说明对象、时间约定、模型、误差含义及残差符号。"
}
```

`data_path` 相对于 spec 所在目录解析，也可使用绝对路径；可直接用 `data` 对象替代外部文件。`mapping` 显式增加字段别名，不推断单位或时间尺度。示例列名需与实际文件一致。

不同恒星、仪器、模型候选及数据角色先明确分组。`y[N,K]` 的每列代表一个已定义系列；对既有工作台 RV 导出，可使用 `load_stellar_rv` 明确选星和模型候选。不要直接把一个文件中不同恒星交错连接起来。

可在 `options` 中声明轴标题、系列标签、`xscale`／`yscale`、范围及反向等选择；不同 recipe 接受的选项取决于其含义。星等图需要时显式设置 `invert_y: true`；时间列名不自动建立 BJD／HJD／MJD 或 TT／TDB／UTC 约定。

## 自定义 Matplotlib 图与新 recipe

现有图型不能准确表达科学问题时，可以直接构造 Matplotlib Figure，使用 GridSpec、subplot_mosaic、subfigures 或领域软件的图，再交给统一导出接口。下面列名只示范显式接入方式：

```python
import sys
from pathlib import Path
import matplotlib.pyplot as plt

skill = Path(".").resolve()
sys.path.insert(0, str(skill / "scripts"))
from stellarplot.adapters import load_data
from stellarplot.core import journal_style, export

data = load_data("results/selected_star_rv.csv")
with journal_style("mnras"):
    fig, ax = plt.subplots(figsize=(3.3, 2.5), layout="constrained")
    try:
        ax.errorbar(data["time_day"], data["observed_km_s"],
                    yerr=data["sigma_km_s"], fmt="o")
        ax.set(xlabel="Time (day)", ylabel="RV (km/s)")
        report = export(fig, "figures/custom_rv", data=data,
                        caption="填写对象、时间约定与误差定义。",
                        journal="mnras", width="single",
                        provenance={"selection": "填写实际选星、筛选及计算说明"})
    finally:
        plt.close(fig)
```

`export` 保留源数据和来源说明；可显式给出 `figure_type="line"`、`"image"` 或 `"combination"`，并核查复杂图的自动识别是否适当。共享代码和真实输入可保存为新 recipe，扩展时继续检查单位、缺测、误差及导出结果，而不把绘图分类当作研究范围限制。

## 交互补充图

对已支持的图型添加 `render --html`，可同时输出交互工作图。并非所有静态 recipe 都有内建交互实现；不支持的组合会报错，应使用自定义 Plotly Figure，或只制作所需静态图。

下面续用上一段已设置的模块路径和 `data`。

```python
import plotly.graph_objects as go
from stellarplot.interactive import export_interactive

interactive_figure = go.Figure(go.Scatter(
    x=data["time_day"], y=data["observed_km_s"], mode="markers",
    error_y={"type": "data", "array": data["sigma_km_s"]}))
interactive_figure.update_layout(
    xaxis_title="Time (day)", yaxis_title="RV (km/s)")
export_interactive(interactive_figure, "figures/custom_rv_interactive",
                   caption="填写交互内容及数据说明。",
                   provenance={"source": data["_source"]})
```

默认要求 HTML 自包含。远程图片、相对图片路径、文件 URL 或需要外部资源的实际地图图层，不能仅靠嵌入 Plotly 程序就认定离线可用；应改用嵌入数据，或在确需联网工作副本时显式指定 `require_self_contained=False`，并保留输出的依赖记录。正式投稿所需静态代表图另行制作与检查。

## 表格：可编辑原稿与机器可读数据

`table` 的 spec 使用 `columns`、`rows`，可附 `units`、`caption`、`notes`、`label`。它导出 `.tex`、`.csv`、`.table.json`；`--preview` 另制作小表的图形预览。完整科研表应保留可编辑版本，图形预览不代替原生表格。

- `--journal aas` 使用 AASTeX 的 `deluxetable` 源码。
- `--journal aa` 或 `mnras` 使用相应横线风格的 LaTeX `table`／`tabular` 源码。
- 通用表格使用 booktabs 风格，需要在实际文档中加载相应支持。

宽表、跨栏、横置、长表及表注安排，需要放进当时的期刊 class 单独编译。程序记录 `compiled: false`，不会把写出 `.tex` 等同于模板验收。CSV／JSON 保留数据及单位说明；数据量、元数据和格式满足哪种期刊机器可读表流程，也需按实际任务核实。

## 输出记录与期刊边界

常规图形除所选格式外，保存 `.data.json`、`.caption.md`、`.export.json` 与 `.qa.json`；其中包括实际数据、配置、来源、软件版本及可测检查。默认色板筛查有自己的范围说明，不能替代对自定义图实际颜色、透明混合或连续色图的检查。HTML 另外记录 `.interactive.json`。

PDF/SVG 可以保留矢量内容，PNG 适合预览；文件后缀不保证所有内容都是矢量、字体已经满足编辑要求或内嵌图像分辨率足够。工作副本允许便于审阅的格式，实际投稿格式按目标期刊判断。

期刊配置和未核实项见 [journals.md](journals.md)。AAS、A&A、MNRAS 和 Nature Astronomy 的规定各自适用；文章类型、初稿／终稿及主图／Extended Data／补充材料仍需区别。数值未知、资料暂定、字体可嵌入或自动检查通过，都不能替代最终人工审阅及官方最新要求。检查记录明确不认证期刊合规。

## 继承的功能与 MIT 许可

原 `scientific-visualization` 的导出、元数据、色板审查、样式和出版参考资料保留在 `vendor/scientific_visualization/`。本工具将这些组件与自有领域图型、数据接入和检查功能组合使用，保留上游 MIT 许可证及提交来源。

高级组件说明在该目录的 `UPSTREAM_GUIDE.md` 与 `references/`；许可和实际用于科研产物时的引用说明见 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)。本工具属于基于开源组件建设的课题工具，继承部分应继续如实署名和溯源。
