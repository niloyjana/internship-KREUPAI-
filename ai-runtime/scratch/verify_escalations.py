import requests
import json
import uuid
import time

def run_test(name, payload):
    print(f"\n--- Running Test: {name} ---")
    url = "http://localhost:8000/v1/finance/ap-officer/execute"
    request_data = {
        "executionId": str(uuid.uuid4()),
        "tenantId": "clt9x9x9x0000ux01v1v1v1v1", # This might need to be real
        "taskPayload": payload
    }
    
    try:
        response = requests.post(url, json=request_data)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            outcome = result.get("output", {}).get("outcome")
            reason = result.get("output", {}).get("reason")
            risk = result.get("output", {}).get("risk_score")
            print(f"Outcome: {outcome}")
            print(f"Risk Score: {risk}")
            print(f"Reason: {reason}")
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Connection Failed: {e}")

# Case 1: Happy Path
payload_happy = {
    "type": "process_invoice",
    "invoice_data": {
        "invoice_number": "INV-2024-SUCCESS",
        "vendor_name": "Global Logistics Ltd",
        "total_amount": 1250.00,
        "po_number": "PO-2024-882",
        "currency": "USD"
    }
}

# Case 2: Price Variance (Should Escalate)
payload_variance = {
    "type": "process_invoice",
    "invoice_data": {
        "invoice_number": "INV-2024-VAR-999",
        "vendor_name": "Global Logistics Ltd",
        "total_amount": 1850.00, # PO is 1250.00
        "po_number": "PO-2024-882",
        "currency": "USD"
    }
}

# Case 3: First-time Bank Details (Should Escalate)
payload_first_time = {
    "type": "process_invoice",
    "invoice_data": {
        "invoice_number": "INV-SECURITY-001",
        "vendor_name": "Global Logistics Ltd",
        "total_amount": 1250.00,
        "po_number": "PO-2024-882",
        "currency": "USD",
        "bank_details": {
            "iban": "US1234567890",
            "bank_name": "New Security Bank"
        }
    }
}

if __name__ == "__main__":
    # Give the server a moment to be ready if it just started
    time.sleep(2)
    run_test("Happy Path", payload_happy)
    run_test("Price Variance", payload_variance)
    run_test("First-time Bank Details", payload_first_time)
