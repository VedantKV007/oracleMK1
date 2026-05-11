"""
mock_data.py — Synthetic FHIR R4 patient data for High-Stakes Efficacy Oracle
All data is fully synthetic and de-identified. No real PHI.
FHIR resource structure based on HL7 FHIR R4 specification.
LOINC codes used:
  - eGFR:  33914-3
  - ALT:   1742-6
  - AST:   1920-8
  - EGFR mutation: 81704-3
"""

PATIENTS = {

    # ── Patient 001 ─────────────────────────────────────────────────────────
    # Good responder profile: T790M-positive, normal metabolizer, healthy organs
    # Expected P_success: HIGH (70–85%)
    "patient_001": {
        "resourceType": "Patient",
        "id": "patient_001",
        "meta": {"profile": ["http://hl7.org/fhir/R4/patient.html"]},
        "identifier": [{"system": "urn:oracle:mk1:synthetic", "value": "PT-001"}],
        "gender": "female",
        "birthDate": "1962-04-15",
        "active": True,

        # FHIR Genomics — Observation resource (LOINC 81704-3)
        "genomics": {
            "resourceType": "Observation",
            "id": "obs-genomics-001",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "81704-3",
                    "display": "Genetic variant assessment"
                }]
            },
            "subject": {"reference": "Patient/patient_001"},
            "component": [
                {
                    "code": {"text": "EGFR mutation status"},
                    "valueString": "T790M_positive"
                },
                {
                    # T790M allelic fraction / EGFR driver AF ratio
                    # Research basis: PMC8099906 — higher ratio = better osimertinib response
                    # Ratio > 0.35 correlates with response (mean responders = 0.395)
                    "code": {"text": "T790M_ratio"},
                    "valueDecimal": 0.42
                },
                {
                    # CYP3A4 phenotype — osimertinib primary metabolism enzyme
                    # Gene Activity Score (GAS): poor=0, intermediate=0.5, normal=1, rapid=2
                    # Research basis: PharmVar / CYP2D6 GAS system
                    "code": {"text": "CYP3A4_phenotype"},
                    "valueString": "normal_metabolizer",
                    "valueDecimal": 1.0
                },
                {
                    "code": {"text": "EGFR_driver_mutation"},
                    "valueString": "L858R"
                }
            ]
        },

        # FHIR Lab Observations — renal and liver function
        "lab_observations": {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-egfr-001",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "33914-3",
                                "display": "Glomerular filtration rate/1.73 sq M.predicted"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_001"},
                        # eGFR >= 60 = normal/mildly reduced renal function
                        # Osimertinib dose adjustment not required above 45 ml/min/1.73m2
                        "valueQuantity": {
                            "value": 78.0,
                            "unit": "mL/min/1.73m2",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-alt-001",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1742-6",
                                "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_001"},
                        # ALT normal range: 7–56 U/L
                        # Elevated ALT signals hepatic stress → CYP3A4 impairment
                        "valueQuantity": {
                            "value": 28.0,
                            "unit": "U/L",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-ast-001",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1920-8",
                                "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_001"},
                        # AST normal range: 10–40 U/L
                        "valueQuantity": {
                            "value": 22.0,
                            "unit": "U/L",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                }
            ]
        },

        # FHIR MedicationRequest — prior TKI therapy history
        "medication_history": {
            "resourceType": "MedicationRequest",
            "id": "medrx-001",
            "status": "completed",
            "intent": "order",
            "subject": {"reference": "Patient/patient_001"},
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1860487",
                    "display": "Gefitinib"
                }]
            },
            "extension": [
                {
                    # Prior PFS on 1st-gen EGFR-TKI
                    # Research basis: PMC6468762 — prior PFS significantly predicts osimertinib PFS
                    # PFS > 12 months = good predictor of osimertinib response
                    "url": "prior_pfs_months",
                    "valueInteger": 16
                },
                {
                    "url": "best_response",
                    # CR=complete response, PR=partial response, SD=stable disease, PD=progressive disease
                    "valueString": "PR"
                }
            ]
        }
    },

    # ── Patient 002 ─────────────────────────────────────────────────────────
    # Poor responder profile: Low T790M ratio, poor metabolizer, impaired liver
    # Expected P_success: LOW (20–35%)
    "patient_002": {
        "resourceType": "Patient",
        "id": "patient_002",
        "meta": {"profile": ["http://hl7.org/fhir/R4/patient.html"]},
        "identifier": [{"system": "urn:oracle:mk1:synthetic", "value": "PT-002"}],
        "gender": "male",
        "birthDate": "1955-11-30",
        "active": True,

        "genomics": {
            "resourceType": "Observation",
            "id": "obs-genomics-002",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "81704-3",
                    "display": "Genetic variant assessment"
                }]
            },
            "subject": {"reference": "Patient/patient_002"},
            "component": [
                {
                    "code": {"text": "EGFR mutation status"},
                    "valueString": "T790M_positive"
                },
                {
                    # Low T790M ratio — below the 0.35 threshold from PMC8099906
                    # Non-responder range in study was mean 0.202
                    "code": {"text": "T790M_ratio"},
                    "valueDecimal": 0.18
                },
                {
                    # Poor metabolizer GAS = 0 — minimal CYP3A4 activity
                    # Drug accumulates → toxicity risk, unpredictable PK
                    "code": {"text": "CYP3A4_phenotype"},
                    "valueString": "poor_metabolizer",
                    "valueDecimal": 0.0
                },
                {
                    "code": {"text": "EGFR_driver_mutation"},
                    "valueString": "exon19_deletion"
                }
            ]
        },

        "lab_observations": {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-egfr-002",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "33914-3",
                                "display": "Glomerular filtration rate/1.73 sq M.predicted"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_002"},
                        # eGFR 30–44 = severely reduced — Stage 3b CKD
                        "valueQuantity": {
                            "value": 38.0,
                            "unit": "mL/min/1.73m2",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-alt-002",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1742-6",
                                "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_002"},
                        # ALT 112 — elevated (>3x ULN signals significant hepatotoxicity risk)
                        "valueQuantity": {
                            "value": 112.0,
                            "unit": "U/L",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-ast-002",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1920-8",
                                "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_002"},
                        "valueQuantity": {
                            "value": 98.0,
                            "unit": "U/L",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                }
            ]
        },

        "medication_history": {
            "resourceType": "MedicationRequest",
            "id": "medrx-002",
            "status": "completed",
            "intent": "order",
            "subject": {"reference": "Patient/patient_002"},
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1860487",
                    "display": "Erlotinib"
                }]
            },
            "extension": [
                {
                    # Short prior PFS — poor predictor of osimertinib response
                    "url": "prior_pfs_months",
                    "valueInteger": 6
                },
                {
                    "url": "best_response",
                    "valueString": "PD"
                }
            ]
        }
    },

    # ── Patient 003 ─────────────────────────────────────────────────────────
    # Borderline profile: moderate T790M ratio, intermediate metabolizer
    # Expected P_success: MODERATE (45–60%)
    "patient_003": {
        "resourceType": "Patient",
        "id": "patient_003",
        "meta": {"profile": ["http://hl7.org/fhir/R4/patient.html"]},
        "identifier": [{"system": "urn:oracle:mk1:synthetic", "value": "PT-003"}],
        "gender": "male",
        "birthDate": "1970-07-22",
        "active": True,

        "genomics": {
            "resourceType": "Observation",
            "id": "obs-genomics-003",
            "status": "final",
            "code": {
                "coding": [{
                    "system": "http://loinc.org",
                    "code": "81704-3",
                    "display": "Genetic variant assessment"
                }]
            },
            "subject": {"reference": "Patient/patient_003"},
            "component": [
                {
                    "code": {"text": "EGFR mutation status"},
                    "valueString": "T790M_positive"
                },
                {
                    # Near the mean T790M ratio for all patients (0.3643 from PMC8099906)
                    "code": {"text": "T790M_ratio"},
                    "valueDecimal": 0.36
                },
                {
                    # Intermediate metabolizer GAS = 0.5
                    "code": {"text": "CYP3A4_phenotype"},
                    "valueString": "intermediate_metabolizer",
                    "valueDecimal": 0.5
                },
                {
                    "code": {"text": "EGFR_driver_mutation"},
                    "valueString": "L858R"
                }
            ]
        },

        "lab_observations": {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-egfr-003",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "33914-3",
                                "display": "Glomerular filtration rate/1.73 sq M.predicted"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_003"},
                        # eGFR 45–59 = moderately reduced — Stage 3a CKD
                        "valueQuantity": {
                            "value": 54.0,
                            "unit": "mL/min/1.73m2",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-alt-003",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1742-6",
                                "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_003"},
                        # ALT mildly elevated — borderline hepatic stress
                        "valueQuantity": {
                            "value": 62.0,
                            "unit": "U/L",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                },
                {
                    "resource": {
                        "resourceType": "Observation",
                        "id": "obs-ast-003",
                        "status": "final",
                        "code": {
                            "coding": [{
                                "system": "http://loinc.org",
                                "code": "1920-8",
                                "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"
                            }]
                        },
                        "subject": {"reference": "Patient/patient_003"},
                        "valueQuantity": {
                            "value": 48.0,
                            "unit": "U/L",
                            "system": "http://unitsofmeasure.org"
                        }
                    }
                }
            ]
        },

        "medication_history": {
            "resourceType": "MedicationRequest",
            "id": "medrx-003",
            "status": "completed",
            "intent": "order",
            "subject": {"reference": "Patient/patient_003"},
            "medicationCodeableConcept": {
                "coding": [{
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1860487",
                    "display": "Gefitinib"
                }]
            },
            "extension": [
                {
                    # Moderate prior PFS — borderline predictor
                    "url": "prior_pfs_months",
                    "valueInteger": 11
                },
                {
                    "url": "best_response",
                    "valueString": "SD"
                }
            ]
        }
    }
}


