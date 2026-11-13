"""Explicit-coordinate sky maps and WCS images; no reprojection or inference.

All five entries consume already measured or calculated arrays. Celestial
coordinates require a named Astropy frame and explicit angular units. WCS
images require a genuine two-dimensional celestial FITS header.
"""
from __future__ import annotations

import math
from typing import Any

import matplotlib.pyplot as plt
import numpy as np


REGISTRY = {
    "sky_map": {"required": ["lon", "lat", "frame", "lon_unit", "lat_unit"], "category": "sky", "description": "Named-frame catalogue on an all-sky projection; explicit angular units and longitude direction; ra/dec may replace lon/lat."},
    "wcs_image": {"required": ["image", "wcs_header"], "category": "sky", "description": "2D celestial WCS image; missing pixels masked; optional transformed contours with their own WCS."},
    "sky_catalog": {"required": ["image", "wcs_header", "catalog"], "category": "sky", "description": "Catalogue overlay on a celestial WCS image; catalogue frame and angular units declared independently."},
    "localization_map": {"required": ["lon", "lat", "probability", "frame", "lon_unit", "lat_unit", "probability_type"], "category": "sky", "description": "Supplied rectangular-grid localization probability or density; no normalization or credible-area calculation."},
    "image_montage": {"required": ["images", "titles"], "category": "sky", "description": "Multi-image/multi-band panels with explicit common or separate scales; optional individual WCS headers; no alignment or reprojection inferred."},
}


def _array(value: Any, name: str, ndim=None, *, missing=True) -> np.ndarray:
    try:
        result = np.asarray(value, dtype=float)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name} must contain numeric values") from exc
    if not result.size or (ndim is not None and result.ndim != ndim):
        raise ValueError(f"{name} has an unsupported empty array or shape {result.shape}")
    if np.isinf(result).any() or (not missing and np.isnan(result).any()) or not np.isfinite(result).any():
        raise ValueError(f"{name} must have finite data, with only explicitly missing NaNs allowed")
    return result


def _frame_context(data):
    from astropy.coordinates import frame_transform_graph
    frame = data.get("frame")
    frame_class = frame_transform_graph.lookup_name(frame) if isinstance(frame, str) else None
    if frame_class is None:
        raise ValueError("A recognized Astropy frame name is required; no frame is inferred")
    attributes = data.get("frame_attributes", {})
    if not isinstance(attributes, dict):
        raise ValueError("frame_attributes must be a mapping")
    attributes = dict(attributes)
    names = set(frame_class.frame_attributes)
    if set(attributes) - names:
        raise ValueError("Unrecognized frame attributes: " + ", ".join(sorted(set(attributes)-names)))
    for name in ("equinox", "obstime", "location"):
        value = attributes.get(name)
        if name in names and (name not in attributes or value is None or isinstance(value, str) and not value.strip()):
            raise ValueError(f"Frame {frame} requires explicit frame_attributes.{name}; its source context is not inferred")
    try:
        instance = frame_class(**attributes)
        for key in attributes:
            getattr(instance, key)  # Validate deferred Astropy frame attributes.
    except Exception as exc:
        raise ValueError("Invalid frame context; use explicit Astropy-compatible times, equinox or observing location") from exc
    return frame, attributes


def _coordinates(data: dict, *, vectors=True):
    from astropy import units as u
    frame, attributes = _frame_context(data)
    if "lon" in data or "lat" in data:
        if "lon" not in data or "lat" not in data:
            raise ValueError("Both lon and lat are required")
        lon_source, lat_source = data["lon"], data["lat"]
    elif "ra" in data and "dec" in data:
        if frame not in {"icrs", "fk4", "fk5"}:
            raise ValueError("ra/dec aliases require an equatorial frame; use lon/lat for other frames")
        lon_source, lat_source = data["ra"], data["dec"]
    else:
        raise ValueError("Supply both lon/lat or equatorial ra/dec")
    if "lon_unit" not in data or "lat_unit" not in data:
        raise ValueError("lon_unit and lat_unit must be stated explicitly")
    try:
        lu, bu = u.Unit(data["lon_unit"]), u.Unit(data["lat_unit"])
        if not lu.is_equivalent(u.deg) or not bu.is_equivalent(u.deg):
            raise ValueError("Coordinate units must be angular")
        lon = (_array(lon_source, "longitude", 1) * lu).to_value(u.deg)
        lat = (_array(lat_source, "latitude", 1) * bu).to_value(u.deg)
    except (ValueError, TypeError, u.UnitsError) as exc:
        raise ValueError("Coordinate units must be convertible angular units") from exc
    if vectors and lon.shape != lat.shape:
        raise ValueError("Catalogue longitude and latitude vectors must match")
    if vectors and not np.any(np.isfinite(lon) & np.isfinite(lat)):
        raise ValueError("Catalogue has no finite paired longitude/latitude coordinates")
    # Signed and unsigned single-turn longitudes are both accepted explicitly.
    if np.any(np.abs(lon[np.isfinite(lon)]) > 360 + 1e-10):
        raise ValueError("Longitude must lie within a signed/unsigned single turn; wrap it explicitly first")
    if np.any(np.abs(lat[np.isfinite(lat)]) > 90 + 1e-10):
        raise ValueError("Latitude must be within [-90, 90] degrees")
    return lon, lat, frame


