"""Statistical Fragility detector — fragility index for 2x2 trial results.

Implements compute_fragility_index using Fisher exact test.
For positive trials (p < 0.05): modify fewer-events arm, add events
one at a time until p >= 0.05.

FI <= 3: severity 0.8; FI 4-7: 0.5; FI 8-15: 0.3
Coverage: ~5-15% of trials (only those with extractable 2x2 tables).
"""
import logging

import pandas as pd

from pipeline.detectors.base import BaseDetector, DetectorResult

logger = logging.getLogger(__name__)


def compute_fragility_index(
    events_a: int, total_a: int, events_b: int, total_b: int
) -> int | None:
    """Compute the Fragility Index for a 2x2 table.

    Modifies the fewer-events arm only, adding events one at a time
    until Fisher exact p >= 0.05.

    Parameters
    ----------
    events_a, total_a : int
        Events and total in arm A.
    events_b, total_b : int
        Events and total in arm B.

    Returns
    -------
    int | None
        Fragility index, or None if initial p >= 0.05 (not significant).
    """
    from scipy.stats import fisher_exact

    # Validate inputs
    if (
        total_a <= 0 or total_b <= 0
        or events_a < 0 or events_b < 0
        or events_a > total_a or events_b > total_b
    ):
        return None

    # Build initial 2x2 table
    table = [
        [events_a, total_a - events_a],
        [events_b, total_b - events_b],
    ]
    _, p = fisher_exact(table)
    if p >= 0.05:
        return None  # Not significant — no fragility index

    # Determine which arm has fewer events (that's the one we modify)
    fi = 0
    # Work on copies
    ea, na = events_a, total_a
    eb, nb = events_b, total_b

    # We add events to the arm with fewer events
    modify_a = ea <= eb

    max_iter = 1000  # safety guard
    while fi < max_iter:
        if modify_a:
            if ea >= na:
                break
            ea += 1
        else:
            if eb >= nb:
                break
            eb += 1

        table = [[ea, na - ea], [eb, nb - eb]]
        _, p = fisher_exact(table)
        fi += 1

        if p >= 0.05:
            return fi

    return fi if fi > 0 else None


def _fi_to_severity(fi: int | None) -> float:
    """Map fragility index to severity score."""
    if fi is None:
        return 0.0
    if fi <= 3:
        return 0.8
    if fi <= 7:
        return 0.5
    if fi <= 15:
        return 0.3
    return 0.1


class StatisticalFragilityDetector(BaseDetector):
    name = "statistical_fragility"
    description = "Trial results that would change with very few event reassignments"
    aact_tables = ["outcome_counts", "outcomes"]

    def detect(
        self, master_df: pd.DataFrame, raw_tables: dict | None = None
    ) -> DetectorResult:
        nct_ids: list[str] = []
        flags: list[bool] = []
        severities: list[float] = []
        details: list[str] = []

        # Try to load outcome data for 2x2 extraction
        tables_2x2 = self._extract_2x2_tables(master_df, raw_tables)

        for _, row in master_df.iterrows():
            nct = row["nct_id"]
            nct_ids.append(nct)

            data = tables_2x2.get(nct)
            if data is None:
                flags.append(False)
                severities.append(0.0)
                details.append("")
                continue

            fi = compute_fragility_index(
                data["events_a"], data["total_a"],
                data["events_b"], data["total_b"],
            )
            if fi is not None:
                sev = _fi_to_severity(fi)
                flags.append(True)
                severities.append(sev)
                details.append(
                    f"FI={fi} (events: {data['events_a']}/{data['total_a']} "
                    f"vs {data['events_b']}/{data['total_b']})"
                )
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

    def _extract_2x2_tables(
        self, master_df: pd.DataFrame, raw_tables: dict | None
    ) -> dict[str, dict]:
        """Extract 2x2 tables from AACT outcome_counts.

        This is a best-effort extraction. Many trials won't have
        parseable 2x2 data, which is expected (low coverage detector).
        """
        try:
            if raw_tables is not None:
                oc = raw_tables.get("outcome_counts")
                if oc is None:
                    return {}
            else:
                from pipeline.ingest import load_aact_table
                oc = load_aact_table("outcome_counts")
        except (KeyError, FileNotFoundError) as e:
            logger.warning("Could not load outcome_counts: %s", e)
            return {}

        if oc is None or oc.empty:
            return {}

        nct_set = set(master_df["nct_id"])
        oc = oc[oc["nct_id"].isin(nct_set)].copy()

        # outcome_counts has: nct_id, outcome_id, result_group_id, ctgov_group_code, scope, units, count
        if "count" not in oc.columns or "scope" not in oc.columns:
            return {}

        oc["count"] = pd.to_numeric(oc["count"], errors="coerce")

        result: dict[str, dict] = {}
        for nct, grp in oc.groupby("nct_id"):
            # Try to find participant counts (scope = "Participants")
            participants = grp[grp["scope"].str.upper().eq("PARTICIPANTS")] if "scope" in grp.columns else grp

            if participants.empty:
                continue

            # Group by ctgov_group_code — need exactly 2 groups
            if "ctgov_group_code" not in participants.columns:
                continue

            group_counts = participants.groupby("ctgov_group_code")["count"].sum()
            if len(group_counts) != 2:
                continue

            groups = sorted(group_counts.index.tolist())
            total_a = int(group_counts[groups[0]])
            total_b = int(group_counts[groups[1]])

            if total_a <= 0 or total_b <= 0:
                continue

            # For events, use the first outcome_id's data as proxy
            outcome_ids = participants["outcome_id"].unique()
            if len(outcome_ids) == 0:
                continue

            first_outcome = participants[participants["outcome_id"] == outcome_ids[0]]
            events_by_group = first_outcome.groupby("ctgov_group_code")["count"].sum()

            if len(events_by_group) == 2:
                events_a = int(events_by_group.get(groups[0], 0))
                events_b = int(events_by_group.get(groups[1], 0))

                # Sanity check
                if 0 <= events_a <= total_a and 0 <= events_b <= total_b:
                    result[nct] = {
                        "events_a": events_a,
                        "total_a": total_a,
                        "events_b": events_b,
                        "total_b": total_b,
                    }

        return result
