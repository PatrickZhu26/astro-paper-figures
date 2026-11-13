"""Independent integration checks for scientific meaning and export boundaries."""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
_cache = tempfile.TemporaryDirectory(prefix="stellar-review-cache-")
os.environ["MPLBACKEND"] = "Agg"
os.environ["MPLCONFIGDIR"] = str(Path(_cache.name) / "mpl")
os.environ["XDG_CACHE_HOME"] = str(Path(_cache.name) / "xdg")

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
from stellarplot import core, interactive, tables


class IntegrationReview(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="stellar-review-")
        self.root = Path(self.directory.name)

    def tearDown(self):
        plt.close("all")
        self.directory.cleanup()

    def test_multistar_velocity_keeps_values_errors_and_residual_sign(self):
        observed = np.array([[10., 15.], [12., 14.], [14., 13.], [16., 12.]])
        model = observed + np.array([[.1, -.2], [.2, -.1], [-.3, .4], [.4, -.3]])
        sigma = np.array([[.1, .2], [.15, .25], [.2, .3], [.25, .35]])
        times = np.array([1., 2., 4., 8.])
        figure = interactive.render_interactive("radial_velocity", {
            "x": times, "observed": observed, "model": model,
            "sigma": sigma, "labels": ["Star A", "Star B"],
        }, {"xscale": "log", "yscale": "log", "ylabel": "RV (km/s)"})
        self.assertEqual(len(figure.data), 6)
        for index in range(2):
            observed_trace, model_trace, residual_trace = figure.data[3 * index:3 * index + 3]
            np.testing.assert_allclose(observed_trace.x, times)
            np.testing.assert_allclose(observed_trace.y, observed[:, index])
            np.testing.assert_allclose(model_trace.y, model[:, index])
            np.testing.assert_allclose(residual_trace.y, observed[:, index] - model[:, index])
            np.testing.assert_allclose(observed_trace.error_y.array, sigma[:, index])
            np.testing.assert_allclose(residual_trace.error_y.array, sigma[:, index])
            self.assertNotEqual(observed_trace.yaxis, residual_trace.yaxis)
            self.assertIn(["Star A", "Star B"][index], observed_trace.name)
        self.assertEqual(figure.layout.yaxis.type, "log")
        self.assertEqual(figure.layout.yaxis2.type, "linear")
        self.assertEqual(figure.layout.xaxis2.type, "log")
        self.assertEqual(figure.layout.xaxis.matches, "x2")

    def test_magnitude_axis_reverses_only_observation_panel(self):
        figure = interactive.render_interactive("light_curve", {
            "x": [1., 2., 3., 4.], "observed": [12., 12.3, 12.2, 12.],
            "model": [12., 12.2, 12.2, 12.], "sigma": [.1, .2, .1, .1],
        }, {"invert_y": True, "ylabel": "Magnitude (mag)"})
        self.assertEqual(figure.layout.yaxis.autorange, "reversed")
        self.assertNotEqual(figure.layout.yaxis2.autorange, "reversed")
        np.testing.assert_allclose(figure.data[2].y, [0., .1, 0., 0.], atol=1e-12)

    def test_asymmetric_errors_keep_upper_and_lower_distinct(self):
        lower = np.array([.1, .2, .3, .4])
        upper = np.array([.5, .6, .7, .8])
        figure = interactive.render_interactive("errorbar", {
            "x": [1., 2., 3., 4.], "y": [5., 6., 7., 8.],
            "yerr": np.stack([lower, upper]),
        })
        error = figure.data[0].error_y
        self.assertFalse(error.symmetric)
        np.testing.assert_allclose(error.arrayminus, lower)
        np.testing.assert_allclose(error.array, upper)

    def test_external_image_is_not_reported_as_an_offline_artifact(self):
        remote = "https://example.com/science-image.png"
        figure = go.Figure(go.Scatter(x=[1., 2.], y=[3., 4.]))
        figure.add_layout_image(source=remote, x=1, y=1)
        strict = self.root / "strict"
        with self.assertRaises(ValueError):
            interactive.export_interactive(figure, strict)
        self.assertEqual(list(self.root.glob("strict.*")), [])
        allowed = self.root / "explicit-online"
        result = interactive.export_interactive(figure, allowed, require_self_contained=False)
        self.assertFalse(result["self_contained"])
        report = json.loads((self.root / "explicit-online.interactive.json").read_text())
        self.assertFalse(report["self_contained"])
        self.assertIn(remote, report["external_resources"])
        self.assertTrue("example.com" in (self.root / "explicit-online.html").read_text(),
                        "The explicitly online HTML should retain the image reference")

    def test_plain_scatter_with_default_template_can_be_self_contained(self):
        figure = go.Figure(go.Scatter(x=[1., 2.], y=[3., 4.]))
        report = interactive.export_interactive(figure, self.root / "offline")
        self.assertTrue(report["self_contained"])
        metadata = json.loads((self.root / "offline.interactive.json").read_text())
        self.assertEqual(metadata["external_resources"], [])

    def test_relative_and_file_image_dependencies_are_not_embedded(self):
        for index, source in enumerate(["images/source.png", "file:///tmp/source.png"]):
            with self.subTest(source=source):
                figure = go.Figure(go.Scatter(x=[1., 2.], y=[3., 4.]))
                figure.update_layout(template=None)
                figure.add_layout_image(source=source, x=1, y=1)
                base = self.root / f"unbundled-{index}"
                with self.assertRaises(ValueError):
                    interactive.export_interactive(figure, base)
                self.assertEqual(list(self.root.glob(f"unbundled-{index}.*")), [])

    def test_unknown_table_journal_fails_before_writing(self):
        with self.assertRaises(ValueError):
            tables.export_table(["mass"], [[1.]], self.root / "unknown", journal="mnars")
        self.assertEqual(list(self.root.glob("unknown.*")), [])

    def test_infinity_is_rejected_and_nan_means_missing_in_all_table_outputs(self):
        for number in [float("inf"), float("-inf"), np.float64("inf")]:
            with self.subTest(number=number), self.assertRaises(ValueError):
                tables.export_table(["value"], [[number]], self.root / "infinite")
        self.assertEqual(list(self.root.glob("infinite.*")), [])
        result = tables.export_table(["object", "mass"], [["A", float("nan")], ["B", 2.]],
                                    self.root / "missing", units={"mass": "solMass"})
        report = json.loads((self.root / "missing.table.json").read_text())
        self.assertIsNone(report["rows"][0][1])
        self.assertEqual(report["rows"][1][1], 2.)
        with (self.root / "missing.csv").open(newline="") as source:
            records = list(csv.reader(source))
        self.assertEqual(records[1], ["A", ""])
        self.assertEqual(float(records[2][1]), 2.)
        latex = (self.root / "missing.tex").read_text().lower()
        self.assertNotIn("nan", latex)
        self.assertNotIn("infinity", latex)
        self.assertFalse(result["compiled"])
        self.assertFalse(report["compiled"])

    def test_mnras_combination_uses_appropriate_raster_resolution(self):
        with core.journal_style("mnras"):
            figure, axis = plt.subplots(figsize=(3.3, 2.5), layout="constrained")
            axis.imshow([[1., 2.], [3., 4.]])
            axis.set(xlabel="Pixel coordinate", ylabel="Pixel coordinate")
            report = core.export(figure, self.root / "combination", data={"z": [[1., 2.], [3., 4.]]},
                journal="mnras", formats=["png"], caption="Synthetic image and labels; export verification only.")
        self.assertEqual(report["export"]["provenance"]["figure_type"], "combination")
        self.assertGreaterEqual(report["export"]["settings"]["dpi"], 800.)
        self.assertFalse(report["qa"]["journal_compliance_certified"])
        self.assertTrue(all(axis.spines[side].get_visible() for side in ["left", "right", "bottom", "top"]))

    def test_explicit_low_dpi_is_flagged_and_invalid_image_type_is_rejected(self):
        with core.journal_style("mnras"):
            figure, axis = plt.subplots(figsize=(3.3, 2.5), layout="constrained")
            axis.imshow([[1., 2.], [3., 4.]])
            with self.assertRaises(ValueError):
                core.export(figure, self.root / "bad-kind", figure_type="unknown-kind", formats=["png"])
            report = core.export(figure, self.root / "low-dpi", data={"z": [[1., 2.], [3., 4.]]},
                journal="mnras", formats=["png"], dpi=200, figure_type="combination")
        self.assertTrue(any("below" in note.lower() and "800" in note for note in report["qa"]["notices"]))
        self.assertFalse(report["qa"]["journal_compliance_certified"])
        self.assertEqual(list(self.root.glob("bad-kind.*")), [])

    def _cli(self, specification, base):
        path = self.root / (base + "-spec.json")
        path.write_text(json.dumps(specification))
        return subprocess.run([sys.executable, str(SKILL / "scripts" / "stellar_figures.py"),
            "render", str(path), "--output", str(self.root / base), "--html"],
            capture_output=True, text=True, timeout=60)

    def test_html_preflight_rejection_leaves_no_static_products(self):
        result = self._cli({"kind": "histogram", "data": {"values": [1., 2., 3., 4.]}}, "unsupported")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(list(self.root.glob("unsupported.*")), [])

    def test_existing_html_cannot_cause_partial_static_replacement(self):
        sentinel = self.root / "existing.html"
        sentinel.write_text("preserve existing result")
        result = self._cli({"kind": "line", "data": {"x": [1., 2., 3.], "y": [4., 5., 6.]}}, "existing")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(sentinel.read_text(), "preserve existing result")
        self.assertEqual(sorted(p.name for p in self.root.glob("existing.*")), ["existing.html"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