def _image(value, name="image"):
    image = _array(value, name, 2)
    if min(image.shape) < 2:
        raise ValueError("Images require at least two pixels along both axes")
    return image


def _wcs(header, shape):
    from astropy.io import fits
    from astropy.wcs import WCS
    if not isinstance(header, dict) or not header:
        raise ValueError("wcs_header must contain a nonempty FITS-header mapping")
    cards = fits.Header()
    try:
        for key, value in header.items():
            cards[str(key)] = value
        wcs = WCS(cards)
    except Exception as exc:
        raise ValueError("Invalid FITS WCS header") from exc
    if wcs.pixel_n_dim != 2 or wcs.world_n_dim != 2 or not wcs.has_celestial:
        raise ValueError("A 2D celestial WCS is required; slice higher-dimensional data and WCS explicitly")
    if wcs.wcs.lng < 0 or wcs.wcs.lat < 0:
        raise ValueError("WCS must have celestial longitude and latitude axes")
    if str(cards.get("RADESYS", cards.get("RADECSYS", ""))).upper() in {"FK4", "FK5", "FK4-NO-E"} and "EQUINOX" not in cards:
        raise ValueError("FK4/FK5 WCS requires an explicit EQUINOX in its source header")
    for key, expected in (("NAXIS1", shape[1]), ("NAXIS2", shape[0])):
        if key in cards and int(cards[key]) != expected:
            raise ValueError(f"{key} does not match the displayed image shape")
    middle = [(shape[1] - 1) / 2, (shape[0] - 1) / 2]
    if not np.isfinite(wcs.all_pix2world([middle], 0)).all():
        raise ValueError("WCS does not map the image centre to finite world coordinates")
    return wcs


def _normalization(images, options):
    from matplotlib.colors import Normalize, LogNorm
    finite = np.concatenate([image[np.isfinite(image)] for image in images])
    vmin, vmax = float(options.get("vmin", finite.min())), float(options.get("vmax", finite.max()))
    if not math.isfinite(vmin) or not math.isfinite(vmax) or vmin > vmax:
        raise ValueError("Colour bounds must be finite and ordered")
    if vmin == vmax:
        if "vmin" in options or "vmax" in options:
            raise ValueError("Explicit colour bounds must be distinct")
        delta = max(abs(vmin) * 0.01, 1e-12)
        vmin, vmax = vmin - delta, vmax + delta
    scale = options.get("norm", "linear")
    if scale == "log":
        if np.any(finite <= 0) or vmin <= 0:
            raise ValueError("Log colour scale requires positive values and bounds; no pixels are silently dropped")
        norm = LogNorm(vmin=vmin, vmax=vmax, clip=False)
    elif scale == "linear":
        norm = Normalize(vmin=vmin, vmax=vmax, clip=False)
    else:
        raise ValueError("Built-in image norms are linear or log; use the custom API for another explicit normalization")
    return norm, {"norm": scale, "vmin": vmin, "vmax": vmax,
                  "below_colour_range": int(np.sum(finite < vmin)), "above_colour_range": int(np.sum(finite > vmax))}


def _cmap(options):
    return plt.get_cmap(options.get("cmap", "viridis")).with_extremes(bad="#777777")


def _unit_label(data, options):
    return options.get("zlabel", "Image value" + (f" ({data['unit']})" if data.get("unit") else " (supplied units)"))


