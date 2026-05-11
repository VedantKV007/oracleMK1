"""
test_live.py — Test the live Railway deployment
"""

import httpx
import json

BASE = "https://oraclemk1-production.up.railway.app/mcp"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def parse_sse(raw: str) -> dict:
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                return json.loads(payload)
    raise ValueError(f"No data line found in SSE response:\n{raw}")


def init_session(client: httpx.Client) -> str:
    payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "oracle-live-test", "version": "1.0.0"},
        },
    }
    r = client.post(BASE, json=payload, headers=HEADERS, timeout=30)
    session_id = r.headers.get("mcp-session-id", "")
    if not session_id:
        print("ERROR: No session ID. Response:")
        print(r.text)
        raise RuntimeError("Could not initialize session")
    print(f"  ✅ Live server reached. Session: {session_id[:16]}...")
    return session_id


def call_tool(client, session_id, name, arguments, label):
    headers = {**HEADERS, "mcp-session-id": session_id}
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    r = client.post(BASE, json=payload, headers=headers, timeout=30)

    try:
        data = r.json()
    except Exception:
        data = parse_sse(r.text)

    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")

    try:
        content = data["result"]["content"][0]["text"]
        result = json.loads(content)
        print(f"  triage_decision : {result.get('triage_decision')}")
        print(f"  p_success       : {result.get('p_success')}")
        print(f"  confidence      : {result.get('confidence')}")
        print(f"  recommendation  : {result.get('recommendation')}")
        if result.get("clinical_flags"):
            for flag in result["clinical_flags"]:
                print(f"  ⚠               : {flag}")
    except Exception:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    print("\n=== OracleMK1 — LIVE Railway Tests ===")
    print(f"  Endpoint: {BASE}\n")

    with httpx.Client() as client:
        session_id = init_session(client)

        call_tool(client, session_id,
            name="evaluate_prescription",
            arguments={"patient_id": "patient_001", "drug_name": "bevacizumab"},
            label="TEST 1 — Below threshold → STANDARD_WORKFLOW",
        )

        call_tool(client, session_id,
            name="evaluate_prescription",
            arguments={"patient_id": "patient_001", "drug_name": "osimertinib"},
            label="TEST 2 — patient_001 + osimertinib → HIGH",
        )

        call_tool(client, session_id,
            name="evaluate_prescription",
            arguments={"patient_id": "patient_002", "drug_name": "osimertinib"},
            label="TEST 3 — patient_002 + osimertinib → LOW",
        )

        call_tool(client, session_id,
            name="evaluate_prescription",
            arguments={"patient_id": "patient_001", "drug_name": "ipilimumab"},
            label="TEST 4 — Above threshold → BOARD_REVIEW",
        )

    print("\n=== Live tests complete. Oracle is deployed. ===")
