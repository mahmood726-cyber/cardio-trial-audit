# CardioTrialAudit — Design Spec

## Purpose

Large-scale systematic analysis of structural flaws in cardiology RCTs registered on ClinicalTrials.gov (2005–2026), quantifying how trial quality is decaying over time. Produces a Python analysis pipeline + interactive HTML dashboard.

**Target outputs:**
- BMJ primary manuscript (methodological audit of cardiology RCT integrity)
- Companion data paper (PLoS Medicine / F1000Research) with full dataset + interactive dashboard

## Data Sources

### Primary: AACT Local Export
- Path: `C:\Users\user\Pairwise70\hfpef_registry_calibration\data\aact\20260219_export_ctgov.zip`
- Format: 49 pipe-delimited text files, Feb 2026 snapshot (2.3GB)
- Tables used: studies, outcomes, outcome_measurements, eligibilities, baseline_measurements, sponsors, facilities, countries, interventions, design_groups, designs, milestones, participant_flows, reported_events, result_agreements

### Supplementary: CT.gov API v2
- For outcome version history (outcome switching detector)
- Rate-limited; cache responses locally

### Seed Filters: CardioOracle
- Path: `C:\Models\CardioOracle\curate\extract_aact.py` + `shared.py`
- Provides: condition pattern regex, drug class map, endpoint classifier
- Extend with full MeSH cardiovascular terms + intervention-based matching

## Cardiology Scoping Strategy (C + D)

1. **Seed from CardioOracle**: Phase 3 CV condition patterns + drug class map
2. **Expand conditions**: Full MeSH cardiovascular tree (C14.*) + common text patterns for: coronary artery disease, heart failure, atrial fibrillation, hypertension, valvular heart disease, cardiomyopathy, acute coronary syndrome, peripheral artery disease, pulmonary hypertension, aortic disease, venous thromboembolism, sudden cardiac death, cardiac arrest, myocarditis, pericarditis, congenital heart disease, cardiac surgery, cardiac rehabilitation
3. **Expand interventions**: CV drug classes (statins, antiplatelets, anticoagulants, SGLT2i, ARNi, beta-blockers, CCBs, ACEi/ARBs, antiarrhythmics, nitrates, diuretics, inotropes) + devices (PCI/stent, TAVR/SAVR, ICD, CRT, LVAD, catheter ablation, balloon valvuloplasty)
4. **Union**: Any trial matching condition OR intervention criteria
5. **Sub-domain tagging**: Each trial tagged with one or more: HF, CAD, arrhythmia, hypertension, structural, vascular, prevention, VTE, other-CV
6. **Phase scope**: All phases (1–4) + observational, to capture full landscape

Expected yield: ~15,000–30,000 cardiology trials in the 2005–2026 window.

## Time Window & Trend Analysis

- **Range**: 2005–2026 (start_date or first_posted_date)
- **Granularity**: Year-by-year for dashboard; 3-year rolling bins for manuscript
- **Regulatory milestones** (annotated on all trend plots):
  - 2007: FDAAA mandatory registration
  - 2017: Final Rule enforcement (results posting mandate)
  - 2020–2021: COVID disruption period
- **Trend method**: Poisson/negative-binomial regression for counts; beta regression for proportions; Joinpoint for breakpoint detection

## Architecture

```
CardioTrialAudit/
├── pipeline/
│   ├── __init__.py
│   ├── ingest.py              # AACT ZIP extraction + table loading
│   ├── cardio_filter.py       # Cardiology scoping (seed + expand + tag)
│   ├── master_table.py        # Build one-row-per-trial master table
│   ├── detectors/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract detector interface
│   │   ├── ghost_protocols.py
│   │   ├── outcome_switching.py
│   │   ├── population_distortion.py
│   │   ├── sample_size_decay.py
│   │   ├── sponsor_concentration.py
│   │   ├── geographic_shifts.py
│   │   ├── results_delay.py
│   │   ├── endpoint_softening.py
│   │   ├── comparator_manipulation.py
│   │   └── statistical_fragility.py
│   ├── trends.py              # Temporal trend analysis + regression
│   ├── composite.py           # Aggregate flaw score per trial
│   └── export.py              # CSV/JSON/figure export
├── dashboard/
│   └── index.html             # Single-file interactive explorer
├── data/                      # gitignored
│   ├── raw/                   # Extracted AACT tables (pipe-delimited)
│   ├── processed/             # Master table + detector outputs
│   └── results/               # Trend analysis + figures
├── manuscript/
│   ├── figures/
│   └── tables/
├── tests/
│   ├── test_ingest.py
│   ├── test_cardio_filter.py
│   ├── test_detectors.py
│   └── test_trends.py
├── requirements.txt
└── README.md
```

