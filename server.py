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
from dotenv import load_dotenv
from fastmcp import FastMCP
from mock_data import (
    get_patient,
    extract_genomic_factors,
    extract_lab_factors,
    extract_medication_factors,
)
from scoring import calculate_p_success

load_dotenv()

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

DRUG_COST_TABLE = {
    "osimertinib":   12400.0,   # Tagrisso — 3rd gen EGFR-TKI (in triage range)
    "tagrisso":      12400.0,   # Brand name alias
    "pembrolizumab": 13800.0,   # Keytruda — PD-1 inhibitor (in triage range)
    "keytruda":      13800.0,   # Brand name alias
    "nivolumab":     11200.0,   # Opdivo — PD-1 inhibitor (in triage range)
    "opdivo":        11200.0,   # Brand name alias
    "cetuximab":     8500.0,    # Erbitux — below threshold (standard workflow)
    "bevacizumab":   7200.0,    # Avastin — below threshold
    "trastuzumab":   6800.0,    # Herceptin — below threshold
    "ipilimumab":    16200.0,   # Yervoy — above threshold (board review)
    "atezolizumab":  15800.0,   # Tecentriq — above threshold
}

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


# ── MCP Tool 1: evaluate_prescription ────────────────────────────────────────

@mcp.tool()
def evaluate_prescription(
        patient_id: str,
        drug_name: str,
        drug_cost_usd: float | None = None,
) -> dict:
    """
    Core Oracle tool. Evaluates whether a high-cost oncology prescription
    is likely to succeed for a specific patient.

    Implements the Smart Triage Gate:
      - Below $10,000  → Standard Workflow (no simulation needed)
      - $10,000–$15,000 → Deep Simulation (genomic + clinical scoring)
      - Above $15,000  → Manual Board Review Required

    Args:
        patient_id    : SHARP context token — secure patient identifier
                        (e.g. "patient_001", "patient_002", "patient_003")
        drug_name     : Name of the prescribed drug (generic or brand)
                        (e.g. "osimertinib", "pembrolizumab")
        drug_cost_usd : Optional unit cost override in USD.
                        If omitted, cost is resolved from internal formulary.

    Returns:
        dict with keys:
          triage_decision   : "STANDARD_WORKFLOW" | "SIMULATION_COMPLETE" | "BOARD_REVIEW"
          drug_name         : Resolved drug name
          drug_cost_usd     : Resolved cost
          patient_id        : Echo of patient identifier
          p_success         : Success probability 0–100% (simulation only)
          confidence        : HIGH | MODERATE | LOW (simulation only)
          recommendation    : Clinical recommendation string
          factor_scores     : Individual normalised factor scores (simulation only)
          clinical_flags    : List of clinical warnings (simulation only)
          sharp_context     : Confirms SHARP context was received
    """

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
        # Below threshold — standard workflow, no simulation needed
        return {
            "triage_decision": "STANDARD_WORKFLOW",
            "drug_name": drug_name,
            "drug_cost_usd": cost,
            "patient_id": patient_id,
            "p_success": None,
            "confidence": None,
            "recommendation": (
                f"{drug_name.title()} costs ${cost:,.0f}/unit — below the $10,000 "
                "high-stakes threshold. Standard prescribing workflow applies. "
                "No deep simulation required."
            ),
            "factor_scores": None,
            "clinical_flags": [],
            "sharp_context": "received",
        }

    if cost > TRIAGE_MAX:
        # Above threshold — too high-stakes for automated simulation
        return {
            "triage_decision": "BOARD_REVIEW",
            "drug_name": drug_name,
            "drug_cost_usd": cost,
            "patient_id": patient_id,
            "p_success": None,
            "confidence": None,
            "recommendation": (
                f"{drug_name.title()} costs ${cost:,.0f}/unit — above the $15,000 "
                "automated simulation ceiling. Manual multidisciplinary board review "
                "is required before prescribing. Please escalate to the clinical review board."
            ),
            "factor_scores": None,
            "clinical_flags": [],
            "sharp_context": "received",
        }

    # ── Step 3: Deep simulation ($10,000–$15,000 range) ──────────────────────

    # Verify patient exists in FHIR data layer
    patient = get_patient(patient_id)
    if not patient:
        return {
            "triage_decision": "ERROR",
            "drug_name": drug_name,
            "drug_cost_usd": cost,
            "patient_id": patient_id,
            "error": (
                f"Patient '{patient_id}' not found in FHIR data layer. "
                "Valid IDs: patient_001, patient_002, patient_003"
            ),
            "sharp_context": "received",
        }

    # Extract FHIR data via SHARP context patient_id
    genomic_factors    = extract_genomic_factors(patient_id)
    lab_factors        = extract_lab_factors(patient_id)
    medication_factors = extract_medication_factors(patient_id)

    # Run weighted probability simulation
    result = calculate_p_success(
        t790m_ratio      = genomic_factors.get("t790m_ratio", 0.0),
        cyp3a4_gas       = genomic_factors.get("cyp3a4_gas", 1.0),
        egfr_ml_min      = lab_factors.get("egfr_ml_min", 60.0),
        alt_u_l          = lab_factors.get("alt_u_l", 30.0),
        ast_u_l          = lab_factors.get("ast_u_l", 25.0),
        prior_pfs_months = medication_factors.get("prior_pfs_months", 0),
        best_response    = medication_factors.get("best_response", "unknown"),
    )

    return {
        "triage_decision": "SIMULATION_COMPLETE",
        "drug_name": drug_name,
        "drug_cost_usd": cost,
        "patient_id": patient_id,
        "p_success": result.p_success,
        "confidence": result.confidence,
        "recommendation": result.recommendation,
        "factor_scores": result.factor_scores,
        "factor_contributions": result.factor_contributions,
        "clinical_flags": result.clinical_flags,
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


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))

    print("=" * 60)
    print("  High-Stakes Efficacy Oracle — OracleMK1")
    print(f"  MCP Server starting on http://0.0.0.0:{port}")
    print("  Tools: evaluate_prescription | list_patients | get_drug_formulary")
    print("=" * 60)

    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)