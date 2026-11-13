"""Deterministic synthetic rendering fixtures, never research results.

``cases()`` returns ``{recipe: (data, options)}``.  It covers every registered
recipe and deliberately contains multi-star, multi-chain and missing-data
examples. Scientific models, real observations and journal acceptance are not
validated by these fixtures.
"""
from __future__ import annotations

import copy
import numpy as np


def cases() -> dict[str, tuple[dict, dict]]:
    rng = np.random.default_rng(20261112)
    x = np.linspace(0.1, 3.0, 40)
    y = np.sin(2 * np.pi * x)
    ys = np.column_stack([y, 0.5 * np.cos(2 * np.pi * x), -0.4 * y])
    sigma = np.full(len(x), 0.08)
    samples = rng.multivariate_normal([0.0, 0.0, 0.0], [[1,.4,0],[.4,1,.1],[0,.1,.8]], 300)
    grid = np.linspace(-1.5, 1.5, 30)
    gx, gy = np.meshgrid(grid, grid)
    scalar = gx ** 2 + gy ** 2
    mapping = {"x": grid, "y": grid, "z": scalar}
    plain = {"x": x, "y": y}
    multi = {"x": x, "y": ys, "labels": ["Synthetic A", "Synthetic B", "Synthetic C"]}
    fitted = {"x": x, "observed": ys + rng.normal(0, .03, ys.shape), "model": ys, "sigma": sigma, "labels": ["Synthetic A", "Synthetic B", "Synthetic C"]}
    result: dict[str, tuple[dict, dict]] = {}

    def add(kind: str, data: dict, **options: object) -> None:
        options.setdefault("title", f"Synthetic tool test: {kind}")
        result[kind] = (copy.deepcopy(data), dict(options))

    add("line", multi)
    # NaN must remain an explicit line break.
    result["line"][0]["y"][15, 0] = np.nan
    add("scatter", multi)
    add("errorbar", {**plain, "yerr": sigma}, uncertainty="Synthetic supplied 1-sigma test errors")
    add("bar", {"x": ["Test bin A", "Test bin B", "Test bin C"], "y": [[1, 2], [3, 2], [2, 4]], "labels": ["Test model 1", "Test model 2"]})
    add("histogram", {"values": samples, "labels": ["Test p1", "Test p2", "Test p3"]}, bins=14)
    add("boxplot", {"groups": [samples[:,0], samples[:,1]], "labels": ["Test group 1", "Test group 2"]})
    add("violin", {"groups": [samples[:,0], samples[:,1]], "labels": ["Test group 1", "Test group 2"]})
    for kind in ["heatmap", "image"]: add(kind, {"z": scalar})
    for kind in ["contour", "stability_map"]: add(kind, mapping, zlabel="Synthetic scalar; no stability inference")
    add("quiver", {"x": grid, "y": grid, "u": -gy, "v": gx}, vector_scale=3)
    add("envelope", {**plain, "lower": y-.1, "upper": y+.1}, uncertainty="Synthetic supplied interval")
    for kind in ["timeseries_fit", "light_curve", "radial_velocity"]:
        add(kind, fitted, residual_ylabel="Residual\n(test unit)", model_points=kind == "light_curve", invert_y=kind == "light_curve")
    add("phase_curve", {**multi, "period": 1.0, "t0": 0.0, "yerr": sigma})
    angles = np.linspace(0, 2*np.pi, len(x))
    add("orbit2d", {"x": np.column_stack([np.cos(angles), -0.5*np.cos(angles), x-1]), "y": np.column_stack([np.sin(angles), -0.5*np.sin(angles), 0.2*x*x]), "labels": ["Synthetic bound A", "Synthetic bound B", "Synthetic outgoing C"]})
    add("orbit3d", {"x": np.column_stack([np.cos(angles), -0.5*np.cos(angles)]), "y": np.column_stack([np.sin(angles), -0.5*np.sin(angles)]), "z": np.column_stack([np.zeros(len(x)), 0.1*np.sin(angles)]), "labels": ["Synthetic A", "Synthetic B"]})
    add("astrometry", {**plain, "xerr": sigma, "yerr": sigma}, ra_increases_left=True)
    for kind in ["oc", "eclipse_timing", "etv"]:
        add(kind, {"x": np.arange(len(x)), "y": y*.001, "yerr": sigma*.001}, ylabel="Synthetic timing residual (test day)")
    for kind in ["periodogram", "power_spectrum"]:
        add(kind, {"x": x, "y": y*y, "threshold": .8}, zlabel="Synthetic power")
    add("secular_evolution", {**multi, "ylabels": ["Test element 1", "Test element 2", "Test element 3"]})
    add("transfer_history", {"x": x, "y": np.column_stack([1+.01*y, .01*y, 2+.1*y]), "ylabels": ["Synthetic mass (test unit)", "Synthetic rate (test unit / time)", "Synthetic angular momentum (test unit)"]})
    for kind in ["phase_portrait", "poincare"]: add(kind, plain)
    add("hr_diagram", {"x": [4000, 5000, 6000, 7000], "y": [.3, .8, 1.5, 4]})
    add("mass_radius", {"x": [.5, .8, 1, 1.3], "y": [.4, .7, 1, 1.4], "yerr": [.03, .05, .04, .1]})
    for kind in ["spectrum", "sed"]: add(kind, {"x": x, "y": 1.5+y})
    add("corner", {"samples": samples, "labels": ["Test p1", "Test p2", "Test p3"]})
    chains = np.stack([samples, samples + rng.normal(0, .05, samples.shape)], axis=1)
    for kind in ["trace", "autocorrelation"]: add(kind, {"samples": chains, "labels": ["Test p1", "Test p2", "Test p3"]}, max_lag=40)
    add("forest", {"estimate": [1,2,3], "lower": [.8,1.6,2.7], "upper": [1.1,2.1,3.4], "labels": ["Test model A", "Test model B", "Test model C"]}, uncertainty="Synthetic test interval")
    add("correlation", {"samples": samples, "labels": ["Test p1", "Test p2", "Test p3"]})
    add("residual_diagnostics", {"residuals": samples[:,0]})
    add("convergence", {"x": x, "y": .001*x*x}, xscale="log", yscale="log")
    add("benchmark", {"x": x, "y": .001/x}, xscale="log", yscale="log")
    add("roche_map", {**mapping, "levels": [.2,.5,1,2], "critical_points": {"x": [0], "y": [0], "labels": ["Test point"]}}, title="Synthetic scalar grid only; not a Roche solution", zlabel="Synthetic scalar (test units)")
    add("eclipse_geometry", {"centers": [[-.4,0],[.4,.1],[1.4,.4]], "radii": [.7,.6,.3], "front_order": [2,0,1], "labels": ["Test star A", "Test star B", "Test star C"]})
    add("streamlines", {"x": grid, "y": grid, "u": -gy, "v": gx}, title="Synthetic vector field; not accretion dynamics", density=.8)
    add("dynamic_spectrum", {"x": x, "y": np.linspace(1,10,len(grid)), "z": np.outer(np.linspace(.2,1,len(grid)), 1+y*y)}, title="Synthetic spectral map only")
    add("visibility", {"x": x, "y": 1/(1+x*x), "yerr": sigma*.1}, title="Synthetic visibility export test")
    add("uv_coverage", {"x": np.cos(angles), "y": .5*np.sin(angles)})
    add("polarimetry", {**multi, "labels": ["Test Q", "Test U", "Test V"]}, title="Synthetic Stokes-series export test")
    add("selection_function", {"x": grid, "y": grid, "z": 1/(1+np.exp(-gx-gy))}, title="Synthetic probabilities; not measured completeness")
    return result
