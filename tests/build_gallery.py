"""Export the entire recipe registry with deterministic synthetic fixtures.

The gallery exercises rendering/export, not a physical model or journal
acceptance. No real astronomical measurements are generated or modified.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import traceback

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = SKILL / "outputs" / "stellar-gallery"
sys.path.insert(0, str(SKILL / "scripts"))
os.environ["MPLBACKEND"] = "Agg"
os.environ.setdefault("MPLCONFIGDIR", str(SKILL / ".cache" / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(SKILL / ".cache"))


def write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def contact_sheets(output: Path, records: dict) -> list[str]:
    from PIL import Image, ImageDraw, ImageFont

    successful = [(kind, record) for kind, record in records.items() if record["status"] == "passed"]
    files = []
    cell_width, cell_height = 520, 430
    font = ImageFont.load_default(size=22)
    small_font = ImageFont.load_default(size=17)
    for page, start in enumerate(range(0, len(successful), 12), 1):
        canvas = Image.new("RGB", (4 * cell_width, 3 * cell_height + 65), "white")
        draw = ImageDraw.Draw(canvas)
        draw.text((20, 15), f"SYNTHETIC RECIPE EXPORT TESTS - contact sheet {page}", fill="black", font=font)
        for number, (kind, record) in enumerate(successful[start:start + 12]):
            col, row = number % 4, number // 4
            left, top = col * cell_width, 65 + row * cell_height
            draw.text((left + 12, top + 5), kind, fill="black", font=font)
            path = Path(record["png"])
            with Image.open(path) as image:
                thumb = image.convert("RGB")
                thumb.thumbnail((cell_width - 18, cell_height - 70), Image.Resampling.LANCZOS)
                canvas.paste(thumb, (left + (cell_width - thumb.width) // 2, top + 40))
            draw.text((left + 12, top + cell_height - 24), "180 mm source; thumbnail preview only", fill="#444444", font=small_font)
        destination = output / f"contact-{page:02d}.png"
        canvas.save(destination)
        files.append(str(destination))
    return files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--only", help="Comma-separated recipes; preserves other report entries")
    parser.add_argument("--force", action="store_true", help="Replace outputs for the selected recipes")
    args = parser.parse_args(argv)
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    import matplotlib.pyplot as plt
    from stellarplot.core import export, journal_style, jsonable
    from stellarplot.recipes import RECIPES, render
    from recipe_cases import cases

    fixtures = cases()
    if set(fixtures) != set(RECIPES):
        raise ValueError(f"Fixtures and registry differ: missing={set(RECIPES)-set(fixtures)}, extra={set(fixtures)-set(RECIPES)}")
    selected = args.only.split(",") if args.only else list(fixtures)
    if set(selected) - set(RECIPES):
        raise ValueError(f"Unknown recipes: {set(selected)-set(RECIPES)}")
    report_path = output / "gallery-report.json"
    if args.only and report_path.exists():
        report = json.loads(report_path.read_text())
    else:
        report = {"schema_version": 1, "tool": "stellar-paper-figures", "synthetic": True,
                  "purpose": "Recipe rendering and final-size export verification only; not astronomical evidence or journal acceptance",
                  "journal": "aas", "width_mm": 180, "png_dpi": 300,
                  "recipe_count": len(RECIPES), "random_seed": 20261112,
                  "packages": {name: importlib.metadata.version(name) for name in ["numpy", "matplotlib", "scipy", "pypdf", "pillow", "corner"]},
                  "results": {}}
    report["status"] = "running"
    write_report(report_path, report)

    heights = {"corner": 185, "trace": 185, "autocorrelation": 185,
               "secular_evolution": 185, "transfer_history": 210,
               "orbit3d": 155, "correlation": 140, "heatmap": 140,
               "image": 140, "stability_map": 140, "roche_map": 145,
               "residual_diagnostics": 105, "forest": 100,
               "eclipse_geometry": 115}
    caption = ("Synthetic installation-acceptance demonstration only. Values are deterministic test fixtures, "
               "not observations, fitted stellar parameters, physical simulation results, or evidence of sampling convergence. "
               "Supplied test uncertainties and model curves carry no empirical interpretation. "
               "Residuals, where present, are synthetic observed minus synthetic model.")
    for kind in selected:
        fig = None
        data, options = fixtures[kind]
        height = heights.get(kind, 120)
        try:
            with journal_style("aas"):
                fig, metadata = render(kind, data, options)
                result = export(fig, output / kind, data=data, caption=caption,
                                journal="aas", width=180, height_mm=height,
                                formats=("pdf", "png"), dpi=300,
                                provenance={"synthetic": True, "fixture": "tests/recipe_cases.py", "recipe": kind,
                                            "render_metadata": metadata, "options": options},
                                overwrite=args.force)
            files = {item["format"]: item["path"] for item in result["export"]["outputs"]}
            record = {"status": "passed", "synthetic": True, "pdf": files["pdf"], "png": files["png"],
                      "height_mm": height, "width_mm": 180, "png_dpi": 300,
                      "qa": str(output / f"{kind}.qa.json"),
                      "export_manifest": result["export"]["manifest"],
                      "input_sha256": hashlib.sha256(json.dumps(jsonable(data), sort_keys=True, allow_nan=False).encode()).hexdigest()}
            print(f"PASS {kind}", flush=True)
        except Exception as exc:
            record = {"status": "failed", "synthetic": True, "height_mm": height,
                      "exception": type(exc).__name__, "error": str(exc),
                      "traceback": traceback.format_exc()}
            print(f"FAIL {kind}: {type(exc).__name__}: {exc}", flush=True)
        finally:
            if fig is not None:
                plt.close(fig)
        report["results"][kind] = record
        write_report(report_path, report)
    report["passed"] = sum(row["status"] == "passed" for row in report["results"].values())
    report["failed"] = sum(row["status"] == "failed" for row in report["results"].values())
    report["status"] = "passed" if report["passed"] == len(RECIPES) and not report["failed"] else "incomplete_or_failed"
    report["contact_sheets"] = contact_sheets(output, report["results"])
    write_report(report_path, report)
    print(json.dumps({"report": str(report_path), "passed": report["passed"], "failed": report["failed"], "contact_sheets": report["contact_sheets"]}, ensure_ascii=False), flush=True)
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
