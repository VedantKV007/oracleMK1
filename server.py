"""
server.py — High-Stakes Efficacy Oracle MCP Server
Hackathon: Agents Assemble (Prompt Opinion / Darena Health)
Track: Option 1 — Build a Superpower (MCP Server)

Architecture:
  - Built with fastmcp (Python)
  - Implements SHARP context: accepts patient_id as secure context token
  - Smart Triage Gate: filters by drug cost before running simulation
  - FHIR data layer: mock_data.py (synthetic FHIR R4 resources)
  - Scoring engine: scoring.py (weighted clinical probability model)
"""


import os
from fastmcp import FastMCP
from mock_data import (
    get_patient,
    extract_genomic_factors,
    extract_lab_factors,
    extract_medication_factors,
)
from scoring import calculate_p_success



# ── Server initialisation ────────────────────────────────────────────────────

mcp = FastMCP(
    name=os.getenv("SERVER_NAME", "HighStakesEfficacyOracle"),
    instructions="""
    High-Stakes Efficacy Oracle — Clinical Decision Support MCP Server.

    This server predicts the success probability (0-100%) of high-cost oncology
    prescriptions using a weighted clinical simulation model.

    Implements the Smart Triage Gate:
      - Drug cost < $10,000  : Returns standard workflow bypass
      - Drug cost $10,000–$15,000 : Runs full genomic + clinical simulation
      - Drug cost > $15,000  : Returns manual board review required

    Accepts patient_id via SHARP context for secure FHIR data retrieval.
    All patient data is synthetic and de-identified (no real PHI).
    """,
)


# ── Drug cost reference table ─────────────────────────────────────────────────
# Unit costs in USD — representative values for demo purposes
# In production these would be pulled from a formulary/pharmacy benefits API
# STAR update m1

DRUG_COST_TABLE = {
    # EGFR-TKI 3rd gen
    "osimertinib":   12400.0,
    "tagrisso":      12400.0,
    # EGFR-TKI 1st/2nd gen
    "erlotinib":     11100.0,
    "tarceva":       11100.0,
    "gefitinib":     10800.0,
    "iressa":        10800.0,
    "afatinib":      13200.0,
    "gilotrif":      13200.0,
    "dacomitinib":   14100.0,
    "vizimpro":      14100.0,
    # ALK inhibitors
    "alectinib":     14500.0,
    "alecensa":      14500.0,
    "crizotinib":    12800.0,
    "xalkori":       12800.0,
    "brigatinib":    13600.0,
    "alunbrig":      13600.0,
    # PD-1 / PD-L1 inhibitors
    "pembrolizumab": 13800.0,
    "keytruda":      13800.0,
    "nivolumab":     11200.0,
    "opdivo":        11200.0,
    "durvalumab":    11800.0,
    "imfinzi":       11800.0,
    "avelumab":      12900.0,
    "bavencio":      12900.0,
    # PARP inhibitors
    "olaparib":      13400.0,
    "lynparza":      13400.0,
    "niraparib":     11600.0,
    "zejula":        11600.0,
    # Below threshold
    "cetuximab":     8500.0,
    "bevacizumab":   7200.0,
    "trastuzumab":   6800.0,
    "erlotinib_low": 9800.0,
    # Above threshold
    "ipilimumab":    16200.0,
    "atezolizumab":  15800.0,
}

