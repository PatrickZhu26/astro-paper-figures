#!/usr/bin/env python3
"""Command-line entry point; input JSON never executes Python code."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "stellar-paper-figures-mpl"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(tempfile.gettempdir()) / "stellar-paper-figures-cache"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
(Path(os.environ["XDG_CACHE_HOME"]) / "fontconfig").mkdir(parents=True, exist_ok=True)


def main(argv=None):
    from stellarplot.core import profiles, export, journal_style, write_json
    parser = argparse.ArgumentParser(description="Astro Paper Figures")
    from stellarplot import __version__
    parser.add_argument("--version", action="version", version=f"Astro Paper Figures {__version__}")
    parser.add_argument("--profile-file", help="Task-local journal profiles JSON; packaged defaults are unchanged")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List supported recipes and input requirements")
    commands.add_parser("journals", help="Show dated journal profiles and verification limits")
    p = commands.add_parser("render", help="Render a JSON specification")
    p.add_argument("spec")
    p.add_argument("--output", required=True, help="Output basename without extension")
    p.add_argument("--journal", default=None)
    p.add_argument("--width", default=None, help="single, double, or millimetres")
    p.add_argument("--formats", default="pdf,svg,png")
    p.add_argument("--dpi", type=float)
    p.add_argument("--force", action="store_true")
    p.add_argument("--html", action="store_true", help="Also render a supported self-contained interactive view")
    q = commands.add_parser("inspect", help="Inspect existing PDF/SVG/raster metadata")
    q.add_argument("file")
    q = commands.add_parser("table", help="Export table JSON as LaTeX and CSV")
    q.add_argument("spec")
    q.add_argument("--output", required=True)
    q.add_argument("--journal", default="general")
    q.add_argument("--force", action="store_true")
    q.add_argument("--preview", action="store_true", help="Also export a small table preview as PDF/SVG/PNG")
    args = parser.parse_args(argv)
    try:
        if args.profile_file:
            from stellarplot.core import load_profile_file
            load_profile_file(args.profile_file)
        if args.command == "list":
            from stellarplot.registry import catalogue
            result = catalogue()
        elif args.command == "journals":
            result = profiles()
        elif args.command == "inspect":
            from image_metadata import inspect_file
            result = inspect_file(args.file)
        elif args.command == "table":
            from stellarplot.adapters import load_data
            from stellarplot.tables import export_table
            spec = load_data(args.spec)
            result = export_table(spec["columns"], spec["rows"], args.output,
                journal=args.journal, caption=spec.get("caption", ""), units=spec.get("units"),
                notes=spec.get("notes", ""), label=spec.get("label", "tab:results"), overwrite=args.force,
                provenance={"spec_source": spec.get("_source")})
            if args.preview:
                import matplotlib.pyplot as plt
                from stellarplot.tables import render_table
                with journal_style(args.journal):
                    fig = render_table(spec["columns"], spec["rows"], units=spec.get("units"))
                    try:
                        result["preview"] = export(fig, str(args.output) + "_preview", data=spec,
                            caption=spec.get("caption", ""), journal=args.journal, width="double",
                            overwrite=args.force, provenance={"spec_source": spec.get("_source"), "purpose": "Editable table companion preview"})
                    finally:
                        plt.close(fig)
        else:
            import matplotlib.pyplot as plt
            from stellarplot.adapters import load_data, apply_mapping
            from stellarplot.registry import render
            from stellarplot.astroio import load_input
            spec_path = Path(args.spec).resolve()
            spec = load_data(spec_path)
            if "data_path" in spec:
                path = Path(spec["data_path"])
                data = load_input(path if path.is_absolute() else spec_path.parent / path, spec.get("data_loader"))
                annotations = spec.get("data", {})
                if not isinstance(annotations, dict) or "_source" in annotations:
                    raise ValueError("Supplementary data metadata must be an object without reserved source fields")
                if set(annotations).intersection(data):
                    raise ValueError("Supplementary metadata cannot silently replace loaded columns or image/WCS values")
                data = {**data, **annotations}
            else:
                data = spec.get("data", {})
            data = apply_mapping(data, spec.get("mapping", {}))
            journal = args.journal or spec.get("journal", "general")
            with journal_style(journal):
                fig, meta = render(spec["kind"], data, spec.get("options", {}))
                try:
                    interactive = None
                    if args.html:
                        from stellarplot.interactive import render_interactive, preflight_interactive
                        interactive = render_interactive(spec["kind"], data, spec.get("options", {}))
                        preflight_interactive(args.output, overwrite=args.force)
                    result = export(fig, args.output, data=data, caption=spec.get("caption", ""),
                        journal=journal, width=args.width or spec.get("width", "single"),
                        height_mm=spec.get("height_mm"), formats=args.formats.split(","), dpi=args.dpi,
                        figure_type=spec.get("figure_type", "combination" if spec["kind"] in {"heatmap", "image", "contour", "stability_map", "roche_map", "dynamic_spectrum", "selection_function", "wcs_image", "localization_map", "image_montage", "position_velocity"} else None),
                        provenance={"spec_source": spec.get("_source"), "recipe": spec["kind"],
                                    "render_metadata": meta, "options": spec.get("options", {}),
                                    "units": spec.get("units", {}), "synthetic": spec.get("synthetic", False)},
                        overwrite=args.force)
                finally:
                    plt.close(fig)
            if args.html:
                from stellarplot.interactive import export_interactive
                result["interactive"] = export_interactive(interactive, args.output,
                    caption=spec.get("caption", ""), provenance={"spec_source": spec.get("_source")}, overwrite=args.force)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        return 0
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(f"astro-paper-figures: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
