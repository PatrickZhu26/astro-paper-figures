"""Independent astronomy-input checks; no prior adapters or old recipes rerun."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL / "scripts"))
from stellarplot import astroio


def celestial_header():
    header = fits.Header()
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRPIX1"] = 2.0
    header["CRPIX2"] = 2.0
    header["CRVAL1"] = 30.0
    header["CRVAL2"] = -10.0
    header["CDELT1"] = -0.1
    header["CDELT2"] = 0.1
    header["CUNIT1"] = "deg"
    header["CUNIT2"] = "deg"
    return header


class AstronomyIOTests(unittest.TestCase):
    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory(prefix="astroio-review-")
        self.root = Path(self.workspace.name)

    def tearDown(self):
        self.workspace.cleanup()

    def test_fits_scaled_image_preserves_physical_values_and_source(self):
        path = self.root / "scaled.fits"
        raw = np.array([[0, 1, 2], [3, -999, 5]], dtype=np.int16)
        header = fits.Header([
            ("SIMPLE", True), ("BITPIX", 16), ("NAXIS", 2),
            ("NAXIS1", 3), ("NAXIS2", 2), ("EXTEND", True),
            ("BSCALE", 2.0), ("BZERO", 100.0), ("BLANK", -999),
            ("BUNIT", "Jy/beam"),
        ])
        for card in celestial_header().cards:
            header.append(card)
        # Write raw storage bytes so fixture construction cannot absorb scaling.
        payload = raw.astype(">i2").tobytes()
        path.write_bytes(header.tostring().encode("ascii") + payload + b"\0" * ((-len(payload)) % 2880))
        self.assertEqual(fits.getheader(path)["BSCALE"], 2.0)
        original_bytes = path.read_bytes()
        result = astroio.load_fits_image(path)
        expected = raw.astype(float) * 2 + 100
        expected[raw == -999] = np.nan
        np.testing.assert_allclose(result["image"], expected, equal_nan=True)
        self.assertEqual(result["unit"], "Jy/beam")
        self.assertEqual(result["_source"]["original_bscale"], 2.0)
        self.assertEqual(result["_source"]["original_bzero"], 100.0)
        self.assertEqual(result["_source"]["sha256"], hashlib.sha256(original_bytes).hexdigest())
        self.assertEqual(path.read_bytes(), original_bytes)

    def test_wcs_reference_pixel_and_hdu_are_preserved(self):
        path = self.root / "extension.fits"
        header = celestial_header()
        fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(data=np.arange(20).reshape(4, 5), header=header, name="SCI")]).writeto(path)
        result = astroio.load_fits_image(path, hdu="SCI")
        reference = WCS(header).pixel_to_world_values(1.0, 1.0)
        restored = WCS(result["wcs_header"]).pixel_to_world_values(1.0, 1.0)
        np.testing.assert_allclose(restored, reference, atol=1e-10)
        np.testing.assert_allclose(restored, (30., -10.), atol=1e-10)
        self.assertEqual(result["_source"]["hdu"], "SCI")
        self.assertEqual(result["image"].shape, (4, 5))

    def test_cube_requires_and_preserves_explicit_plane(self):
        path = self.root / "cube.fits"
        values = np.arange(2 * 4 * 5, dtype=float).reshape(2, 4, 5)
        header = celestial_header()
        header["CTYPE3"] = "FREQ"
        header["CRPIX3"] = 1.
        header["CRVAL3"] = 1.4e9
        header["CDELT3"] = 1.e6
        header["CUNIT3"] = "Hz"
        fits.PrimaryHDU(data=values, header=header).writeto(path)
        with self.assertRaises(ValueError):
            astroio.load_fits_image(path)
        result = astroio.load_fits_image(path, plane=1)
        np.testing.assert_array_equal(result["image"], values[1])
        self.assertEqual(result["_source"]["plane_numpy_indices"], [1])
        self.assertEqual(result["_source"]["original_shape"], [2, 4, 5])
        self.assertEqual(WCS(result["wcs_header"]).pixel_n_dim, 2)
        for invalid in [True, [0, 0], -1, 2]:
            with self.subTest(plane=invalid), self.assertRaises(ValueError):
                astroio.load_fits_image(path, plane=invalid)

    def test_non_display_celestial_axes_are_rejected(self):
        path = self.root / "different_axis_order.fits"
        header = fits.Header({"CTYPE1": "FREQ", "CTYPE2": "RA---TAN", "CTYPE3": "DEC--TAN",
                              "CRPIX1": 1., "CRPIX2": 2., "CRPIX3": 1.,
                              "CRVAL1": 1.4e9, "CRVAL2": 30., "CRVAL3": -10.,
                              "CDELT1": 1e6, "CDELT2": -.1, "CDELT3": .1,
                              "CUNIT1": "Hz", "CUNIT2": "deg", "CUNIT3": "deg"})
        fits.PrimaryHDU(data=np.zeros((2, 4, 5)), header=header).writeto(path)
        with self.assertRaises(ValueError):
            astroio.load_fits_image(path, plane=0)

    def test_fits_table_units_nulls_and_columns(self):
        path = self.root / "catalog.fits"
        table = fits.BinTableHDU.from_columns([
            fits.Column(name="id", format="J", array=[1, -99, 3], null=-99),
            fits.Column(name="mass", format="D", array=[1.2, 1.3, 1.4], unit="solMass"),
            fits.Column(name="name", format="8A", array=["one", "two", "three"]),
        ])
        fits.HDUList([fits.PrimaryHDU(), table]).writeto(path)
        before = path.read_bytes()
        result = astroio.load_fits_table(path, columns=["id", "mass"])
        np.testing.assert_allclose(result["id"], [1., np.nan, 3.], equal_nan=True)
        np.testing.assert_allclose(result["mass"], [1.2, 1.3, 1.4])
        self.assertEqual(result["_source"]["units"], {"mass": "solMass"})
        self.assertNotIn("name", result)
        self.assertEqual(result["_source"]["null_encoding"]["id"]["count"], 1)
        self.assertEqual(path.read_bytes(), before)
        for columns in [["id", "id"], ["missing"], []]:
            with self.subTest(columns=columns), self.assertRaises(ValueError):
                astroio.load_fits_table(path, columns=columns)

    def test_tnull_is_applied_in_stored_integer_space_before_scaling(self):
        path = self.root / "scaled_table.fits"
        primary = fits.PrimaryHDU()
        primary.header["EXTEND"] = True
        header = fits.Header([
            ("XTENSION", "BINTABLE"), ("BITPIX", 8), ("NAXIS", 2),
            ("NAXIS1", 4), ("NAXIS2", 3), ("PCOUNT", 0), ("GCOUNT", 1),
            ("TFIELDS", 1), ("TTYPE1", "flux"), ("TFORM1", "J"),
            ("TUNIT1", "Jy"), ("TSCAL1", 2.0), ("TZERO1", 10.0), ("TNULL1", -99),
        ])
        raw = np.array([3, -99, 7], dtype=">i4").tobytes()
        path.write_bytes(primary.header.tostring().encode("ascii") + header.tostring().encode("ascii") + raw + b"\0" * ((-len(raw)) % 2880))
        result = astroio.load_fits_table(path)
        np.testing.assert_allclose(result["flux"], [16., np.nan, 24.], equal_nan=True)
        self.assertEqual(result["_source"]["null_encoding"]["flux"]["count"], 1)

    def test_wrong_hdu_kind_is_rejected(self):
        path = self.root / "mixed.fits"
        fits.HDUList([fits.PrimaryHDU(data=np.ones((2, 2))),
                      fits.BinTableHDU.from_columns([fits.Column(name="x", format="D", array=[1.])])]).writeto(path)
        with self.assertRaises(ValueError):
            astroio.load_fits_image(path, hdu=1)
        with self.assertRaises(ValueError):
            astroio.load_fits_table(path, hdu=0)

    def test_numpy_numeric_arrays_preserve_values_missingness_and_hash(self):
        image = np.array([[1., np.nan], [3., 4.]])
        npy = self.root / "image.npy"
        np.save(npy, image)
        before = npy.read_bytes()
        result = astroio.load_numpy(npy)
        np.testing.assert_allclose(result["array"], image, equal_nan=True)
        self.assertFalse(result["_source"]["allow_pickle"])
        self.assertEqual(result["_source"]["sha256"], hashlib.sha256(before).hexdigest())
        self.assertEqual(npy.read_bytes(), before)
        npz = self.root / "bundle.npz"
        np.savez_compressed(npz, image=image, time=np.arange(2))
        result = astroio.load_numpy(npz)
        self.assertEqual(set(result), {"image", "time", "_source"})
        np.testing.assert_allclose(result["image"], image, equal_nan=True)

    def test_pickle_complex_infinity_and_reserved_numpy_keys_are_rejected(self):
        for extension in ["npy", "npz"]:
            for name, array in [
                ("object", np.array([{"not": "numeric"}], dtype=object)),
                ("complex", np.array([1 + 2j])),
                ("inf", np.array([1., np.inf])),
            ]:
                with self.subTest(extension=extension, value=name):
                    path = self.root / f"{name}.{extension}"
                    if extension == "npy":
                        np.save(path, array)
                    else:
                        np.savez(path, values=array)
                    with self.assertRaises(ValueError):
                        astroio.load_numpy(path)
        reserved = self.root / "reserved.npz"
        np.savez(reserved, _source=np.arange(3))
        with self.assertRaises(ValueError):
            astroio.load_numpy(reserved)

    def test_duplicate_npz_array_names_are_rejected(self):
        path = self.root / "duplicate.npz"
        one, two = io.BytesIO(), io.BytesIO()
        np.save(one, np.array([1.]))
        np.save(two, np.array([2.]))
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("x.npy", one.getvalue())
            archive.writestr("x.npy", two.getvalue())
        with self.assertRaises(ValueError):
            astroio.load_numpy(path)

    def test_input_budgets_are_enforced_without_large_allocations(self):
        path = self.root / "small.npy"
        np.save(path, np.arange(4))
        with patch.object(astroio, "MAX_BYTES", 1), self.assertRaises(ValueError):
            astroio.load_numpy(path)
        with patch.object(astroio, "MAX_ELEMENTS", 3), self.assertRaises(ValueError):
            astroio.load_numpy(path)
        compressed = self.root / "compressible.npz"
        np.savez_compressed(compressed, data=np.zeros(10000))
        with patch.object(astroio, "MAX_BYTES", compressed.stat().st_size + 100), self.assertRaises(ValueError):
            astroio.load_numpy(compressed)

    def test_new_dispatch_requires_explicit_table_mode(self):
        image = self.root / "image.fits"
        fits.PrimaryHDU(data=np.ones((2, 3))).writeto(image)
        self.assertEqual(astroio.load_input(image)["image"].shape, (2, 3))
        table = self.root / "table.fits"
        fits.HDUList([fits.PrimaryHDU(), fits.BinTableHDU.from_columns([
            fits.Column(name="value", format="D", array=[2., 3.], unit="Jy")])]).writeto(table)
        result = astroio.load_input(table, {"format": "fits_table", "columns": ["value"]})
        np.testing.assert_allclose(result["value"], [2., 3.])
        with self.assertRaises(ValueError):
            astroio.load_input(table)
        npy = self.root / "values.npy"
        np.save(npy, np.arange(3))
        with self.assertRaises(ValueError):
            astroio.load_input(npy, {"unit": "Jy"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
