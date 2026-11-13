---
name: astro-paper-figures
description: 为各类天体和天文学研究制作可复现的论文图表、期刊配置输出和交互补充图。支持天球与WCS图像、测光、光谱、时序、动力学、恒星与多星、行星、星系、宇宙学和多信使等图表，并按具体研究扩展新图型。
metadata:
  version: "2.0.0"
  author: "PatrickZhu26"
---

# 天体科研论文图表

围绕科学问题选择图形，保留数据来源、单位、变换、误差定义与生成脚本。这个工具提供可复用实现和判断依据，图型目录和期刊配置都可以按任务扩展。

## 入口

本目录 `scripts/astro_figures.py` 提供 `list`、`journals`、`render`、`table`、`inspect`；旧的 `stellar_figures.py` 与 `stellarplot` Python 接口保留兼容。
建议在仓库根目录创建 Python 3.12 虚拟环境，并用 `requirements.txt` 安装依赖；`requirements.lock.txt` 保留已验证版本。

```sh
".venv/bin/python" /path/to/astro-paper-figures/scripts/astro_figures.py list
".venv/bin/python" /path/to/astro-paper-figures/scripts/astro_figures.py render spec.json --output figures/rv --journal mnras
```

`/path/to/astro-paper-figures` 指当前技能目录；先定位实际目录再运行。通用天文学入口、FITS/WCS与自定义期刊配置见 [astronomy-usage.md](references/astronomy-usage.md)，天体类别与研究问题路由见 [astronomy-scope.md](references/astronomy-scope.md)。原有基础与多星图表接口见 [usage.md](references/usage.md)；输入契约见 [data-contract.md](references/data-contract.md)，期刊配置和未确认项见 [journals.md](references/journals.md)。

## 图表选择与扩展

`list` 返回实际实现的图型、必需字段和说明。覆盖通用编码以及轨道、光变/RV拟合残差、相位、天测、O−C、频谱、稳定性、相空间、长期演化、恒星性质、后验、采样与数值性能图。
原有多星专题对应关系见 [coverage.md](references/coverage.md)，仍包含各种双星/三星，不要求系统为层级结构或点质量模型。新增天球/WCS、色星等、透射谱、多波段时序、BPT、哈勃图、径向剖面、族群分布、角功率谱、灵敏度与演化等入口；目录用于路由，天体类别不是输入白名单。
Roche 等势面、共振结构、SED 或仪器相关图应读取相应科学计算结果，绘图器不凭外观生成物理证据。
目录没有的图型可以直接用 Matplotlib/Plotly 编写，再调用统一导出接口；不要因为未列在目录中而放弃研究或强行改成不合适的图。新图型使用同样的数据溯源和验证方式，并可补充成新 recipe。

```python
import sys
sys.path.insert(0, "/path/to/astro-paper-figures/scripts")
from stellarplot.core import journal_style, export
with journal_style("mnras"):
    # 使用真实数据建立任意 Matplotlib Figure
    report = export(fig, "figures/custom", data=data, caption=caption,
                    journal="mnras", width="single")
```

复杂布局可直接使用 GridSpec、subplot_mosaic 或 subfigures。交互图可用 `stellarplot.interactive.export_interactive` 输出任意 Plotly Figure，或对已支持图型使用 `render --html`；HTML 和静态投稿文件分别交付。

## 科学表达

区分实测值、模型、插值、预测、合成示例和后验样本。拟合最优解不能冒充后验样本，训练残差不能冒充留出预测。
不同恒星、仪器、模型候选与观测时段须明确分组；按时间连接前先核实排序和缺测间隔。相位计算需要周期和历元，BJD/HJD/MJD 及时间尺度不由列名猜测。
误差条、置信区间、可信区间、散布和上下限注明含义。保持不对称误差、缺测断点和异常点说明，不静默抹去不利数据。
热图、等高线和归一化标明量、单位、掩码与色标；同类对照采用可比较的范围。用颜色结合线型/符号，检查灰度及色觉差异。
轨道投影保持适当几何比例并声明坐标约定；HR图的方向依温度/色指数定义决定；误差与耗时比较需保留可比物理、精度目标和硬件条件。
表格提供可编辑 LaTeX 与机器可读 CSV，单位、有效数字及不确定度定义随数据交付。目标期刊原生模板中的编译与长表安排单独验证。
FITS图像与目录保留HDU、显式立方切片、缩放/缺测约定和WCS；跨坐标系目录叠加要声明角度单位及所需分点/时刻/位置。区分像素概率与概率密度、Cl与Dl、ASD与PSD、不同距离定义和波长/频率红移方向。HEALPix/MOC、重投影、射电立方处理、MHD或相对论辐射等专业结果可由相应科学软件计算后接入；按问题读取 [astronomy-sources.md](references/astronomy-sources.md) 与 [sky.md](references/sky.md)，不将绘图器当成全部物理算法。

## 期刊与检查

配置包含 general、AAS、A&A、MNRAS 和 Nature Astronomy 的带日期资料。区分官方门槛、本地建议和未核实项；暂定配置或格式样式不代表投稿合规。不同文章类型、初稿/终稿及补充材料可能有不同要求，按当时官方说明补充配置。
其他期刊可用 `--profile-file` 或 `register_profile` 加入当前任务配置；用户只给期刊名时，代为核对官方说明并生成设置即可，无需要求用户手写JSON。
导出以最终物理尺寸检查文字边界、嵌入字体、PDF字体类型和文件元数据，保存源数据、caption、版本与检查记录。PNG/SVG等可作为工作副本，实际投稿格式以目标期刊规定为准。
最终审阅原图和论文内的实际尺寸，检查重叠、遮挡、图注、单位、误差定义及真实科学含义。自动报告不代替这些判断。保留失败结果和修正记录，避免只凭成功写文件宣称验收。

## 继承组件与参考

`vendor/scientific_visualization/` 保留原工具的导出、样式、色板/对比审查、元数据检查和出版资料，作为本工具内部组件。其脚本仍可单独运行；高级细节可按需查阅其中 `UPSTREAM_GUIDE.md` 与 `references/`。原组件的MIT许可证、来源提交和引用说明随包保留，改造后的工具不能冒充完全原创的上游代码。
新工具的来源、许可与上游论文致谢条件见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。使用资料与脚本版本可随论文软件说明记录。
