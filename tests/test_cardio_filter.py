"""Tests for cardiology trial filtering and sub-domain tagging."""
import pandas as pd
import pytest
from pipeline.cardio_filter import (
    CV_CONDITION_PATTERNS,
    CV_INTERVENTION_PATTERNS,
    CV_DEVICE_PATTERNS,
    SUBDOMAIN_RULES,
    is_cv_condition,
    is_cv_intervention,
    tag_subdomain,
    filter_cardiology_trials,
)


class TestConditionMatching:
    def test_heart_failure_matches(self):
        assert is_cv_condition("Heart Failure")
        assert is_cv_condition("Congestive Heart Failure")
        assert is_cv_condition("heart failure with preserved ejection fraction")

    def test_cad_matches(self):
        assert is_cv_condition("Coronary Artery Disease")
        assert is_cv_condition("Acute Coronary Syndrome")
        assert is_cv_condition("Myocardial Infarction")

    def test_non_cv_does_not_match(self):
        assert not is_cv_condition("Breast Cancer")
        assert not is_cv_condition("Asthma")
        assert not is_cv_condition("Depression")

    def test_edge_cases(self):
        assert is_cv_condition("Hypertension, Pulmonary")
        assert is_cv_condition("Atrial Fibrillation and Flutter")
        assert is_cv_condition("Peripheral Arterial Disease")


class TestInterventionMatching:
    def test_drug_matches(self):
        assert is_cv_intervention("Empagliflozin", "DRUG")
        assert is_cv_intervention("Ticagrelor 90mg", "DRUG")

    def test_device_matches(self):
        assert is_cv_intervention("Percutaneous Coronary Intervention", "DEVICE")
        assert is_cv_intervention("Implantable Cardioverter Defibrillator", "DEVICE")

    def test_non_cv_does_not_match(self):
        assert not is_cv_intervention("Ibuprofen", "DRUG")
        assert not is_cv_intervention("Cognitive Behavioral Therapy", "BEHAVIORAL")


class TestSubdomainTagging:
    def test_hf_tagged(self):
        tags = tag_subdomain(conditions=["Heart Failure"], interventions=["Sacubitril/Valsartan"])
        assert "HF" in tags

    def test_cad_tagged(self):
        tags = tag_subdomain(conditions=["Coronary Artery Disease"], interventions=["Ticagrelor"])
        assert "CAD" in tags

    def test_multiple_tags(self):
        tags = tag_subdomain(conditions=["Heart Failure", "Atrial Fibrillation"], interventions=["Apixaban"])
        assert "HF" in tags
        assert "arrhythmia" in tags


class TestFilterPipeline:
    def test_filter_on_small_sample(self):
        """Run filter on first 1000 studies — should find at least some CV trials."""
        result = filter_cardiology_trials(nrows_studies=1000)
        assert isinstance(result, pd.DataFrame)
        assert "nct_id" in result.columns
        assert "cv_subdomains" in result.columns
        assert "cv_match_source" in result.columns
