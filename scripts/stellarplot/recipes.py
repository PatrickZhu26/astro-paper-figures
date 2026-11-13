"""Data-driven astronomical figure recipes; no physical model is fitted here.

Public API: ``render(kind, data, options=None) -> (Figure, metadata)``.
Most line/scatter recipes accept x[N], y[N] or y[N, series], and optional
yerr[N], yerr[2, N], yerr[N, series] or yerr[2, N, series].  Coordinates and
uncertainties are supplied in their intended display units. Fit recipes need
model values at each observed x. Matrix maps use z[Ny, Nx], x[Nx], y[Ny].
RECIPES documents special schemas. Missing line values remain gaps; no recipe
silently drops observations, changes units, estimates orbital parameters, or
turns an optimizer solution into posterior samples.
"""
from __future__ import annotations

from typing import Any

import matplotlib.pyplot as plt
import numpy as np


RECIPES: dict[str, dict[str, Any]] = {}


def _register(kinds: str, required: list[str], category: str, description: str) -> None:
    for kind in kinds.split():
        RECIPES[kind] = {"required": required, "category": category, "description": description}


_register("line scatter errorbar", ["x", "y"], "general", "x[N], y[N] or y[N,K]; optional yerr, xerr")
_register("bar", ["x", "y"], "general", "categorical x[N], y[N] or y[N,K]; grouped bars")
_register("histogram", ["values"], "general", "finite values[N] or values[N,K]; shared bins")
_register("boxplot violin", ["groups"], "general", "list of finite one-dimensional groups; optional labels")
_register("heatmap image", ["z"], "general", "z[Ny,Nx]; optional x[Nx], y[Ny]; image also accepts RGB(A)")
_register("contour stability_map", ["x", "y", "z"], "maps", "x[Nx], y[Ny], z[Ny,Nx]; supplied diagnostic only")
_register("quiver", ["x", "y", "u", "v"], "maps", "x/y mesh or coordinate vectors and u/v[Ny,Nx]")
_register("envelope", ["x", "y", "lower", "upper"], "uncertainty", "x/y[N], lower/upper[N]; supplied interval")
_register("timeseries_fit light_curve radial_velocity", ["x", "observed", "model"], "observables", "matched x/observed/model[N] or observed/model[N,K]; optional sigma")
_register("phase_curve", ["x", "y", "period"], "observables", "x=time[N], y[N,K]; period>0, optional t0 and yerr; observations stay points")
_register("orbit2d astrometry", ["x", "y"], "orbits", "x/y[N] or x/y[N,K]; optional xerr/yerr; detached/contact/hierarchical or nonhierarchical trajectories; no coordinate convention assumed")
_register("orbit3d", ["x", "y", "z"], "orbits", "x/y/z[N] or x/y/z[N,K] in a common spatial unit; bound, resonant, nonhierarchical, scattering or escaping trajectories supplied by the model")
_register("oc eclipse_timing etv", ["x", "y"], "observables", "x=epoch or time, y=precomputed observed-minus-calculated eclipse timing / ETV; optional yerr; ephemeris is not fitted here")
_register("periodogram power_spectrum", ["x", "y"], "spectra", "x=frequency, y=supplied power; optional threshold; no significance inferred")
_register("secular_evolution", ["x", "y"], "dynamics", "x[N], y[N,K]; separate panels per supplied element; optional ylabels")
_register("transfer_history", ["x", "y", "ylabels"], "interacting_stars", "x=time[N], y[N,K], ylabels[K] include quantity and units; supplied masses, transfer rates, radii, spin or angular momentum; no derivatives computed")
_register("roche_map", ["x", "y", "z"], "interacting_stars", "supplied effective-potential z[Ny,Nx], x/y coordinate vectors; explicit levels required in data or options; optional critical_points mapping")
_register("eclipse_geometry", ["centers", "radii"], "interacting_stars", "projected centers[2 or 3,2], positive radii[2 or 3]; optional back-to-front front_order; geometric disks only, no flux calculation")
_register("streamlines", ["x", "y", "u", "v"], "interacting_stars", "uniform increasing x/y vectors and supplied u/v[Ny,Nx]; no hydrodynamic solver, coordinate interpolation or critical-point calculation")
_register("dynamic_spectrum", ["x", "y", "z"], "spectra", "x=time[Nt], y=frequency or spectral coordinate[Nf], z[Nf,Nt]; supplied power/flux map, no Fourier transform computed")
_register("visibility uv_coverage", ["x", "y"], "interferometry", "visibility: supplied baseline x[N] and amplitude/squared visibility y[N,K] with optional yerr; uv_coverage: sampled u/v coordinates, no conjugate points fabricated")
_register("polarimetry", ["x", "y", "labels"], "spectra", "supplied time/wavelength x[N], Stokes/polarization y[N,K], labels[K]; normalization and angular conventions declared by caller")
_register("selection_function", ["x", "y", "z"], "population", "supplied detection/selection probability z[Ny,Nx] in [0,1] on parameter grid; no completeness correction is inferred")
_register("phase_portrait poincare", ["x", "y"], "dynamics", "supplied phase-space coordinates or precomputed section crossings")
_register("hr_diagram mass_radius", ["x", "y"], "stellar", "supplied temperature/luminosity or mass/radius; optional errors")
_register("spectrum sed", ["x", "y"], "spectra", "supplied spectral coordinate and flux quantity; transformations only on explicit request")
_register("corner", ["samples"], "inference", "finite posterior samples[draw,parameter]; optional parameter labels")
_register("trace autocorrelation", ["samples"], "inference", "finite samples[draw,parameter] or [draw,chain,parameter]")
_register("forest", ["estimate", "lower", "upper", "labels"], "inference", "paired estimates and supplied interval endpoints[N], categorical labels[N]")
_register("correlation", [], "inference", "either matrix[P,P] with unit diagonal, or finite samples[draw,P]; optional labels")
_register("residual_diagnostics", ["residuals"], "diagnostics", "finite residuals[N]; optional x[N], sigma[N], standardize option")
_register("convergence benchmark", ["x", "y"], "numerics", "paired supplied step/tolerance versus error, or time versus error; no fairness claim inferred")