## Detector Specifications

### Standard Interface

```python
class BaseDetector(ABC):
    name: str                   # e.g., "ghost_protocols"
    description: str
    aact_tables: list[str]      # Tables this detector needs

    @abstractmethod
    def detect(self, master_df: pd.DataFrame, raw_tables: dict) -> pd.DataFrame:
        """Returns DataFrame with columns:
        - nct_id: str
        - flaw_detected: bool
        - severity: float (0.0–1.0)
        - detail: str (human-readable explanation)
        - subcategory: str (optional flaw subcategory)
        """
        ...
```

### Detector 1: Ghost Protocols
- **Tables**: studies, reported_events
- **Logic**:
  - Type A (never started): registered ≥3 years ago, status = "Not yet recruiting" or "Withdrawn" with no enrollment
  - Type B (abandoned): status = "Unknown" or "Suspended" with no update ≥2 years
  - Type C (results withheld): status = "Completed" but results_first_posted_date is NULL and completion ≥13 months ago (FDAAA +1 month grace)
- **Severity**: years_overdue / 5.0, capped at 1.0
- **Trend hypothesis**: Ghost rate stable or increasing despite FDAAA enforcement

### Detector 2: Outcome Switching
- **Tables**: outcomes (from results), CT.gov API version history
- **Logic**:
  - Compare registered primary outcome titles vs. reported primary outcome titles
  - Fuzzy matching (token sort ratio ≥ 0.85 = match, < 0.60 = likely switch)
  - Flag: new primary outcomes in results not in registration; registered primaries demoted to secondary
  - Flag: time_frame changes in primary outcomes
- **Severity**: 0.3 (time frame change), 0.7 (demotion), 1.0 (new unregistered primary)
- **Limitation**: Version history only via API, not in AACT. Will work on subset with API supplement.

### Detector 3: Population Distortion
- **Tables**: eligibilities, baseline_measurements
- **Logic**:
  - Age restriction score: max_age < 75 for HF (median HF patient ~76), max_age < 80 for CAD, min_age > 40 for prevention
  - Comorbidity exclusion score: text search in criteria for CKD/renal exclusion, diabetes exclusion, liver disease exclusion, cognitive impairment exclusion — count how many common comorbidities are excluded
  - Gender imbalance: compare baseline male% to expected disease prevalence male%
  - Race/ethnicity: proportion of baseline_measurements reporting race; diversity of enrolled population
  - Composite: weighted average of sub-scores
- **Severity**: composite score 0–1
- **Benchmark data**: AHA/ESC epidemiology reports for age/sex distributions by CV condition

### Detector 4: Sample Size Decay
- **Tables**: studies (enrollment, enrollment_type), participant_flows, milestones
- **Logic**:
  - Planned vs actual: if enrollment_type = "Anticipated", compare with actual (from participant_flows started count)
  - Attrition: (enrolled - analyzed) / enrolled
  - Asymmetric dropout: |dropout_arm1 - dropout_arm2| / avg_dropout
  - Early termination: status = "Terminated" with enrollment < 50% of target
- **Severity**: max(planned_vs_actual_shortfall, attrition_rate, asymmetric_flag * 0.5)

### Detector 5: Sponsor Concentration
- **Tables**: sponsors, studies, outcomes
- **Logic**:
  - Per-year Herfindahl-Hirschman Index (HHI) of lead sponsor names
  - Industry vs. academic vs. other proportion per year
  - Positive result rate by sponsor type (industry vs. academic)
  - Individual sponsor "batting average" (% positive primary outcomes)
- **Severity**: trial-level = industry_sponsored * abs(result_is_positive - base_rate). Population-level = HHI trend.

### Detector 6: Geographic Shifts
- **Tables**: facilities, countries
- **Logic**:
  - Per trial: proportion of sites in World Bank high-income countries vs. LMIC
  - Per year: median LMIC site proportion, trend
  - Flag: trials with >80% sites in countries with <50th percentile regulatory capacity (WHO index)
  - Regional breakdown: North America, Western Europe, Eastern Europe, Asia, South America, Africa, Middle East
- **Severity**: 1.0 - proportion_high_income_sites (so all-LMIC = 1.0)

### Detector 7: Time-to-Results Bloat
- **Tables**: studies (primary_completion_date, results_first_posted_date)
- **Logic**:
  - delay_days = results_first_posted_date - primary_completion_date
  - FDAAA compliant = delay_days ≤ 365
  - Flag severity: 0.0 (≤12 months), 0.3 (12–24 months), 0.6 (24–36 months), 1.0 (>36 months or never posted)
