"""
scoring.py — Weighted Clinical Scoring Engine for High-Stakes Efficacy Oracle
Calculates P_success (0–100%) for high-cost oncology prescriptions.

Scientific basis for each factor:
  - T790M ratio weight    : PMC8099906  — T790M/driver AF ratio predicts osimertinib response
  - CYP3A4 GAS weight     : PharmVar / biorxiv 2020.03.02.967554 — GAS system for metabolizer phenotype
  - eGFR weight           : Renal clearance directly affects osimertinib plasma concentration
  - Liver function weight : CYP3A4 hepatic metabolism — ALT/AST elevation signals impaired metabolism
  - Prior TKI PFS weight  : PMC6468762 — prior EGFR-TKI PFS is significant predictor of osimertinib PFS

Factor weights (must sum to 1.0):
  T790M ratio     = 0.35
  CYP3A4 GAS      = 0.25
  eGFR            = 0.20
  Liver function  = 0.10
  Prior TKI PFS   = 0.10
"""

from dataclasses import dataclass


# ── Scoring weights ──────────────────────────────────────────────────────────

WEIGHTS = {
    "t790m_ratio":    0.35,
    "cyp3a4_gas":     0.25,
    "egfr_renal":     0.20,
    "liver_function": 0.10,
    "prior_tki_pfs":  0.10,
}

# Sanity check — weights must sum to 1.0
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "Weights must sum to 1.0"


# ── Clinical reference ranges ─────────────────────────────────────────────────

# eGFR thresholds (ml/min/1.73m²) — CKD staging
EGFR_NORMAL    = 90.0   # >= 90: normal
EGFR_MILD      = 60.0   # 60–89: mildly reduced
EGFR_MODERATE  = 45.0   # 45–59: moderately reduced
EGFR_SEVERE    = 30.0   # 30–44: severely reduced
# < 30: kidney failure

# Liver function — ALT/AST upper limits of normal (ULN)
ALT_ULN = 56.0   # U/L — upper limit of normal for ALT
AST_ULN = 40.0   # U/L — upper limit of normal for AST

# Prior TKI PFS thresholds (months)
# Research basis: PMC6468762 — PFS > 12 months on prior EGFR-TKI is a
# significant positive predictor of osimertinib outcomes
PFS_EXCELLENT  = 18   # > 18 months: excellent predictor
PFS_GOOD       = 12   # 12–18 months: good predictor
PFS_MODERATE   = 8    # 8–11 months: moderate predictor
# < 8 months: poor predictor

# Prior response mapping to score (ordinal scale)
RESPONSE_SCORES = {
    "CR": 1.0,    # Complete Response — best outcome
    "PR": 0.75,   # Partial Response — good outcome
    "SD": 0.45,   # Stable Disease — moderate outcome
    "PD": 0.10,   # Progressive Disease — poor outcome
    "unknown": 0.40,
}

# T790M ratio thresholds
# Research basis: PMC8099906
# Mean responders = 0.395, mean non-responders = 0.202
T790M_HIGH     = 0.40   # >= 0.40: strong predictor of response
T790M_MODERATE = 0.30   # 0.30–0.39: moderate predictor
T790M_LOW      = 0.20   # 0.20–0.29: weak predictor
# < 0.20: poor predictor


# ── Normalisation functions ───────────────────────────────────────────────────

def normalise_t790m_ratio(ratio: float) -> float:
    """
    Normalise T790M allelic fraction ratio to 0–1 score.
    Based on PMC8099906 — ratio significantly correlates with osimertinib response.
    Mean responder ratio = 0.395, mean non-responder = 0.202.
    Uses a soft sigmoid-like scale anchored to clinical breakpoints.
    """
    if ratio >= T790M_HIGH:
        return min(1.0, 0.85 + (ratio - T790M_HIGH) * 0.75)
    elif ratio >= T790M_MODERATE:
        # Linear interpolation between 0.30 and 0.40
        return 0.60 + ((ratio - T790M_MODERATE) / (T790M_HIGH - T790M_MODERATE)) * 0.25
    elif ratio >= T790M_LOW:
        return 0.30 + ((ratio - T790M_LOW) / (T790M_MODERATE - T790M_LOW)) * 0.30
    else:
        # Below 0.20 — non-responder territory (PMC8099906)
        return max(0.0, ratio / T790M_LOW * 0.30)


