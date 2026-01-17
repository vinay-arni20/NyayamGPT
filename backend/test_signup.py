import requests
import json

url = "http://127.0.0.1:8000/auth/signup"
payload = {
    "email": "test_api_check@example.com",
    "password": "TestPass123!",
    "confirm_password": "TestPass123!",
    "full_name": "Test API Check"
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Request failed: {e}")
