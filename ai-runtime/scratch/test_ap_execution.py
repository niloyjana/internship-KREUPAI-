
import requests
import json

url = "http://localhost:8000/v1/finance/ap-officer/execute"
payload = {
    "executionId": "test-exec-001",
    "tenantId": "cmostem4m0000y76cglzikowk",
    "taskPayload": {
        "type": "process_invoice",
        "vendor_name": "Global Logistics Ltd",
        "invoice_number": "INV-VAR-999",
        "total_amount": 1400.00,
        "currency": "USD",
        "po_number": "PO-2024-882",
        "line_items": [
            {"description": "Shipping Services", "quantity": 1, "unit_price": 1400.00}
        ]
    }
}

response = requests.post(url, json=payload)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