def get_patient(patient_id: str) -> dict | None:
    """
    Retrieve synthetic FHIR patient bundle by patient_id.
    Returns None if patient not found.
    In production this would call a real FHIR server endpoint:
      GET /Patient/{patient_id}/$everything
    """
    return PATIENTS.get(patient_id)


def get_genomics(patient_id: str) -> dict | None:
    patient = get_patient(patient_id)
    if not patient:
        return None
    return patient.get("genomics")


def get_labs(patient_id: str) -> dict | None:
    patient = get_patient(patient_id)
    if not patient:
        return None
    return patient.get("lab_observations")


def get_medication_history(patient_id: str) -> dict | None:
    patient = get_patient(patient_id)
    if not patient:
        return None
    return patient.get("medication_history")


def extract_genomic_factors(patient_id: str) -> dict:
    """
    Pull the key genomic scoring inputs from the FHIR Observation resource.
    Returns a flat dict ready for the scoring engine.
    """
    genomics = get_genomics(patient_id)
    if not genomics:
        return {}

    result = {}
    for component in genomics.get("component", []):
        code_text = component.get("code", {}).get("text", "")
        if code_text == "T790M_ratio":
            result["t790m_ratio"] = component.get("valueDecimal", 0.0)
        elif code_text == "CYP3A4_phenotype":
            result["cyp3a4_gas"] = component.get("valueDecimal", 1.0)
            result["cyp3a4_phenotype"] = component.get("valueString", "normal_metabolizer")
        elif code_text == "EGFR mutation status":
            result["egfr_status"] = component.get("valueString", "unknown")

    return result


