"""Results Delay detector — time from primary completion to results posting.

Severity tiers:
- <= 12 months: compliant (no flag)
- 12-24 months: severity 0.3
- 24-36 months: severity 0.6
- > 36 months: scaled up to 1.0
- No results on completed trial: severity based on months since completion
"""
import pandas as pd

from pipeline.detectors.base import BaseDetector, DetectorResult

_NOW = pd.Timestamp("2026-02-19")


class ResultsDelayDetector(BaseDetector):
    name = "results_delay"
    description = "Excessive delay between trial completion and results posting"
    aact_tables: list[str] = []

    def detect(
        self, master_df: pd.DataFrame, raw_tables: dict | None = None
    ) -> DetectorResult:
        nct_ids: list[str] = []
        flags: list[bool] = []
        severities: list[float] = []
        details: list[str] = []

        for _, row in master_df.iterrows():
            nct = row["nct_id"]
            nct_ids.append(nct)

            pcd = pd.to_datetime(row.get("primary_completion_date"), errors="coerce")
            results_date = pd.to_datetime(
                row.get("results_first_posted_date"), errors="coerce"
            )
            has_results = bool(row.get("has_results", False))
            status = str(row.get("overall_status", "") or "").upper()

            if pd.isna(pcd):
                flags.append(False)
                severities.append(0.0)
                details.append("")
                continue

            if has_results and pd.notna(results_date):
                # Compute actual delay
                delay_months = (results_date - pcd).days / 30.44
                if delay_months <= 12.0:
                    flags.append(False)
                    severities.append(0.0)
                    details.append("")
                elif delay_months <= 24.0:
                    flags.append(True)
                    severities.append(0.3)
                    details.append(f"Results delay: {delay_months:.0f} months")
                elif delay_months <= 36.0:
                    flags.append(True)
                    severities.append(0.6)
                    details.append(f"Results delay: {delay_months:.0f} months")
                else:
                    sev = min(0.6 + (delay_months - 36.0) / 48.0, 1.0)
                    flags.append(True)
                    severities.append(round(sev, 4))
                    details.append(f"Results delay: {delay_months:.0f} months")
            elif not has_results and status in (
                "COMPLETED", "TERMINATED",
                "ACTIVE, NOT RECRUITING", "ACTIVE_NOT_RECRUITING",
            ):
                # No results at all — compute months since completion
                months_since = (_NOW - pcd).days / 30.44
                if months_since > 12.0:
                    sev = min(months_since / 60.0, 1.0)  # scale over 5 years
                    flags.append(True)
                    severities.append(round(sev, 4))
                    details.append(
                        f"No results {months_since:.0f}m after completion"
                    )
                else:
                    flags.append(False)
                    severities.append(0.0)
                    details.append("")
            else:
                flags.append(False)
                severities.append(0.0)
                details.append("")

        return DetectorResult(
            nct_ids=nct_ids,
            flaw_detected=flags,
            severity=severities,
            detail=details,
        )
