"""Ghost Protocols detector — trials that vanish from the evidence record.

Type A: NOT_YET_RECRUITING / WITHDRAWN, registered >= 3 years ago.
Type B: UNKNOWN / SUSPENDED, no update >= 2 years.
Type C: COMPLETED / TERMINATED, no results >= 13 months after primary_completion_date.
"""
import pandas as pd

from pipeline.detectors.base import BaseDetector, DetectorResult

_NOW = pd.Timestamp("2026-02-19")


class GhostProtocolsDetector(BaseDetector):
    name = "ghost_protocols"
    description = "Trials that vanish from the evidence record without results or updates"
    aact_tables: list[str] = []

    def detect(
        self, master_df: pd.DataFrame, raw_tables: dict | None = None
    ) -> DetectorResult:
        nct_ids: list[str] = []
        flags: list[bool] = []
        severities: list[float] = []
        details: list[str] = []

        for _, row in master_df.iterrows():
            nct_ids.append(row["nct_id"])
            status = str(row.get("overall_status", "") or "").upper()
            start_date = pd.to_datetime(row.get("start_date"), errors="coerce")
            last_update = pd.to_datetime(row.get("last_update_posted_date"), errors="coerce")
            pcd = pd.to_datetime(row.get("primary_completion_date"), errors="coerce")
            has_results = bool(row.get("has_results", False))

            flagged = False
            sev = 0.0
            det = ""

            # Type A: zombie registrations
            if status in ("NOT YET RECRUITING", "NOT_YET_RECRUITING", "WITHDRAWN"):
                if pd.notna(start_date):
                    years_since = (_NOW - start_date).days / 365.25
                    if years_since >= 3.0:
                        flagged = True
                        sev = min(years_since / 5.0, 1.0)
                        det = f"Type A: {status}, registered {years_since:.1f}y ago"

            # Type B: silent trials
            if not flagged and status in ("UNKNOWN STATUS", "UNKNOWN", "SUSPENDED"):
                if pd.notna(last_update):
                    years_silent = (_NOW - last_update).days / 365.25
                    if years_silent >= 2.0:
                        flagged = True
                        sev = min(years_silent / 5.0, 1.0)
                        det = f"Type B: {status}, silent {years_silent:.1f}y"

            # Type C: results-free completed trials
            if not flagged and status in ("COMPLETED", "TERMINATED"):
                if not has_results and pd.notna(pcd):
                    months_overdue = (_NOW - pcd).days / 30.44
                    if months_overdue >= 13.0:
                        years_overdue = months_overdue / 12.0
                        flagged = True
                        sev = min(years_overdue / 5.0, 1.0)
                        det = f"Type C: {status}, no results {months_overdue:.0f}m after completion"

            flags.append(flagged)
            severities.append(round(sev, 4))
            details.append(det)

        return DetectorResult(
            nct_ids=nct_ids,
            flaw_detected=flags,
            severity=severities,
            detail=details,
        )