- **Severity**: min(delay_days / (365 * 3), 1.0)
- **Trend**: median delay per year, % compliant per year

### Detector 8: Endpoint Softening
- **Tables**: outcomes
- **Logic**:
  - Classify each primary outcome as:
    - Hard: all-cause mortality, cardiovascular mortality, MI, stroke, hospitalization (HF/CV), MACE composite
    - Surrogate: biomarkers (BNP, troponin, LDL, HbA1c), imaging (EF, LV volume, CMR), functional (6MWT, NYHA class, VO2max)
    - PRO: quality of life, symptom scores, patient-reported
  - Keywords + regex dictionary for classification
  - Per year: proportion of trials with at least one hard primary endpoint
  - Per sub-domain: endpoint composition trends
- **Severity**: 0.0 (hard only), 0.5 (mixed hard + surrogate), 1.0 (surrogate only as primary)

### Detector 9: Comparator Manipulation
- **Tables**: interventions, design_groups, designs
- **Logic**:
  - Flag placebo-controlled when condition has established standard-of-care
  - Detect from intervention descriptions: "placebo" or "sham" as comparator
  - Cross-reference: is there an FDA-approved therapy for this condition? (use curated lookup table for major CV conditions)
  - Dose extraction: regex for dose values in intervention names/descriptions; flag if comparator dose < standard therapeutic range
- **Severity**: 0.5 (placebo when SOC exists), 1.0 (subtherapeutic active comparator)

### Detector 10: Statistical Fragility
- **Tables**: outcome_measurements, outcomes
- **Logic**:
  - Extract 2x2 tables from binary primary outcomes (event counts per arm)
  - Calculate fragility index: minimum event modifications in one arm to flip p-value across 0.05
  - Only for trials with reported significance (p < 0.05 on primary)
- **Severity**: FI=0 → 1.0, FI=1–3 → 0.8, FI=4–7 → 0.5, FI=8–15 → 0.3, FI>15 → 0.0
- **Limitation**: Only works for subset with extractable 2x2 tables

## Composite Flaw Score

Per trial, aggregate across all applicable detectors:
- `composite_score = mean(severity_i for detectors where flaw_detected)`
- `flaw_count = sum(flaw_detected)`
- `flaw_categories = list of detector names where flaw_detected`

For trends: track mean composite_score per year and per 3-year bin.

## Dashboard Design (Single-File HTML)

### Views:
1. **Overview**: headline stats (N trials, flaw prevalence, worst year), 10-detector radar chart
2. **Trends**: line charts per detector (yearly + 3-yr bins), regulatory milestone annotations
3. **Heatmap**: year × detector matrix showing prevalence rates (color intensity)
4. **Trial explorer**: searchable/filterable table of all trials with flaw flags, drill-down to detail
5. **Sub-domain comparison**: HF vs CAD vs arrhythmia flaw profiles
6. **Sponsor analysis**: top sponsors, industry vs academic comparison
7. **Geographic map**: world map of site distribution trends

### Tech: vanilla HTML/CSS/JS, Chart.js for charts, no framework dependencies.

## Manuscript Structure (BMJ)

1. **Title**: "Structural Integrity of Cardiology Randomised Controlled Trials: A Systematic Audit of ClinicalTrials.gov 2005–2026"
2. **Abstract**: structured (Objective, Design, Data sources, Main outcome measures, Results, Conclusions)
3. **Introduction**: evidence-based medicine depends on trial integrity; growing concerns; no large-scale systematic audit exists
4. **Methods**: data sources, cardiology scoping, 10 flaw detectors, trend analysis, composite scoring
5. **Results**: per-detector prevalence + trends, composite trends, sub-domain differences, sponsor effects
6. **Discussion**: which flaws are worsening, regulatory intervention effectiveness, implications for evidence synthesis
7. **Figures**: 3–4 main (trend lines, heatmap, radar), 6–8 supplementary

## Testing Strategy

- Unit tests for each detector on synthetic trials with known flaws
- Integration test: run full pipeline on 100-trial sample, verify outputs
- Validation: spot-check 50 flagged trials manually against CT.gov
- Regression: snapshot detector counts, alert if re-run shifts >5%

## Dependencies

- Python 3.11+
- pandas, numpy, scipy, statsmodels (analysis)
- rapidfuzz (fuzzy string matching for outcome switching)
- requests (CT.gov API)
- matplotlib, seaborn (manuscript figures)
- pytest