def _wcs_labels(ax, wcs, options):
    types = wcs.world_axis_physical_types
    for i, physical in enumerate(types):
        names = {"pos.eq.ra": "Right ascension", "pos.eq.dec": "Declination",
                 "pos.galactic.lon": "Galactic longitude", "pos.galactic.lat": "Galactic latitude"}
        fallback = names.get(physical, str(wcs.wcs.ctype[i]))
        ax.coords[i].set_axislabel(options.get("xlabel" if i == 0 else "ylabel", fallback))
        ax.coords[i].set_ticks(number=4)
        ax.coords[i].set_ticklabel(size=plt.rcParams["font.size"], exclude_overlapping=True)
    if options.get("grid", False):
        ax.coords.grid(color="white", alpha=.6, linestyle=":")


def render(kind: str, data: dict, options: dict | None = None):
    if kind not in REGISTRY:
        raise ValueError(f"Unknown sky recipe {kind!r}")
    if not isinstance(data, dict) or (options is not None and not isinstance(options, dict)):
        raise ValueError("data and options must be mappings")
    options = dict(options or {})
    meta = {"recipe": kind, "transformations": [], "notes": [], "missing_data_policy": "Source arrays retained; NaN coordinates are not drawn and NaN image pixels are grey masked"}
    fig = None
    try:
        if kind == "sky_map":
            lon, lat, frame = _coordinates(data)
            center = float(options.get("center_lon_deg", 0))
            if not math.isfinite(center) or abs(center) > 360:
                raise ValueError("Sky-map central longitude must be finite and within a single turn")
            projection = options.get("projection", "mollweide")
            if projection not in {"mollweide", "hammer", "aitoff"}:
                raise ValueError("Built-in all-sky projections are mollweide, hammer and aitoff")
            increases_left = bool(options.get("longitude_increases_left", True))
            wrapped = np.remainder(lon - center + 180, 360) - 180
            display_lon = np.deg2rad(-wrapped if increases_left else wrapped)
            # GeoAxes' fixed aspect can leave a title outside the page under
            # constrained layout; reserve explicit title and angular-label space.
            fig = plt.figure(figsize=(7.2, 4.3))
            fig.subplots_adjust(left=.08, right=.92, bottom=.20, top=.82)
            ax = fig.add_subplot(projection=projection)
            colors = data.get("values")
            if colors is not None:
                colors = _array(colors, "values", 1)
                if colors.shape != lon.shape:
                    raise ValueError("Sky-map colour values must match coordinates")
            points = ax.scatter(display_lon, np.deg2rad(lat), c=colors, s=options.get("marker_size", 14), cmap=_cmap(options) if colors is not None else None)
            if colors is not None:
                fig.colorbar(points, ax=ax, orientation="horizontal", pad=.13, fraction=.06, label=options.get("zlabel", "Supplied value"))
            ticks_deg = np.arange(-150, 151, 30)
            tick_values = np.remainder(center + (-ticks_deg if increases_left else ticks_deg), 360)
            ax.set_xticks(np.deg2rad(ticks_deg), labels=[f"{value:g}°" for value in tick_values])
            ax.grid(True, alpha=.3)
            equatorial = frame in {"icrs", "fk4", "fk5"}
            ax.set(xlabel=options.get("xlabel", f"{frame.upper()} " + ("right ascension" if equatorial else "longitude") + " (deg)"),
                   ylabel=options.get("ylabel", "Declination (deg)" if equatorial else f"{frame} latitude (deg)"))
            drawn = np.isfinite(lon) & np.isfinite(lat)
            if colors is not None:
                drawn &= np.isfinite(colors)
            meta.update({"frame": frame, "frame_attributes": _frame_context(data)[1], "longitude_increases_left": increases_left,
                         "drawn_coordinate_pairs": int(np.sum(drawn))})
            meta["transformations"].append({"display": "angular units to degrees, central-longitude wrapping and radians for projection", "center_lon_deg": center, "projection": projection})
            meta["notes"].append("Coordinates are plotted in the declared input frame; no cross-frame transformation, source clustering or probability inference is performed.")
        elif kind in {"wcs_image", "sky_catalog"}:
            image = _image(data["image"])
            wcs = _wcs(data["wcs_header"], image.shape)
            norm, normalization = _normalization([image], options)
            fig = plt.figure(layout="constrained")
            ax = fig.add_subplot(projection=wcs)
            artist = ax.imshow(np.ma.masked_invalid(image), origin="lower", interpolation="nearest", norm=norm, cmap=_cmap(options))
            _wcs_labels(ax, wcs, options)
            fig.colorbar(artist, ax=ax, label=_unit_label(data, options), pad=.02, fraction=.045)
            meta["normalization"] = normalization
            meta["wcs"] = {"ctype": list(wcs.wcs.ctype), "cunit": [str(unit) for unit in wcs.wcs.cunit], "pixel_origin": 0, "image_origin": "lower", "shape": list(image.shape)}
            for index, contour in enumerate(data.get("contours", [])):
                if not isinstance(contour, dict):
                    raise ValueError("Each contour overlay must be a mapping")
                contour_image = _image(contour["image"], f"contours[{index}].image")
                contour_wcs = _wcs(contour["wcs_header"], contour_image.shape)
                levels = _array(contour["levels"], "contour levels", 1, missing=False)
                if np.any(np.diff(levels) <= 0):
                    raise ValueError("Supplied contour levels must be strictly increasing")
                ax.contour(np.ma.masked_invalid(contour_image), transform=ax.get_transform(contour_wcs),
                           levels=levels, colors=contour.get("color", "white"), linewidths=.8)
                meta["transformations"].append({"contour_overlay": index, "levels": levels.tolist(), "coordinate_transform": "input contour WCS to displayed image WCS; no data resampling"})
            if kind == "sky_catalog" or "catalog" in data:
                from astropy import units as u
                from astropy.coordinates import SkyCoord, frame_transform_graph
                catalog = data["catalog"]
                lon, lat, frame = _coordinates(catalog)
                attributes = _frame_context(catalog)[1]
                try:
                    frame_obj = frame_transform_graph.lookup_name(frame)(**attributes)
                    coordinates = SkyCoord(lon * u.deg, lat * u.deg, frame=frame_obj)
                    px, py = wcs.world_to_pixel(coordinates)
                except Exception as exc:
                    raise ValueError("Catalogue frame cannot transform to this WCS; supply the required frame attributes") from exc
                ax.scatter(px, py, s=options.get("catalog_marker_size", 36), marker=options.get("catalog_marker", "o"),
                           facecolors="none", edgecolors=options.get("catalog_color", "white"), linewidths=.8,
                           label=options.get("catalog_label", "Supplied catalogue"))
                ax.legend(loc="upper right")
                meta["catalog"] = {"frame": frame, "frame_attributes": attributes, "rows": len(lon),
                    "outside_image_or_undefined": int(np.sum(~np.isfinite(px) | ~np.isfinite(py) | (px < -.5) | (px > image.shape[1]-.5) | (py < -.5) | (py > image.shape[0]-.5)))}
                meta["transformations"].append("Catalogue frame converted to the image's celestial WCS and then zero-origin pixels; source coordinates retained")
            # Overlays outside the image should be clipped, not silently zoom the field.
            ax.set_xlim(-.5, image.shape[1]-.5)
            ax.set_ylim(-.5, image.shape[0]-.5)
            meta["notes"].append("The celestial orientation follows the supplied WCS, including its rotation/handedness. No north-up rotation, pixel alignment, reprojection or astrometric calibration is inferred.")
        elif kind == "localization_map":
            lon, lat, frame = _coordinates(data, vectors=False)
            if min(len(lon), len(lat)) < 2 or np.isnan(lon).any() or np.isnan(lat).any():
                raise ValueError("Localization grids need at least two finite coordinate centres per axis")
            if not np.all(np.diff(lon) > 0) or not np.all(np.diff(lat) > 0):
                raise ValueError("Localization grid centres must increase; handle a longitude wrap explicitly")
            probability = _image(data["probability"], "probability")
            if probability.shape != (len(lat), len(lon)):
                raise ValueError("Probability must have shape [latitude, longitude]")
            finite = probability[np.isfinite(probability)]
            if np.any(finite < 0):
                raise ValueError("Probability/density values must be nonnegative")
            probability_type = data["probability_type"]
            if probability_type == "per_pixel":
                if np.any(finite > 1) or finite.sum() > 1 + 1e-8:
                    raise ValueError("Supplied per-pixel probabilities must be within [0,1] and sum to no more than one")
                label = "Probability per supplied pixel"
            elif probability_type == "density":
                if not isinstance(data.get("probability_unit"), str) or not data["probability_unit"]:
                    raise ValueError("Probability density requires an explicit probability_unit")
                from astropy import units as u
                try:
                    if not u.Unit(data["probability_unit"]).is_equivalent(u.sr ** -1):
                        raise ValueError("Probability density must be per angular area")
                except (ValueError, u.UnitsError) as exc:
                    raise ValueError("Probability density unit must be convertible to inverse solid angle") from exc
                label = f"Probability density ({data['probability_unit']})"
            else:
                raise ValueError("probability_type must be per_pixel or density")
            norm, normalization = _normalization([probability], options)
            fig, ax = plt.subplots(layout="constrained")
            artist = ax.pcolormesh(lon, lat, np.ma.masked_invalid(probability), shading="nearest", norm=norm, cmap=_cmap(options))
            if options.get("longitude_increases_left", True):
                ax.invert_xaxis()
            ax.set(xlabel=options.get("xlabel", f"{frame} longitude (deg)"), ylabel=options.get("ylabel", f"{frame} latitude (deg)"))
            fig.colorbar(artist, ax=ax, label=options.get("zlabel", label))
            meta.update({"frame": frame, "frame_attributes": _frame_context(data)[1], "probability_type": probability_type, "normalization": normalization})
            if probability_type == "per_pixel":
                meta["supplied_probability_sum"] = float(finite.sum())
            meta["notes"].append("Only the supplied grid is displayed. No renormalization, spherical area correction, HEALPix conversion, confidence contour or credible-region area is computed.")
        else:
            images = [_image(value, f"images[{index}]") for index, value in enumerate(data["images"])]
            titles = data["titles"]
            if not images or len(images) > 16 or isinstance(titles, str) or len(titles) != len(images):
                raise ValueError("A montage requires 1–16 images and one explicit title per image")
            headers = data.get("wcs_headers")
            if headers is not None and len(headers) != len(images):
                raise ValueError("wcs_headers must match images")
            units = data.get("units", [data.get("unit")] * len(images))
            if isinstance(units, str) or len(units) != len(images):
                raise ValueError("units must contain one unit label per image")
            if any(unit is not None and not isinstance(unit, str) for unit in units):
                raise ValueError("Each panel unit must be a string or null for an undeclared unit")
            shared = bool(options.get("shared_scale", True))
            if shared and len(set(units)) != 1:
                raise ValueError("A shared numerical colour scale requires matching declared units; use separate scales otherwise")
            columns = options.get("columns", min(3, len(images)))
            if not isinstance(columns, int) or not 1 <= columns <= min(8, len(images)):
                raise ValueError("Montage columns must be a valid integer")
            rows = math.ceil(len(images) / columns)
            fig = plt.figure(figsize=(3.1 * columns, 2.7 * rows), layout="constrained")
            grid = fig.add_gridspec(rows, columns)
            shared_norm, shared_metadata = _normalization(images, options) if shared else (None, None)
            axes, artists, limits = [], [], []
            for index, image in enumerate(images):
                wcs = _wcs(headers[index], image.shape) if headers is not None else None
                ax = fig.add_subplot(grid[index // columns, index % columns], projection=wcs)
                norm, normalization = (shared_norm, shared_metadata) if shared else _normalization([image], options)
                artist = ax.imshow(np.ma.masked_invalid(image), origin="lower", interpolation="nearest", norm=norm, cmap=_cmap(options))
                ax.set_title(str(titles[index]))
                if wcs is not None:
                    _wcs_labels(ax, wcs, {})
                else:
                    ax.set(xlabel="Pixel x", ylabel="Pixel y")
                if not shared:
                    fig.colorbar(artist, ax=ax, label=units[index] or "Supplied value")
                axes.append(ax); artists.append(artist); limits.append(normalization)
            if shared:
                fig.colorbar(artists[0], ax=axes, label=options.get("zlabel", units[0] or "Supplied value"), fraction=.04, pad=.02)
            meta.update({"shared_numerical_scale": shared, "normalization": limits,
                         "alignment": data.get("alignment", "not verified by renderer"), "panel_units": units})
            meta["notes"].append("Panels are not reprojected or registered. A shared numerical scale does not establish equal photometric calibration, PSF, resolution or comparable surface brightness.")
        if options.get("title"):
            if kind == "image_montage":
                fig.suptitle(str(options["title"]))
            else:
                ax.set_title(str(options["title"]))
        return fig, meta
    except Exception:
        if fig is not None:
            plt.close(fig)
        raise
