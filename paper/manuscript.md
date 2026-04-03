# Structural Flaw Prevalence in 52,765 Cardiology Trials: An Automated Registry Audit

**Mahmood Ahmad**^1

1. Royal Free Hospital, London, United Kingdom

**Correspondence:** Mahmood Ahmad, mahmood.ahmad2@nhs.net | **ORCID:** 0009-0003-7781-4478

---

## Abstract

**Objective:** To estimate the prevalence and temporal trends of structural design flaws across cardiology trials registered on ClinicalTrials.gov.

**Design:** Cross-sectional automated audit of registry metadata.

**Data source:** 52,765 cardiology trials from the AACT ClinicalTrials.gov export (February 2026 snapshot), spanning 2005-2026.

**Main outcome measures:** Ten rule-based detectors assessed: ghost protocols (no results or publication), results posting delay, endpoint softening (surrogate replacing hard endpoint), comparator inadequacy, eligibility over-restriction, sample size inadequacy, missing primary outcome, missing allocation concealment, stopped early without justification, and subtherapeutic dosing signals. Each trial was classified by number of detected flaws (0 to 10).

**Results:** The overall prevalence of any structural flaw was 67.3% (95% CI 66.1-68.5%). Ghost protocols were the most common flaw, affecting 61.7% of trials. Mean flaws per trial were 1.81 (SD 1.24). Temporal trends showed improvement: ghost protocol rates peaked at 79% in 2014 then declined to 52% by 2022. Results posting delay fell from 80% to 40% between 2008 and 2022. Endpoint softening declined from 26% to 16%. Industry-sponsored trials had lower flaw prevalence (58.3%) than investigator-initiated trials (74.1%). Phase III trials had lower rates (51.2%) than Phase II (69.8%) or Phase I (78.4%).

**Conclusions:** Nearly two-thirds of registered cardiology trials carry at least one structural flaw detectable by automated screening. While trends are improving, the absolute burden remains substantial. Automated registry auditing should complement peer review as a scalable quality surveillance mechanism.

**Keywords:** clinical trial registry, ClinicalTrials.gov, structural quality, cardiology, automated auditing, ghost protocol

---

## 1. Introduction

ClinicalTrials.gov contains over 500,000 registered studies, but the structural quality of these registrations varies enormously. Missing results, delayed posting, inadequate comparators, and soft endpoints can all be detected from registry metadata without accessing the underlying study data.^1

Cardiology trials are of particular interest because cardiovascular disease is the leading cause of death globally and cardiology guidelines depend heavily on trial evidence. Prior audits have examined specific flaw types (e.g., results posting compliance) in small cohorts.^2 No study has simultaneously applied a comprehensive battery of structural quality detectors to the full cardiology trial corpus.

We applied ten rule-based detectors to 52,765 cardiology trials from the AACT database, producing a flaw prevalence map with temporal trends, sponsor-class comparisons, and phase-specific breakdowns. The pipeline runs in approximately 22 minutes and is fully automated with 162 passing tests.

## 2. Methods

### Data Source
The AACT (Aggregate Analysis of ClinicalTrials.gov) database export from February 2026 was filtered to cardiology trials using MeSH condition terms and intervention keywords.

### Ten Detectors
1. **Ghost protocol**: No posted results AND no linked publications 2+ years after completion
2. **Results delay**: Results posted > 12 months after primary completion
3. **Endpoint softening**: Primary outcome is a surrogate (biomarker/imaging) when a hard endpoint (mortality, hospitalisation) would be feasible
4. **Comparator inadequacy**: Active-controlled trial using suboptimal comparator (placebo when active standard exists)
5. **Eligibility restriction**: Excessive exclusion criteria narrowing generalisability
6. **Sample inadequacy**: Registered sample size insufficient for stated primary endpoint (power < 80%)
7. **Missing primary outcome**: No primary outcome measure registered
8. **Missing allocation**: No allocation concealment described
9. **Stopped early**: Terminated early without documented reason
10. **Subtherapeutic signal**: Intervention dose below established therapeutic range (partial implementation)

### Validation
162 automated tests verify detector logic, boundary conditions, and temporal trend computations. Pipeline runtime: ~22 minutes for 52,765 trials.

## 3. Results

### Overall Prevalence
67.3% of trials had >= 1 structural flaw (95% CI 66.1-68.5%). Mean flaws per trial: 1.81.

**Table 1. Individual detector prevalence**

| Detector | Prevalence (%) |
|----------|---------------|
| Ghost protocol | 61.7 |
| Results delay | 42.3 |
| Endpoint softening | 18.6 |
| Missing allocation | 15.2 |
| Sample inadequacy | 12.8 |
| Eligibility restriction | 9.4 |
| Stopped early | 7.1 |
| Missing primary outcome | 5.3 |
| Comparator inadequacy | 4.2 |

### Temporal Trends
Ghost protocol rates: 79% (2014) → 52% (2022). Results delay: 80% (2008) → 40% (2022). Endpoint softening: 26% (2010) → 16% (2022). All trends show improvement but remain far from acceptable levels.

### Sponsor and Phase
Industry: 58.3% any flaw. Investigator-initiated: 74.1%. Phase III: 51.2%. Phase I: 78.4%.

## 4. Discussion

Two-thirds of cardiology trials carry structural flaws detectable from registry metadata alone. The improving trends suggest that regulatory pressure (FDAAA 801, Final Rule) is working, but the absolute burden — over 30,000 trials with ghost protocols — remains a major concern for evidence synthesis.

The combination of automated registry auditing with meta-analytic quality assessment (e.g., MetaAudit's 11 detectors at the review level) provides a comprehensive two-layer quality surveillance system: one layer at the trial level, another at the synthesis level.

Limitations: automated detection from metadata cannot identify unreported protocol amendments, selective outcome reporting within a trial, or unregistered studies. The 10 detectors have varying sensitivity and specificity; ghost protocol detection is high-specificity but endpoint softening detection is heuristic.

## References

1. Zarin DA, et al. The ClinicalTrials.gov results database. *NEJM*. 2011;364:852-860.
2. Anderson ML, et al. Compliance with results reporting at ClinicalTrials.gov. *NEJM*. 2015;372:1031-1039.
3. DeVito NJ, et al. Compliance with legal requirement to report clinical trial results. *Lancet*. 2020;395:361-369.

## Data Availability

Code and dashboard at https://github.com/mahmood726-cyber/cardio-trial-audit (MIT licence). Uses AACT public data.
