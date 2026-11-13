"""Bounded astronomy inputs with explicit HDU/plane, WCS and provenance."""
from __future__ import annotations
import hashlib
from pathlib import Path

MAX_BYTES = 200 * 1024 * 1024
MAX_ELEMENTS = 20_000_000


def _source(path):
    path = Path(path).expanduser()
    if path.is_symlink() or not path.is_file():
        raise ValueError("Input must be a regular file, not a final-path symlink")
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError("Astronomy input exceeds 200 MiB; make an explicit scientific subset first")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return path.resolve(), {"path": str(path.resolve()), "bytes": size, "sha256": digest.hexdigest()}


def _numeric(array, name):
    import numpy as np
    array = np.asarray(array)
    if array.size > MAX_ELEMENTS or not array.size:
        raise ValueError(f"{name} must have 1–20 million elements")
    if array.dtype.kind not in "biuf":
        raise ValueError(f"{name} must contain real numeric data; choose an explicit transform for complex/object arrays")
    if np.isinf(array).any():
        raise ValueError(f"{name} contains infinity; handle it explicitly before plotting")
    return array.copy()


def load_fits_image(path, *, hdu=0, plane=None):
    """Read a 2D image or explicitly select leading numpy axes of a cube.

    The celestial WCS must belong to FITS pixel axes 1 and 2. More complicated
    axis arrangements require a caller-supplied scientific slice/reprojection.
    BSCALE/BZERO and BLANK are handled by Astropy, with originals recorded.
    """
    import math
    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS
    path, provenance = _source(path)
    with fits.open(path, mode="readonly", memmap=False, lazy_load_hdus=True) as hdus:
        selected = hdus[hdu]
        if not isinstance(selected, (fits.PrimaryHDU, fits.ImageHDU, fits.CompImageHDU)):
            raise ValueError("Selected HDU is not an image; choose a specific image HDU or the FITS table loader")
        header = selected.header.copy()
        shape = tuple(selected.shape or ())
        if len(shape) < 2 or math.prod(shape) > MAX_ELEMENTS:
            raise ValueError("Image has no 2D plane or exceeds 20 million source pixels; subset it explicitly")
        if len(shape) > 2:
            if plane is None:
                raise ValueError("A FITS cube requires explicit indices for every leading numpy axis")
            indices = [plane] if isinstance(plane, int) and not isinstance(plane, bool) else plane
            if not isinstance(indices, (list, tuple)) or len(indices) != len(shape) - 2:
                raise ValueError("plane must specify one index per leading numpy axis")
            if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < size for v, size in zip(indices, shape)):
                raise ValueError("FITS plane index is outside its axis")
        else:
            if plane is not None:
                raise ValueError("plane is only valid for images with more than two dimensions")
            indices = []
        image = _numeric(selected.data[tuple(indices)] if indices else selected.data, "FITS image")
        wcs_header = None
        if any(str(header.get(f"CTYPE{i}", "")).strip() for i in range(1, len(shape) + 1)):
            wcs = WCS(header)
            if wcs.has_celestial:
                if {wcs.wcs.lng, wcs.wcs.lat} != {0, 1}:
                    raise ValueError("Celestial coordinates are not on the displayed FITS axes; provide a verified scientific slice")
                wcs_header = dict(wcs.celestial.to_header(relax=True))
        provenance.update({"format": "fits_image", "hdu": hdu, "plane_numpy_indices": list(indices),
            "original_shape": list(shape), "display_shape": list(image.shape),
            "original_bscale": header.get("BSCALE", 1), "original_bzero": header.get("BZERO", 0),
            "blank_value": header.get("BLANK"), "wcs_projection": "header supplied; no reprojection",
            "pixel_origin": "numpy zero-based; FITS header conventions retained by Astropy"})
        return {"image": image, "wcs_header": wcs_header, "unit": header.get("BUNIT"), "_source": provenance}