def _array(value: Any, name: str, *, ndim: int | tuple[int, ...] | None = None, missing: bool = True) -> np.ndarray:
    try:
        a = np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if ndim is not None and a.ndim not in ((ndim,) if isinstance(ndim, int) else ndim):
        raise ValueError(f"{name} has unsupported shape {a.shape}")
    if not a.size or np.isinf(a).any() or (not missing and np.isnan(a).any()):
        raise ValueError(f"{name} must be nonempty and contain no infinity" + (" or missing values" if not missing else ""))
    if not np.isfinite(a).any():
        raise ValueError(f"{name} contains no finite data")
    return a


def _need(data: dict, key: str) -> Any:
    if key not in data:
        raise ValueError(f"Required data field is missing: {key}")
    return data[key]


def _series(a: np.ndarray) -> np.ndarray:
    return a[:, None] if a.ndim == 1 else a


def _xy(data: dict, ykey: str = "y") -> tuple[np.ndarray, np.ndarray]:
    x = _array(_need(data, "x"), "x", ndim=1)
    y = _series(_array(_need(data, ykey), ykey, ndim=(1, 2)))
    if y.shape[0] != len(x):
        raise ValueError(f"x and {ykey} lengths do not match")
    if not np.any(np.isfinite(x[:, None]) & np.isfinite(y)):
        raise ValueError("No finite paired x/y observations")
    return x, y


def _labels(data: dict, options: dict, n: int, key: str = "labels") -> list[str]:
    labels = options.get(key, data.get(key))
    if labels is None:
        return [f"Series {i + 1}" for i in range(n)] if n > 1 else [""]
    if isinstance(labels, str) or len(labels) != n:
        raise ValueError(f"{key} must contain exactly {n} labels")
    return [str(x) for x in labels]


def _error(value: Any, n: int, k: int, name: str) -> list[np.ndarray | None]:
    if value is None:
        return [None] * k
    a = _array(value, name)
    if np.any(a[np.isfinite(a)] < 0):
        raise ValueError(f"{name} must be nonnegative")
    if a.ndim == 0:
        return [np.full(n, float(a)) for _ in range(k)]
    if a.shape == (n,):
        return [a for _ in range(k)]
    if a.shape == (2, n):
        return [a for _ in range(k)]
    if a.shape == (n, k):
        return [a[:, i] for i in range(k)]
    if a.shape == (2, n, k):
        return [a[:, :, i] for i in range(k)]
    raise ValueError(f"{name} shape {a.shape} does not match N={n}, K={k}")


def _scale_valid(a: np.ndarray, scale: str, label: str, error: np.ndarray | None = None) -> None:
    v = a[np.isfinite(a)]
    if scale not in {"linear", "log", "symlog", "logit"}:
        raise ValueError(f"Unsupported {label} scale: {scale}")
    if scale == "log" and np.any(v <= 0):
        raise ValueError(f"{label} log scale requires strictly positive finite values; nothing was dropped")
    if scale == "logit" and np.any((v <= 0) | (v >= 1)):
        raise ValueError(f"{label} logit scale requires values strictly between 0 and 1")
    if scale in {"log", "logit"} and error is not None:
        lo = a - (error[0] if error.ndim == 2 else error)
        hi = a + (error[1] if error.ndim == 2 else error)
        _scale_valid(lo, scale, f"{label} lower uncertainty bound")
        _scale_valid(hi, scale, f"{label} upper uncertainty bound")


def _decorate(ax: Any, options: dict, *, xlabel: str = "x (supplied units)", ylabel: str = "y (supplied units)", scales: bool = True) -> None:
    ax.set_xlabel(options.get("xlabel", xlabel))
    ax.set_ylabel(options.get("ylabel", ylabel))
    if options.get("title"):
        ax.set_title(str(options["title"]))
    if scales:
        # Re-applying even the same scale resets fixed categorical locators.
        if options.get("xscale", "linear") != ax.get_xscale():
            ax.set_xscale(options.get("xscale", "linear"))
        if options.get("yscale", "linear") != ax.get_yscale():
            ax.set_yscale(options.get("yscale", "linear"))
    if options.get("grid", False):
        ax.grid(alpha=0.25)
    for name in ("xlim", "ylim"):
        if name in options:
            bounds = _array(options[name], name, ndim=1, missing=False)
            if len(bounds) != 2 or bounds[0] == bounds[1]:
                raise ValueError(f"{name} must be two distinct finite bounds")
            if options.get(name[0] + "scale") == "log" and np.any(bounds <= 0):
                raise ValueError(f"{name} log bounds must be positive")
            getattr(ax, "set_" + name)(bounds)
    if options.get("invert_y", False):
        ax.set_ylim(sorted(ax.get_ylim(), reverse=True))


def _color(options: dict, i: int) -> str | None:
    colors = options.get("colors") or plt.rcParams["axes.prop_cycle"].by_key().get("color", ["#0072B2"])
    return colors[i % len(colors)]


