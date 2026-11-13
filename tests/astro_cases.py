"""Synthetic fixtures for the new general-astronomy recipes, not research data."""
from __future__ import annotations
import numpy as np


def cases():
    result = {}
    def add(kind, data, **options):
        options.setdefault("title", f"Synthetic astronomy test: {kind}")
        result[kind] = (data, options)

    x = np.linspace(.1, 2., 25)
    err = np.full(len(x), .05)
    add("color_magnitude", {"x": x, "y": 2 + 3*x, "color_label": "g − r", "magnitude_label": "M_g", "magnitude_system": "AB", "magnitude_kind": "absolute", "yerr": err})
    add("bpt_diagram", {"x": x-1.5, "y": .3*np.sin(3*x), "x_ratio": "[N II]6584 / Halpha", "y_ratio": "[O III]5007 / Hbeta", "ratio_scale": "log10", "boundaries": [{"x": x-1.5, "y": -.2*x, "label": "Supplied synthetic boundary"}]})
    add("hubble_diagram", {"x": x, "y": 35+3*x, "distance_kind": "distance_modulus", "yunit": "mag", "yerr": err})
    add("radial_profile", {"x": x, "y": np.exp(-x), "xunit": "arcsec", "yunit": "Jy / arcsec2", "profile_quantity": "Surface brightness", "yerr": err/10})
    add("luminosity_function", {"x": x, "y": np.exp(-x), "x_quantity": "Synthetic luminosity", "xunit": "solLum", "yunit": "1 / (Mpc3 dex)", "density_definition": "Supplied density per volume per dex", "bin_width": np.full(len(x), .05), "yerr": err/10})
    add("transmission_spectrum", {"x": x, "y": 10000+100*np.sin(3*x), "xunit": "um", "yunit": "ppm", "quantity": "Transit depth", "yerr": np.full(len(x), 20.)})
    add("multi_band_lightcurve", {"x": x, "y": np.column_stack([15+.1*np.sin(3*x), 16+.1*np.cos(3*x)]), "bands": ["Test g", "Test r"], "quantity": "magnitude", "xunit": "d", "yunit": "mag", "time_system": "Synthetic elapsed test time; not a time standard", "yerr": np.full((len(x),2), .03)}, offsets=[0., -.5])
    wavelength = np.linspace(600., 750., 150)
    add("spectral_lines", {"x": wavelength, "y": 1+.2*np.sin(wavelength/15), "xunit": "nm", "yunit": "Jy", "spectral_frame": "observed", "redshift": .05, "lines": [{"position": 656.28, "unit": "nm", "frame": "rest", "label": "Halpha (test)"}]})
    position = np.linspace(-2,2,30); velocity = np.linspace(-50,50,24)
    px, vy = np.meshgrid(position, velocity)
    add("position_velocity", {"x": position, "y": velocity, "z": np.exp(-px*px-(vy/25)**2), "xunit": "arcsec", "yunit": "km/s", "zunit": "Jy/beam"})
    ell = np.arange(2,80)
    add("angular_power_spectrum", {"x": ell, "y": 1/(1+ell/10)**2, "convention": "Cl", "spectrum": "Synthetic TT", "yunit": "uK2"}, yscale="log")
    frequency = np.geomspace(10,1000,40)
    add("sensitivity_curve", {"x": frequency, "y": 1e-23*(1+(frequency/150)**2+(50/frequency)**2), "xunit": "Hz", "yunit": "1 / Hz(1/2)", "signal_unit": "1", "quantity": "ASD"})
    add("evolution_tracks", {"tracks": [{"x": x, "y": np.exp(-x), "label": "Synthetic track A"}, {"x": x[::2], "y": 1.5*np.exp(-x[::2]), "label": "Synthetic track B"}], "x_quantity": "Supplied age", "y_quantity": "Supplied luminosity", "xunit": "Gyr", "yunit": "solLum"})
    add("abundance_pattern", {"x": [6,8,12,14,20,26], "y": [.1,.2,.15,.05,.0,-.05], "elements": ["C","O","Mg","Si","Ca","Fe"], "abundance_definition": "[X/Fe]", "reference": "Declared synthetic reference", "yerr": [.03]*6}, ylabel="[X/Fe] (dex; synthetic reference)")
    add("rotation_curve", {"x": x, "y": 100*(1-np.exp(-x)), "xunit": "kpc", "yunit": "km/s", "velocity_convention": "Supplied deprojected rotation speed", "yerr": np.full(len(x), 3.), "components": [{"x": x, "y": 70*(1-np.exp(-x)), "label": "Supplied synthetic component"}]})
    return result
