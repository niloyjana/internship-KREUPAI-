import requests
import json

url = "http://localhost:8000/v1/agent/execute"

# This payload uses the JSON stringified "task" payload typical of the portal
task_payload_str = json.dumps({
    "task_type": "quality_report",
    "build_id": "b-2024-05-17",
    "feature_name": "Authentication Redesign",
    "requirements": ["Must support 2FA", "Must integrate with SSO"],
    "defects": [
        {"id": "DEF-100", "title": "Login crash on mobile", "description": "App crashes when typing in password on iOS", "status": "open"}
    ],
    "test_results": [
        {"id": "TR-1", "name": "test_sso_login", "status": "passed"},
        {"id": "TR-2", "name": "test_2fa_prompt", "status": "failed"},
        {"id": "TR-3", "name": "test_password_reset", "status": "passed"}
    ]
})

payload = {
    "executionId": "test-exec-qa-001",
    "tenantId": "cmostem4m0000y76cglzikowk",
    "agentId": "ai-qa-coordinator",
    "stepId": "step-qa-1",
    "taskPayload": {
        "task": task_payload_str
    }
}

print(f"Sending request to {url} for QA Coordinator...")
response = requests.post(url, json=payload)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    print(json.dumps(response.json(), indent=2))
else:
    print(response.text)