def load_fits_table(path, *, hdu=1, columns=None):
    import numpy as np
    from astropy.io import fits
    path, provenance = _source(path)
    with fits.open(path, mode="readonly", memmap=False, lazy_load_hdus=True) as hdus:
        selected = hdus[hdu]
        if not isinstance(selected, (fits.BinTableHDU, fits.TableHDU)):
            raise ValueError("Selected HDU is not a table")
        if int(selected.header.get("NAXIS2", 0)) > 2_000_000:
            raise ValueError("Table exceeds two million rows; select a scientific subset first")
        names = list(selected.columns.names) if columns is None else list(columns)
        if not names or len(set(names)) != len(names) or any(n not in selected.columns.names or n.startswith("_") for n in names):
            raise ValueError("Specify nonempty unique existing FITS table columns; reserved names are not allowed")
        result = {}
        units = {}
        nulls = {}
        count = 0
        for name in names:
            value = np.asarray(selected.data[name])
            count += value.size
            if count > MAX_ELEMENTS or value.dtype.kind not in "biufSU":
                raise ValueError("FITS table columns must be bounded real numeric or text arrays; object/complex columns need explicit preparation")
            null = selected.columns[name].null
            if value.dtype.kind in "biuf":
                value = _numeric(value, name)
                if null is not None:
                    # TNULL names a value in the stored integer domain; Astropy
                    # presents TSCAL/TZERO-scaled physical values to the caller.
                    scale = selected.columns[name].bscale
                    zero = selected.columns[name].bzero
                    scale = 1 if scale is None else scale
                    zero = 0 if zero is None else zero
                    if scale == 0:
                        raise ValueError("A scaled FITS null cannot be distinguished with zero TSCAL; prepare that column explicitly")
                    scaled_null = null * scale + zero
                    masked = value == scaled_null
                    if masked.any():
                        value = value.astype(float)
                        value[masked] = np.nan
                        nulls[name] = {"fits_tnull_storage": null, "tscal": scale, "tzero": zero,
                                       "physical_null": scaled_null, "count": int(masked.sum())}
            else:
                value = value.astype(str)
            result[name] = value
            if selected.columns[name].unit:
                units[name] = selected.columns[name].unit
        provenance.update({"format": "fits_table", "hdu": hdu, "columns": names,
                           "units": units, "null_encoding": nulls, "rows": len(selected.data)})
        result["_source"] = provenance
        return result


def load_numpy(path):
    """Read numeric NPY/NPZ with pickle disabled and decompressed-size limits."""
    import numpy as np
    import zipfile
    path, provenance = _source(path)
    if path.suffix.lower() == ".npz":
        with zipfile.ZipFile(path) as archive:
            if sum(info.file_size for info in archive.infolist()) > MAX_BYTES or len(archive.infolist()) > 128:
                raise ValueError("NPZ decompressed contents exceed the input budget")
            keys = [info.filename[:-4] if info.filename.endswith(".npy") else info.filename for info in archive.infolist()]
            if len(set(keys)) != len(keys):
                raise ValueError("NPZ contains duplicate array/member names")
        with np.load(path, allow_pickle=False) as archive:
            if any(key.startswith("_") for key in archive.files):
                raise ValueError("NPZ uses reserved source metadata names")
            result = {key: _numeric(archive[key], key) for key in archive.files}
        if sum(v.size for v in result.values()) > MAX_ELEMENTS:
            raise ValueError("NPZ exceeds twenty million total elements")
    else:
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        result = {"array": _numeric(array, "array")}
    provenance.update({"format": path.suffix.lstrip("."), "arrays": {k: {"shape": list(v.shape), "dtype": str(v.dtype)} for k, v in result.items()}, "allow_pickle": False})
    return {**result, "_source": provenance}


def load_input(path, options=None):
    """Dispatch explicit astronomy formats; preserve original table adapters."""
    from .adapters import load_data
    options = dict(options or {})
    mode = options.pop("format", None)
    suffix = Path(path).suffix.lower()
    if mode == "fits_table":
        return load_fits_table(path, **options)
    is_fits = suffix in {".fits", ".fit", ".fts", ".fz"} or str(path).lower().endswith((".fits.gz", ".fit.gz", ".fts.gz"))
    if mode == "fits_image" or (mode is None and is_fits):
        return load_fits_image(path, **options)
    if mode == "numpy" or (mode is None and suffix in {".npy", ".npz"}):
        if options:
            raise ValueError("NumPy input has no implicit conversion options; use explicit mapping")
        return load_numpy(path)
    if mode is not None or options:
        raise ValueError("Unknown data loader mode or options")
    return load_data(path)
