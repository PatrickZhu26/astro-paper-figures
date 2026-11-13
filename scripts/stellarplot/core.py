"""Journal-aware styling, provenance, safe exports, and reviewable checks."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import sys

SKILL_ROOT = Path(__file__).resolve().parents[2]
VENDOR = SKILL_ROOT / "vendor" / "scientific_visualization" / "scripts"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

PALETTE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#000000", "#56B4E9"]
_PROFILE_OVERRIDES = {}


def jsonable(value):
    """Keep NaN observations as explicit nulls in saved source tables."""
    import numpy as np
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return jsonable(value.tolist())
    if isinstance(value, np.generic):
        return jsonable(value.item())
    if isinstance(value, float) and math.isinf(value):
        raise ValueError("Infinity is not a valid scientific source value; handle it explicitly before export")
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path, value, *, overwrite=False):
    from _common import atomic_write_bytes
    payload = (json.dumps(jsonable(value), ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()
    atomic_write_bytes(Path(path), payload, force=overwrite)


def profiles():
    import copy
    return {**json.loads((SKILL_ROOT / "assets" / "journals.json").read_text())["profiles"], **copy.deepcopy(_PROFILE_OVERRIDES)}


def _validated_profile(name, config):
    import copy
    if not isinstance(name, str) or not name or not isinstance(config, dict):
        raise ValueError("Custom journal profiles need a name and an object")
    config = copy.deepcopy(config)
    widths = config.setdefault("widths_mm", {"single": None, "double": None})
    if not isinstance(widths, dict):
        raise ValueError("widths_mm must be an object")
    checks = list(widths.values()) + [config.get(k) for k in ("font_size_pt", "min_font_pt", "min_line_pt", "maximum_width_mm", "recommended_raster_dpi")]
    raster = config.setdefault("raster_dpi", {})
    if not isinstance(raster, dict):
        raise ValueError("raster_dpi must be an object")
    checks.extend(raster.values())
    for number in checks:
        if number is not None and (isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number <= 0):
            raise ValueError("Journal dimensions, font sizes, line widths and DPI must be positive finite numbers or null")
    config.setdefault("font_family", "serif")
    config.setdefault("font_size_pt", 8)
    config.setdefault("notes", [])
    if not isinstance(config["notes"], list):
        raise ValueError("Profile notes must be a list")
    config["status"] = "custom_profile"
    config["notes"].append("Task-local custom configuration; its scientific/editorial requirements need source verification.")
    return config


def register_profile(name, config):
    """Register a task-local journal profile without changing packaged defaults."""
    _PROFILE_OVERRIDES[name] = _validated_profile(name, config)


def load_profile_file(path):
    from .adapters import load_data
    path = Path(path)
    if path.stat().st_size > 1024 * 1024:
        raise ValueError("Journal configuration exceeds 1 MiB")
    document = load_data(path)
    entries = document.get("profiles")
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Journal configuration needs a nonempty profiles object")
    pending = {}
    for name, config in entries.items():
        config = {**config, "configuration_source": document["_source"]} if isinstance(config, dict) else config
        pending[name] = _validated_profile(name, config)
    _PROFILE_OVERRIDES.update(pending)
    return list(entries)


def profile(name="general"):
    entries = profiles()
    if name not in entries:
        raise ValueError(f"Unknown journal {name!r}; choose {', '.join(entries)}")
    return entries[name]


def width_mm(journal="general", width="single"):
    config = profile(journal)
    if isinstance(width, (int, float)):
        result = float(width)
    else:
        try:
            result = float(width)
        except (ValueError, TypeError):
            if width not in {"single", "double"}:
                raise ValueError("width must be single, double, or a width in millimetres")
            result = (config["widths_mm"].get(width)
                      or config.get("recommended_width_mm", {}).get(width)
                      or {"single": 88.0, "double": 180.0}[width])
    if not math.isfinite(result) or not 20 <= result <= 1000:
        raise ValueError("Figure width must be finite and between 20 and 1000 mm")
    return result


@contextlib.contextmanager
def journal_style(journal="general"):
    import matplotlib as mpl
    from cycler import cycler
    config = profile(journal)
    size = max(float(config.get("font_size_pt") or 8), float(config.get("min_font_pt") or 0))
    all_sides = config.get("ticks_on_all_sides", False)
    settings = {
        "font.family": config.get("font_family", "DejaVu Sans"), "font.size": size,
        "axes.labelsize": size, "axes.titlesize": size, "legend.fontsize": size,
        "xtick.labelsize": size, "ytick.labelsize": size,
        "axes.prop_cycle": cycler(color=PALETTE),
        "lines.linewidth": max(0.8, config.get("min_line_pt") or 0),
        "lines.markersize": 3, "axes.linewidth": 0.6,
        "axes.spines.top": True, "axes.spines.right": True,
        "xtick.direction": "in", "ytick.direction": "in",
        "xtick.top": all_sides, "ytick.right": all_sides,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "figure.facecolor": "white", "axes.facecolor": "white", "axes.grid": False,
        "savefig.bbox": None, "savefig.facecolor": "white",
        "text.usetex": False,
    }
    with mpl.rc_context(settings):
        yield config


def figure_audit(fig, config):
    """Inspect artists at final size; checks are aids, not acceptance criteria."""
    from matplotlib.text import Text
    import numpy as np
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    bounds = fig.bbox
    fonts = []
    clipped = []
    outside_ticks = set()
    for axis_group in fig.axes:
        axes_to_check = [axis_group.xaxis, axis_group.yaxis]
        if hasattr(axis_group, "zaxis"):
            axes_to_check.append(axis_group.zaxis)
        for axis in axes_to_check:
            lower, upper = sorted(axis.get_view_interval())
            transform = axis.get_transform()
            transformed = np.asarray(transform.transform([lower, upper]), dtype=float)
            lower_t, upper_t = sorted(transformed)
            tolerance = abs(upper_t - lower_t) * 1e-10 + max(abs(lower_t), abs(upper_t)) * np.finfo(float).eps * 4
            for tick in [*axis.get_major_ticks(), *axis.get_minor_ticks()]:
                location = float(np.asarray(transform.transform(tick.get_loc())))
                if not math.isfinite(location) or not lower_t - tolerance <= location <= upper_t + tolerance:
                    outside_ticks.update((id(tick.label1), id(tick.label2)))
    minimum = config.get("min_font_pt")
    small = []
    for artist in fig.findobj(match=Text):
        if not artist.get_visible() or not artist.get_text().strip() or id(artist) in outside_ticks:
            continue
        point_size = float(artist.get_fontsize())
        fonts.append(point_size)
        if minimum is not None and point_size + 1e-6 < minimum:
            small.append({"text": artist.get_text(), "pt": point_size})
        box = artist.get_window_extent(renderer)
        if box.x0 < bounds.x0 - 2 or box.y0 < bounds.y0 - 2 or box.x1 > bounds.x1 + 2 or box.y1 > bounds.y1 + 2:
            clipped.append(artist.get_text())
    return {
        "minimum_text_pt": min(fonts) if fonts else None,
        "text_below_profile_minimum": small,
        "text_outside_page": clipped,
        "manual_checks_remaining": ["label and mark overlap", "scientific meaning and units", "caption and uncertainty definition", "colour vision and grayscale review", "latest journal guidance and manuscript placement"],
    }


def export(fig, base, *, data=None, caption="", journal="general", width="single",
           height_mm=None, formats=("pdf", "svg", "png"), dpi=None, provenance=None,
           overwrite=False, figure_type=None, transparent=False):
    """Export any Matplotlib Figure, including new or bespoke domain diagrams."""
    import numpy as np
    from figure_export import export_figure
    from image_metadata import inspect_file
    from palette_audit import audit_palette
    from _common import checked_output_file, atomic_write_bytes
    base = Path(base).expanduser().absolute()
    base.parent.mkdir(parents=True, exist_ok=True)
    config = profile(journal)
    if figure_type is None:
        from matplotlib.collections import QuadMesh
        figure_type = "combination" if any(ax.images or any(isinstance(c, QuadMesh) for c in ax.collections) for ax in fig.axes) else "line"
    if figure_type not in {"line", "image", "combination"}:
        raise ValueError("figure_type must be line, image, combination, or None for automatic image detection")
    target_width = width_mm(journal, width)
    if height_mm is None:
        target_height = target_width * fig.get_figheight() / fig.get_figwidth()
    else:
        target_height = float(height_mm)
    if not math.isfinite(target_height) or not 10 <= target_height <= 1500:
        raise ValueError("Figure height must be finite and between 10 and 1500 mm")
    if config.get("maximum_width_mm") and target_width > config["maximum_width_mm"]:
        raise ValueError("Requested figure width exceeds the profile's documented maximum")
    raster_minimum = max(config.get("raster_dpi", {}).get(figure_type) or 0,
                         config.get("general_bitmap_effective_dpi") or 0)
    dpi = max(400.0, float(raster_minimum), config.get("recommended_raster_dpi") or 0) if dpi is None else float(dpi)
    if not math.isfinite(dpi) or dpi <= 0 or dpi > 2400:
        raise ValueError("DPI must be finite and within (0, 2400]")
    # Avoid accidental multi-gigabyte rasters; use vectors or reduce the raster DPI.
    if target_width / 25.4 * dpi * target_height / 25.4 * dpi > 80_000_000:
        raise ValueError("Raster canvas exceeds 80 million pixels; reduce size or DPI")
    sidecars = [base.with_name(base.name + suffix) for suffix in (".data.json", ".qa.json", ".caption.md")]
    for path in sidecars:
        checked_output_file(path, force=overwrite)
    fig.set_size_inches(target_width / 25.4, target_height / 25.4)
    audit = figure_audit(fig, config)
    if audit["text_below_profile_minimum"] or audit["text_outside_page"]:
        raise ValueError("Figure failed final-size text checks; adjust size/layout: " + json.dumps(audit, ensure_ascii=False))
    versions = {}
    for package in ("numpy", "scipy", "matplotlib", "pandas", "corner", "astropy"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    source = jsonable(data or {})
    source_hash = hashlib.sha256(json.dumps(source, sort_keys=True, allow_nan=False).encode()).hexdigest()
    from . import __version__, TOOL_NAME
    prov = {**(provenance or {}), "source_data_sha256": source_hash, "journal": journal,
            "figure_type": figure_type, "missing_value_encoding": "NaN is saved as null; Infinity is rejected",
            "journal_profile": config, "package_versions": versions,
            "caption": caption, "tool": f"{TOOL_NAME} {__version__}"}
    report = export_figure(fig, base, formats=formats, dpi=dpi, transparent=transparent,
                           bbox_inches=None, font_mode="truetype", overwrite=overwrite,
                           metadata={"Creator": f"Astro Paper Figures {__version__}"},
                           provenance=jsonable(prov), write_manifest=True)
    inspections = []
    for output in report["outputs"]:
        info = inspect_file(output["path"])
        meta = info["metadata"]
        accepted = config.get("supported_formats", [])
        canonical = {"jpeg": "jpg", "tif": "tiff"}
        info["submission_format_supported_by_snapshot"] = canonical.get(output["format"], output["format"]) in {canonical.get(x, x) for x in accepted} if accepted else None
        if meta.get("width_mm") is not None and abs(meta["width_mm"] - target_width) > 0.2:
            raise RuntimeError("Export changed the requested physical width")
        font_report = meta.get("font_resources", {})
        if font_report.get("all_embedded") is False:
            raise RuntimeError("PDF contains unembedded fonts")
        if any(f.get("subtype") == "/Type3" for f in font_report.get("fonts", [])):
            raise RuntimeError("PDF contains Type 3 fonts")
        inspections.append(info)
    notices = list(config.get("notes", []))
    if config.get("status") != "official_snapshot":
        notices.append("Provisional profile: verify the live official journal guidance before submission.")
    if dpi < raster_minimum:
        notices.append(f"Requested DPI {dpi} is below the profile snapshot minimum {raster_minimum}.")
    if config.get("raster_min_width_px"):
        for item in inspections:
            pixels = item["metadata"].get("width_px")
            if pixels and pixels < config["raster_min_width_px"]:
                notices.append(f"{item['input']['name']} is narrower than the profile's minimum raster pixel width.")
    if any(item.get("submission_format_supported_by_snapshot") is False for item in inspections):
        notices.append("Some requested formats are working copies rather than verified submission formats; see each file's format flag.")
    if not caption:
        notices.append("No caption supplied; scientific review and uncertainty definitions remain pending.")
    qa = {"schema_version": 1, "journal_compliance_certified": False,
          "target_width_mm": target_width, "target_height_mm": target_height,
          "artist_checks": audit, "files": inspections,
          "palette_screen": {"scope": "Default palette only; actual custom colours, alpha blending and continuous maps require figure-specific review",
                             "report": audit_palette(PALETTE, background="#FFFFFF", role="graphical")},
          "notices": notices,
          "notice": "Metadata and layout checks do not establish scientific validity or journal acceptance."}
    write_json(sidecars[0], source, overwrite=overwrite)
    write_json(sidecars[1], qa, overwrite=overwrite)
    atomic_write_bytes(sidecars[2], (caption + "\n").encode(), force=overwrite)
    return {"export": report, "qa": qa, "sidecars": [str(p) for p in sidecars]}

