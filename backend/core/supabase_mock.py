"""
Temporary mock for Supabase to allow app to run during debugging.
This will be replaced with proper Supabase when Python 3.14 compatibility is resolved.
"""

# Hardcoded users for local development
MOCK_USERS = {
    "Jhonalfredvillegas@outlook.es": {
        "password": "Vane0702.",
        "role": "admin",
        "company_id": "petroflow-admin"
    }
}

class MockUser:
    def __init__(self, email, role, company_id):
        self.id = f"test-user-{email}"
        self.email = email
        self.app_metadata = {"role": role, "company_id": company_id}

class MockSession:
    def __init__(self):
        self.access_token = "mock-token"

class MockResponse:
    def __init__(self, email, role, company_id):
        self.user = MockUser(email, role, company_id)
        self.session = MockSession()

class MockClient:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.auth = MockAuth()
        
class MockAuth:
    def sign_in_with_password(self, credentials):
        email = credentials.get("email", "")
        password = credentials.get("password", "")
        
        # Check against our mock database
        if email in MOCK_USERS and MOCK_USERS[email]["password"] == password:
            user_data = MOCK_USERS[email]
            return MockResponse(email, user_data["role"], user_data["company_id"])
        
        # If not found or wrong password, raise an exception to simulate Supabase error
        raise Exception("Invalid login credentials")
    
    def sign_out(self):
        pass

def create_client(url, key):
    return MockClient(url, key)

Client = MockClient
