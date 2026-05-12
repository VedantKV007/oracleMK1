# 🧬 OracleMK1: The LLM Simulation Engine for Hospitals
**An MCP-powered Clinical Decision Support tool that allows Hospital AI Copilots to run predictive biological simulations.**

Built for the **Prompt Opinion / Darena Health "Agents Assemble" Hackathon** (Track 1: Build a Superpower).

## 🚨 The Problem: LLMs Cannot Simulate Biology
When a doctor asks an AI Copilot, *"Will Osimertinib work for Patient X?"*, the LLM typically relies on generic training data to generate an answer. **This is dangerous.** Standard LLMs cannot calculate pharmacogenomics, they cannot factor in real-time renal clearance rates, and they cannot run mathematical simulations. They hallucinate.

## 🚀 The Superpower: Predictive AI Simulation
OracleMK1 gives Hospital LLMs a mathematical "brain module" via the **Model Context Protocol (MCP)**. 

Instead of guessing, the AI Copilot securely passes the patient's ID (via Darena Health's **SHARP protocol**) into the Oracle. The Oracle then pulls the patient's synthetic **FHIR R4** records and runs a **weighted probability simulation** to predict the drug's exact efficacy based on their unique DNA and organ function.

## ✨ The Simulation Pipeline

* 🤖 **1. The "What-If" Trigger:** The LLM receives a prompt from the doctor and triggers the Oracle's `evaluate_prescription` tool to test a clinical hypothesis.
* 🚦 **2. The Smart Triage Gate:** To save hospital compute costs, the simulator refuses to run on cheap drugs (e.g., Amoxicillin). It only triggers the heavy simulation for high-stakes prescriptions ($10,000–$15,000).
* 🔬 **3. The Deep Biological Simulation:** The engine calculates a `P_Success` (0-100%) score by running the patient's FHIR data through a weighted algorithmic model:
    * *Genomic Factors:* T790M/AF Driver Ratios (35%) & CYP3A4 Gene Activity Scores (25%).
    * *Clinical Vitals:* eGFR Renal Clearance (20%) & Hepatic ALT/AST Stress (10%).
* 🔄 **4. Autonomous Scenario Testing:** If the simulation fails (Success < 50%), the Oracle automatically runs background simulations on alternative drugs in the same class to find a safer option for the LLM to recommend.
* 💼 **5. CFO Financial Output:** The simulator calculates the exact USD amount of wasted expenditure prevented by blocking the ineffective treatment, feeding ROI data directly back to the Copilot.

## 🛠️ MCP Tools Exposed to the LLM
1.  `evaluate_prescription(patient_id, drug_name)`: Runs the predictive scenario and returns the mathematical probability of success.
2.  `patient_risk_summary(patient_id)`: Allows the LLM to "read the room" by analyzing the patient's FHIR profile before a drug is even suggested.
3.  `get_drug_formulary()`: Allows the LLM to check hospital pricing rules and simulation thresholds.

## 💻 Tech Stack
* **Protocol:** `fastmcp` (Model Context Protocol / streamable-http)
* **Language:** Python 3.12
* **Integration:** Darena Health / Prompt Opinion Copilot (SHARP Context Native)
* **Data Layer:** Synthetic FHIR R4 
* **Deployment:** Railway (Persistent SSE connections)

## 🏁 How to Run Locally
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the MCP simulation server
python server.py

# 3. Test the LLM endpoints
python test_live.py
