import requests

def login_and_get_agents():
    base_url = "http://localhost:7860"  # Replace with your server address if different

    credentials = {
        "email_or_username": "subshur_tester",
        "password": "helsinki77&&"
    }

    # Login to obtain a token
    login_response = requests.post(f"{base_url}/auth/login", json=credentials)
    if login_response.status_code != 200:
        print("Failed to login:", login_response.json())
        return

    login_data = login_response.json()
    token = login_data.get('token')
    print("Successfully logged in!")

    # Fetch agents using the token
    headers = {
        "Authorization": f"Bearer {token}"
    }

    agents_response = requests.get(f"{base_url}/agents", headers=headers)
    if agents_response.status_code != 200:
        print("Failed to fetch agents:", agents_response.json())
        return

    agents = agents_response.json()
    print("Agents:", agents)

if __name__ == "__main__":
    login_and_get_agents()
