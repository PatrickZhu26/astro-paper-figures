# 双星与三星论文图表覆盖矩阵

本工具服务于各种双星与三星研究的**数据表达与图表交付**，不限定层级结构、点质量近似、系统是否相接或天体是否为普通恒星。现成 recipe、通用编码和自定义 Matplotlib/Plotly 接口共同构成覆盖范围。下列输入均应来自可核查的观测、推导或科学程序；合成测试不代表物理验证。

## 系统及科学问题

| 系统 / 问题 | 已有图表入口 | 使用边界 |
| --- | --- | --- |
| 不相接、圆轨道及偏心双星；目视、分光、天测双星 | `orbit2d`、`orbit3d`、`radial_velocity`、`astrometry`、`timeseries_fit` | 输入各星坐标或各组可观测量；明确质心、相对坐标、投影及时间单位 |
| 食双星、食三星；多仪器光变 | `light_curve`、`phase_curve`、`eclipse_geometry`、`eclipse_timing`、`etv` | 光变来自外部物理模型；圆盘图仅表达投影几何，不能代替形变、亮度及遮掩积分 |
| 半相接、相接、过相接、Algol 类；质量交换 | `roche_map`、`transfer_history`、`contour`、`image`、`quiver`、`streamlines` | 势场、临界点、质量转移率、形变表面与流场均需科学计算提供；不同旋转/偏心条件不能套用同一 Roche 近似 |
| 吸积、盘、喷流、共包层相关双星/三星研究 | `image`、`dynamic_spectrum`、`spectrum`、`sed`、`polarimetry`、`transfer_history`、流场图 | 输出已计算的辐射/流体结果；图形流线不是物质随时间运动的积分解 |
| 层级三星、摄动、长期轨道交换、潮汐与相对论修正 | `orbit2d/3d`、`secular_evolution`、`phase_portrait`、`poincare`、`stability_map`、`oc` | 不重新求轨道根数、不判定物理机制；注明根数定义、平均方式和参考系 |
| 非层级、共振、混沌、近遇、散射、交换、逃逸或碰撞三星 | 同样使用多对象 `orbit2d/3d`、相空间图、`stability_map`、`line`、`heatmap` | 绘图不假设层级结构或封闭椭圆；逃逸、碰撞和稳定性判据由模型及论文定义 |
| 紧致双星/三星、脉冲星计时、引力波相关可观测量 | `line`、`timeseries_fit`、`oc`、`dynamic_spectrum`、`spectrum`、后验图 | 使用相应理论产生的时间序列、波形、频谱或计时残差；不生成波形或替代相对论计算 |
| 干涉观测与分辨天测 | `visibility`、`uv_coverage`、`astrometry`、`image` | 说明振幅或平方可见度、基线/波长单位及观测约定；不自动制造共轭采样或执行成像反演 |
| 恒星性质、演化轨迹与双/三星总体分布 | `hr_diagram`、`mass_radius`、`scatter`、`histogram`、`bar`、`boxplot`、`violin` | 描述质量、半径、光度、年龄等已算量；不同物理量分面显示或明确归一化 |
| 巡天选择、检出率、样本与总体推断 | `selection_function`、`heatmap`、`histogram`、`scatter`、区间图及表格 | 选择概率必须由数据或注入恢复实验提供；不从一张图自动建立完备性校正 |
| 参数反演、退化、多解、误差与预测 | `corner`、`trace`、`autocorrelation`、`forest`、`correlation`、`envelope`、`residual_diagnostics` | 后验样本与最优拟合值分开；链图不自动证明收敛，Q–Q 图不自动证明正态 |
| 数值方法、守恒、收敛、效率和跨软件比较 | `convergence`、`benchmark`、`line`、`errorbar`、`heatmap` | 精度、硬件、模型和工作负载可比性单独建立；绘图不把更快自动解释为更优 |

## 主要输入契约