def _draw_xy(ax: Any, x: np.ndarray, y: np.ndarray, data: dict, options: dict, *, points: bool = False, force_errors: bool = False) -> None:
    n, k = y.shape
    labels = _labels(data, options, k)
    ye = _error(data.get("yerr"), n, k, "yerr")
    xe = _error(data.get("xerr"), n, k, "xerr")
    if force_errors and "yerr" not in data and "xerr" not in data:
        raise ValueError("errorbar requires yerr or xerr")
    for i in range(k):
        _scale_valid(x, options.get("xscale", "linear"), "x", xe[i])
        _scale_valid(y[:, i], options.get("yscale", "linear"), "y", ye[i])
        kw = {"label": labels[i] or None, "color": _color(options, i)}
        if ye[i] is not None or xe[i] is not None:
            ax.errorbar(x, y[:, i], xerr=xe[i], yerr=ye[i], fmt="o" if points else "-", markersize=options.get("markersize", 3), capsize=2, **kw)
        elif points:
            ax.scatter(x, y[:, i], s=options.get("marker_size", 14), marker=["o", "s", "^", "D"][i % 4], **kw)
        else:
            ax.plot(x, y[:, i], linestyle=["-", "--", "-.", ":"][i % 4], **kw)
    if any(labels):
        ax.legend()


