"""Synthetic fixtures for sky/WCS exports, not astronomical findings."""
from __future__ import annotations
import copy
import numpy as np


def cases():
    x, y = np.meshgrid(np.arange(48), np.arange(40))
    image = np.exp(-((x-24)**2+(y-20)**2)/90) + .02
    image[2:5, 3:7] = np.nan
    header = {"NAXIS": 2, "NAXIS1": 48, "NAXIS2": 40, "CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN",
              "CUNIT1": "deg", "CUNIT2": "deg", "CRVAL1": 150., "CRVAL2": 2., "CRPIX1": 24.5,
              "CRPIX2": 20.5, "CDELT1": -.01, "CDELT2": .01, "RADESYS": "ICRS"}
    base = {"image": image, "wcs_header": header, "unit": "synthetic unit"}
    catalogue = {"lon": [149.95, 150.0, 150.08], "lat": [1.95, 2.0, 2.04],
                 "frame": "icrs", "lon_unit": "deg", "lat_unit": "deg"}
    lon, lat = np.linspace(149.5, 150.5, 30), np.linspace(1.5, 2.5, 25)
    gx, gy = np.meshgrid(lon, lat)
    probability = np.exp(-((gx-150)**2+(gy-2)**2)/.06)
    probability /= probability.sum()
    output = {
        "sky_map": ({"lon": [0, 30, 90, 150, 200, 270, 359], "lat": [0, 20, -20, 30, -45, 50, 5],
                     "frame": "icrs", "lon_unit": "deg", "lat_unit": "deg", "values": [1, 2, 3, 4, 5, 6, 7]},
                    {"title": "Synthetic sky catalogue", "zlabel": "Synthetic value"}),
        "wcs_image": (base, {"title": "Synthetic celestial WCS image"}),
        "sky_catalog": ({**base, "catalog": catalogue}, {"title": "Synthetic catalogue overlay"}),
        "localization_map": ({"lon": lon, "lat": lat, "frame": "icrs", "lon_unit": "deg", "lat_unit": "deg",
                              "probability": probability, "probability_type": "per_pixel"},
                             {"title": "Synthetic localization grid"}),
        "image_montage": ({"images": [image, image*.7, image*.4], "titles": ["Synthetic band A", "Synthetic band B", "Synthetic band C"],
                           "units": ["synthetic unit"]*3, "alignment": "Synthetic arrays share a test pixel grid; no real alignment inferred"},
                          {"title": "Synthetic multi-band panels", "shared_scale": True}),
    }
    return copy.deepcopy(output)
