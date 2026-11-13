"""Escaped LaTeX tables plus machine-readable data, with explicit uncertainty."""
from __future__ import annotations
import csv
import io
import math
from pathlib import Path

from .core import write_json, profile, jsonable


def latex_escape(value):
    conversion = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                  "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(conversion.get(c, c) for c in str(value))


def export_table(columns, rows, base, *, caption="", label="tab:results", journal="general",
                 units=None, notes="", overwrite=False, provenance=None):
    from _common import checked_output_file, atomic_write_bytes
    import importlib.metadata
    profile(journal)
    if not isinstance(columns, list) or not columns or len(set(columns)) != len(columns):
        raise ValueError("Table columns must be nonempty unique column names")
    if not all(isinstance(x, str) for x in columns):
        raise ValueError("Table column names must be strings")
    if not isinstance(rows, list) or not rows:
        raise ValueError("A table needs at least one supplied data row")
    if isinstance(rows[0], dict):
        if any(set(row) != set(columns) for row in rows):
            raise ValueError("Every table row must match the declared columns exactly")
        values = [[row[col] for col in columns] for row in rows]
    else:
        values = rows
    if any(not isinstance(row, (list, tuple)) or len(row) != len(columns) for row in values):
        raise ValueError("Table rows must match the declared column count")
    # Use one explicit missing-value encoding across all formats; infinity is an error.
    values = jsonable(values)
    if any(isinstance(cell, (list, dict)) for row in values for cell in row):
        raise ValueError("Table cells must be scalar values; represent arrays in separate machine-readable tables")
    if not label or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:-_" for c in label):
        raise ValueError("Table label contains unsafe LaTeX characters")
    units = units or {}
    if any(key not in columns for key in units):
        raise ValueError("Unit supplied for an unknown column")
    base = Path(base).absolute()
    base.parent.mkdir(parents=True, exist_ok=True)
    destinations = [base.with_name(base.name + x) for x in (".tex", ".csv", ".table.json")]
    for p in destinations:
        checked_output_file(p, force=overwrite)
    alignment = "l" * len(columns)
    headers = [latex_escape(c) + (f" ({latex_escape(units[c])})" if c in units else "") for c in columns]
    escaped = [[latex_escape("" if v is None else v) for v in row] for row in values]
    if journal == "aas":
        tex = [f"\\begin{{deluxetable}}{{{alignment}}}",
               r"\tablecaption{" + latex_escape(caption) + r"\label{" + label + "}}",
               "\\tablehead{" + " & ".join(r"\colhead{" + h + "}" for h in headers) + "}", "\\startdata"]
        tex += [" & ".join(row) + r" \\" for row in escaped]
        tex += ["\\enddata"]
        if notes:
            tex += [r"\tablecomments{" + latex_escape(notes) + "}"]
        tex += ["\\end{deluxetable}"]
    else:
        # A&A and MNRAS both accept tabular; their native classes supply rules.
        if journal == "aa":
            top, mid, bottom = r"\hline\hline", r"\hline", r"\hline"
        elif journal == "mnras":
            top, mid, bottom = r"\hline", r"\hline", r"\hline"
        else:
            top, mid, bottom = r"\toprule", r"\midrule", r"\bottomrule"
        tex = [r"\begin{table}", r"\centering", r"\caption{" + latex_escape(caption) + "}",
               r"\label{" + label + "}", r"\begin{tabular}{" + alignment + "}", top,
               " & ".join(headers) + r" \\", mid]
        tex += [" & ".join(row) + r" \\" for row in escaped]
        tex += [bottom, r"\end{tabular}"]
        if notes:
            tex += [r"\par\smallskip\footnotesize " + latex_escape(notes)]
        tex += [r"\end{table}"]
    atomic_write_bytes(destinations[0], ("\n".join(tex) + "\n").encode(), force=overwrite)
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(columns)
    writer.writerows(values)
    atomic_write_bytes(destinations[1], stream.getvalue().encode(), force=overwrite)
    write_json(destinations[2], {"columns": columns, "rows": values, "units": units,
        "caption": caption, "notes": notes, "journal": journal, "label": label,
        "provenance": provenance or {}, "versions": {"tool": __import__('stellarplot').TOOL_NAME + " " + __import__('stellarplot').__version__, "python": __import__('platform').python_version()},
        "compiled": False, "notice": "Insert and compile in the journal's current native class; source export is not template acceptance."}, overwrite=overwrite)
    return {"files": [str(p) for p in destinations], "compiled": False}


def render_table(columns, rows, *, units=None):
    """Small display table; full scientific tables remain editable native LaTeX/CSV."""
    import matplotlib.pyplot as plt
    import textwrap
    if not rows or len(rows) > 40:
        raise ValueError("A single-page preview requires 1–40 rows; use native long-table markup for longer data")
    if any(not isinstance(c, str) for c in columns):
        raise ValueError("Table column names must be strings")
    values = [[r[c] for c in columns] for r in rows] if isinstance(rows[0], dict) else rows
    if any(len(row) != len(columns) for row in values):
        raise ValueError("Table row width does not match columns")
    values = jsonable(values)
    display = [[textwrap.fill("" if x is None else str(x), width=24) for x in row] for row in values]
    headers = [textwrap.fill(c + (f" ({units[c]})" if units and c in units else ""), width=24) for c in columns]
    fig, ax = plt.subplots(figsize=(7.1, max(1.0, 0.30 * (len(rows) + 2))))
    ax.axis("off")
    table = ax.table(cellText=display, colLabels=headers, loc="center", cellLoc="left", edges="horizontal")
    table.auto_set_font_size(False)
    table.set_fontsize(plt.rcParams["font.size"])
    for (row, column), cell in table.get_celld().items():
        cell.visible_edges = "TB" if row == 0 else ("B" if row == len(rows) else "")
    table.scale(1, 1.5)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
    return fig

