# 通用天文学图表资料来源

核查日期：2026-11-13。以下为官方软件文档，服务于数据语义、绘图与专用接口选择；未以这些软件的可用性宣称它们均已安装或接入本工具。`stable`、`latest` 页面会变化，实际项目还应记录使用的软件版本和相关输入处理配置。

| 官方资料 | 本工具使用的依据 | 对实际研究的要求 |
| --- | --- | --- |
| [Astropy FITS](https://docs.astropy.org/en/stable/io/fits/index.html) | FITS 由 HDU 组织头信息与图像/表；读入需明确所用扩展和数据结构 | 保留原文件、HDU 选择、头信息、单位、掩码和切片，不以打开文件成功代替校准或科学验证 |
| [Astropy WCS](https://docs.astropy.org/en/stable/wcs/index.html) | 像素与世界坐标转换；API 的坐标/数组顺序和起点约定 | 防止 `(x, y)` 与 `(row, column)`、0 起点与 1 起点混淆；复杂失真与多维耦合按产品验证 |
| [Astropy WCSAxes](https://docs.astropy.org/en/stable/visualization/wcsaxes/index.html) | 在 Matplotlib 中显示带世界坐标的图像与坐标网格 | 正确性取决于输入 WCS；图上有 RA/Dec 标签不能证明影像已经配准 |
| [Astropy units](https://docs.astropy.org/en/stable/units/index.html) | 物理量、单位和需要明确条件的等价变换 | 展示单位可由元数据传递；频谱、流量密度或速度变换应保存明确的转换过程 |
| [Astropy time](https://docs.astropy.org/en/stable/time/index.html) | 区分时间表示与 UTC、TT、TDB 等时间尺度 | 保存历元、尺度、地点和已经实施的校正；不凭 JD/MJD/BJD 名称推断全部时间语义 |
| [Matplotlib Figure](https://matplotlib.org/stable/users/explain/figure/figure_intro.html) | Figure/Axes 是自定义组合图与统一导出的基础 | 新研究图形可以直接构建 Figure，不必局限于固定 recipe 名称；最终尺寸仍需检查 |
| [healpy 官方教程](https://healpy.readthedocs.io/en/latest/tutorial.html) | HEALPix 的 RING/NESTED 排序、像素与无效值约定 | 接入全天地图时明确排序、分辨率、坐标系和掩码；不把一维像素数组直接 reshape 为经纬网 |
| [ligo.skymap 官方文档](https://lscsoft.docs.ligo.org/ligo.skymap/) 与[天图绘制](https://lscsoft.docs.ligo.org/ligo.skymap/plot/allsky.html) | 引力波概率地图的读写、后处理与绘制；不同天图投影和坐标约定 | 分清概率与概率密度，可信区域采用有记录的处理算法；该软件是按需适配选项 |
| [reproject 官方说明](https://docs.astropy.org/projects/reproject/en/latest/index.html) 与[算法及通量约定](https://docs.astropy.org/projects/reproject/en/latest/explanation/algorithms.html) | WCS 重采样与图像拼接；插值和面亮度/通量保存具有不同性质 | 重投影假定输入 WCS 正确，不能代替缺失 WCS 的图像配准。输出需记录算法、覆盖与测光约定 |
| [CASA 图像分析](https://casadocs.readthedocs.io/en/stable/notebooks/image_analysis.html) | 成像产品、谱立方、矩分析等领域处理的适配入口 | 绘图前明确谱轴、通道、掩码和波束；专门处理软件的结果不由通用显示步骤重新解释 |

访问边界：本次成功读取以上 Astropy、Matplotlib、healpy、CASA 官方页面。`ligo.skymap` 总览及天图绘制内容来自官方检索结果；直接访问旧的 `plot/index.html` 路径失败，因此改用仍有官方索引的总览及 `plot/allsky.html`。`reproject` 的旧 Read the Docs 入口重定向受阻，采用官方 Astropy 项目文档的索引正文。具体调用这些可选软件时，再核对当时版本的完整 API；本次没有安装它们或执行其科学处理。
