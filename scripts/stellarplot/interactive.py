"""Plotly views with explicit offline-resource and scientific-semantics checks."""
from __future__ import annotations
import html
from pathlib import Path
from .core import write_json


def _external_resources(value, *, in_template=False):
    found = []
    if isinstance(value, dict):
        if not in_template and value.get("type") in {"scattergeo", "choropleth", "scattermapbox", "densitymapbox", "choroplethmapbox", "scattermap", "densitymap", "choroplethmap"}:
            found.append("Map/geo trace may require external tiles or topology")
        for key, item in value.items():
            if key in {"source", "url"} and isinstance(item, str) and not item.strip().lower().startswith("data:"):
                found.append(item)
            found.extend(_external_resources(item, in_template=in_template or key == "template"))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_external_resources(item, in_template=in_template))
    return sorted(set(found))


def preflight_interactive(base, *, overwrite=False):
    from _common import checked_output_file
    base = Path(base).absolute()
    base.parent.mkdir(parents=True, exist_ok=True)
    for suffix in (".html", ".interactive.json"):
        checked_output_file(base.with_name(base.name + suffix), force=overwrite)


def export_interactive(figure, base, *, caption="", provenance=None, overwrite=False,
                       require_self_contained=True):
    from _common import atomic_write_bytes
    base = Path(base).absolute()
    preflight_interactive(base, overwrite=overwrite)
    output = base.with_name(base.name + ".html")
    manifest = base.with_name(base.name + ".interactive.json")
    resources = _external_resources(figure.to_plotly_json())
    if resources and require_self_contained:
        raise ValueError("Figure has external resources; supply local data or explicitly allow a non-offline export: " + ", ".join(resources))
    document = figure.to_html(include_plotlyjs=True, full_html=True,
        config={"displaylogo": False, "responsive": True}, div_id="stellar-figure")
    heading = '<section aria-label="Figure description"><h1>Astro Paper Figures</h1><p>' + html.escape(caption) + '</p><p>Interactive working figure. Submit a separately checked static figure when required.</p></section>'
    document = document.replace("<body>", "<body>" + heading, 1)
    atomic_write_bytes(output, document.encode(), force=overwrite)
    from . import TOOL_NAME, __version__
    write_json(manifest, {"tool": f"{TOOL_NAME} {__version__}", "self_contained": not resources,
        "external_resources": resources, "caption": caption, "provenance": provenance or {},
        "journal_compliance_certified": False}, overwrite=overwrite)
    return {"files": [str(output), str(manifest)], "self_contained": not resources}


