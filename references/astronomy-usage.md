# 通用天文学图表：日常使用

当前包名为 `astro-paper-figures`，版本 2.0.0。原有 49 个基础/多星入口保留，新增 19 个通用天文学专题入口，共 68 个名称；其中部分名称共享实现。通用 Python 接口可用于目录之外的科学图，按实际课题补充计算、数据接入和验收。

## 最常用的方式

指定目标与数据，例如：

> 读取这组 FITS 图像和源目录，制作带正确天球坐标的多波段图，按 ApJ 终稿要求导出，并附可追溯的数据和图注。

使用时核实数据含义、坐标和期刊要求，选择现有入口或创建合适的新图型，再检查实际文件。数据不能因换期刊而被静默重新拟合或筛选。

## 新增入口

天球/图像：`sky_map`、`wcs_image`、`sky_catalog`、`localization_map`、`image_montage`。输入及坐标上下文详见 [sky.md](sky.md)。

其他专题：`color_magnitude`、`bpt_diagram`、`hubble_diagram`、`radial_profile`、`luminosity_function`、`transmission_spectrum`、`multi_band_lightcurve`、`spectral_lines`、`position_velocity`、`angular_power_spectrum`、`sensitivity_curve`、`evolution_tracks`、`abundance_pattern`、`rotation_curve`。

运行 `list` 查看每项实际必需字段；单位、红移/参考系、星等系统、距离种类及谱密度约定按入口明确声明，不靠变量名猜测。

```sh
PLOT_PY=".venv/bin/python"
PLOT_SKILL="."
"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" list
"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" render spec.json --output figures/result --journal aas
```

## FITS、目录与数值数组

普通 JSON/CSV/TSV/ECSV 沿用原数据契约。JSON 图规格可用 `data_path` 指向文件；相对路径以该规格文件所在目录为基准。

FITS 图像默认读取指定图像 HDU。三维及以上图像必须明确选择所有前置 NumPy 轴，避免把数据立方隐式压成图片：

```json
{
  "kind": "wcs_image",
  "data_path": "data/image.fits",
  "data_loader": {"format": "fits_image", "hdu": 0},
  "caption": "Describe the object, quantity, coordinate system and display here."
}
```

数据立方可另加 `"plane": [3]`；它选择数组第 0 轴的索引 3，不代表自动识别波长或速度。天球 WCS 不位于实际显示的两个像素轴时，本内建读取器拒绝猜测，应先制作科学上正确的切片或使用 Astropy WCSAxes 的显式切片接口。

FITS 目录使用 `"data_loader": {"format": "fits_table", "hdu": 1, "columns": ["RA", "DEC"]}`，再通过 `mapping` 将列名映射为入口字段。目录单位和缺测记录会保存；需要的参考系、角度单位等可随规格显式提供，或调用 Python API 组合元数据。
同时使用 `data_path` 与 `data` 时，`data` 用于补充 `frame`、`lon_unit`、`lat_unit`、`catalog` 等声明；它不能覆盖已读取的列、图像、WCS或来源记录。已有值的科学换算应在显式、可追溯的预处理步骤完成。

NPY 返回 `array` 字段，NPZ 保留数组名，使用 `mapping` 指定科学含义。仅允许实数数值数组，禁用 pickle，拒绝重复数组名、Infinity和过大输入；NaN仍表示缺测。大数据应先做可追溯的科学子集。

Python API：`stellarplot.astroio.load_fits_image`、`load_fits_table`、`load_numpy`、`load_input`；统一绘制入口是 `stellarplot.registry.render`，原 `stellarplot.recipes.render` 仍保持原 49 项兼容。

## 自定义期刊配置是什么意思

期刊配置是一份排版设置，保存最终图宽、字体/字号、线宽、位图分辨率和允许格式，并记录官方来源、核对日期及稿件阶段。用户只需说“按某期刊的初稿/终稿要求”，使用前核对官网并生成设置。

切换配置改变图表的排版和输出，不重算或改变研究数据。官网未明确的字段保持未知或注明建议；配置不会变成投稿认证。

需要查看配置文件时，可参考 `examples/custom_journal_profile.json`。该文件是演示数值，不属于任何真实刊物的规范。使用时把其中值替换为实际期刊的官方要求：

```sh
"$PLOT_PY" "$PLOT_SKILL/scripts/astro_figures.py" \
  --profile-file my_journal.json render spec.json \
  --journal my-journal --output figures/result
```

配置文件根对象包含 `profiles`，其中 `my-journal` 是自选名称。整个文件先验证成功再应用；设置仅影响当前进程，不改写打包的五套资料。Python 可用 `stellarplot.core.register_profile` 注册同样的配置。

## 科学软件与特殊图

全天 HEALPix/MOC、CASA 数据立方、复杂 WCS 重投影、数值相对论、MHD 与辐射输运等计算由适合的科学软件完成，保留其约定和结果再接入。任意 Matplotlib Figure 可交给 `stellarplot.core.export`；任意合适的 Plotly Figure 可用交互导出接口。外部地图或图片资源不会被无条件标记成离线自包含。

数据的实际来源、单位、变换、掩码、颜色归一化、软件版本和原生期刊表格编译等边界，随结果一起交付。