def normalise_cyp3a4_gas(gas: float) -> float:
    """
    Normalise CYP3A4 Gene Activity Score to 0–1.
    GAS scale: 0=poor, 0.5=intermediate, 1.0=normal, 2.0=rapid metabolizer.
    Research basis: PharmVar GAS system / biorxiv 2020.03.02.967554.

    For osimertinib (a CYP3A4 substrate):
    - Poor metabolizer (GAS=0): drug accumulates → increased toxicity, unpredictable PK → lower score
    - Normal metabolizer (GAS=1): standard PK → full score
    - Rapid metabolizer (GAS=2): drug cleared faster → may need dose adjustment → moderate score
    """
    if gas == 0.0:
        return 0.10   # Poor — high toxicity risk, unpredictable
    elif gas == 0.5:
        return 0.55   # Intermediate — reduced but manageable
    elif gas == 1.0:
        return 1.00   # Normal — ideal pharmacokinetics
    elif gas >= 2.0:
        return 0.70   # Rapid — faster clearance, may reduce efficacy
    else:
        # Interpolate for any value in between
        return min(1.0, max(0.0, gas))


def normalise_egfr_renal(egfr_ml_min: float) -> float:
    """
    Normalise eGFR (ml/min/1.73m²) to 0–1 renal function score.
    Osimertinib dose adjustment is recommended below 45 ml/min/1.73m².
    Clinical thresholds based on KDIGO CKD staging.
    """
    if egfr_ml_min >= EGFR_NORMAL:
        return 1.00   # Normal kidney function
    elif egfr_ml_min >= EGFR_MILD:
        # Linear interpolation 60–90
        return 0.75 + ((egfr_ml_min - EGFR_MILD) / (EGFR_NORMAL - EGFR_MILD)) * 0.25
    elif egfr_ml_min >= EGFR_MODERATE:
        # Linear interpolation 45–60
        return 0.50 + ((egfr_ml_min - EGFR_MODERATE) / (EGFR_MILD - EGFR_MODERATE)) * 0.25
    elif egfr_ml_min >= EGFR_SEVERE:
        # Linear interpolation 30–45 — dose adjustment territory
        return 0.25 + ((egfr_ml_min - EGFR_SEVERE) / (EGFR_MODERATE - EGFR_SEVERE)) * 0.25
    else:
        # < 30: kidney failure — high risk
        return max(0.0, egfr_ml_min / EGFR_SEVERE * 0.25)


def normalise_liver_function(alt: float, ast: float) -> float:
    """
    Normalise liver function to 0–1 score based on ALT and AST.
    Osimertinib is primarily metabolised by CYP3A4 in the liver.
    Elevated transaminases signal hepatic stress → impaired CYP3A4 activity.

    Grading based on CTCAE v5.0 liver toxicity scale:
      Grade 1: 1–3x ULN  → mild
      Grade 2: 3–5x ULN  → moderate
      Grade 3: 5–20x ULN → severe
    """
    # Use ALT as primary marker, AST as secondary (average their x-ULN)
    alt_x_uln = alt / ALT_ULN
    ast_x_uln = ast / AST_ULN
    avg_x_uln = (alt_x_uln + ast_x_uln) / 2.0

    if avg_x_uln <= 1.0:
        return 1.00   # Normal — no hepatic concern
    elif avg_x_uln <= 3.0:
        # Grade 1 — mild elevation, linear penalty
        return max(0.60, 1.0 - (avg_x_uln - 1.0) * 0.20)
    elif avg_x_uln <= 5.0:
        # Grade 2 — moderate elevation
        return max(0.25, 0.60 - (avg_x_uln - 3.0) * 0.175)
    else:
        # Grade 3+ — severe, high risk of hepatotoxicity
        return max(0.0, 0.25 - (avg_x_uln - 5.0) * 0.05)


def normalise_prior_tki_pfs(pfs_months: int, best_response: str) -> float:
    """
    Normalise prior TKI progression-free survival to 0–1 score.
    Research basis: PMC6468762 — prior PFS with initial EGFR-TKI significantly
    related to PFS and OS with osimertinib (p=0.035).

    Combines PFS duration with best treatment response for a composite score.
    """
    # PFS duration component (0–1)
    if pfs_months >= PFS_EXCELLENT:
        pfs_score = 1.00
    elif pfs_months >= PFS_GOOD:
        pfs_score = 0.75 + ((pfs_months - PFS_GOOD) / (PFS_EXCELLENT - PFS_GOOD)) * 0.25
    elif pfs_months >= PFS_MODERATE:
        pfs_score = 0.45 + ((pfs_months - PFS_MODERATE) / (PFS_GOOD - PFS_MODERATE)) * 0.30
    else:
        pfs_score = max(0.0, pfs_months / PFS_MODERATE * 0.45)

    # Best response component (0–1)
    response_score = RESPONSE_SCORES.get(best_response.upper(), RESPONSE_SCORES["unknown"])

    # Weighted composite: 60% PFS duration, 40% best response
    return round(0.60 * pfs_score + 0.40 * response_score, 4)


# ── Main scoring function ────────────────────────────────────────────────────

@dataclass
class ScoringResult:
    p_success: float           # Final probability 0–100%
    confidence: str            # HIGH / MODERATE / LOW
    recommendation: str        # Clinical recommendation string
    factor_scores: dict        # Individual normalised scores (0–1)
    factor_contributions: dict # Weighted contributions to final score
    clinical_flags: list       # Any clinical warnings


