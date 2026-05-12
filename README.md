# 🧬 OracleMK1: The LLM Simulation Engine for Hospitals

**An MCP-powered Clinical Decision Support system that enables Hospital AI Copilots to run deterministic biological compatible simulations on high-cost Drugs.**

Built for the **Prompt Opinion / Darena Health "Agents Assemble" Hackathon 2026 ** *(Track 1: Build a Superpower).*

---

# 🚨 The Problem: LLMs Cannot Simulate Biology

When a doctor asks an AI Copilot:

> *"Will Osimertinib work for Patient X?"*

the LLM typically relies on generalized training data to generate a probabilistic response.

**This is dangerous.**

Standard LLMs cannot:
- calculate pharmacogenomic interactions,
- model renal or hepatic drug clearance,
- evaluate mutation-specific efficacy,
- or run deterministic clinical simulations.

They generate plausible language — not biological validation.

In oncology, a single failed therapy can cost:
- months of patient suffering,
- irreversible toxicity,
- and \$15,000+ in pharmaceutical waste.

OracleMK1 was built on a simple belief:

> oncology is not a language problem.  
> it is a biological one.

---

# 🚀 The Superpower: Predictive Clinical Simulation

OracleMK1 gives Hospital AI Copilots a mathematical reasoning layer through the **Model Context Protocol (MCP)**.

Instead of guessing, the Copilot securely passes a patient context ID through Darena Health's **SHARP protocol** into the Oracle engine.

OracleMK1 then:
1. pulls the patient's synthetic **FHIR R4** records,
2. extracts genomic + physiological biomarkers,
3. runs a weighted simulation model,
4. and returns an evidence-grounded probability of treatment success.

The result is a deterministic clinical reasoning workflow instead of probabilistic autocomplete.

---

# ✨ The Simulation Pipeline

## 🤖 1. Clinical "What-If" Trigger
The LLM receives a physician prompt and invokes the Oracle's `evaluate_prescription()` MCP tool to test a treatment hypothesis.

---

## 🚦 2. Cost-Based Triage Gate
To reduce unnecessary hospital compute expenditure, OracleMK1 refuses to run expensive simulations on low-risk medications.

Simulation only activates for:
- high-cost,
- high-risk,
- clinically consequential therapies.

*(e.g. \$10,000–\$15,000 oncology prescriptions)*

---

## 🔬 3. Deep Biological Simulation

The engine computes a `P_success` score using weighted biological factors derived from structured FHIR observations.

### Weighted Factors
| Signal | Weight |
|---|---|
| T790M / AF Driver Mutation Ratios | 35% |
| CYP3A4 Pharmacogenomic Activity | 25% |
| eGFR Renal Clearance | 20% |
| Hepatic ALT/AST Toxicity Stress | 10% |

This allows OracleMK1 to mathematically estimate therapeutic viability before treatment begins.

---

## 🔄 4. Autonomous Scenario Testing

If the predicted success probability falls below threshold:

```python
P_success < 0.50
