"""Sponsor Concentration detector — market dominance and industry influence.

Flags trials based on:
- Industry sponsorship (0.2 base)
- Sponsor with >10% share of year's trials (+0.3)
- High HHI year (>0.15) (+0.1)
Threshold: flag if total >= 0.3
"""
import pandas as pd

from pipeline.detectors.base import BaseDetector, DetectorResult


def _compute_hhi(sponsor_counts: pd.Series) -> float:
    """Herfindahl-Hirschman Index from a Series of trial counts per sponsor."""
    total = sponsor_counts.sum()
    if total == 0:
        return 0.0
    shares = sponsor_counts / total
    return float((shares ** 2).sum())


class SponsorConcentrationDetector(BaseDetector):
    name = "sponsor_concentration"
    description = "Sponsor market dominance and industry influence on trial landscape"
    aact_tables: list[str] = []

    def detect(
        self, master_df: pd.DataFrame, raw_tables: dict | None = None
    ) -> DetectorResult:
        nct_ids: list[str] = []
        flags: list[bool] = []
        severities: list[float] = []
        details: list[str] = []

        # Pre-compute per-year statistics
        year_stats = self._compute_year_stats(master_df)

        for _, row in master_df.iterrows():
            nct = row["nct_id"]
            nct_ids.append(nct)
            score = 0.0
            issues: list[str] = []

            sponsor_class = str(row.get("lead_sponsor_class", "") or "").upper()
            sponsor_name = str(row.get("lead_sponsor_name", "") or "")
            year = row.get("start_year")

            # 1. Industry sponsorship base
            if sponsor_class == "INDUSTRY":
                score += 0.2
                issues.append("Industry-sponsored")

            # 2. Per-year concentration checks
            if year is not None and not pd.isna(year):
                year = int(year)
                stats = year_stats.get(year, {})

                # Sponsor share > 10%
                sponsor_share = stats.get("shares", {}).get(sponsor_name, 0.0)
                if sponsor_share > 0.10:
                    score += 0.3
                    issues.append(
                        f"Sponsor holds {sponsor_share:.0%} of {year} trials"
                    )

                # High HHI year
                hhi = stats.get("hhi", 0.0)
                if hhi > 0.15:
                    score += 0.1
                    issues.append(f"High concentration year (HHI={hhi:.3f})")

            flagged = score >= 0.3
            flags.append(flagged)
            severities.append(round(min(score, 1.0), 4))
            details.append("; ".join(issues) if flagged else "")

        return DetectorResult(
            nct_ids=nct_ids,
            flaw_detected=flags,
            severity=severities,
            detail=details,
        )

    def _compute_year_stats(
        self, master_df: pd.DataFrame
    ) -> dict[int, dict]:
        """Compute HHI and sponsor shares per start_year."""
        stats: dict[int, dict] = {}
        if "start_year" not in master_df.columns or "lead_sponsor_name" not in master_df.columns:
            return stats

        valid = master_df.dropna(subset=["start_year", "lead_sponsor_name"])
        for year, grp in valid.groupby("start_year"):
            year = int(year)
            counts = grp["lead_sponsor_name"].value_counts()
            total = counts.sum()
            shares = (counts / total).to_dict() if total > 0 else {}
            hhi = _compute_hhi(counts)
            stats[year] = {"shares": shares, "hhi": hhi}
        return stats
