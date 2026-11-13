"""Validate newly added astronomy views without rerunning the accepted stellar gallery."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import traceback

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
os.environ["MPLBACKEND"] = "Agg"
os.environ.setdefault("MPLCONFIGDIR", str(SKILL / ".cache" / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(SKILL / ".cache"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SKILL / "outputs" / "astronomy-gallery")
    parser.add_argument("--only", help="Only rerun listed changed recipes")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    import matplotlib.pyplot as plt
    from stellarplot.registry import catalogue, render
    from stellarplot.core import export, journal_style
    from astro_cases import cases as astro_cases
    from sky_cases import cases as sky_cases
    from build_gallery import contact_sheets
    fixtures = {**astro_cases(), **sky_cases()}
    selected = args.only.split(",") if args.only else list(fixtures)
    if set(selected) - set(fixtures):
        raise ValueError("Unknown new recipe")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "gallery-report.json"
    report = json.loads(report_path.read_text()) if args.only and report_path.exists() else {
        "schema_version": 1, "tool": "astro-paper-figures 2.0.0", "synthetic": True,
        "scope": "New general-astronomy entries only; the accepted stellar gallery is retained separately",
        "new_recipe_count": len(fixtures), "total_catalogue_count": len(catalogue()), "results": {}}
    heights = {"sky_map": 115, "wcs_image": 115, "sky_catalog": 115,
               "localization_map": 115, "image_montage": 75, "position_velocity": 135}
    caption = "Synthetic astronomy tool acceptance fixture only. No observational, physical, posterior or journal-acceptance claim is made. Units and transformations follow the saved fixture."
    for kind in selected:
        fig = None
        data, options = fixtures[kind]
        try:
            with journal_style("aas"):
                fig, meta = render(kind, data, options)
                result = export(fig, output / kind, data=data, caption=caption,
                    journal="aas", width=180, height_mm=heights.get(kind, 135),
                    formats=("pdf", "png"), dpi=300, overwrite=args.force,
                    provenance={"recipe": kind, "render_metadata": meta, "options": options, "synthetic": True})
            paths = {item["format"]: item["path"] for item in result["export"]["outputs"]}
            report["results"][kind] = {"status": "passed", "png": paths["png"], "pdf": paths["pdf"], "qa": str(output / (kind + ".qa.json"))}
            print("PASS", kind, flush=True)
        except Exception as exc:
            report["results"][kind] = {"status": "failed", "error": str(exc), "traceback": traceback.format_exc()}
            print("FAIL", kind, str(exc), flush=True)
        finally:
            if fig is not None:
                plt.close(fig)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    report["passed"] = sum(item["status"] == "passed" for item in report["results"].values())
    report["failed"] = sum(item["status"] != "passed" for item in report["results"].values())
    report["status"] = "passed" if report["passed"] == len(fixtures) and report["failed"] == 0 else "incomplete_or_failed"
    report["contact_sheets"] = contact_sheets(output, report["results"])
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"status": report["status"], "passed": report["passed"], "failed": report["failed"], "report": str(report_path)}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
