# 🧬 OracleMK1: The LLM Simulation Engine for Hospitals

**An MCP-powered Clinical Decision Support system that enables Hospital AI Copilots to run deterministic biological simulations on high-risk therapies.**

Built for the **Prompt Opinion / Darena Health "Agents Assemble" Hackathon** *(Track 1: Build a Superpower)*.

---

## 🚨 The Problem: LLMs Cannot Simulate Biology

When a doctor asks an AI Copilot:

> *"Will Osimertinib work for Patient X?"*

a standard LLM typically generates an answer from generalized training patterns and statistical inference. In clinical environments, this is dangerous.

LLMs cannot:
- calculate pharmacogenomic response,
- model renal or hepatic drug clearance,
- validate contraindication severity,
- or execute deterministic biological simulations.

They generate plausible language — not mechanistic clinical reasoning.

In oncology, where a single treatment cycle can exceed **$15,000**, probabilistic guesses are not sufficient.

---

## 🚀 The Superpower: Predictive Clinical Simulation

OracleMK1 gives Hospital LLMs a deterministic mathematical reasoning layer through the **Model Context Protocol (MCP)**.

Instead of guessing, the AI Copilot securely passes a patient's identity through Darena Health's **SHARP protocol** into the Oracle engine. OracleMK1 then retrieves the patient's synthetic **FHIR R4** records and executes a weighted clinical simulation to predict therapeutic efficacy based on genomic, metabolic, and physiological factors.

The result is not a generated opinion.

It is a computationally auditable treatment simulation.

---

## ✨ The Simulation Pipeline

### 🤖 1. Clinical Hypothesis Trigger
The Hospital Copilot receives a physician prompt and invokes OracleMK1's `evaluate_prescription` MCP tool to test a treatment scenario.

### 🚦 2. Cost-Based Triage Gate
To optimize hospital compute utilization, OracleMK1 selectively bypasses low-risk generic medications and reserves full simulation workloads for high-cost therapies (typically \$10k–\$15k+).

### 🔬 3. Deterministic Biological Simulation
The engine calculates a `P_success` score using weighted clinical factors derived from structured FHIR observations.

#### Example Weighted Factors
- **Genomics**
  - T790M Driver Mutation Ratios *(35%)*
  - CYP3A4 Activity Scores *(25%)*
- **Clinical Biomarkers**
  - eGFR Renal Clearance *(20%)*
  - ALT/AST Hepatic Stress *(10%)*

### 🔄 4. Autonomous Alternative Drug Testing
If predicted efficacy falls below threshold (`Success < 50%`), OracleMK1 automatically runs background simulations against therapeutically adjacent alternatives to identify safer candidates.

### 💼 5. Financial Toxicity Analysis
The engine calculates projected pharmaceutical waste prevented by blocking ineffective treatment paths, returning ROI-aware clinical intelligence directly to the Copilot.

---

## 📐 Simulation Logic

OracleMK1 computes treatment success probability using a weighted deterministic model:

```math
P_{success} = \sum_{i=1}^{n}(w_i \cdot s_i)
