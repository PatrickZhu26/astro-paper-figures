# 天文学期刊图表配置与使用边界

核查日期：2026-11-12。配置在 `assets/journals.json`。这是有日期的部分规范快照；编辑部、文章类型、稿件阶段和最新官方指南共同决定最终要求。`official_snapshot` 只表示已读官方页面，不能作为自动投稿认证。`provisional` 表示仍有明确访问或核实缺口。

## 如何读取配置

- `widths_mm` 只收录已核实的官方单／双栏值；`null` 表示未确认，不能解释为无限制。`recommended_width_mm` 是本工具排版起点。
- `font_size_pt` 是建议工作字号；`min_font_pt` 和 `min_line_pt` 才是已核实门槛。普通字体族只是本机可渲染的选择，不能代替字体嵌入检查。
- DPI 只约束位图或矢量文件内嵌的位图；PDF/SVG 后缀本身不能证明所有内容均为矢量。
- `supported_formats` 是本次核查能确认的提交格式；空列表表示未确认。SVG 可用作编辑中间文件，是否可提交需单独判断。
- 显示项目数、图注长度、补充材料和交互图要求应按文章类型核查，不从一种稿件推及全部稿件。

## AAS：ApJ、AJ、ApJS 等

已直接核查[图形指南](https://journals.aas.org/graphics-guide/)。它给出 6 pt 字号和 0.5 pt 线宽下限；位图至少 300 dpi、横向至少 1000 像素。单、双栏宽度留空，按实际稿件模板测量。交互或动画仍需静态代表图。

[AASTeX 7 指南](https://journals.aas.org/aastexguide/)优先使用 `deluxetable`；跨栏、长表、横置表有各自环境和命令，需在目标 class 中编译。超过 200 行的长表应走机器可读数据流程，并附短样表或列描述；仅生成普通 booktabs 表不代表完成 AASTeX 适配。

## A&A

[官方作者指南 PDF](https://www.aanda.org/doc_journal/instructions/aadoc.pdf)的索引正文给出单栏 88 mm、全宽最多 180 mm；允许 EPS/PDF/JPG/TIFF，并要求背景网格有科学含义。直接抓取返回 403，因此此配置暂定，尚未完整核验当前 PDF。8 pt serif 是本工具建议；未确认的字号、线宽和 DPI 门槛保留空值。

表格使用目标 `aa` 类的 `table`／`table*`、`tabular` 及相应表注机制。机器可读数据另存，并保留列名、单位、缺测值和说明。当前模板版本及 CDS 提交流程须在真实投稿时复核。

## MNRAS

已直接核查[作者指南 §2.4、§2.7、§5.3、§6.1](https://academic.oup.com/mnras/pages/General_Instructions)。艺术制作段落给出单栏 84 mm、约 8 pt、线宽至少 0.3 pt；定量图要求四边框及四边刻度。灰阶 TIFF 为 300 ppi，混合图为 800 ppi；另有一般位图至少 400 dpi 的表述，不能混为一条统一门槛。

表格采用顶、底及表头下横线，不用竖线。单栏 `table` 或跨栏 `table*` 应在实际 MNRAS 类中检查。长表附样表、完整机器可读数据与列说明；在线附件不会由出版方自动编译 LaTeX。

## Nature Astronomy

使用 [Nature Astronomy 专属 AIP 指南](https://www.nature.com/natastron/submission-guidelines/aip-and-formatting)，没有沿用 Nature 主刊参数。官方索引全文给出最大宽 180 mm、标准文字 5–7 pt sans serif、图像至少 300 dpi；标签及尺度／误差条应可编辑。直接访问重定向到不可用认证端点，所以格式清单和完整规则待复核，配置暂定。

表格放在正文文件末尾，复杂表可单独提供 Excel，统计表注解释误差。[文章类型](https://www.nature.com/natastron/content)和[首次投稿](https://www.nature.com/natastron/submission-guidelines/initial-formatting)另有要求；主图、Extended Data、补充图表不能混用同一套数量或文件规定。

## 出图后的实际核验

检查物理页尺寸、最小文字和线宽、字体嵌入、位图实际像素与有效 DPI，以及最终稿件中的遮挡和裁切。机器检查只覆盖可测项目；阅读性、科学含义、图注、单位、误差定义、来源数据和编辑要求仍需审阅。保存当次所用配置、日期、输入与输出，投稿前重新查阅官方网页。