def calculate_p_success(
        t790m_ratio: float,
        cyp3a4_gas: float,
        egfr_ml_min: float,
        alt_u_l: float,
        ast_u_l: float,
        prior_pfs_months: int,
        best_response: str,
) -> ScoringResult:
    """
    Calculate P_success for high-cost oncology prescription.
    Returns a ScoringResult dataclass with full breakdown.

    All inputs are from FHIR resource extraction (mock_data.py).
    All factor scores are normalised to 0–1 before weighting.
    Final P_success = sum(factor_score * weight) * 100
    """

    # Step 1 — Normalise each factor to 0–1
    factor_scores = {
        "t790m_ratio":    normalise_t790m_ratio(t790m_ratio),
        "cyp3a4_gas":     normalise_cyp3a4_gas(cyp3a4_gas),
        "egfr_renal":     normalise_egfr_renal(egfr_ml_min),
        "liver_function": normalise_liver_function(alt_u_l, ast_u_l),
        "prior_tki_pfs":  normalise_prior_tki_pfs(prior_pfs_months, best_response),
    }

    # Step 2 — Apply weights
    factor_contributions = {
        factor: round(score * WEIGHTS[factor], 4)
        for factor, score in factor_scores.items()
    }

    # Step 3 — Sum weighted scores and convert to percentage
    raw_score = sum(factor_contributions.values())
    p_success = round(min(100.0, max(0.0, raw_score * 100)), 1)

    # Step 4 — Round individual scores for readability
    factor_scores = {k: round(v, 3) for k, v in factor_scores.items()}

    # Step 5 — Clinical flags
    clinical_flags = []

    if t790m_ratio < T790M_LOW:
        clinical_flags.append(
            f"Low T790M ratio ({t790m_ratio:.2f}) — below non-responder threshold of 0.20"
        )
    if cyp3a4_gas == 0.0:
        clinical_flags.append(
            "Poor CYP3A4 metabolizer — risk of drug accumulation and toxicity"
        )
    if egfr_ml_min < EGFR_MODERATE:
        clinical_flags.append(
            f"eGFR {egfr_ml_min} ml/min — dose adjustment may be required per SmPC"
        )
    if alt_u_l > 3 * ALT_ULN or ast_u_l > 3 * AST_ULN:
        clinical_flags.append(
            f"Hepatic stress — ALT {alt_u_l} U/L / AST {ast_u_l} U/L (>3x ULN)"
        )
    if best_response == "PD":
        clinical_flags.append(
            "Progressive disease on prior EGFR-TKI — limited predictive signal for osimertinib"
        )

    # Step 6 — Confidence and recommendation
    if p_success >= 65:
        confidence = "HIGH"
        recommendation = (
            f"Simulation supports prescribing. P_success {p_success}% — "
            "genomic and clinical profile consistent with osimertinib response."
        )
    elif p_success >= 40:
        confidence = "MODERATE"
        recommendation = (
            f"Proceed with caution. P_success {p_success}% — borderline profile. "
            "Consider MDT review and close monitoring."
        )
    else:
        confidence = "LOW"
        recommendation = (
            f"Simulation does not support prescribing at this time. P_success {p_success}% — "
            "clinical factors suggest high risk of non-response or toxicity."
        )

    return ScoringResult(
        p_success=p_success,
        confidence=confidence,
        recommendation=recommendation,
        factor_scores=factor_scores,
        factor_contributions=factor_contributions,
        clinical_flags=clinical_flags,
    )


if __name__ == "__main__":
    # Sanity check — run with: python scoring.py
    from mock_data import extract_genomic_factors, extract_lab_factors, extract_medication_factors

    print("=== OracleMK1 — Scoring Engine Sanity Check ===\n")

    for pid in ["patient_001", "patient_002", "patient_003"]:
        g = extract_genomic_factors(pid)
        l = extract_lab_factors(pid)
        m = extract_medication_factors(pid)

        result = calculate_p_success(
            t790m_ratio       = g["t790m_ratio"],
            cyp3a4_gas        = g["cyp3a4_gas"],
            egfr_ml_min       = l["egfr_ml_min"],
            alt_u_l           = l["alt_u_l"],
            ast_u_l           = l["ast_u_l"],
            prior_pfs_months  = m["prior_pfs_months"],
            best_response     = m["best_response"],
        )

        print(f"Patient : {pid}")
        print(f"  P_success    : {result.p_success}%")
        print(f"  Confidence   : {result.confidence}")
        print(f"  Factor scores: {result.factor_scores}")
        print(f"  Contributions: {result.factor_contributions}")
        if result.clinical_flags:
            print(f"  ⚠ Flags      : {result.clinical_flags}")
        print(f"  Recommendation: {result.recommendation}")
        print()