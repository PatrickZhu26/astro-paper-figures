"""Bounded, explicit scientific-data loading; never infer a physical model."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any, Mapping

MAX_INPUT_BYTES = 200 * 1024 * 1024
SUPPORTED_SUFFIXES = {".json", ".csv", ".tsv", ".ecsv"}


def _read(path: str | Path) -> tuple[Path, bytes, dict[str, Any]]:
    source = Path(path).expanduser()
    if source.is_symlink() or not source.is_file():
        raise ValueError("Input must be a regular file, not a final-path symlink")
    if source.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError("Supported inputs: JSON, CSV, TSV, ECSV; no pickle or object archives")
    if source.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the 200 MiB file-size limit")
    with source.open("rb") as handle:
        payload = handle.read(MAX_INPUT_BYTES + 1)
    if len(payload) > MAX_INPUT_BYTES:
        raise ValueError("Input exceeds the 200 MiB file-size limit")
    resolved = source.resolve()
    return resolved, payload, {
        "path": str(resolved), "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload), "format": source.suffix.lower().lstrip("."),
    }


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("JSON contains a non-finite number; use null for missing values")
    return value


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _no_constant(text: str) -> None:
    raise ValueError(f"Non-standard JSON constant {text}; use null for missing values")


def _metadata_plain(value: Any) -> Any:
    """Keep source metadata JSON-safe without changing scientific data arrays."""
    if isinstance(value, Mapping):
        return {str(k): _metadata_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_metadata_plain(v) for v in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "tolist"):
        return _metadata_plain(value.tolist())
    return str(value)


def load_data(path: str | Path) -> dict[str, Any]:
    """Load a root JSON object or named table columns plus reserved ``_source``.

    CSV/TSV missing numeric cells remain NaN; ECSV masks become None. Recipes
    decide which missing values are displayable. Units and time scales in plain
    tables are not inferred. No source file is modified.
    """
    source, payload, provenance = _read(path)
    text = payload.decode("utf-8-sig")
    if source.suffix.lower() == ".json":
        data = json.loads(
            text, object_pairs_hook=_pairs, parse_float=_finite_float,
            parse_constant=_no_constant,
        )
        if not isinstance(data, dict):
            raise ValueError("JSON input must contain one root object")
        if "_source" in data:
            raise ValueError("_source is reserved for loader-generated provenance")
        provenance["keys"] = list(data)
    elif source.suffix.lower() == ".ecsv":
        from astropy.table import Table

        table = Table.read(text.splitlines(), format="ascii.ecsv")
        if "_source" in table.colnames:
            raise ValueError("_source is a reserved column name")
        data = {name: table[name].tolist() for name in table.colnames}
        provenance.update({
            "columns": table.colnames, "rows": len(table),
            "units": {name: str(table[name].unit) for name in table.colnames if table[name].unit is not None},
            "table_meta": _metadata_plain(table.meta),
        })
    else:
        import pandas as pd

        delimiter = "\t" if source.suffix.lower() == ".tsv" else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError("Table is empty") from exc
        if not header or any(not name.strip() for name in header):
            raise ValueError("Every table column needs a nonempty name")
        if len(set(header)) != len(header):
            raise ValueError("Duplicate table column names are not permitted")
        if "_source" in header:
            raise ValueError("_source is a reserved column name")
        # Reject ragged records rather than allowing a parser to infer an index.
        rows = 0
        for row in reader:
            if not row:  # CSV blank lines carry no observation.
                continue
            rows += 1
            if len(row) != len(header):
                raise ValueError(f"Table record {rows + 1} has {len(row)} fields; expected {len(header)}")
        frame = pd.read_csv(io.StringIO(text), sep=delimiter, header=0)
        data = {name: frame[name].tolist() for name in frame.columns}
        provenance.update({"columns": list(frame.columns), "rows": len(frame), "units": {}, "time_system": "unspecified"})
    data["_source"] = provenance
    return data


def apply_mapping(data: Mapping[str, Any], mapping: Mapping[str, str]) -> dict[str, Any]:
    """Alias ``target: source`` fields; do not drop originals or change values."""
    result = dict(data)
    for target, source in mapping.items():
        if not target or target.startswith("_"):
            raise ValueError("Mapped target names must be nonempty and cannot start with _")
        if source not in data or source.startswith("_"):
            raise ValueError(f"Unknown or reserved source field: {source}")
        if target in data and target != source:
            raise ValueError(f"Mapping would replace an existing field: {target}")
        result[target] = data[source]
    provenance = dict(data.get("_source", {}))
    provenance["column_mapping"] = dict(mapping)
    result["_source"] = provenance
    return result


def load_stellar_rv(
    path: str | Path, *, star: str | int, candidate: str | None = None,
    model_column: str | None = None,
) -> dict[str, Any]:
    """Explicitly adapt known workbench RV exports for one star and one model.

    Output: x/t, observed, model, sigma (km/s); time values are copied unchanged.
    The source's time coordinate does not establish its TT/TDB/UTC convention.
    """
    data = load_data(path)
    if "star" not in data:
        raise ValueError("RV adapter requires an explicit star column")
    time_columns = [key for key in ("bjd", "time_day") if key in data]
    sigma_columns = [key for key in ("sigma_km_s", "quoted_sigma_km_s") if key in data]
    if len(time_columns) != 1 or len(sigma_columns) != 1 or "observed_km_s" not in data:
        raise ValueError("RV export must have one supported time, quoted sigma, and observed_km_s column")
    model_columns = [key for key in ("predicted_km_s", "fitted_km_s") if key in data]
    if model_column is None:
        if len(model_columns) != 1:
            raise ValueError("Specify the model column when there is not exactly one supported model field")
        model_column = model_columns[0]
    if model_column not in data or model_column.startswith("_"):
        raise ValueError("Selected model column does not exist")
    candidates = {str(v) for v in data.get("candidate", [])}
    if candidate is None and len(candidates) > 1:
        raise ValueError("Multiple model candidates are present; select one explicitly")
    if candidate is not None and (not candidates or candidate not in candidates):
        raise ValueError("Selected model candidate does not exist")
    selected = [
        i for i, value in enumerate(data["star"])
        if str(value) == str(star)
        and (candidate is None or str(data["candidate"][i]) == candidate)
    ]
    if not selected:
        raise ValueError("Selected star/candidate has no rows")
    fields = {"x": time_columns[0], "observed": "observed_km_s", "model": model_column, "sigma": sigma_columns[0]}
    result = {target: [data[source][i] for i in selected] for target, source in fields.items()}
    result["t"] = result["x"]
    provenance = dict(data["_source"])
    provenance.update({
        "adapter": "stellar_workbench_rv", "selected_star": str(star),
        "selected_candidate": candidate, "selected_rows": selected,
        "column_mapping": fields, "value_units": "km/s", "time_unit": "day",
        "time_column": time_columns[0], "time_scale": "not verified by adapter",
    })
    result["_source"] = provenance
    return result


def inspect_project_results(root: str | Path, *, limit: int = 200) -> list[dict[str, Any]]:
    """List bounded, shallow result tables; never guess a recipe from a name.

    ``root`` is one explicitly chosen model-version directory, not the entire
    workspace. Scan only results/ and validation/ and their direct children.
    """
    if not isinstance(limit, int) or limit <= 0 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    result: list[dict[str, Any]] = []
    project = Path(root).expanduser().resolve()
    directories: list[Path] = []
    for name in ("results", "validation"):
        parent = project / name
        if parent.is_dir() and not parent.is_symlink():
            directories.append(parent)
            directories.extend(p for p in sorted(parent.iterdir()) if p.is_dir() and not p.is_symlink())
    for directory in directories:
        for path in sorted(directory.iterdir()):
            if path.is_file() and not path.is_symlink() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                size = path.stat().st_size
                if size <= MAX_INPUT_BYTES:
                    result.append({"path": str(path), "bytes": size, "format": path.suffix.lower().lstrip(".")})
                    if len(result) == limit:
                        return result
    return result
