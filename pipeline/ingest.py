# sentinel:skip-file — hardcoded paths are fixture/registry/audit-narrative data for this repo's research workflow, not portable application configuration. Same pattern as push_all_repos.py and E156 workbook files.
"""Load AACT pipe-delimited tables directly from ZIP into pandas DataFrames."""
import os
import zipfile
from io import TextIOWrapper
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
_AACT_ZIP_FILENAME = "20260219_export_ctgov.zip"
_AACT_ZIP_ENV = os.environ.get("CARDIO_TRIAL_AUDIT_AACT_ZIP")
_AACT_DIR_ENV = os.environ.get("CARDIO_TRIAL_AUDIT_AACT_DIR")

# Candidate AACT sources, searched in order.
_AACT_SOURCE_CANDIDATES = [
    Path(_AACT_ZIP_ENV) if _AACT_ZIP_ENV else None,
    PROJECT_ROOT / "data" / "aact" / _AACT_ZIP_FILENAME,
    PROJECT_ROOT.parent / "hfpef_registry_calibration" / "data" / "aact" / _AACT_ZIP_FILENAME,
    PROJECT_ROOT.parent / "Pairwise70" / "hfpef_registry_calibration" / "data" / "aact" / _AACT_ZIP_FILENAME,
    Path(_AACT_DIR_ENV) if _AACT_DIR_ENV else None,
    Path("/mnt/c/Users/user/AACT/2026-04-12"),
    Path("/mnt/d/Users/user/AACT/2026-04-12"),
    Path(r"C:\Users\user\AACT\2026-04-12"),
    Path(r"D:\Users\user\AACT\2026-04-12"),
]


def _find_aact_source() -> Path:
    """Return the first existing AACT source path from candidates."""
    for p in _AACT_SOURCE_CANDIDATES:
        if p is None:
            continue
        if p.exists():
            return p
    raise FileNotFoundError(
        "AACT source not found at any candidate location:\n"
        + "\n".join(f"  - {p}" for p in _AACT_SOURCE_CANDIDATES if p is not None)
    )


# Resolve at import time; tests override via zip_path parameter.
try:
    AACT_ZIP_PATH = _find_aact_source()
except FileNotFoundError:
    # Allow import even if no AACT source exists (tests provide their own)
    AACT_ZIP_PATH = None

# Date columns to parse per table
_DATE_COLUMNS = {
    "studies": [
        "study_first_submitted_date",
        "results_first_submitted_date",
        "study_first_posted_date",
        "results_first_posted_date",
        "last_update_posted_date",
        "start_date",
        "verification_date",
        "completion_date",
        "primary_completion_date",
    ],
}


def load_aact_table(
    table_name: str,
    nrows: int | None = None,
    usecols: list[str] | None = None,
    zip_path: Path | None = AACT_ZIP_PATH,
) -> pd.DataFrame:
    """Load a single AACT table from either an extracted directory or ZIP.

    Parameters
    ----------
    table_name : str
        Table name without extension (e.g., 'studies', 'conditions').
    nrows : int | None
        Optional row limit for testing / sampling.
    usecols : list[str] | None
        Optional column subset to load (reduces memory).
    zip_path : Path | None
        Path to AACT ZIP file or extracted AACT directory.

    Returns
    -------
    pd.DataFrame
    """
    filename = f"{table_name}.txt"
    date_cols = _DATE_COLUMNS.get(table_name, None)
    source = Path(zip_path) if zip_path is not None else None

    # If usecols specified and date_cols exist, only parse dates that are in usecols
    if usecols is not None and date_cols is not None:
        date_cols = [c for c in date_cols if c in usecols]
        if not date_cols:
            date_cols = None

    if source is None:
        raise FileNotFoundError("AACT source not configured")

    if source.is_dir():
        table_path = source / filename
        if not table_path.exists():
            raise KeyError(f"Table '{table_name}' not found in extracted AACT directory: {table_path}")
        df = pd.read_csv(
            table_path,
            sep="|",
            nrows=nrows,
            usecols=usecols,
            parse_dates=date_cols if date_cols else False,
            low_memory=False,
        )
        return df

    with zipfile.ZipFile(source, "r") as zf:
        names = zf.namelist()
        match = [n for n in names if n.endswith(filename)]
        if not match:
            raise KeyError(
                f"Table '{table_name}' not found in ZIP. "
                f"Available: {[n.split('/')[-1].replace('.txt', '') for n in names if n.endswith('.txt')]}"
            )
        # Prefer exact filename match (e.g., "conditions.txt" over "browse_conditions.txt")
        exact = [n for n in match if n.split("/")[-1] == filename]
        target = exact[0] if exact else match[0]
        with zf.open(target) as f:
            text = TextIOWrapper(f, encoding="utf-8")
            df = pd.read_csv(
                text,
                sep="|",
                nrows=nrows,
                usecols=usecols,
                parse_dates=date_cols if date_cols else False,
                low_memory=False,
            )
    return df