- `line/scatter/errorbar` 等：`x[N]`、`y[N]` 或 `y[N,K]`。多系列表示不同恒星、仪器或模型时提供 `labels[K]`。误差可为共享 `yerr[N]`、不对称 `yerr[2,N]`、逐系列 `yerr[N,K]` 或 `yerr[2,N,K]`；N=K=2 时二维误差按共享不对称格式解释，需要逐系列时用三维格式。
- 拟合图：`x`、`observed`、`model` 必须在同一组时刻上匹配，可加 `sigma`。残差以观测减模型计算；`residual_ylabel` 明确单位。`model_points=true` 可避免稀疏或未排序采样被折线误连；也可在原序列加入明确的 NaN 断点。
- 星等图：`invert_y=true` 只改变显示方向；拟合图只反向上方观测轴，残差符号保持不变。温度 HR 图默认温度向右减小；色星等图设置 `hr_x_kind="color"` 或 `temperature_decreases_right=false`，并填写正确轴名。
- `orbit2d/3d`：每个空间坐标可为 `[N]` 或 `[N,K]`。二维和三维坐标必须使用相同空间单位才能解释等比例显示；同样适用于非层级、散射和逃逸轨迹。
- `eclipse_timing/etv/oc`：`x` 是历元或时间，`y` 是外部已经计算的 O−C/ETV，可加误差；绘图不拟合星历，也不把残差自动归因为第三体。
- `transfer_history`：`x`、`y[N,K]`、`ylabels[K]`，后者写明质量、质量率、角动量或自转等量及其单位；各量分面，绘图不求导。
- `roche_map`：`x[Nx]`、`y[Ny]`、已算势场 `z[Ny,Nx]`，并明确给出 `levels`。可提供 `critical_points={x,y,labels}`；位置与名称均来自科学计算。该 recipe 不能凭图形外观创造 L1/L2 等证据。
- `eclipse_geometry`：`centers[2或3,2]`、正 `radii[2或3]`。默认只画轮廓；填充遮挡需要明确的 `front_order`，按从后到前列出各星索引。只表示圆盘投影，不包含真实形变、临边昏暗或光度。
- `quiver/streamlines`：`x/y` 与 `u/v` 来自已有流场；流线要求严格递增且均匀的坐标网格，不会悄悄重采样。
- `dynamic_spectrum`：`x=时间`、`y=频率或谱坐标`、`z[Ny,Nx]=功率或通量`；注明归一化、时间窗、谱轴及单位。STFT/小波/傅里叶计算由上游完成。
- `visibility/uv_coverage/polarimetry`：通用 x/y 系列附明确物理定义。Stokes 系列提供 `labels`；偏振归一化、位置角周期、可见度定义均不自动推断。
- `selection_function`：网格 `x/y/z`，有限 z 必须在 `[0,1]`；无效单元保留掩码，不生成检测概率。
- 后验类：`samples[draw,parameter]`，链类也接受 `[draw,chain,parameter]`。缺测、预热剔除和权重如需处理应显式记录。`autocorrelation` 为每链减均值、按零滞后归一化的有偏 ACF，不自动估算有效样本量。

## 目录之外的表达

没有独立名称的专题，如多普勒层析图、光谱线轮廓序列、相互食事件时间线、角度轨迹、共振角、注入恢复矩阵或专门的模型结构示意图，可以使用已有通用编码组合，或建立任意 Matplotlib/Plotly Figure 后调用统一导出接口。依照科学问题决定是否增加新 recipe；不为图型目录强行改变数据含义。

这是双星与三星领域的广覆盖及可扩展实现，不是对所有未来论文图型的穷举证明，也不是所有天体物理的专门计算包。实际科学输入、推导、拟合、动力学/流体/辐射传输、频谱分析和统计检验应使用适当方法及程序独立验证。

期刊配置的官方门槛、建议和未确认项见 [journals.md](journals.md)。同一期刊的文章类型、投稿阶段、主图与补充材料也可能不同；能够导出某种文件并不自动证明符合全部期刊规范。
