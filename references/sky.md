# 天球、WCS 与多图像输入

本模块显示已给定的数据，不完成天体测量标定、图像配准、重投影或定位概率推断。

- `sky_map`：提供 `lon`、`lat`、`frame`、`lon_unit`、`lat_unit`；赤道坐标也可用 `ra`、`dec`。单位必须是 Astropy 可识别的角度单位，如 `deg`、`rad`、`hourangle`。纬度须在 ±90°；经度接受一个有符号或无符号周圈，先转换为度后检查。默认经度向左增加，可通过 `longitude_increases_left` 更改。`center_lon_deg` 仅改变投影中心，默认 0°。Mollweide、Hammer 和 Aitoff 的绘制坐标转换及经度包装记入元数据。
- 需要分点、观测时刻或观测位置的坐标系，必须显式提供相应 `frame_attributes.equinox`、`obstime`、`location`，不使用未知来源的默认 J2000 或默认时刻。叠加时这些属性用于实际 Astropy 坐标变换；复杂时间/位置对象不能由输入表达时，先用明确配置的自定义 Astropy 接口转为可表达的坐标系。
- `wcs_image`：提供二维 `image` 与 `wcs_header` 字典。头必须给出真实二维天球 WCS；存在的 `NAXIS1/2` 必须与图像形状相符。读取 FITS 或从数据立方体切片时，由调用方同时得到正确的二维 WCS。显示遵循输入头的旋转和方向，不强制北上东左。
- `sky_catalog`：在 `wcs_image` 输入上增加 `catalog`，其坐标契约与 `sky_map` 相同；可额外提供 `frame_attributes`。源位置经 Astropy 从声明的坐标系转换到图像像素。没有所需历元、时间或位置属性而无法转换时会报错，不凭列名猜测。图像范围外的源保持在来源数据中，显示时裁剪并计数。
- 可选 `contours` 是列表，每项有自己的 `image`、`wcs_header` 与明确的 `levels`。等高线通过其 WCS 转换显示，不对原始数组重新采样。
- `localization_map`：提供升序一维经纬网格、角度单位、`frame`、二维 `probability[latitude,longitude]` 和 `probability_type`。`per_pixel` 值为非负像素概率且总和不超过 1；`density` 必须另外给出与逆立体角相容的 `probability_unit`，如 `sr-1`。不重新归一化、不计算球面面积或可信域；HEALPix 输入需先由合适工具按明确方式转为地图，不能把数组重排当成投影。
- `image_montage`：提供 `images` 列表及一一对应的 `titles`，可提供 `units`、`wcs_headers` 和 `alignment`。默认共用数值色标，声明单位不相同则拒绝共用；可用 `shared_scale=false` 分开。共标度不等于各波段已经具有相同标定、PSF 或空间分辨率。

图像 NaN 显示为灰色掩码；无穷值会报错。对数色标要求有限像素为正，不静默抹去零或负值。显式设置的色标截断范围会在记录中报告超出范围的像素数。

实现时核对的官方资料（2026-11-13）：

- [Astropy WCSAxes](https://docs.astropy.org/en/stable/visualization/wcsaxes/)
- [WCS 标记、目录与等高线叠加](https://docs.astropy.org/en/stable/visualization/wcsaxes/overlays.html)
- [Astropy 角度的包装与边界](https://docs.astropy.org/en/stable/coordinates/angles.html)