def extract_lab_factors(patient_id: str) -> dict:
    """
    Pull eGFR, ALT, AST from the FHIR Bundle of lab Observations.
    Returns a flat dict ready for the scoring engine.
    """
    labs = get_labs(patient_id)
    if not labs:
        return {}

    result = {}
    for entry in labs.get("entry", []):
        resource = entry.get("resource", {})
        loinc_code = ""
        for coding in resource.get("code", {}).get("coding", []):
            loinc_code = coding.get("code", "")

        value = resource.get("valueQuantity", {}).get("value", None)

        if loinc_code == "33914-3":
            result["egfr_ml_min"] = value
        elif loinc_code == "1742-6":
            result["alt_u_l"] = value
        elif loinc_code == "1920-8":
            result["ast_u_l"] = value

    return result


def extract_medication_factors(patient_id: str) -> dict:
    """
    Pull prior TKI response data from the FHIR MedicationRequest resource.
    Returns a flat dict ready for the scoring engine.
    """
    med = get_medication_history(patient_id)
    if not med:
        return {}

    result = {}
    for ext in med.get("extension", []):
        url = ext.get("url", "")
        if url == "prior_pfs_months":
            result["prior_pfs_months"] = ext.get("valueInteger", 0)
        elif url == "best_response":
            result["best_response"] = ext.get("valueString", "unknown")

    drug_name = med.get("medicationCodeableConcept", {}).get("coding", [{}])[0].get("display", "unknown")
    result["prior_drug"] = drug_name

    return result


if __name__ == "__main__":
    # Quick sanity check — run with: python mock_data.py
    print("=== OracleMK1 — Mock Data Sanity Check ===\n")
    for pid in ["patient_001", "patient_002", "patient_003"]:
        print(f"Patient: {pid}")
        print(f"  Genomics : {extract_genomic_factors(pid)}")
        print(f"  Labs     : {extract_lab_factors(pid)}")
        print(f"  Meds     : {extract_medication_factors(pid)}")
        print()