DRUG_CLASS_TABLE = {
    # EGFR-TKI 3rd gen — CYP3A4 primary
    "osimertinib":   {"class": "EGFR-TKI",  "generation": "3G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_T790M"},
    "tagrisso":      {"class": "EGFR-TKI",  "generation": "3G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_T790M"},
    # EGFR-TKI 1st/2nd gen — CYP3A4 primary
    "erlotinib":     {"class": "EGFR-TKI",  "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "tarceva":       {"class": "EGFR-TKI",  "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "gefitinib":     {"class": "EGFR-TKI",  "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "iressa":        {"class": "EGFR-TKI",  "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "afatinib":      {"class": "EGFR-TKI",  "generation": "2G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "gilotrif":      {"class": "EGFR-TKI",  "generation": "2G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "dacomitinib":   {"class": "EGFR-TKI",  "generation": "2G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    "vizimpro":      {"class": "EGFR-TKI",  "generation": "2G", "cyp_enzyme": "CYP3A4", "biomarker": "EGFR_exon19_L858R"},
    # ALK inhibitors — CYP3A4 primary
    "alectinib":     {"class": "ALK-inhibitor", "generation": "2G", "cyp_enzyme": "CYP3A4", "biomarker": "ALK_fusion"},
    "alecensa":      {"class": "ALK-inhibitor", "generation": "2G", "cyp_enzyme": "CYP3A4", "biomarker": "ALK_fusion"},
    "crizotinib":    {"class": "ALK-inhibitor", "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "ALK_fusion"},
    "xalkori":       {"class": "ALK-inhibitor", "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "ALK_fusion"},
    "brigatinib":    {"class": "ALK-inhibitor", "generation": "2G", "cyp_enzyme": "CYP2D6", "biomarker": "ALK_fusion"},
    "alunbrig":      {"class": "ALK-inhibitor", "generation": "2G", "cyp_enzyme": "CYP2D6", "biomarker": "ALK_fusion"},
    # PD-1/PD-L1 — minimal CYP metabolism (monoclonal antibodies)
    "pembrolizumab": {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "keytruda":      {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "nivolumab":     {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "opdivo":        {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "durvalumab":    {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "imfinzi":       {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "avelumab":      {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    "bavencio":      {"class": "PD1-inhibitor", "generation": "1G", "cyp_enzyme": "none", "biomarker": "PD-L1"},
    # PARP inhibitors — CYP3A4 primary
    "olaparib":      {"class": "PARP-inhibitor", "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "BRCA1_2"},
    "lynparza":      {"class": "PARP-inhibitor", "generation": "1G", "cyp_enzyme": "CYP3A4", "biomarker": "BRCA1_2"},
    "niraparib":     {"class": "PARP-inhibitor", "generation": "1G", "cyp_enzyme": "CYP2D6", "biomarker": "BRCA1_2"},
    "zejula":        {"class": "PARP-inhibitor", "generation": "1G", "cyp_enzyme": "CYP2D6", "biomarker": "BRCA1_2"},
    # Below/above threshold
    "cetuximab":     {"class": "EGFR-mAb",       "generation": "1G", "cyp_enzyme": "none",   "biomarker": "EGFR_wildtype"},
    "bevacizumab":   {"class": "VEGF-mAb",        "generation": "1G", "cyp_enzyme": "none",   "biomarker": "VEGF"},
    "ipilimumab":    {"class": "CTLA4-inhibitor", "generation": "1G", "cyp_enzyme": "none",   "biomarker": "TMB"},
}

ALIAS_GROUPS = [
    {"osimertinib", "tagrisso"},
    {"erlotinib", "tarceva"},
    {"gefitinib", "iressa"},
    {"afatinib", "gilotrif"},
    {"dacomitinib", "vizimpro"},
    {"alectinib", "alecensa"},
    {"crizotinib", "xalkori"},
    {"brigatinib", "alunbrig"},
    {"pembrolizumab", "keytruda"},
    {"nivolumab", "opdivo"},
    {"durvalumab", "imfinzi"},
    {"avelumab", "bavencio"},
    {"olaparib", "lynparza"},
    {"niraparib", "zejula"},
]


TRIAGE_MIN = 10_000.0
TRIAGE_MAX = 15_000.0


# ── Helper: resolve drug cost ────────────────────────────────────────────────

def resolve_drug_cost(drug_name: str, override_cost: float | None) -> float:
    """
    Resolve the unit cost of a drug.
    Uses override_cost if provided, otherwise looks up DRUG_COST_TABLE.
    Returns 0.0 if drug is not recognised and no override given.
    """
    if override_cost is not None and override_cost > 0:
        return float(override_cost)
    return DRUG_COST_TABLE.get(drug_name.lower().strip(), 0.0)
#STAR update part 2 m1

def find_best_alternative(patient_id: str, failed_drug: str, failed_cost: float) -> dict | None:
    """
    Simulates all same-class alternatives in triage range.
    Prefers drugs with different CYP enzyme for poor metabolizers.
    Returns the best scoring alternative.
    """
    failed_info  = DRUG_CLASS_TABLE.get(failed_drug.lower(), {})
    failed_class = failed_info.get("class")
    failed_cyp   = failed_info.get("cyp_enzyme", "")
    if not failed_class:
        return None

    failed_group = next((g for g in ALIAS_GROUPS if failed_drug.lower() in g), {failed_drug.lower()})

    genomic_factors    = extract_genomic_factors(patient_id)
    lab_factors        = extract_lab_factors(patient_id)
    medication_factors = extract_medication_factors(patient_id)
    cyp3a4_gas         = genomic_factors.get("cyp3a4_gas", 1.0)
    is_poor_metabolizer = cyp3a4_gas == 0.0

    best_score  = -1.0
    best_drug   = None
    best_result = None
    best_cyp    = None

    for drug, info in DRUG_CLASS_TABLE.items():
        if drug in failed_group:
            continue
        if info["class"] != failed_class:
            continue
        cost = DRUG_COST_TABLE.get(drug, 0.0)
        if not (TRIAGE_MIN <= cost <= TRIAGE_MAX):
            continue

        # Skip aliases already evaluated
        drug_group = next((g for g in ALIAS_GROUPS if drug in g), {drug})
        primary    = min(drug_group)
        if primary != drug:
            continue

        try:
            result = calculate_p_success(
                t790m_ratio      = genomic_factors.get("t790m_ratio", 0.0),
                cyp3a4_gas       = genomic_factors.get("cyp3a4_gas", 1.0),
                egfr_ml_min      = lab_factors.get("egfr_ml_min", 60.0),
                alt_u_l          = lab_factors.get("alt_u_l", 35.0),
                ast_u_l          = lab_factors.get("ast_u_l", 25.0),
                prior_pfs_months = medication_factors.get("prior_pfs_months", 0),
                best_response    = medication_factors.get("best_response", "unknown"),
            )

            score = result.p_success
            # Bonus: prefer different CYP enzyme for poor CYP3A4 metabolizers
            alt_cyp = info.get("cyp_enzyme", "")
            if is_poor_metabolizer and alt_cyp != "CYP3A4" and alt_cyp != "none":
                score += 8.0

            if score > best_score:
                best_score  = score
                best_drug   = drug
                best_result = result
                best_cyp    = alt_cyp
        except Exception:
            continue


    if best_result and best_result.p_success <= 30.0:
        return None

    if best_drug and best_result:
        cyp_note = (
            f" Uses {best_cyp} metabolism pathway — preferred for poor CYP3A4 metabolizers."
            if is_poor_metabolizer and best_cyp and best_cyp != "CYP3A4"
            else ""
        )
        return {
            "suggested_drug":       best_drug,
            "suggested_cost_usd":   DRUG_COST_TABLE[best_drug],
            "suggested_p_success":  round(min(100.0, best_score), 1), # <--- FIXED THIS
            "suggested_confidence": best_result.confidence,
            "drug_class":           failed_class,
            "cyp_enzyme":           best_cyp,
            "reason": (
                f"{failed_drug.title()} scored below 50% success threshold. "
                f"Oracle simulated {len(DRUG_CLASS_TABLE)} formulary drugs. "
                f"{best_drug.title()} is the highest-scoring same-class alternative "
                f"at {round(min(100.0, best_score), 1)}% success probability.{cyp_note}" # <--- FIXED THIS
            ),
        }
    return None

# ── MCP Tool 1: evaluate_prescription ────────────────────────────────────────

@mcp.tool()
def evaluate_prescription(
        patient_id: str,
        drug_name: str,
        drug_cost_usd: float | None = None,
        fhir_context: dict | None = None,
) -> dict:
    """
    Core Oracle tool. Evaluates whether a high-cost oncology prescription
    is likely to succeed for a specific patient.
    """

    # --- ADDED: Input Validation Safety Net ---
    try:
        if not patient_id or not patient_id.strip():
            raise ValueError("patient_id cannot be empty")
        if not drug_name or not drug_name.strip():
            raise ValueError("drug_name cannot be empty")
    except Exception as e:
        return {
            "triage_decision": "ERROR",
            "error": str(e),
            "recommendation": f"Invalid input: {str(e)}",
            "sharp_context": "received",
        }

    # ── Step 1: Resolve drug cost ────────────────────────────────────────────
    cost = resolve_drug_cost(drug_name, drug_cost_usd)

    if cost == 0.0:
        return {
            "triage_decision": "ERROR",
            "drug_name": drug_name,
            "drug_cost_usd": 0.0,
            "patient_id": patient_id,
            "error": (
                f"Drug '{drug_name}' not found in formulary and no cost override provided. "
                "Please provide drug_cost_usd manually."
            ),
            "sharp_context": "received",
        }

    # ── Step 2: Smart Triage Gate ─────────────────────────────────────────────
    if cost < TRIAGE_MIN:
        return {
            "triage_decision": "STANDARD_WORKFLOW",
            "drug_name": drug_name,
            "drug_cost_usd": cost,
            "patient_id": patient_id,
            "p_success": None,
            "confidence": None,
            "recommendation": (
                f"{drug_name.title()} costs ${cost:,.0f}/unit — below the $10,000 threshold."
            ),
            "factor_scores": None,
            "clinical_flags": [],
            "sharp_context": "received",
        }

    if cost > TRIAGE_MAX:
        return {
            "triage_decision": "BOARD_REVIEW",
            "drug_name": drug_name,
            "drug_cost_usd": cost,
            "patient_id": patient_id,
            "p_success": None,
            "confidence": None,
            "recommendation": (
                f"{drug_name.title()} costs ${cost:,.0f}/unit — requires Manual Board Review."
            ),
            "factor_scores": None,
            "clinical_flags": [],
            "sharp_context": "received",
        }

    # ── Step 3: Deep simulation ──────────────────────────────────────────────

    patient = get_patient(patient_id)
    if not patient:
        return {
            "triage_decision": "ERROR",
            "error": f"Patient '{patient_id}' not found.",
            "sharp_context": "received",
        }

    # Extract FHIR data
    genomic_factors    = extract_genomic_factors(patient_id)
    lab_factors        = extract_lab_factors(patient_id)
    medication_factors = extract_medication_factors(patient_id)

    # --- ADDED: Simulation Safety Net ---
    try:
        result = calculate_p_success(
            t790m_ratio      = genomic_factors.get("t790m_ratio", 0.0),
            cyp3a4_gas       = genomic_factors.get("cyp3a4_gas", 1.0),
            egfr_ml_min      = lab_factors.get("egfr_ml_min", 60.0),
            alt_u_l          = lab_factors.get("alt_u_l", 30.0),
            ast_u_l          = lab_factors.get("ast_u_l", 25.0),
            prior_pfs_months = medication_factors.get("prior_pfs_months", 0),
            best_response    = medication_factors.get("best_response", "unknown"),
        )
        alternative = None
        if result.p_success < 50.0:
            alternative = find_best_alternative(patient_id, drug_name, cost)
    except Exception as e:
        return {
            "triage_decision": "ERROR",
            "error": f"Simulation failed: {str(e)}",
            "recommendation": "Internal error during simulation. Please try again.",
            "sharp_context": "received",
        }
    # --- CFO Financial Impact Payload ---
    waste_prevented = cost if result.p_success < 50.0 else 0.0
    financial_impact = {
        "drug_cost_usd": cost,
        "waste_prevented_usd": waste_prevented,
        "financial_note": (
            f"By avoiding an ineffective prescription, Oracle avoided ${cost:,.0f} in wasted expenditure."
        ) if waste_prevented > 0 else "Prescription cost clinically justified by high simulated efficacy."
    }

    return {
        "triage_decision":      "SIMULATION_COMPLETE",
        "drug_name":            drug_name,
        "drug_cost_usd":        cost,
        "patient_id":           patient_id,
        "p_success":            result.p_success,
        "confidence":           result.confidence,
        "recommendation":       result.recommendation,
        "factor_scores":        result.factor_scores,
        "factor_contributions": result.factor_contributions,
        "clinical_flags":       result.clinical_flags,
        "suggested_alternative": alternative,
        "financial_impact":     financial_impact,
        "fhir_data_summary": {
            "egfr_mutation_status": genomic_factors.get("egfr_status"),
            "t790m_ratio":          genomic_factors.get("t790m_ratio"),
            "cyp3a4_phenotype":     genomic_factors.get("cyp3a4_phenotype"),
            "egfr_renal":           lab_factors.get("egfr_ml_min"),
            "alt_u_l":              lab_factors.get("alt_u_l"),
            "ast_u_l":              lab_factors.get("ast_u_l"),
            "prior_drug":           medication_factors.get("prior_drug"),
            "prior_pfs_months":     medication_factors.get("prior_pfs_months"),
            "best_response":        medication_factors.get("best_response"),
        },
        "sharp_context": "received",
        "error":         None,
        "scoring_context": {
            "weights_used": {
                "t790m_ratio":    "35% — primary genomic predictor (PMC8099906)",
                "cyp3a4_gas":     "25% — pharmacokinetic metabolism (PharmVar GAS)",
                "egfr_renal":     "20% — renal drug clearance (KDIGO staging)",
                "liver_function": "10% — hepatic CYP3A4 metabolism (CTCAE v5.0)",
                "prior_tki_pfs":  "10% — prior treatment response (PMC6468762)",
            },
            "interpretation_guide": {
                "p_success_above_65": "Simulation supports prescribing",
                "p_success_40_to_65": "Proceed with caution — MDT review recommended",
                "p_success_below_40": "High risk of non-response or toxicity",
            },
        },
        "llm_reasoning_prompt": (
            f"Patient {patient_id} has a {result.p_success}% predicted success probability "
            f"for {drug_name}. Key factors: "
            f"T790M ratio {genomic_factors.get('t790m_ratio')} (weight 35%), "
            f"CYP3A4 {genomic_factors.get('cyp3a4_phenotype')} (weight 25%), "
            f"eGFR {lab_factors.get('egfr_ml_min')} ml/min (weight 20%), "
            f"ALT {lab_factors.get('alt_u_l')} U/L (weight 10%), "
            f"prior PFS {medication_factors.get('prior_pfs_months')} months on "
            f"{medication_factors.get('prior_drug')} with {medication_factors.get('best_response')} response (weight 10%). "
            f"Clinical flags: {result.clinical_flags if result.clinical_flags else 'none'}. "
            f"Explain this result in clinical terms."
        ),
    }

# ── MCP Tool 2: list_patients ─────────────────────────────────────────────────

@mcp.tool()
def list_patients() -> dict:
    """
    Returns available synthetic patient profiles for demo/testing.
    In production this would be replaced by FHIR Patient search.

    Returns:
        dict with list of available patient_ids and brief clinical summaries.
    """
    return {
        "available_patients": [
            {
                "patient_id": "patient_001",
                "profile": "Good responder — high T790M ratio, normal metabolizer, healthy organ function",
                "expected_outcome": "HIGH success probability",
            },
            {
                "patient_id": "patient_002",
                "profile": "Poor responder — low T790M ratio, poor CYP3A4 metabolizer, impaired renal/liver function",
                "expected_outcome": "LOW success probability",
            },
            {
                "patient_id": "patient_003",
                "profile": "Borderline — moderate T790M ratio, intermediate metabolizer, mildly reduced organ function",
                "expected_outcome": "MODERATE-HIGH success probability",
            },
        ],
        "note": "All data is synthetic and de-identified. No real PHI.",
    }


# ── MCP Tool 3: get_drug_formulary ────────────────────────────────────────────

@mcp.tool()
def get_drug_formulary() -> dict:
    """
    Returns the internal drug cost formulary used by the triage gate.
    Clinicians can use this to check which drugs trigger deep simulation.

    Returns:
        dict with drug names, costs, and triage classifications.
    """
    formulary = []
    for drug, cost in DRUG_COST_TABLE.items():
        if cost < TRIAGE_MIN:
            tier = "STANDARD_WORKFLOW"
        elif cost <= TRIAGE_MAX:
            tier = "SIMULATION_TRIGGERED"
        else:
            tier = "BOARD_REVIEW"

        formulary.append({
            "drug_name": drug,
            "cost_usd": cost,
            "triage_tier": tier,
        })

    return {
        "formulary": sorted(formulary, key=lambda x: x["cost_usd"]),
        "triage_thresholds": {
            "standard_workflow_below": TRIAGE_MIN,
            "simulation_range": f"${TRIAGE_MIN:,.0f} – ${TRIAGE_MAX:,.0f}",
            "board_review_above": TRIAGE_MAX,
        },
    }

# -- MCP tool #4 Major update number 6 -------------------------------------------------------

@mcp.tool()
def patient_risk_summary(
        patient_id: str,
        fhir_context: dict | None = None, ) -> dict:
    """
    Returns a full clinical risk profile for a patient before any drug is mentioned.
    Use this as the first step in any clinical decision workflow.
    Accepts patient_id via SHARP context.
    """
    patient = get_patient(patient_id)
    if not patient:
        return {
            "error": f"Patient '{patient_id}' not found.",
            "valid_ids": ["patient_001", "patient_002", "patient_003"],
        }

    genomic_factors    = extract_genomic_factors(patient_id)
    lab_factors        = extract_lab_factors(patient_id)
    medication_factors = extract_medication_factors(patient_id)

    # Genomic risk
    t790m = genomic_factors.get("t790m_ratio", 0.0)
    cyp   = genomic_factors.get("cyp3a4_phenotype", "unknown")

    if t790m >= 0.40:
        genomic_risk = "FAVOURABLE"
    elif t790m >= 0.25:
        genomic_risk = "INTERMEDIATE"
    else:
        genomic_risk = "UNFAVOURABLE"

    # Renal risk
    egfr_val = lab_factors.get("egfr_ml_min", 60.0)
    if egfr_val >= 60:
        renal_risk = "NORMAL"
    elif egfr_val >= 45:
        renal_risk = "MILDLY_REDUCED"
    else:
        renal_risk = "SEVERELY_REDUCED"

    # Hepatic risk
    alt = lab_factors.get("alt_u_l", 35.0)
    ast = lab_factors.get("ast_u_l", 25.0)
    if alt <= 56 and ast <= 40:
        hepatic_risk = "NORMAL"
    elif alt <= 168:
        hepatic_risk = "MILDLY_ELEVATED"
    else:
        hepatic_risk = "SEVERELY_ELEVATED"

    # Metabolizer risk
    if cyp == "normal_metabolizer":
        metabolizer_risk = "STANDARD"
    elif cyp == "intermediate_metabolizer":
        metabolizer_risk = "REDUCED_CLEARANCE"
    else:
        metabolizer_risk = "HIGH_ACCUMULATION_RISK"

    # Overall risk tier
    risk_factors = [genomic_risk, renal_risk, hepatic_risk]
    if "UNFAVOURABLE" in risk_factors or "SEVERELY_REDUCED" in risk_factors or "SEVERELY_ELEVATED" in risk_factors:
        overall_risk = "HIGH"
    elif "INTERMEDIATE" in risk_factors or "MILDLY_REDUCED" in risk_factors or "MILDLY_ELEVATED" in risk_factors:
        overall_risk = "MODERATE"
    else:
        overall_risk = "LOW"

    return {
        "patient_id":     patient_id,
        "overall_risk_tier": overall_risk,
        "genomic_profile": {
            "egfr_mutation_status": genomic_factors.get("egfr_status"),
            "t790m_ratio":          t790m,
            "genomic_risk":         genomic_risk,
            "cyp3a4_phenotype":     cyp,
            "metabolizer_risk":     metabolizer_risk,
        },
        "organ_function": {
            "egfr_ml_min":  egfr_val,
            "renal_risk":   renal_risk,
            "alt_u_l":      alt,
            "ast_u_l":      ast,
            "hepatic_risk": hepatic_risk,
        },
        "treatment_history": {
            "prior_drug":        medication_factors.get("prior_drug"),
            "prior_pfs_months":  medication_factors.get("prior_pfs_months"),
            "best_response":     medication_factors.get("best_response"),
        },
        "clinical_note": (
            f"Patient presents with {overall_risk} overall risk profile. "
            f"Genomic status is {genomic_risk.lower()} for EGFR-targeted therapy. "
            f"Renal function is {renal_risk.lower().replace('_', ' ')}. "
            f"Hepatic function is {hepatic_risk.lower().replace('_', ' ')}. "
            f"CYP3A4 metabolizer status: {cyp.replace('_', ' ')}."
        ),
        "sharp_context": "received",
    }

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))

    print("=" * 60)
    print("  High-Stakes Efficacy Oracle — OracleMK1")
    print(f"  MCP Server starting on http://0.0.0.0:{port}")
    print("  Tools: evaluate_prescription | list_patients | get_drug_formulary")
    print("=" * 60)

    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)