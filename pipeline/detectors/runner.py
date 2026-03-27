"""Detector runner — registry and orchestration for all flaw detectors."""
import logging

import pandas as pd

from pipeline.detectors.base import BaseDetector, DetectorResult
from pipeline.detectors.ghost_protocols import GhostProtocolsDetector
from pipeline.detectors.outcome_switching import OutcomeSwitchingDetector
from pipeline.detectors.population_distortion import PopulationDistortionDetector
from pipeline.detectors.sample_size_decay import SampleSizeDecayDetector
from pipeline.detectors.sponsor_concentration import SponsorConcentrationDetector
from pipeline.detectors.geographic_shifts import GeographicShiftsDetector
from pipeline.detectors.results_delay import ResultsDelayDetector
from pipeline.detectors.endpoint_softening import EndpointSofteningDetector
from pipeline.detectors.comparator_manipulation import ComparatorManipulationDetector
from pipeline.detectors.statistical_fragility import StatisticalFragilityDetector

logger = logging.getLogger(__name__)

# Registry: name -> detector instance
DETECTOR_REGISTRY: dict[str, BaseDetector] = {
    "ghost_protocols": GhostProtocolsDetector(),
    "outcome_switching": OutcomeSwitchingDetector(),
    "population_distortion": PopulationDistortionDetector(),
    "sample_size_decay": SampleSizeDecayDetector(),
    "sponsor_concentration": SponsorConcentrationDetector(),
    "geographic_shifts": GeographicShiftsDetector(),
    "results_delay": ResultsDelayDetector(),
    "endpoint_softening": EndpointSofteningDetector(),
    "comparator_manipulation": ComparatorManipulationDetector(),
    "statistical_fragility": StatisticalFragilityDetector(),
}


def run_all_detectors(
    master_df: pd.DataFrame,
    raw_tables: dict[str, pd.DataFrame] | None = None,
    detectors: list[str] | None = None,
) -> pd.DataFrame:
    """Run selected (or all) detectors and merge results into a single DataFrame.

    Parameters
    ----------
    master_df : pd.DataFrame
        One-row-per-trial master table.
    raw_tables : dict | None
        Optional pre-loaded AACT tables {name: DataFrame}.
    detectors : list[str] | None
        Detector names to run. If None, runs all.

    Returns
    -------
    pd.DataFrame
        master_df with detector columns appended (one _detected, _severity,
        _detail per detector).
    """
    if detectors is None:
        to_run = DETECTOR_REGISTRY
    else:
        to_run = {
            name: DETECTOR_REGISTRY[name]
            for name in detectors
            if name in DETECTOR_REGISTRY
        }
        missing = set(detectors) - set(to_run.keys())
        if missing:
            logger.warning("Unknown detectors skipped: %s", missing)

    result_df = master_df.copy()

    for name, detector in to_run.items():
        logger.info("Running detector: %s", name)
        try:
            dr: DetectorResult = detector.detect(master_df, raw_tables)
            if len(dr.nct_ids) != len(master_df):
                logger.error(
                    "Detector %s returned %d rows, expected %d — skipping",
                    name, len(dr.nct_ids), len(master_df),
                )
                continue
            det_df = dr.to_dataframe(name)
            # Merge on nct_id to handle potential ordering differences
            result_df = result_df.merge(
                det_df, on="nct_id", how="left", suffixes=("", f"_{name}_dup")
            )
        except Exception as e:
            logger.error("Detector %s failed: %s", name, e, exc_info=True)
            # Add empty columns so downstream code doesn't break
            result_df[f"{name}_detected"] = False
            result_df[f"{name}_severity"] = 0.0
            result_df[f"{name}_detail"] = ""

    return result_df
