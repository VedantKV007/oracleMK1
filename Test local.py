"""
test_local.py — Fixed for fastmcp 3.x session protocol
FastMCP 3.x streamable-http requires:
  1. POST /mcp to initialize session → get mcp-session-id header
  2. Use that session ID in all subsequent requests
"""

import httpx
import json

BASE = "http://localhost:8000/mcp"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def init_session(client: httpx.Client) -> str:
    """Initialize MCP session and return session ID."""
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "oracle-test-client", "version": "1.0.0"},
        },
    }
    r = client.post(BASE, json=payload, headers=HEADERS)
    session_id = r.headers.get("mcp-session-id", "")
    if not session_id:
        print("ERROR: No session ID returned. Response:")
        print(r.text)
        raise RuntimeError("Could not initialize MCP session")
    print(f"  Session initialized: {session_id[:16]}...")
    return session_id


def parse_sse(raw: str) -> dict:
    """Extract JSON payload from SSE response (data: {...} lines)."""
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                return json.loads(payload)
    raise ValueError(f"No data line found in SSE response:\n{raw}")


def call_tool(client: httpx.Client, session_id: str, name: str, arguments: dict, test_label: str):
    headers = {**HEADERS, "mcp-session-id": session_id}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    r = client.post(BASE, json=payload, headers=headers, timeout=15)

    # fastmcp 3.x returns SSE stream — parse data: lines
    try:
        data = r.json()
    except Exception:
        data = parse_sse(r.text)

    print(f"\n{'='*60}")
    print(f"  {test_label}")
    print(f"{'='*60}")

    try:
        content = data["result"]["content"][0]["text"]
        result = json.loads(content)
        print(f"  triage_decision : {result.get('triage_decision')}")
        print(f"  drug_name       : {result.get('drug_name')}")
        cost = result.get('drug_cost_usd')
        print(f"  drug_cost_usd   : ${cost:,.0f}" if cost else "  drug_cost_usd   : N/A")
        print(f"  p_success       : {result.get('p_success')}")
        print(f"  confidence      : {result.get('confidence')}")
        print(f"  recommendation  : {result.get('recommendation')}")
        if result.get("clinical_flags"):
            for flag in result["clinical_flags"]:
                print(f"  ⚠ flag          : {flag}")
        if result.get("fhir_data_summary"):
            print(f"  fhir_summary    : {result.get('fhir_data_summary')}")
        if result.get("available_patients"):
            for p in result["available_patients"]:
                print(f"  patient         : {p['patient_id']} — {p['expected_outcome']}")
    except Exception:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    print("\n=== OracleMK1 — Live Server Tests ===\n")

    with httpx.Client() as client:
        session_id = init_session(client)

        # Test 1 — Below $10k → STANDARD_WORKFLOW
        call_tool(client, session_id,
                  name="evaluate_prescription",
                  arguments={"patient_id": "patient_001", "drug_name": "bevacizumab"},
                  test_label="TEST 1 — Below threshold ($7,200) → expect STANDARD_WORKFLOW",
                  )

        # Test 2 — In range, good patient → HIGH
        call_tool(client, session_id,
                  name="evaluate_prescription",
                  arguments={"patient_id": "patient_001", "drug_name": "osimertinib"},
                  test_label="TEST 2 — Simulation, patient_001 + osimertinib → expect HIGH",
                  )

        # Test 3 — In range, poor patient → LOW
        call_tool(client, session_id,
                  name="evaluate_prescription",
                  arguments={"patient_id": "patient_002", "drug_name": "osimertinib"},
                  test_label="TEST 3 — Simulation, patient_002 + osimertinib → expect LOW",
                  )

        # Test 4 — Above $15k → BOARD_REVIEW
        call_tool(client, session_id,
                  name="evaluate_prescription",
                  arguments={"patient_id": "patient_001", "drug_name": "ipilimumab"},
                  test_label="TEST 4 — Above threshold ($16,200) → expect BOARD_REVIEW",
                  )

        # Test 5 — list_patients
        call_tool(client, session_id,
                  name="list_patients",
                  arguments={},
                  test_label="TEST 5 — list_patients tool",
                  )

    print("\n=== All tests complete ===")