def render_interactive(kind, data, options=None):
    """Preserve grouping, uncertainty, residuals, scale and aspect for common views."""
    import numpy as np
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from .recipes import _xy, _series, _array, _error, _scale_valid, _labels, _color
    from matplotlib.colors import to_hex
    options = dict(options or {})
    fit = kind in {"radial_velocity", "light_curve", "timeseries_fit"}
    supported = {"line", "scatter", "errorbar", "orbit2d", "orbit3d", "radial_velocity", "light_curve", "timeseries_fit", "oc", "phase_portrait", "spectrum", "sed", "astrometry"}
    if kind not in supported:
        raise ValueError("No built-in interactive view for this recipe; construct a Plotly Figure and use export_interactive().")
    if options.get("xscale", "linear") not in {"linear", "log"} or options.get("yscale", "linear") not in {"linear", "log"}:
        raise ValueError("Built-in HTML supports linear/log axes; use a custom Plotly view for other scales")
    if kind == "orbit3d":
        x = _series(_array(data["x"], "x", ndim=(1, 2)))
        y = _series(_array(data["y"], "y", ndim=(1, 2)))
        if x.shape != y.shape:
            raise ValueError("3D coordinates must match")
    else:
        x, y = _xy(data, "observed" if fit else "y")
    n, count = y.shape
    labels = _labels(data, options, count)
    errors = _error(data.get("sigma", data.get("yerr")), n, count, "yerr")
    xerrors = _error(data.get("xerr"), n, count, "xerr")
    model = _series(_array(data["model"], "model", ndim=(1, 2))) if fit else None
    if fit and model.shape != y.shape:
        raise ValueError("Model/observed shapes must match")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.75, 0.25]) if fit else go.Figure()

    def error_spec(error):
        if error is None:
            return None
        if error.ndim == 2:
            return {"type": "data", "symmetric": False, "array": error[1], "arrayminus": error[0], "visible": True}
        return {"type": "data", "array": error, "visible": True}

    if kind == "orbit3d":
        z = _series(_array(data["z"], "z", ndim=(1, 2)))
        if z.shape != y.shape:
            raise ValueError("3D coordinates must match")
        for i in range(count):
            fig.add_trace(go.Scatter3d(x=x[:, i], y=y[:, i], z=z[:, i], mode="lines", name=labels[i] or f"Trajectory {i+1}", connectgaps=False, line={"color": to_hex(_color(options, i))}))
        fig.update_layout(scene={"aspectmode": "data", "xaxis_title": options.get("xlabel", "x"),
            "yaxis_title": options.get("ylabel", "y"), "zaxis_title": options.get("zlabel", "z")})
    else:
        for i in range(count):
            _scale_valid(x, options.get("xscale", "linear"), "x", xerrors[i])
            _scale_valid(y[:, i], options.get("yscale", "linear"), "y", errors[i])
            color = to_hex(_color(options, i))
            points = fit or kind in {"scatter", "errorbar", "sed", "astrometry"}
            trace = go.Scatter(x=x, y=y[:, i], mode="markers" if points else "lines", connectgaps=False,
                name=labels[i] or ("Observed" if fit else f"Series {i+1}"), error_y=error_spec(errors[i]),
                error_x=error_spec(xerrors[i]), marker={"color": color, "symbol": ["circle", "square", "triangle-up", "diamond"][i % 4]}, line={"color": color})
            if fit:
                fig.add_trace(trace, row=1, col=1)
                _scale_valid(model[:, i], options.get("yscale", "linear"), "model")
                fig.add_trace(go.Scatter(x=x, y=model[:, i], mode="markers" if options.get("model_points") else "lines", connectgaps=False,
                    name=(labels[i] + " model").strip(), line={"color": color}, marker={"color": color}), row=1, col=1)
                fig.add_trace(go.Scatter(x=x, y=y[:, i]-model[:, i], mode="markers", connectgaps=False,
                    name=(labels[i] + " residual").strip(), error_y=error_spec(errors[i]), marker={"color": color}), row=2, col=1)
            else:
                fig.add_trace(trace)
        fig.update_xaxes(type=options.get("xscale", "linear"), title_text=options.get("xlabel", "x"), row=2 if fit else None, col=1 if fit else None)
        fig.update_yaxes(type=options.get("yscale", "linear"), title_text=options.get("ylabel", "Observed/model" if fit else "y"), row=1 if fit else None, col=1 if fit else None)
        if fit:
            fig.update_yaxes(type="linear", title_text=options.get("residual_ylabel", "O−model"), row=2, col=1)
            fig.add_hline(y=0, line_color="#666666", row=2, col=1)
        if options.get("invert_y"):
            fig.update_yaxes(autorange="reversed", row=1 if fit else None, col=1 if fit else None)
        if kind in {"orbit2d", "astrometry"} and options.get("equal_aspect", True):
            fig.update_yaxes(scaleanchor="x", scaleratio=1)
        if kind == "astrometry" and options.get("ra_increases_left"):
            fig.update_xaxes(autorange="reversed")
        if kind == "oc":
            fig.add_hline(y=0, line_color="#666666")
        for axis_name in ("x", "y"):
            limits = options.get(axis_name + "lim")
            if limits is not None:
                limits = np.asarray(limits, dtype=float)
                if options.get(axis_name + "scale") == "log":
                    if np.any(limits <= 0):
                        raise ValueError("Log axis limits must be positive")
                    limits = np.log10(limits)
                updater = fig.update_xaxes if axis_name == "x" else fig.update_yaxes
                updater(range=limits.tolist(), row=1 if fit and axis_name == "y" else None, col=1 if fit and axis_name == "y" else None)
    fig.update_layout(template="plotly_white", title=options.get("title", ""))
    return fig

