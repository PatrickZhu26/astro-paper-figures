"""Behavioral checks; run with the project's plotting Python from any directory."""
from __future__ import annotations
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
_cache = tempfile.TemporaryDirectory(prefix="stellar-test-cache-")
os.environ["MPLBACKEND"] = "Agg"
os.environ["MPLCONFIGDIR"] = str(Path(_cache.name) / "mpl")
os.environ["XDG_CACHE_HOME"] = str(Path(_cache.name) / "xdg")

import matplotlib.pyplot as plt
import numpy as np
from stellarplot import adapters, core, interactive, recipes, tables


class WorkspaceTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="stellar-tests-")
        self.root = Path(self.directory.name)

    def tearDown(self):
        plt.close("all")
        self.directory.cleanup()


class InputContractTests(WorkspaceTest):
    def test_csv_missing_and_explicit_mapping_preserve_input(self):
        path = self.root / "source.csv"
        payload = b"time,flux\n1,2\n2,\n"
        path.write_bytes(payload)
        data = adapters.load_data(path)
        mapped = adapters.apply_mapping(data, {"x": "time", "y": "flux"})
        self.assertEqual(mapped["x"], [1, 2])
        self.assertTrue(np.isnan(mapped["y"][1]))
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(data["_source"]["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertNotIn("x", data)

    def test_ambiguous_or_unsafe_inputs_are_rejected(self):
        cases = {
            "duplicate.json": '{"x":1,"x":2}',
            "nan.json": '{"x":NaN}',
            "overflow.json": '{"x":1e999}',
            "root.json": '[1,2]',
            "duplicate.csv": 'x,x\n1,2\n',
            "ragged.csv": 'x,y\n1,2,3\n',
            "object.pkl": 'not executable input',
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                path = self.root / name
                path.write_text(payload)
                with self.assertRaises(ValueError):
                    adapters.load_data(path)

    def test_ecsv_units_and_masks_round_trip(self):
        from astropy.table import Table, MaskedColumn
        import astropy.units as u
        path = self.root / "units.ecsv"
        table = Table()
        table["time"] = MaskedColumn([1., 2.], mask=[False, True], unit=u.day)
        table.write(path, format="ascii.ecsv")
        loaded = adapters.load_data(path)
        self.assertEqual(loaded["time"], [1., None])
        self.assertEqual(loaded["_source"]["units"], {"time": "d"})

    def test_no_hierarchy_or_contact_filter_is_inferred(self):
        for system in ["nonhierarchical_triple", "contact_binary", "semidetached_binary", "detached_binary"]:
            with self.subTest(system=system):
                path = self.root / (system + ".json")
                original = {"system_class": system, "potential": [[0., 1.], [2., 3.]], "coordinate": [0., 1.]}
                path.write_text(json.dumps(original))
                data = adapters.load_data(path)
                mapped = adapters.apply_mapping(data, {"x": "coordinate", "y": "coordinate", "z": "potential"})
                self.assertEqual(mapped["system_class"], system)
                fig, _ = recipes.render("contour", mapped, {"levels": 3})
                self.assertIsNotNone(fig)


class ScientificEncodingTests(WorkspaceTest):
    def test_categorical_labels_survive_decoration(self):
        labels = ["Detached", "Contact"]
        for kind in ["bar", "boxplot", "violin"]:
            with self.subTest(kind=kind):
                data = {"x": labels, "y": [1., 2.]} if kind == "bar" else {
                    "groups": [[1., 2., 3.], [2., 3., 4.]], "labels": labels}
                fig, _ = recipes.render(kind, data)
                fig.canvas.draw()
                self.assertEqual([tick.get_text() for tick in fig.axes[0].get_xticklabels()], labels)
        fig, _ = recipes.render("forest", {"estimate": [1., 2.], "lower": [.9, 1.8],
            "upper": [1.1, 2.2], "labels": labels})
        fig.canvas.draw()
        self.assertEqual([tick.get_text() for tick in fig.axes[0].get_yticklabels()], labels)

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            recipes.render("errorbar", {"x": [1, 2], "y": [1, 2], "yerr": [.1, -.1]})
        with self.assertRaises(ValueError):
            recipes.render("radial_velocity", {"x": [1, 2], "observed": [1, 2], "model": [1, 2], "sigma": [-1, 1]})

    def test_log_values_and_uncertainty_bounds_cannot_be_dropped(self):
        for y in [[0., 2.], [-1., 2.]]:
            with self.subTest(y=y), self.assertRaises(ValueError):
                recipes.render("line", {"x": [1, 2], "y": y}, {"yscale": "log"})
        with self.assertRaises(ValueError):
            recipes.render("errorbar", {"x": [1, 2], "y": [.1, 2], "yerr": [.2, .1]}, {"yscale": "log"})

    def test_nan_line_gap_is_retained(self):
        data = {"x": [0., 1., 2.], "y": [1., float("nan"), 3.]}
        fig, _ = recipes.render("line", data)
        shown = fig.axes[0].lines[0].get_ydata()
        self.assertEqual(len(shown), 3)
        self.assertTrue(np.isnan(shown[1]))

    def test_phase_wrap_and_input_preservation(self):
        data = {"x": [-.5, 0., .5, 2.], "y": [1., 2., 3., 4.], "period": 2.}
        before = json.dumps(data, sort_keys=True)
        fig, _ = recipes.render("phase_curve", data)
        shown = np.asarray(fig.axes[0].collections[0].get_offsets())[:, 0]
        np.testing.assert_allclose(shown, [.75, 0., .25, 0.])
        self.assertTrue(np.all((shown >= 0.) & (shown < 1.)))
        self.assertEqual(json.dumps(data, sort_keys=True), before)
        with self.assertRaises(ValueError):
            recipes.render("phase_curve", {**data, "period": 0.})

    def test_fit_residuals_are_observed_minus_model(self):
        data = {"x": [1., 2., 3.], "observed": [3., 6., 5.], "model": [2., 4., 8.]}
        fig, meta = recipes.render("radial_velocity", data)
        shown = np.asarray(fig.axes[1].collections[0].get_offsets())[:, 1]
        np.testing.assert_allclose(shown, [1., 2., -3.])
        self.assertTrue(any("observed" in str(x) for x in meta["transformations"]))

    def test_orbit_has_equal_physical_axes(self):
        fig, _ = recipes.render("orbit2d", {"x": [-2., 0., 2.], "y": [-1., 1., -1.]})
        fig.canvas.draw()
        ax = fig.axes[0]
        origin, xpoint, ypoint = ax.transData.transform([(0., 0.), (1., 0.), (0., 1.)])
        self.assertAlmostEqual(np.linalg.norm(xpoint-origin), np.linalg.norm(ypoint-origin), places=5)

    def test_heatmap_rows_are_y_and_columns_are_x(self):
        z = [[1., 2., 3.], [10., 20., 30.]]
        fig, _ = recipes.render("heatmap", {"x": [1., 2., 3.], "y": [10., 20.], "z": z})
        np.testing.assert_allclose(fig.axes[0].collections[0].get_array(), z)
        self.assertFalse(fig.axes[0].yaxis_inverted())
        with self.assertRaises(ValueError):
            recipes.render("heatmap", {"x": [1., 2.], "y": [10., 20.], "z": z})


class NativeTableTests(WorkspaceTest):
    def test_numeric_csv_and_latex_escaping(self):
        value = .12345678901234566
        base = self.root / "parameters"
        tables.export_table(["parameter", "value"], [["mass_A&B%", value]], base,
                            caption="Fit_A & 95% interval", notes="quoted_sigma", journal="aas")
        with base.with_suffix(".csv").open(newline="") as handle:
            row = next(csv.DictReader(handle))
        self.assertEqual(float(row["value"]), value)
        self.assertEqual(row["parameter"], "mass_A&B%")
        tex = base.with_suffix(".tex").read_text()
        self.assertIn(r"mass\_A\&B\%", tex)
        self.assertIn(r"Fit\_A \& 95\% interval", tex)
        self.assertIn(r"\begin{deluxetable}", tex)
        self.assertIn(r"\colhead{value}", tex)

    def test_mnras_dialect_has_three_rules_and_no_vertical_rules(self):
        base = self.root / "mnras"
        tables.export_table(["name", "value"], [["A", 1.]], base, journal="mnras")
        tex = base.with_suffix(".tex").read_text()
        self.assertEqual(tex.count(r"\hline"), 3)
        self.assertIn(r"\begin{tabular}{ll}", tex)
        self.assertNotIn("deluxetable", tex)

    def test_table_rejects_unsafe_label_and_shape(self):
        with self.assertRaises(ValueError):
            tables.export_table(["a"], [[1]], self.root / "unsafe", label=r"tab:\input{secret}")
        with self.assertRaises(ValueError):
            tables.export_table(["a", "b"], [[1]], self.root / "shape")


class ExportTests(WorkspaceTest):
    def _figure(self):
        return recipes.render("line", {"x": [0., 1., 2.], "y": [1., 2., 1.]}, {"xlabel": "Time (day)", "ylabel": "Signal"})[0]

    def test_dimensions_fonts_provenance_and_source_data(self):
        from pypdf import PdfReader
        data = {"x": [0., 1., 2.], "y": [1., 2., 1.]}
        base = self.root / "figure"
        with core.journal_style("aas"):
            fig = self._figure()
            report = core.export(fig, base, data=data, caption="Synthetic verification only.",
                                 journal="aas", width="double", formats=("pdf", "png"), dpi=120,
                                 provenance={"synthetic": True})
        page = PdfReader(base.with_suffix(".pdf")).pages[0]
        self.assertAlmostEqual(float(page.mediabox.width) * 25.4/72, core.width_mm("aas", "double"), delta=.02)
        resources = page["/Resources"]["/Font"]
        for font in resources.values():
            self.assertNotEqual(str(font.get_object().get("/Subtype")), "/Type3")
        source = json.loads(base.with_name(base.name+".data.json").read_text())
        self.assertEqual(source, data)
        manifest = json.loads(Path(report["export"]["manifest"]).read_text())
        self.assertEqual(manifest["provenance"]["synthetic"], True)
        self.assertEqual(manifest["provenance"]["journal"], "aas")
        self.assertEqual(len(manifest["provenance"]["source_data_sha256"]), 64)
        self.assertFalse(report["qa"]["journal_compliance_certified"])

    def test_existing_exports_are_not_overwritten(self):
        base = self.root / "protected"
        with core.journal_style("aas"):
            fig = self._figure()
            core.export(fig, base, caption="Test", journal="aas", width="double", formats=("pdf",), dpi=120)
            original = base.with_suffix(".pdf").read_bytes()
            with self.assertRaises(ValueError):
                core.export(fig, base, caption="Changed", journal="aas", width="double", formats=("pdf",), dpi=120)
        self.assertEqual(base.with_suffix(".pdf").read_bytes(), original)

    def test_obviously_clipped_text_prevents_export(self):
        base = self.root / "clipped"
        with core.journal_style("aas"):
            fig = self._figure()
            fig.text(1.4, .5, "Outside final page")
            with self.assertRaises(ValueError):
                core.export(fig, base, caption="Test", journal="aas", width="double", formats=("pdf",), dpi=120)
        self.assertFalse(base.with_suffix(".pdf").exists())

    def test_interactive_is_self_contained_and_caption_is_escaped(self):
        fig = interactive.render_interactive("line", {"x": [0., 1.], "y": [1., 2.]})
        base = self.root / "interactive"
        caption = '<img src=x onerror="sentinel"> & synthetic'
        interactive.export_interactive(fig, base, caption=caption, provenance={"synthetic": True})
        document = base.with_suffix(".html").read_text()
        self.assertGreater(len(document), 1_000_000)
        self.assertIsNone(re.search(r'<script[^>]+src\s*=\s*[\"\x27]https?://', document, re.I))
        self.assertNotIn(caption, document)
        self.assertIn("&lt;img src=x onerror=&quot;sentinel&quot;&gt; &amp; synthetic", document)


if __name__ == "__main__":
    unittest.main(verbosity=2)
