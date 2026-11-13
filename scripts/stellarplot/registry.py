"""Modular astronomy registry; the validated stellar API remains compatible."""
from .recipes import RECIPES as STELLAR_RECIPES, render as render_stellar


def registries():
    from . import sky, astro
    return [(STELLAR_RECIPES, render_stellar), (sky.REGISTRY, sky.render), (astro.REGISTRY, astro.render)]


def catalogue():
    result = {}
    for registry, _ in registries():
        for key, description in registry.items():
            if key in result:
                raise RuntimeError("Duplicate astronomy recipe: " + key)
            result[key] = description
    return result


def render(kind, data, options=None):
    if not isinstance(data, dict) or (options is not None and not isinstance(options, dict)):
        raise ValueError("data and options must be mappings")
    for registry, renderer in registries():
        if kind in registry:
            return renderer(kind, data, options)
    raise ValueError(f"Unknown recipe {kind!r}; use the catalogue or the custom figure export API")
