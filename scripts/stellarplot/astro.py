"""Explicit, data-driven recipes for astronomy beyond multiple-star systems.

This module displays supplied scientific quantities. It does not fit distances,
classify sources, compute selection corrections, or infer physical parameters.
"""
from __future__ import annotations

from typing import Any
import matplotlib.pyplot as plt
import numpy as np

from .recipes import _array, _xy, _series, _error, _draw_xy, _decorate, _matrix, _color, _scale_valid

SOURCES = {
    "magnitudes": "https://docs.astropy.org/en/stable/units/logarithmic_units.html",
    "spectral_units": "https://docs.astropy.org/en/stable/units/equivalencies.html#spectral-units",
    "cosmology": "https://docs.astropy.org/en/stable/cosmology/index.html",
    "power_spectra": "https://healpy.readthedocs.io/en/stable/generated/healpy.sphtfunc.anafast.html",
    "spectral_density": "https://gwpy.readthedocs.io/en/stable/spectrum/",
}

REGISTRY = {
    "color_magnitude": {"required": ["x", "y", "color_label", "magnitude_label", "magnitude_system", "magnitude_kind"], "category": "photometry", "description": "Supplied colour and magnitude; bands/system and apparent/absolute/instrumental kind explicit; brighter magnitudes upward"},
    "bpt_diagram": {"required": ["x", "y", "x_ratio", "y_ratio", "ratio_scale"], "category": "emission_lines", "description": "Supplied log10 emission-line ratios; optional supplied boundaries, no automatic classification"},
    "hubble_diagram": {"required": ["x", "y", "distance_kind", "yunit"], "category": "cosmology", "description": "Supplied redshift and distance/modulus; no default cosmology, peculiar-velocity or K correction"},
    "radial_profile": {"required": ["x", "y", "xunit", "yunit", "profile_quantity"], "category": "extended_sources", "description": "Supplied radial surface-brightness/density/intensity profile, explicit units and magnitude convention"},
    "luminosity_function": {"required": ["x", "y", "x_quantity", "xunit", "yunit", "density_definition"], "category": "population", "description": "Supplied bin-centre density/count estimates; optional bin_width; no volume/completeness correction"},
    "transmission_spectrum": {"required": ["x", "y", "xunit", "yunit", "quantity"], "category": "exoplanets", "description": "Supplied wavelength and transit depth/radius quantity; no conversion between ppm, ratios or radii"},
    "multi_band_lightcurve": {"required": ["x", "y", "bands", "quantity", "xunit", "yunit", "time_system"], "category": "time_domain", "description": "Shared time vector and supplied per-band values/errors; optional explicit display offsets, no colour/calibration inference"},
    "spectral_lines": {"required": ["x", "y", "xunit", "yunit", "spectral_frame", "lines"], "category": "spectroscopy", "description": "Supplied spectrum plus explicit line coordinates/units/frame; declared redshift required for frame conversion"},
    "position_velocity": {"required": ["x", "y", "z", "xunit", "yunit", "zunit"], "category": "spectral_imaging", "description": "Supplied position-velocity map z[velocity,position]; no cube extraction or Doppler convention inferred"},
    "angular_power_spectrum": {"required": ["x", "y", "convention", "spectrum", "yunit"], "category": "cosmology", "description": "Supplied integer multipoles and Cl or Dl; no convention transformation or sky/mask deconvolution"},
    "sensitivity_curve": {"required": ["x", "y", "xunit", "yunit", "signal_unit", "quantity"], "category": "instrumentation_multimessenger", "description": "Positive frequencies and matched ASD/PSD/amplitude/characteristic-strain convention with checked units"},
    "evolution_tracks": {"required": ["tracks", "x_quantity", "y_quantity", "xunit", "yunit"], "category": "evolution", "description": "Independently sampled supplied evolutionary/cooling tracks; no stellar/evolutionary model is computed"},
    "abundance_pattern": {"required": ["x", "y", "elements", "abundance_definition", "reference"], "category": "chemical_evolution", "description": "Supplied logarithmic abundance pattern against atomic number, explicit element labels and reference scale"},
    "rotation_curve": {"required": ["x", "y", "xunit", "yunit", "velocity_convention"], "category": "dynamics", "description": "Supplied radius and velocity estimates with optional supplied component curves; no mass-model fit or deprojection"},
}


def _text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must explicitly describe the supplied quantity")
    return value.strip()


