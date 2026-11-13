"""Reproducible semantic checks for the new astronomy recipes and profiles."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL / "tests"))
_cache = tempfile.TemporaryDirectory(prefix="astro-semantics-cache-")
os.environ["MPLBACKEND"] = "Agg"
os.environ["MPLCONFIGDIR"] = str(Path(_cache.name) / "mpl")
os.environ["XDG_CACHE_HOME"] = str(Path(_cache.name) / "xdg")
(Path(_cache.name) / "xdg/fontconfig").mkdir(parents=True)

import matplotlib.pyplot as plt
import numpy as np
from astro_cases import cases
from stellarplot import astro, core, registry
from stellarplot.recipes import RECIPES as STELLAR_RECIPES


class AstronomySemantics(unittest.TestCase):
    def setUp(self):
        self.fixtures = cases()

    def tearDown(self):
        plt.close("all")

    def test_cmd_magnitude_direction_and_source_preservation(self):
        data, options = self.fixtures["color_magnitude"]
        original = copy.deepcopy(data)
        fig, _ = astro.render("color_magnitude", data, options)
        self.assertTrue(fig.axes[0].yaxis_inverted())
        np.testing.assert_array_equal(data["x"], original["x"])
        np.testing.assert_array_equal(data["y"], original["y"])
        self.assertEqual(data["magnitude_system"], original["magnitude_system"])

    def test_multiband_offsets_are_explicit_and_do_not_change_source(self):
        data, options = self.fixtures["multi_band_lightcurve"]
        original = data["y"].copy()
        fig, meta = astro.render("multi_band_lightcurve", data, options)
        self.assertTrue(fig.axes[0].yaxis_inverted())
        np.testing.assert_array_equal(data["y"], original)
        offset_record = meta["transformations"][0]
        self.assertEqual(offset_record["display_offsets_per_band"], [0., -.5])
        # Errorbar data lines expose the displayed central values.
        series = [line for line in fig.axes[0].lines if len(line.get_ydata()) == len(data["x"])]
        np.testing.assert_allclose(series[0].get_ydata(), original[:, 0])
        self.assertTrue(any(np.allclose(line.get_ydata(), original[:, 1] - .5) for line in series))

    def test_wavelength_annotation_uses_declared_redshift_direction(self):
        data, options = self.fixtures["spectral_lines"]
        before = copy.deepcopy(data)
        _, meta = astro.render("spectral_lines", data, options)
        self.assertAlmostEqual(meta["transformations"][0]["display_position"], 656.28 * 1.05)
        self.assertEqual(data["lines"], before["lines"])
        np.testing.assert_array_equal(data["x"], before["x"])

    def test_frequency_annotation_uses_inverse_redshift_factor(self):
        data, options = self.fixtures["spectral_lines"]
        frequency_data = {**data, "x": np.linspace(3.8e14, 5.5e14, 50), "y": np.ones(50), "xunit": "Hz"}
        _, meta = astro.render("spectral_lines", frequency_data, options)
        expected = 299792458 / (656.28e-9) / 1.05
        self.assertAlmostEqual(meta["transformations"][0]["display_position"] / expected, 1.)

    def test_bpt_cannot_mislabel_linear_ratios_as_logarithmic(self):
        data, _ = self.fixtures["bpt_diagram"]
        with self.assertRaises(ValueError):
            astro.render("bpt_diagram", {**data, "ratio_scale": "linear"})

    def test_distance_definition_must_be_known(self):
        data, _ = self.fixtures["hubble_diagram"]
        with self.assertRaises(ValueError):
            astro.render("hubble_diagram", {**data, "distance_kind": "unknown"})

    def test_line_frame_conversion_requires_redshift(self):
        data, _ = self.fixtures["spectral_lines"]
        with self.assertRaises(ValueError):
            astro.render("spectral_lines", {key: value for key, value in data.items() if key != "redshift"})

    def test_asd_units_cannot_be_relabelled_as_psd(self):
        data, _ = self.fixtures["sensitivity_curve"]
        with self.assertRaises(ValueError):
            astro.render("sensitivity_curve", {**data, "quantity": "PSD"})

    def test_angular_multipoles_are_integers(self):
        data, _ = self.fixtures["angular_power_spectrum"]
        with self.assertRaises(ValueError):
            astro.render("angular_power_spectrum", {**data, "x": data["x"] + .2})

    def test_pv_log_axis_does_not_drop_negative_velocity(self):
        data, _ = self.fixtures["position_velocity"]
        with self.assertRaises(ValueError):
            astro.render("position_velocity", data, {"yscale": "log"})

    def test_luminosity_function_does_not_take_log_of_magnitude(self):
        data, _ = self.fixtures["luminosity_function"]
        with self.assertRaises(ValueError):
            astro.render("luminosity_function", {**data, "xunit": "mag", "x_quantity": "absolute_magnitude"}, {"xscale": "log"})

    def test_band_offsets_need_one_value_per_band(self):
        data, _ = self.fixtures["multi_band_lightcurve"]
        with self.assertRaises(ValueError):
            astro.render("multi_band_lightcurve", data, {"offsets": [0.]})

    def test_registry_preserves_all_old_names_and_descriptions(self):
        combined = registry.catalogue()
        self.assertEqual(len(STELLAR_RECIPES), 49)
        for name, old_description in STELLAR_RECIPES.items():
            self.assertEqual(combined[name], old_description)
        for name in astro.REGISTRY:
            self.assertIn(name, combined)


class CustomJournalProfiles(unittest.TestCase):
    def setUp(self):
        self.previous_overrides = copy.deepcopy(core._PROFILE_OVERRIDES)
        self.directory = tempfile.TemporaryDirectory(prefix="astro-profile-test-")

    def tearDown(self):
        core._PROFILE_OVERRIDES.clear()
        core._PROFILE_OVERRIDES.update(self.previous_overrides)
        self.directory.cleanup()

    def test_custom_profile_is_detached_from_inputs_and_default_file(self):
        defaults_path = core.SKILL_ROOT / "assets/journals.json"
        before_bytes = defaults_path.read_bytes()
        previous_aas = core.profile("aas")
        config = {"widths_mm": {"single": 91., "double": 182.}, "font_size_pt": 8.5, "notes": []}
        original = copy.deepcopy(config)
        core.register_profile("test-local-journal", config)
        self.assertEqual(config, original)
        self.assertEqual(core.width_mm("test-local-journal", "single"), 91.)
        self.assertEqual(core.profile("test-local-journal")["status"], "custom_profile")
        config["widths_mm"]["single"] = 99.
        detached = core.profiles()
        detached["test-local-journal"]["widths_mm"]["single"] = 100.
        self.assertEqual(core.width_mm("test-local-journal", "single"), 91.)
        self.assertEqual(core.profile("aas"), previous_aas)
        self.assertEqual(defaults_path.read_bytes(), before_bytes)

    def test_invalid_profile_shapes_and_numeric_values_are_rejected(self):
        cases = [
            ("", {}), ("test-bad", []), ("test-bad", {"widths_mm": []}),
            ("test-bad", {"font_size_pt": 0}), ("test-bad", {"font_size_pt": True}),
            ("test-bad", {"min_line_pt": -1}), ("test-bad", {"font_size_pt": float("nan")}),
            ("test-bad", {"widths_mm": {"single": float("inf")}}),
            ("test-bad", {"raster_dpi": {"image": "300"}}),
            ("test-bad", {"raster_dpi": []}), ("test-bad", {"notes": "unstructured"}),
        ]
        before = copy.deepcopy(core._PROFILE_OVERRIDES)
        for name, config in cases:
            with self.subTest(config=config), self.assertRaises(ValueError):
                core.register_profile(name, config)
        self.assertEqual(core._PROFILE_OVERRIDES, before)

    def test_load_profile_file_retains_source_hash(self):
        path = Path(self.directory.name) / "journals.json"
        payload = {"profiles": {"test-file-journal": {"widths_mm": {"single": 90., "double": None}, "font_size_pt": 9.}}}
        path.write_text(json.dumps(payload))
        names = core.load_profile_file(path)
        self.assertEqual(names, ["test-file-journal"])
        config = core.profile("test-file-journal")
        self.assertEqual(config["configuration_source"]["path"], str(path.resolve()))
        import hashlib
        self.assertEqual(config["configuration_source"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(core.width_mm("test-file-journal", "single"), 90.)

    def test_invalid_profile_document_does_not_partially_apply(self):
        path = Path(self.directory.name) / "partially-invalid.json"
        path.write_text(json.dumps({"profiles": {
            "test-valid-first": {"widths_mm": {"single": 90.}},
            "test-invalid-second": {"font_size_pt": -1.},
        }}))
        before = copy.deepcopy(core._PROFILE_OVERRIDES)
        with self.assertRaises(ValueError):
            core.load_profile_file(path)
        self.assertEqual(core._PROFILE_OVERRIDES, before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
