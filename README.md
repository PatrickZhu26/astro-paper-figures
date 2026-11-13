# Astro Paper Figures

用于可复现天文学论文图表的 **Skill + 本地 Python 命令行工具**。

维护者：[PatrickZhu26](https://github.com/PatrickZhu26) · 版本：2.0.0

提供 68 个命名入口：49 个基础与多星研究入口，以及 19 个天球、图像和通用天文学专题入口。部分入口共享实现或为别名；特殊图型可通过 Matplotlib／Plotly 接口继续扩展。

## 功能

- 轨道、光变与径向速度、天测、O−C／ETV、势场与流场、恒星演化、后验与数值性能图。
- 天球投影、WCS 图像、源目录叠加、多波段图像、色星等图、光谱、位置—速度图、星系与宇宙学图表。
- JSON、CSV、TSV、ECSV、FITS 图像与目录、实数 NPY／NPZ 数据接入，保留单位、选择及来源哈希。
- PDF／SVG／PNG 等静态导出、部分入口的交互 HTML、可编辑 LaTeX／CSV 表格及表格预览。
- 记录输入、图注、显示变换、软件版本和输出检查；默认拒绝覆盖已有结果。

工具展示调用者提供的观测或计算结果，不替代物理求解器、统计推断或专业数据处理。图型目录不意味着穷尽全部天体物理算法；格式检查也不等于期刊接受。

## 安装

建议使用 Python 3.12 和独立虚拟环境。在仓库根目录运行：

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

本地出图不需要模型 API 密钥。需要交互输出时使用依赖中的 Plotly；专用科学处理软件按实际任务另行选择。

## 快速开始

查看入口、必需字段和期刊配置：

```sh
python scripts/astro_figures.py --version
python scripts/astro_figures.py list
python scripts/astro_figures.py journals
```

运行明确标注为合成数据的示例：

```sh
python scripts/astro_figures.py render examples/synthetic_radial_velocity.json \
  --output output/rv --journal aas

python scripts/astro_figures.py inspect output/rv.pdf

python scripts/astro_figures.py table examples/synthetic_parameter_table.json \
  --output output/parameters --journal mnras --preview
```

`--output` 使用不带扩展名的文件名。默认导出 PDF、SVG、PNG，并附数据、图注和检查记录。需要替换已有结果时显式使用 `--force`。

支持的图型可添加 `--html` 生成交互工作副本，例如：

```sh
python scripts/astro_figures.py render examples/synthetic_radial_velocity.json \
  --output output/rv_interactive --journal aas --html
```

示例只用于验证工具，不能作为真实观测或研究结果。

## 自定义期刊配置

内置 general、AAS、A&A、MNRAS、Nature Astronomy 的带日期资料，并区分官方要求、建议值和未确认项。实际使用时应核对目标刊物、文章类型和投稿阶段。

其他期刊可通过任务级 JSON 配置指定图宽、字体、字号、线宽、分辨率及输出格式。`--profile-file` 是全局参数，放在 `render` 之前：

```sh
python scripts/astro_figures.py \
  --profile-file examples/custom_journal_profile.json \
  render examples/synthetic_radial_velocity.json \
  --journal example-journal --output output/custom_rv
```

该配置文件只含演示数值，不代表某本真实刊物。自定义配置整体验证后应用，不改写打包的基础资料；切换排版配置不应改变研究数据。

## 数据与 Python 接口

图规格可内嵌数据，或通过 `data_path` 引用文件；相对路径以规格文件所在目录为基准。FITS 数据立方必须明确选择 HDU 和切片，坐标系、角度单位、星等系统、距离定义以及 PSD／ASD 等约定按入口声明。

原 `stellarplot` Python 命名空间和 `scripts/stellar_figures.py` 入口保留兼容。例如，自定义 Matplotlib 图可沿用统一导出流程：

```python
import sys
sys.path.insert(0, "scripts")

import matplotlib.pyplot as plt
from stellarplot.core import journal_style, export

data = {"x": [0, 1, 2], "y": [1.0, 1.5, 1.2]}
with journal_style("aas"):
    fig, ax = plt.subplots(layout="constrained")
    ax.plot(data["x"], data["y"])
    ax.set(xlabel="Test coordinate", ylabel="Test value")
    export(fig, "output/custom", data=data,
           caption="Synthetic interface example only.", journal="aas")
    plt.close(fig)
```

## 作为 Skill 使用

仓库根目录的 `SKILL.md` 是技能入口。将整个仓库复制或安装到所用兼容工具的技能目录，保留 `scripts/`、`assets/`、`references/` 和 `vendor/` 的相对位置。具体发现及加载方式遵循所用工具的说明。

## 文档与检查

- [使用与数据接入](references/astronomy-usage.md)
- [研究范围与扩展方式](references/astronomy-scope.md)
- [基础和多星图表入口](references/usage.md)
- [天球与 WCS 契约](references/sky.md)
- [期刊要求与验证边界](references/journals.md)
- [官方技术资料](references/astronomy-sources.md)

`tests/` 包含合成夹具、数据和科学表达检查及图库生成脚本。运行自动化检查：

```sh
python -m unittest discover -s tests -p 'test_*.py'
```

图库生成会产生较多文件，请使用独立输出目录。自动检查不能替代对单位、误差定义、图注、真实科学含义和论文内最终尺寸的审阅；原生 LaTeX 表格还需在目标期刊模板中编译。

## 第三方组件与引用

本项目的部分导出、样式、色板及元数据检查组件来自 **K-Dense Scientific Agent Skills**，以 MIT 许可证保留于 `vendor/scientific_visualization/`。这些复用组件的原版权和许可随仓库分发。

请查看 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)、[组件许可证](vendor/scientific_visualization/LICENSE.md) 和 [技术资料索引](references/astronomy-sources.md)。底层科学库分别遵循各自许可证。