def _unit(data: dict, key: str, equivalents=None):
    import astropy.units as u
    raw = _text(data, key)
    try:
        unit = u.Unit(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} is not a recognized Astropy unit: {raw}") from exc
    if equivalents is not None and not any(unit.is_equivalent(target) for target in equivalents):
        raise ValueError(f"{key} has the wrong physical dimension: {raw}")
    return unit


def _one_y(data: dict) -> tuple[np.ndarray, np.ndarray]:
    x, values = _xy(data)
    if values.shape[1] != 1:
        raise ValueError("This recipe needs one supplied y series; use named separate views for different quantities")
    return x, values


def _linear_values(options: dict, axes=("x", "y")) -> None:
    for axis in axes:
        if options.get(axis + "scale", "linear") != "linear":
            raise ValueError(f"{axis} values are already logarithmic/magnitudes and must use a linear display axis")


def _base(kind: str, data: dict, options: dict) -> dict:
    return {"recipe": kind, "transformations": [], "notes": [],
            "uncertainty": options.get("uncertainty", "Supplied errors/intervals; interpretation is not inferred"),
            "units": {k: data[k] for k in ("xunit", "yunit", "zunit") if k in data},
            "sources": SOURCES,
            "missing_data_policy": "No input rows are changed; NaN line gaps and masked map pixels are retained."}