def _matrix(data: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    z = _array(_need(data, "z"), "z", ndim=2)
    x = _array(data.get("x", np.arange(z.shape[1])), "x", ndim=1, missing=False)
    y = _array(data.get("y", np.arange(z.shape[0])), "y", ndim=1, missing=False)
    if z.shape != (len(y), len(x)):
        raise ValueError("z must have shape [len(y), len(x)]")
    for label, coord in [("x", x), ("y", y)]:
        if len(coord) > 1 and not (np.all(np.diff(coord) > 0) or np.all(np.diff(coord) < 0)):
            raise ValueError(f"{label} grid coordinates must be strictly monotonic")
    return x, y, z


def _samples(data: dict, *, chains: bool = False) -> np.ndarray:
    a = _array(_need(data, "samples"), "samples", ndim=(2, 3) if chains else 2, missing=False)
    if a.shape[0] < 3:
        raise ValueError("At least three draws are required")
    return a[:, None, :] if chains and a.ndim == 2 else a


def render(kind: str, data: dict, options: dict | None = None) -> tuple[Any, dict[str, Any]]:
    """Render a validated recipe without mutating supplied arrays or dictionaries."""
    if kind not in RECIPES:
        raise ValueError(f"Unknown recipe {kind!r}; choose from {', '.join(RECIPES)}")
    if not isinstance(data, dict) or (options is not None and not isinstance(options, dict)):
        raise ValueError("data and options must be mappings")
    options = dict(options or {})
    for key in RECIPES[kind]["required"]:
        if key not in data and not (kind == "phase_curve" and key == "period" and key in options):
            raise ValueError(f"Required data field is missing: {key}")
    meta: dict[str, Any] = {"recipe": kind, "transformations": [], "notes": [], "uncertainty": options.get("uncertainty", "not supplied or not specified")}
    fig = None
    try:
        if kind == "corner":
            import corner
            samples = _samples(data)
            if samples.shape[0] <= samples.shape[1]:
                raise ValueError("corner needs more draws than parameters")
            labels = _labels(data, options, samples.shape[1])
            fig = corner.corner(samples, labels=labels, show_titles=options.get("show_titles", True), quantiles=options.get("quantiles", [0.16, 0.5, 0.84]), color=_color(options, 0), quiet=True)
            if options.get("title"):
                fig.suptitle(options["title"])
            meta["input_shape"] = list(samples.shape)
            meta["notes"].append("Supplied samples are displayed; sampling convergence was not established by this plot.")
        elif kind in {"trace", "autocorrelation"}:
            samples = _samples(data, chains=True)
            n, chains, params = samples.shape
            labels = _labels(data, options, params)
            fig, axes = plt.subplots(params, 1, sharex=True, squeeze=False, layout="constrained")
            maxlag = int(options.get("max_lag", min(100, n - 1)))
            if not 0 <= maxlag < n:
                raise ValueError("max_lag must be an integer between 0 and draws-1")
            warmup = int(options.get("warmup", 0))
            if not 0 <= warmup < n:
                raise ValueError("warmup must be between 0 and draws-1")
            for p, ax in enumerate(axes[:, 0]):
                for c in range(chains):
                    vals = samples[:, c, p]
                    if kind == "autocorrelation":
                        centered = vals - vals.mean()
                        denom = np.dot(centered, centered)
                        if denom == 0:
                            raise ValueError("Autocorrelation is undefined for a constant chain")
                        fftsize = 1 << (2 * n - 1).bit_length()
                        fft = np.fft.rfft(centered, n=fftsize)
                        vals = np.fft.irfft(fft * fft.conjugate(), n=fftsize)[:maxlag + 1] / denom
                    ax.plot(np.arange(len(vals)), vals, label=f"Chain {c + 1}", linestyle=["-", "--", "-.", ":"][c % 4], color=_color(options, c))
                if kind == "trace" and warmup:
                    ax.axvspan(0, warmup, color="0.8", alpha=0.4, label="Marked warmup; retained")
                ax.set_ylabel(labels[p] or f"Parameter {p + 1}")
                if chains > 1 or warmup:
                    ax.legend()
            axes[-1, 0].set_xlabel("Lag (draws)" if kind == "autocorrelation" else "Draw index")
            if options.get("title"):
                fig.suptitle(options["title"])
            meta["input_shape"] = list(samples.shape)
            if kind == "autocorrelation":
                meta["transformations"].append("Per-chain mean subtraction and FFT autocorrelation normalized by lag-zero sum of squares; biased estimator; no thinning or warmup removal")
        elif kind in {"timeseries_fit", "light_curve", "radial_velocity"}:
            x, observed = _xy(data, "observed")
            model = _series(_array(_need(data, "model"), "model", ndim=(1, 2)))
            if model.shape != observed.shape:
                raise ValueError("model and observed shapes must match at the same x")
            residual = observed - model
            if not np.any(np.isfinite(residual) & np.isfinite(x[:, None])):
                raise ValueError("No paired finite observed/model values at finite observation times")
            ye = data.get("sigma", data.get("yerr"))
            fig, axes = plt.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [3, 1]}, layout="constrained")
            obsdata = {"yerr": ye, "labels": data.get("labels")}
            _draw_xy(axes[0], x, observed, obsdata, options, points=True)
            for i in range(model.shape[1]):
                _scale_valid(model[:, i], options.get("yscale", "linear"), "model")
                if options.get("model_points", False):
                    axes[0].scatter(x, model[:, i], s=options.get("model_marker_size", 10), facecolors="none", edgecolors=_color(options, i), marker=["o", "s", "^", "D"][i % 4])
                else:
                    axes[0].plot(x, model[:, i], color=_color(options, i), linestyle=["-", "--", "-.", ":"][i % 4])
            _draw_xy(axes[1], x, residual, obsdata, {**options, "yscale": "linear"}, points=True)
            axes[1].axhline(0, color="0.4", linewidth=0.7)
            defaults = {"light_curve": "Flux (supplied units)", "radial_velocity": "Radial velocity (supplied units)"}
            axes[0].set_ylabel(options.get("ylabel", defaults.get(kind, "Observed / model (supplied units)")))
            axes[1].set(xlabel=options.get("xlabel", "Time (supplied system and units)"), ylabel=options.get("residual_ylabel", "O−model"))
            axes[0].set_xscale(options.get("xscale", "linear")); axes[0].set_yscale(options.get("yscale", "linear"))
            if options.get("invert_y", False):
                axes[0].set_ylim(sorted(axes[0].get_ylim(), reverse=True))
            if options.get("title"):
                axes[0].set_title(options["title"])
            meta["transformations"].append("Residual = supplied observed − supplied model at matched observation times")
            meta["notes"].append("Input order is retained. A connected model can bridge unsorted times or long observing gaps; verify sampling or use model_points=true / explicit NaN breaks. Inverted magnitude axes do not change residual signs.")
            meta["input_shape"] = list(observed.shape)
            if ye is not None:
                meta["uncertainty"] = options.get("uncertainty", "Supplied sigma/yerr; interval interpretation not inferred")
        elif kind in {"secular_evolution", "transfer_history"}:
            x, y = _xy(data)
            labels = _labels(data, options, y.shape[1], "ylabels")
            fig, axes = plt.subplots(y.shape[1], 1, sharex=True, squeeze=False, layout="constrained")
            for i, ax in enumerate(axes[:, 0]):
                _draw_xy(ax, x, y[:, i:i+1], {}, {**options, "labels": [""]})
                _decorate(ax, {**options, "title": None, "ylabel": labels[i]}, xlabel="Time (supplied units)")
                if i < len(axes) - 1:
                    ax.set_xlabel("")
            axes[-1, 0].set_xlabel(options.get("xlabel", "Time (supplied units)"))
            if options.get("title"):
                fig.suptitle(options["title"])
            meta["input_shape"] = list(y.shape)
            if kind == "transfer_history":
                meta["notes"].append("Supplied masses, rates, spins or angular momenta use separately labelled panels; no differentiation, conservation inference or accretion model is performed.")
        elif kind == "eclipse_geometry":
            from matplotlib.patches import Circle
            centers = _array(data["centers"], "centers", ndim=2, missing=False)
            radii = _array(data["radii"], "radii", ndim=1, missing=False)
            n = len(radii)
            if centers.shape != (n, 2) or n not in (2, 3) or np.any(radii <= 0):
                raise ValueError("eclipse_geometry needs two or three projected centers[N,2] and positive radii[N]")
            order = data.get("front_order", list(range(n)))
            if sorted(order) != list(range(n)) or any(not isinstance(i, (int, np.integer)) for i in order):
                raise ValueError("front_order must list each star index once, back to front")
            if options.get("xscale", "linear") != "linear" or options.get("yscale", "linear") != "linear":
                raise ValueError("Projected disk geometry uses linear spatial axes")
            labels = _labels(data, options, n)
            fig, ax = plt.subplots(layout="constrained")
            fill = bool(options.get("fill", "front_order" in data))
            if fill and "front_order" not in data:
                raise ValueError("Filled eclipse disks require an explicit back-to-front front_order")
            for layer, i in enumerate(order):
                patch = Circle(centers[i], radii[i], facecolor=_color(options, i) if fill else "none", edgecolor=_color(options, i), linewidth=1.0, zorder=layer + 1, label=labels[i] or f"Star {i + 1}")
                ax.add_patch(patch)
            lower = np.min(centers - radii[:, None], axis=0); upper = np.max(centers + radii[:, None], axis=0)
            pad = max(float(np.max(upper - lower)) * 0.08, float(np.max(radii)) * 0.1)
            ax.set(xlim=(lower[0] - pad, upper[0] + pad), ylim=(lower[1] - pad, upper[1] + pad))
            ax.set_aspect("equal", adjustable="box"); ax.legend()
            _decorate(ax, options, xlabel="Projected x (common supplied spatial unit)", ylabel="Projected y (common supplied spatial unit)")
            meta["notes"].append("Geometric projected circular disks only. A specified front_order controls drawing order; no surface distortion, limb darkening, brightness, flux, radiative transfer or eclipse light curve is computed.")
            meta["transformations"].append({"projected_disk_radii": radii.tolist(), "back_to_front_indices": list(order), "filled": fill})
        elif kind == "orbit3d":
            coords = [_series(_array(_need(data, k), k, ndim=(1, 2))) for k in ("x", "y", "z")]
            if not all(a.shape == coords[0].shape for a in coords):
                raise ValueError("x/y/z orbit coordinates must have matching shapes")
            # Matplotlib's constrained layout does not reserve 3D z-label space.
            fig = plt.figure(); ax = fig.add_subplot(projection="3d")
            fig.subplots_adjust(left=0.03, right=0.80, bottom=0.08, top=0.92)
            from matplotlib.ticker import MaxNLocator, LinearLocator
            ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=4))
            # A thin physical z-range must not become a stack of unreadable ticks.
            ax.zaxis.set_major_locator(LinearLocator(numticks=2))
            labels = _labels(data, options, coords[0].shape[1])
            for i in range(coords[0].shape[1]):
                ax.plot(*(a[:, i] for a in coords), label=labels[i] or None, color=_color(options, i), linestyle=["-", "--", "-.", ":"][i % 4])
            ax.set(xlabel=options.get("xlabel", "x (supplied spatial unit)"), ylabel=options.get("ylabel", "y (supplied spatial unit)"), zlabel=options.get("zlabel", "z (supplied spatial unit)"))
            for axis in ("x", "y", "z"):
                if axis + "lim" in options:
                    bounds = _array(options[axis + "lim"], axis + "lim", ndim=1, missing=False)
                    if len(bounds) != 2 or bounds[0] == bounds[1]:
                        raise ValueError(f"{axis}lim requires two distinct finite bounds")
                    getattr(ax, "set_" + axis + "lim")(bounds)
            if options.get("equal_aspect", True):
                spans = np.array([abs(np.diff(getattr(ax, "get_" + axis + "lim3d")())[0]) for axis in ("x", "y", "z")])
                ax.set_box_aspect(spans)
            if any(labels): ax.legend()
            if options.get("title"): ax.set_title(options["title"])
            meta["input_shape"] = list(coords[0].shape)
            meta["notes"].append("Spatial coordinates must use a common unit for physical aspect ratios.")
        elif kind == "correlation":
            if "matrix" in data:
                matrix = _array(data["matrix"], "matrix", ndim=2, missing=False)
                if matrix.shape[0] != matrix.shape[1] or not np.allclose(matrix, matrix.T) or not np.allclose(np.diag(matrix), 1):
                    raise ValueError("A correlation matrix must be square, symmetric, with unit diagonal")
                if np.any(np.abs(matrix) > 1 + 1e-10):
                    raise ValueError("Correlation coefficients must be in [-1,1]")
            else:
                samples = _samples(data)
                if samples.shape[1] < 2 or np.any(samples.std(axis=0) == 0):
                    raise ValueError("Correlation needs at least two nonconstant parameters")
                matrix = np.corrcoef(samples, rowvar=False)
                meta["transformations"].append("Pearson correlation computed from the explicitly supplied sample columns")
            labels = _labels(data, options, len(matrix))
            fig, ax = plt.subplots(layout="constrained")
            image = ax.imshow(matrix, vmin=-1, vmax=1, cmap=options.get("cmap", "RdBu_r"), interpolation="nearest")
            ax.set(xticks=np.arange(len(matrix)), yticks=np.arange(len(matrix)), xticklabels=labels, yticklabels=labels)
            fig.colorbar(image, ax=ax, label="Pearson correlation")
            if options.get("title"): ax.set_title(options["title"])
        elif kind == "forest":
            estimate, lower, upper = [_array(_need(data, key), key, ndim=1, missing=False) for key in ("estimate", "lower", "upper")]
            if not (len(estimate) == len(lower) == len(upper)) or np.any(lower > estimate) or np.any(estimate > upper):
                raise ValueError("Forest intervals must match the estimates and contain them")
            labels = _labels(data, options, len(estimate))
            _scale_valid(lower, options.get("xscale", "linear"), "lower"); _scale_valid(upper, options.get("xscale", "linear"), "upper")
            fig, ax = plt.subplots(layout="constrained")
            ax.errorbar(estimate, np.arange(len(estimate)), xerr=np.vstack([estimate - lower, upper - estimate]), fmt="o", capsize=3, color=_color(options, 0))
            ax.set(yticks=np.arange(len(estimate)), yticklabels=labels)
            _decorate(ax, options, xlabel="Estimate (supplied units)", ylabel="Parameter / model")
            if "reference" in options: ax.axvline(float(options["reference"]), color="0.4", linestyle="--")
            meta["uncertainty"] = options.get("uncertainty", "Supplied lower/upper interval endpoints; level not inferred")
        elif kind == "residual_diagnostics":
            from scipy import stats
            residual = _array(_need(data, "residuals"), "residuals", ndim=1, missing=False)
            if len(residual) < 3: raise ValueError("Residual diagnostics needs at least three residuals")
            if options.get("standardize", False):
                sigma = _array(_need(data, "sigma"), "sigma", ndim=1, missing=False)
                if sigma.shape != residual.shape or np.any(sigma <= 0): raise ValueError("Standardization needs positive matching sigma")
                residual = residual / sigma
                meta["transformations"].append("Residuals divided by supplied sigma")
            fig, axes = plt.subplots(1, 2, layout="constrained")
            axes[0].hist(residual, bins=options.get("bins", "auto"), color=_color(options, 0), edgecolor="white")
            axes[0].set(xlabel="Residual / sigma" if options.get("standardize") else "Residual (supplied units)", ylabel="Count")
            theoretical, ordered = stats.probplot(residual, fit=False)
            axes[1].scatter(theoretical, ordered, s=12, color=_color(options, 0))
            refx = np.array([min(theoretical), max(theoretical)])
            axes[1].plot(refx, residual.mean() + residual.std(ddof=1) * refx, color="0.4", linestyle="--")
            axes[1].set(xlabel="Standard-normal quantile", ylabel="Ordered residual")
            meta["transformations"].append("Histogram and normal Q–Q plot; reference line uses sample mean and standard deviation, not a goodness-of-fit test")
            if options.get("title"): fig.suptitle(options["title"])
        else:
            fig, ax = plt.subplots(layout="constrained")
            if kind in {"heatmap", "contour", "stability_map", "roche_map", "dynamic_spectrum", "selection_function"}:
                x, y, z = _matrix(data)
                _scale_valid(x, options.get("xscale", "linear"), "x"); _scale_valid(y, options.get("yscale", "linear"), "y")
                cmap = plt.get_cmap(options.get("cmap", "viridis")).with_extremes(bad="#777777")
                limits = {key: options[key] for key in ("vmin", "vmax") if key in options}
                if kind == "selection_function":
                    finite = z[np.isfinite(z)]
                    if np.any((finite < 0) | (finite > 1)):
                        raise ValueError("Selection probabilities must lie in [0,1]")
                    limits = {"vmin": 0, "vmax": 1}
                    meta["notes"].append("Supplied selection probabilities are displayed; no completeness or population correction was calculated.")
                if kind in {"heatmap", "dynamic_spectrum", "selection_function"}:
                    image = ax.pcolormesh(x, y, np.ma.masked_invalid(z), shading="nearest", cmap=cmap, rasterized=options.get("rasterized", False), **limits)
                else:
                    levels = data.get("levels", options.get("levels", 12))
                    if kind == "roche_map":
                        if "levels" not in data and "levels" not in options:
                            raise ValueError("roche_map requires explicit potential levels from the scientific calculation")
                        levels = _array(levels, "potential levels", ndim=1, missing=False)
                        if len(levels) < 1 or np.any(np.diff(levels) <= 0):
                            raise ValueError("Potential levels must be a strictly increasing finite sequence")
                        meta["notes"].append("The effective potential, critical-point positions and contour levels are supplied. No Roche approximation, rotation state, mass ratio or Lagrange point is inferred by the renderer.")
                    filled = options.get("filled", kind != "roche_map")
                    image = ax.contourf(x, y, np.ma.masked_invalid(z), levels=levels, cmap=cmap, **limits) if filled else ax.contour(x, y, np.ma.masked_invalid(z), levels=levels, cmap=cmap, **limits)
                    if kind == "roche_map" and "critical_points" in data:
                        points = data["critical_points"]
                        px = _array(_need(points, "x"), "critical_points.x", ndim=1, missing=False)
                        py = _array(_need(points, "y"), "critical_points.y", ndim=1, missing=False)
                        if px.shape != py.shape: raise ValueError("Critical-point x/y lengths must match")
                        names = _labels(points, {}, len(px))
                        ax.scatter(px, py, marker="+", color="black", zorder=5)
                        for a, b, name in zip(px, py, names):
                            if name: ax.annotate(name, (a, b), xytext=(4, 4), textcoords="offset points")
                zlabel = {"roche_map": "Effective potential (supplied convention)", "dynamic_spectrum": "Spectral power / flux (supplied definition)", "selection_function": "Supplied selection probability"}.get(kind, "Supplied diagnostic (supplied units)")
                if kind == "roche_map" and not options.get("filled", False) and len(levels) == 1:
                    ax.clabel(image, inline=True)
                    meta["notes"].append("A single supplied equipotential is labelled directly; a one-level colorbar is omitted.")
                else:
                    fig.colorbar(image, ax=ax, label=options.get("zlabel", zlabel))
                xydefaults = ("Time (supplied system and units)", "Frequency / spectral coordinate (supplied units)") if kind == "dynamic_spectrum" else ("x (supplied units)", "y (supplied units)")
                _decorate(ax, options, xlabel=xydefaults[0], ylabel=xydefaults[1])
                if kind == "roche_map" and options.get("equal_aspect", True): ax.set_aspect("equal", adjustable="box")
                meta["input_shape"] = list(z.shape)
                meta["notes"].append("Missing cells are masked; values are not interpolated or classified as stable/unstable by the renderer.")
            elif kind == "image":
                z = _array(_need(data, "z"), "z", ndim=(2, 3))
                if z.ndim == 3:
                    if z.shape[2] not in (3, 4) or np.isnan(z).any() or np.any((z < 0) | (z > 1)):
                        raise ValueError("RGB(A) images require finite channels in [0,1]; normalize explicitly before plotting")
                    image = ax.imshow(z, origin=options.get("origin", "lower"), interpolation="nearest", extent=options.get("extent"))
                else:
                    image = ax.imshow(np.ma.masked_invalid(z), origin=options.get("origin", "lower"), interpolation="nearest", cmap=plt.get_cmap(options.get("cmap", "viridis")).with_extremes(bad="#777777"), extent=options.get("extent"))
                    fig.colorbar(image, ax=ax, label=options.get("zlabel", "Intensity (supplied units)"))
                _decorate(ax, options)
                meta["notes"].append("No smoothing, upsampling, or image contrast transformation is performed.")
            elif kind in {"quiver", "streamlines"}:
                u = _array(_need(data, "u"), "u", ndim=2)
                v = _array(_need(data, "v"), "v", ndim=2)
                x = _array(_need(data, "x"), "x", ndim=(1, 2), missing=False)
                y = _array(_need(data, "y"), "y", ndim=(1, 2), missing=False)
                if kind == "streamlines":
                    if x.ndim != 1 or y.ndim != 1 or len(x) < 2 or len(y) < 2:
                        raise ValueError("streamlines needs one-dimensional x/y grids with at least two points per axis")
                    for label, coord in [("x", x), ("y", y)]:
                        delta = np.diff(coord)
                        if np.any(delta <= 0) or not np.allclose(delta, delta[0]):
                            raise ValueError(f"streamlines needs uniformly spaced increasing {label}; no regridding is performed")
                    if u.shape != (len(y), len(x)) or v.shape != u.shape:
                        raise ValueError("Streamline components must have shape [len(y),len(x)]")
                    density = float(options.get("density", 1.0))
                    if not np.isfinite(density) or density <= 0: raise ValueError("Streamline density must be positive and finite")
                    _scale_valid(x, options.get("xscale", "linear"), "x"); _scale_valid(y, options.get("yscale", "linear"), "y")
                    ax.streamplot(x, y, np.ma.masked_invalid(u), np.ma.masked_invalid(v), density=density, color=_color(options, 0))
                    _decorate(ax, options)
                    meta["notes"].append("Streamlines integrate a graphical path through supplied grid vectors; this is not hydrodynamic time evolution, mass transfer or a trajectory solution.")
                else:
                    if x.ndim == y.ndim == 1: x, y = np.meshgrid(x, y)
                    if not (u.shape == v.shape == x.shape == y.shape): raise ValueError("Vector field coordinate/component shapes do not match")
                    _scale_valid(x, options.get("xscale", "linear"), "x"); _scale_valid(y, options.get("yscale", "linear"), "y")
                    ax.quiver(x, y, np.ma.masked_invalid(u), np.ma.masked_invalid(v), angles="xy", scale_units="xy", scale=options.get("vector_scale", 1), color=_color(options, 0))
                    _decorate(ax, options)
                    meta["notes"].append("Arrow scale is explicitly vector_scale; coordinates and components must have appropriate compatible units.")
            elif kind in {"histogram", "boxplot", "violin"}:
                if kind == "histogram":
                    values = _series(_array(_need(data, "values"), "values", ndim=(1, 2), missing=False))
                    labels = _labels(data, options, values.shape[1])
                    edges = np.histogram_bin_edges(values.ravel(), bins=options.get("bins", "auto"))
                    for i in range(values.shape[1]):
                        ax.hist(values[:, i], bins=edges, density=options.get("density", False), histtype="step", label=labels[i] or None, color=_color(options, i))
                    if any(labels): ax.legend()
                    meta["transformations"].append({"histogram_bin_edges": edges.tolist(), "density": bool(options.get("density", False))})
                    _decorate(ax, options, xlabel="Value (supplied units)", ylabel="Density" if options.get("density") else "Count")
                else:
                    groups = [_array(g, f"groups[{i}]", ndim=1, missing=False) for i, g in enumerate(_need(data, "groups"))]
                    if not groups: raise ValueError("groups cannot be empty")
                    labels = _labels(data, options, len(groups))
                    for g in groups: _scale_valid(g, options.get("yscale", "linear"), "group values")
                    if kind == "boxplot": ax.boxplot(groups, tick_labels=labels, orientation="vertical", showfliers=True)
                    else:
                        if any(len(g) < 2 or np.std(g) == 0 for g in groups): raise ValueError("Violin plots need at least two distinct values per group")
                        ax.violinplot(groups, showmedians=True, showextrema=True)
                        ax.set(xticks=np.arange(1, len(groups) + 1), xticklabels=labels)
                        meta["transformations"].append("Matplotlib Gaussian KDE violin; supplied groups retained")
                    _decorate(ax, options, xlabel="Group", ylabel="Value (supplied units)")
            elif kind == "bar":
                categories = _need(data, "x")
                if isinstance(categories, str): raise ValueError("bar x must be a sequence of categories")
                y = _series(_array(_need(data, "y"), "y", ndim=(1, 2), missing=False))
                if len(categories) != y.shape[0]: raise ValueError("Bar category/value lengths do not match")
                if options.get("yscale", "linear") != "linear": raise ValueError("Magnitude bars use a linear axis with a zero baseline")
                if "ylim" in options and not min(options["ylim"]) <= 0 <= max(options["ylim"]):
                    raise ValueError("Magnitude bar limits must retain the zero baseline")
                n, k = y.shape; labels = _labels(data, options, k); errors = _error(data.get("yerr"), n, k, "yerr")
                positions = np.arange(n); width = 0.8 / k
                for i in range(k):
                    ax.bar(positions + (i - (k - 1) / 2) * width, y[:, i], width=width, yerr=errors[i], label=labels[i] or None, color=_color(options, i), edgecolor="black", linewidth=0.5)
                ax.set(xticks=positions, xticklabels=[str(c) for c in categories]); ax.axhline(0, color="0.4", linewidth=0.7)
                if any(labels): ax.legend()
                _decorate(ax, options, xlabel="Category", ylabel="Value (supplied units)")
            elif kind == "orbit2d":
                coords = [_series(_array(_need(data, key), key, ndim=(1, 2))) for key in ("x", "y")]
                if coords[0].shape != coords[1].shape: raise ValueError("Orbit x/y shapes must match")
                labels = _labels(data, options, coords[0].shape[1])
                for i in range(coords[0].shape[1]):
                    _scale_valid(coords[0][:, i], options.get("xscale", "linear"), "x"); _scale_valid(coords[1][:, i], options.get("yscale", "linear"), "y")
                    ax.plot(coords[0][:, i], coords[1][:, i], label=labels[i] or None, color=_color(options, i), linestyle=["-", "--", "-.", ":"][i % 4])
                _decorate(ax, options, xlabel="x (supplied spatial unit)", ylabel="y (supplied spatial unit)")
                if options.get("equal_aspect", True): ax.set_aspect("equal", adjustable="box")
                if any(labels): ax.legend()
                meta["notes"].append("Equal spatial aspect assumes x/y share the same unit.")
            elif kind == "envelope":
                x, y = _xy(data)
                if y.shape[1] != 1: raise ValueError("envelope accepts one estimate series per plot")
                lower = _array(_need(data, "lower"), "lower", ndim=1); upper = _array(_need(data, "upper"), "upper", ndim=1)
                if lower.shape != x.shape or upper.shape != x.shape or np.any(lower > upper): raise ValueError("Envelope bounds must match x and lower <= upper")
                _scale_valid(lower, options.get("yscale", "linear"), "lower bound"); _scale_valid(upper, options.get("yscale", "linear"), "upper bound")
                _draw_xy(ax, x, y, data, options)
                ax.fill_between(x, lower, upper, alpha=0.2, color=_color(options, 0))
                _decorate(ax, options)
                meta["uncertainty"] = options.get("uncertainty", "Supplied envelope bounds; probability level not inferred")
            else:
                x, y = _xy(data)
                points = kind in {"scatter", "errorbar", "astrometry", "poincare", "hr_diagram", "mass_radius", "sed", "benchmark", "oc", "eclipse_timing", "etv", "visibility", "uv_coverage"}
                local_data = dict(data)
                if kind == "phase_curve":
                    period = float(data.get("period", options.get("period", 0)))
                    t0 = float(data.get("t0", options.get("t0", 0)))
                    if not np.isfinite(period) or period <= 0 or not np.isfinite(t0): raise ValueError("phase_curve requires period>0 and finite t0")
                    x = np.remainder((x - t0) / period, 1.0)
                    points = True
                    meta["transformations"].append({"phase": "((time - t0) / period) mod 1", "period": period, "t0": t0})
                    if "xerr" in data: local_data["xerr"] = np.asarray(data["xerr"], dtype=float) / period
                _draw_xy(ax, x, y, local_data, options, points=points, force_errors=kind == "errorbar")
                defaults = {
                    "phase_curve": ("Orbital phase", "Signal (supplied units)"),
                    "oc": ("Epoch / time (supplied units)", "O−C timing (supplied units)"),
                    "eclipse_timing": ("Eclipse epoch / time (supplied system)", "O−C timing (supplied units)"),
                    "etv": ("Eclipse epoch / time (supplied system)", "Eclipse timing variation (supplied units)"),
                    "periodogram": ("Frequency (supplied units)", "Periodogram power (supplied normalization)"),
                    "power_spectrum": ("Frequency (supplied units)", "Spectral power (supplied normalization)"),
                    "hr_diagram": ("Effective temperature (supplied units)", "Luminosity (supplied units)"),
                    "mass_radius": ("Mass (supplied units)", "Radius (supplied units)"),
                    "spectrum": ("Spectral coordinate (supplied units)", "Spectral flux (supplied units)"),
                    "sed": ("Spectral coordinate (supplied units)", "Spectral quantity (supplied definition and units)"),
                    "convergence": ("Step / tolerance (supplied units)", "Error (supplied definition and units)"),
                    "benchmark": ("Measured runtime (supplied units)", "Measured error (supplied definition and units)"),
                    "astrometry": ("Relative sky coordinate (supplied convention)", "Relative sky coordinate (supplied convention)"),
                    "visibility": ("Projected baseline (supplied units)", "Visibility (supplied amplitude or squared convention)"),
                    "uv_coverage": ("u (supplied spatial-frequency unit)", "v (supplied spatial-frequency unit)"),
                    "polarimetry": ("Time / spectral coordinate (supplied convention)", "Stokes / polarization quantity (supplied definition)"),
                }
                xlabel, ylabel = defaults.get(kind, ("x (supplied units)", "y (supplied units)"))
                _decorate(ax, options, xlabel=xlabel, ylabel=ylabel)
                if kind == "hr_diagram":
                    decreases = options.get("temperature_decreases_right", options.get("hr_x_kind", "temperature") == "temperature")
                    if decreases: ax.set_xlim(sorted(ax.get_xlim(), reverse=True))
                    meta["notes"].append("Temperature axes decrease to the right by default. Use hr_x_kind='color' or temperature_decreases_right=false for a color–magnitude diagram, and invert_y=true for a magnitude ordinate.")
                if kind == "astrometry":
                    if options.get("equal_aspect", True): ax.set_aspect("equal", adjustable="box")
                    if options.get("ra_increases_left", False): ax.set_xlim(sorted(ax.get_xlim(), reverse=True))
                if kind == "uv_coverage" and options.get("equal_aspect", True):
                    ax.set_aspect("equal", adjustable="box")
                    meta["notes"].append("Only supplied u/v samples are shown; conjugate baselines and observing coverage are not synthesized.")
                if kind in {"oc", "eclipse_timing", "etv"}:
                    ax.axhline(0, color="0.4", linewidth=0.7)
                    meta["notes"].append("Supplied timing residuals are shown; ephemeris, light-travel-time effects, dynamical timing, apsidal motion and instrumental offsets were not fitted here.")
                if kind == "visibility":
                    meta["notes"].append("Supplied interferometric observable only; amplitude, squared visibility, uncertainty and baseline/wavelength convention must be declared. No Fourier transform or interferometric image reconstruction is inferred.")
                if kind == "polarimetry":
                    meta["notes"].append("Supplied Stokes/polarization series; no debiasing, angle unwrapping, Stokes normalization or radiative transfer is performed.")
                if kind in {"periodogram", "power_spectrum"} and "threshold" in data:
                    threshold = float(data["threshold"])
                    if not np.isfinite(threshold): raise ValueError("threshold must be finite")
                    _scale_valid(np.array([threshold]), options.get("yscale", "linear"), "threshold")
                    ax.axhline(threshold, linestyle="--", color="0.4", label=options.get("threshold_label", "Supplied threshold")); ax.legend()
                    meta["notes"].append("The supplied threshold is displayed; its false-alarm probability was not computed.")
                if kind == "benchmark": meta["notes"].append("Runtime/error pairs are supplied; equal hardware, physical models, workload, and accuracy targets require separate verification.")
                meta["input_shape"] = list(y.shape)
        assert fig is not None
        meta["missing_data_policy"] = "No source rows are deleted; nonfinite points are not drawn, NaN line values remain gaps, matrix NaNs remain masked, posterior/diagnostic samples require explicit finite preprocessing."
        return fig, meta
    except Exception:
        if fig is not None:
            plt.close(fig)
        raise