def render(kind: str, data: dict, options: dict | None = None) -> tuple[Any, dict]:
    if kind not in REGISTRY:
        raise ValueError(f"Unknown astronomy recipe: {kind}")
    if not isinstance(data, dict) or (options is not None and not isinstance(options, dict)):
        raise ValueError("data and options must be mappings")
    options = dict(options or {})
    for key in REGISTRY[kind]["required"]:
        if key not in data:
            raise ValueError(f"Required data field is missing: {key}")
    meta = _base(kind, data, options)
    fig = None
    try:
        fig, ax = plt.subplots(layout="constrained")
        if kind == "color_magnitude":
            _linear_values(options)
            x, y = _xy(data)
            label = _text(data, "color_label")
            magnitude = _text(data, "magnitude_label")
            system = _text(data, "magnitude_system")
            magnitude_kind = _text(data, "magnitude_kind")
            if magnitude_kind not in {"apparent", "absolute", "instrumental"}:
                raise ValueError("magnitude_kind must be apparent, absolute or instrumental")
            _draw_xy(ax, x, y, data, options, points=True)
            _decorate(ax, {**options, "invert_y": True}, xlabel=f"{label} (mag; {system})", ylabel=f"{magnitude} ({magnitude_kind} mag; {system})")
            meta["transformations"].append("Magnitude display axis reversed; supplied magnitudes and colours unchanged")
            meta["notes"].append("Extinction, distance, calibration and photometric-system corrections were not performed.")
        elif kind == "bpt_diagram":
            _linear_values(options)
            if data["ratio_scale"] != "log10":
                raise ValueError("BPT coordinates must explicitly be supplied log10 ratios")
            x, y = _xy(data)
            _draw_xy(ax, x, y, data, options, points=True)
            boundaries = data.get("boundaries", [])
            if not isinstance(boundaries, list):
                raise ValueError("boundaries must be supplied as a list")
            for i, line in enumerate(boundaries):
                bx = _array(line["x"], "boundary x", ndim=1)
                by = _array(line["y"], "boundary y", ndim=1)
                if bx.shape != by.shape:
                    raise ValueError("Boundary coordinate lengths differ")
                ax.plot(bx, by, linestyle="--", color=_color(options, i + y.shape[1]), label=_text(line, "label"))
            if boundaries:
                ax.legend()
            _decorate(ax, options, xlabel=f"log10({_text(data, 'x_ratio')})", ylabel=f"log10({_text(data, 'y_ratio')})")
            meta["notes"].append("No classification boundary, extinction correction, or source class is inferred; boundaries are supplied overlays.")
        elif kind == "hubble_diagram":
            import astropy.units as u
            x, y = _xy(data)
            if np.any(x[np.isfinite(x)] <= -1):
                raise ValueError("Redshift must be greater than -1")
            definition = _text(data, "distance_kind")
            allowed = {"distance_modulus", "luminosity_distance", "angular_diameter_distance", "comoving_distance"}
            if definition not in allowed:
                raise ValueError("Declare a supported distance_kind: " + ", ".join(sorted(allowed)))
            if definition == "distance_modulus":
                _linear_values(options, axes=("y",))
                if _text(data, "yunit") != "mag":
                    raise ValueError("Distance modulus must be supplied in mag")
            else:
                _unit(data, "yunit", (u.pc,))
                if np.any(y[np.isfinite(y)] < 0):
                    raise ValueError("Physical distance estimates must be nonnegative")
            _draw_xy(ax, x, y, data, options, points=True)
            _decorate(ax, options, xlabel="Redshift z", ylabel=f"{definition.replace('_', ' ')} ({data['yunit']})")
            meta["notes"].append("Distances/moduli are inputs; no cosmology, H0, K correction, extinction or peculiar-velocity correction was assumed.")
        elif kind in {"radial_profile", "rotation_curve"}:
            import astropy.units as u
            x, y = _xy(data)
            _unit(data, "xunit", (u.pc, u.rad))
            if np.any(x[np.isfinite(x)] < 0):
                raise ValueError("Radius must be nonnegative")
            if kind == "radial_profile":
                quantity = _text(data, "profile_quantity")
                yunit = _text(data, "yunit")
                magnitude_profile = data.get("profile_kind") == "magnitude_surface_brightness"
                if magnitude_profile:
                    _linear_values(options, axes=("y",))
                local = {**options, "invert_y": magnitude_profile or options.get("invert_y", False)}
                _draw_xy(ax, x, y, data, local, points=options.get("points", True))
                _decorate(ax, local, xlabel=f"Radius ({data['xunit']})", ylabel=f"{quantity} ({yunit})")
                meta["notes"].append("Radial bins and profile are supplied; no image extraction, PSF correction or area normalization is computed.")
            else:
                _unit(data, "yunit", (u.m / u.s,))
                convention = _text(data, "velocity_convention")
                _draw_xy(ax, x, y, data, options, points=True)
                for i, component in enumerate(data.get("components", [])):
                    cx, cy = _one_y(component)
                    _draw_xy(ax, cx, cy, {**component, "labels": [_text(component, "label")]}, {**options, "colors": [_color(options, i + y.shape[1])]}, points=False)
                if data.get("components"):
                    ax.legend()
                _decorate(ax, options, xlabel=f"Radius ({data['xunit']})", ylabel=f"{convention} ({data['yunit']})")
                meta["notes"].append("Components are separate supplied curves; no deprojection, quadrature sum, dynamics fit or mass estimate is performed.")
        elif kind == "luminosity_function":
            x, y = _one_y(data)
            quantity = _text(data, "x_quantity")
            definition = _text(data, "density_definition")
            _text(data, "xunit"); _text(data, "yunit")
            if "magnitude" in quantity.lower() or data["xunit"] == "mag":
                _linear_values(options, axes=("x",))
            local_data = dict(data)
            if "bin_width" in data:
                widths = _array(data["bin_width"], "bin_width", ndim=1, missing=False)
                if widths.shape != x.shape or np.any(widths <= 0):
                    raise ValueError("bin_width must contain one positive width per bin centre")
                if "xerr" in data:
                    raise ValueError("Use bin_width or xerr, not both")
                local_data["xerr"] = widths / 2
                meta["transformations"].append("Horizontal bin half-width displayed as bin_width/2; no y normalization is performed")
            _draw_xy(ax, x, y, local_data, options, points=True)
            _decorate(ax, options, xlabel=f"{quantity} ({data['xunit']})", ylabel=f"{definition} ({data['yunit']})")
            meta["notes"].append("Values already represent the declared count/density; binning, survey volume and selection/completeness corrections are not inferred.")
        elif kind == "transmission_spectrum":
            import astropy.units as u
            x, y = _xy(data)
            _unit(data, "xunit", (u.m,))
            if np.any(x[np.isfinite(x)] <= 0):
                raise ValueError("Wavelength must be positive")
            quantity = _text(data, "quantity")
            _text(data, "yunit")
            _draw_xy(ax, x, y, data, options, points=True)
            _decorate(ax, options, xlabel=f"Wavelength ({data['xunit']})", ylabel=f"{quantity} ({data['yunit']})")
            meta["notes"].append("Transit depth, radius ratio, squared ratio, ppm and physical radius are distinct supplied quantities; no conversion or atmospheric inference is performed.")
        elif kind == "multi_band_lightcurve":
            import astropy.units as u
            x, y = _xy(data)
            bands = data["bands"]
            if isinstance(bands, str) or len(bands) != y.shape[1] or any(not str(b).strip() for b in bands):
                raise ValueError("bands must explicitly label every y series")
            _unit(data, "xunit", (u.s,)); _text(data, "yunit")
            time_system = _text(data, "time_system")
            quantity = _text(data, "quantity")
            offsets = _array(options.get("offsets", np.zeros(y.shape[1])), "offsets", ndim=1, missing=False)
            if len(offsets) != y.shape[1]:
                raise ValueError("offsets must match the number of bands")
            shown = y + offsets[None, :]
            local = {**options, "labels": [str(b) + (f" ({off:+g})" if off else "") for b, off in zip(bands, offsets)], "invert_y": quantity == "magnitude" or options.get("invert_y", False)}
            if quantity == "magnitude":
                _linear_values(options, axes=("y",))
            _draw_xy(ax, x, shown, data, local, points=options.get("points", True))
            _decorate(ax, local, xlabel=f"Time ({data['xunit']}; {time_system})", ylabel=f"{quantity} ({data['yunit']})")
            meta["transformations"].append({"display_offsets_per_band": offsets.tolist(), "bands": list(bands)})
            meta["notes"].append("Only explicit display offsets are applied. No shared zero-point, colour conversion, extinction or time-system conversion is inferred.")
        elif kind == "spectral_lines":
            import astropy.units as u
            x, y = _xy(data)
            xunit = _unit(data, "xunit", (u.m, u.Hz, u.eV))
            _text(data, "yunit")
            if np.any(x[np.isfinite(x)] <= 0):
                raise ValueError("Spectral coordinate must be positive")
            frame = _text(data, "spectral_frame")
            if frame not in {"rest", "observed"}:
                raise ValueError("spectral_frame must be rest or observed; velocity frames need a separate declared conversion")
            lines = data["lines"]
            if not isinstance(lines, list) or len(lines) > 20:
                raise ValueError("lines must be a supplied list of at most 20 annotations; use a custom view for denser line lists")
            _draw_xy(ax, x, y, data, options)
            for i, line in enumerate(lines):
                position = float(line["position"])
                lineunit = _unit(line, "unit", (u.m, u.Hz, u.eV))
                lineframe = _text(line, "frame")
                if lineframe not in {"rest", "observed"} or not np.isfinite(position) or position <= 0:
                    raise ValueError("Line position/frame must be positive and explicitly rest or observed")
                converted = float((position * lineunit).to_value(xunit, equivalencies=u.spectral()))
                if lineframe != frame:
                    if "redshift" not in data:
                        raise ValueError("An explicit redshift is required to convert a line annotation between rest and observed frames")
                    redshift = float(data["redshift"])
                    if not np.isfinite(redshift) or redshift <= -1:
                        raise ValueError("redshift must be finite and greater than -1")
                    factor = (1 + redshift) if xunit.is_equivalent(u.m) else 1 / (1 + redshift)
                    converted *= factor if lineframe == "rest" else 1 / factor
                label = _text(line, "label")
                ax.axvline(converted, linestyle="--", color=_color(options, i + y.shape[1]), linewidth=max(.5, plt.rcParams["lines.linewidth"]))
                ax.text(converted, 0.98, label, transform=ax.get_xaxis_transform(), rotation=90, va="top", ha="right")
                meta["transformations"].append({"line": label, "supplied_position": position, "supplied_unit": str(lineunit), "supplied_frame": lineframe, "display_position": converted, "display_unit": str(xunit), "display_frame": frame, "redshift": data.get("redshift") if lineframe != frame else None})
            _decorate(ax, options, xlabel=f"Spectral coordinate ({data['xunit']}; {frame})", ylabel=f"Spectral quantity ({data['yunit']})")
            meta["notes"].append("Only declared annotation units/redshift are transformed; spectrum samples are unchanged. No line fit, radial velocity or line identification is inferred.")
        elif kind == "position_velocity":
            import astropy.units as u
            _unit(data, "xunit", (u.rad, u.pc)); _unit(data, "yunit", (u.m / u.s,)); _text(data, "zunit")
            x, y, z = _matrix(data)
            _scale_valid(x, options.get("xscale", "linear"), "position")
            _scale_valid(y, options.get("yscale", "linear"), "velocity")
            cmap = plt.get_cmap(options.get("cmap", "viridis")).with_extremes(bad="#777777")
            image = ax.pcolormesh(x, y, np.ma.masked_invalid(z), shading="nearest", cmap=cmap)
            fig.colorbar(image, ax=ax, label=f"Intensity ({data['zunit']})")
            _decorate(ax, options, xlabel=f"Position ({data['xunit']})", ylabel=f"Velocity ({data['yunit']}; supplied convention)")
            meta["notes"].append("Rows are velocity and columns are position. Map extraction, projection geometry, rest frequency and velocity convention were supplied upstream.")
        elif kind == "angular_power_spectrum":
            x, y = _xy(data)
            if np.any(x[np.isfinite(x)] < 0) or not np.allclose(x[np.isfinite(x)], np.rint(x[np.isfinite(x)])):
                raise ValueError("Multipoles ell must be nonnegative integers")
            convention = _text(data, "convention")
            if convention not in {"Cl", "Dl"}:
                raise ValueError("convention must explicitly be Cl or Dl; transform other conventions before plotting")
            spectrum = _text(data, "spectrum"); _text(data, "yunit")
            _draw_xy(ax, x, y, data, options, points=options.get("points", False))
            _decorate(ax, options, xlabel="Multipole ell", ylabel=f"{spectrum} {convention} ({data['yunit']})")
            meta["notes"].append("No Cl↔Dl conversion, beam correction, masking correction, binning or mode coupling calculation is performed. Negative cross-power remains allowed on a linear axis.")
        elif kind == "sensitivity_curve":
            import astropy.units as u
            x, y = _xy(data)
            _unit(data, "xunit", (u.Hz,))
            yunit = _unit(data, "yunit")
            signal = _unit(data, "signal_unit")
            quantity = _text(data, "quantity")
            expected = {"ASD": signal / u.Hz**0.5, "PSD": signal**2 / u.Hz, "amplitude": signal,
                        "characteristic_strain": u.dimensionless_unscaled, "energy_density": u.dimensionless_unscaled}
            if quantity not in expected:
                raise ValueError("quantity must be ASD, PSD, amplitude, characteristic_strain or energy_density")
            if not yunit.is_equivalent(expected[quantity]):
                raise ValueError("yunit is inconsistent with the declared sensitivity quantity and signal_unit")
            if np.any(x[np.isfinite(x)] <= 0) or np.any(y[np.isfinite(y)] <= 0):
                raise ValueError("Sensitivity frequency and supplied curve must be positive; no invalid samples are dropped")
            local = {"xscale": "log", "yscale": "log", **options}
            _draw_xy(ax, x, y, data, local)
            _decorate(ax, local, xlabel=f"Frequency ({data['xunit']})", ylabel=f"{quantity} ({data['yunit']})")
            meta["notes"].append("No PSD↔ASD, strain or energy-density conversion is performed; curves of different quantities cannot share this recipe implicitly.")
        elif kind == "evolution_tracks":
            tracks = data["tracks"]
            if not isinstance(tracks, list) or not tracks:
                raise ValueError("tracks must contain named supplied x/y arrays")
            xq = _text(data, "x_quantity"); yq = _text(data, "y_quantity")
            _text(data, "xunit"); _text(data, "yunit")
            for i, track in enumerate(tracks):
                x, y = _one_y(track)
                _draw_xy(ax, x, y, {**track, "labels": [_text(track, "label")]}, {**options, "colors": [_color(options, i)]})
            ax.legend()
            _decorate(ax, options, xlabel=f"{xq} ({data['xunit']})", ylabel=f"{yq} ({data['yunit']})")
            if options.get("invert_x", False):
                ax.set_xlim(sorted(ax.get_xlim(), reverse=True))
            meta["notes"].append("Tracks may have different sampling and length. No interpolation, cooling, stellar evolution, age, mass or cosmology calculation is performed.")
        elif kind == "abundance_pattern":
            _linear_values(options)
            x, y = _xy(data)
            if not np.allclose(x, np.rint(x)) or np.any((x < 1) | (x > 118)) or len(np.unique(x)) != len(x):
                raise ValueError("Atomic numbers must be unique integers within 1–118")
            elements = data["elements"]
            if isinstance(elements, str) or len(elements) != len(x):
                raise ValueError("elements must label every atomic number")
            definition = _text(data, "abundance_definition"); reference = _text(data, "reference")
            _draw_xy(ax, x, y, data, options, points=True)
            _decorate(ax, options, xlabel="Element (atomic number)", ylabel=f"{definition} (dex; {reference})")
            ax.set_xticks(x, labels=[str(element) for element in elements])
            meta["notes"].append("Logarithmic abundance values and reference scale are supplied; no ionization, LTE/NLTE or solar-scale correction is inferred.")
        assert fig is not None
        return fig, meta
    except Exception:
        if fig is not None:
            plt.close(fig)
        raise
