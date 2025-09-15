import os
import requests
import json
import base64
import time
from pathlib import Path
from dotenv import load_dotenv

# Get the project root directory (parent of docs folder)
PROJECT_ROOT = Path(__file__).parent.parent

# Load variables from the .env file in the project root
env_path = PROJECT_ROOT / '.env'
if not env_path.exists():
    print(f"⚠️  Warning: .env file not found at {env_path}")
load_dotenv(env_path)

# --- Configuration ---
QUIX_TOKEN = os.getenv("QUIX_TOKEN")
QUIX_BASE_URL = os.getenv("QUIX_BASE_URL")
QUIX_WORKSPACE_ID = os.getenv("QUIX_WORKSPACE_ID")

# --- Clickhouse Configuration ---
APP_NAME = "Clickhouse Database"
APP_PATH = "clickhouse-db"
DEPLOYMENT_NAME = "Demo Clickhouse DB"

# Path to the template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "resources" / "_demo-clickhouse-db"


# A simple client to interact with the Quix Portal API
class QuixApiClient:
    """A helper class to simplify calls to the Quix Portal API."""
    def __init__(self, token, portal_api, workspace_id):
        if not all([token, portal_api, workspace_id]):
            raise ValueError("Please ensure QUIX_TOKEN, QUIX_BASE_URL, and QUIX_WORKSPACE_ID are set in your .env file.")
        self.token = token
        self.portal_api = portal_api
        self.headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json", "X-Version": "2.0"}

    def _handle_response(self, response):
        try:
            response.raise_for_status()
            return response.json() if response.text else None
        except requests.exceptions.HTTPError as e:
            print(f"API Error: {e.response.status_code} - {e.response.reason}")
            try: print(f"Response body: {e.response.json()}")
            except json.JSONDecodeError: print(f"Response body: {e.response.text}")
            raise
        except json.JSONDecodeError as e:
            print(f"Failed to decode JSON. Status: {response.status_code}, Body: '{response.text}'")
            raise

    def post(self, endpoint, data):
        return self._handle_response(requests.post(f"{self.portal_api}{endpoint}", headers=self.headers, json=data))
    def get(self, endpoint):
        return self._handle_response(requests.get(f"{self.portal_api}{endpoint}", headers=self.headers))
    def delete(self, endpoint):
        return self._handle_response(requests.delete(f"{self.portal_api}{endpoint}", headers=self.headers))


def load_template_files():
    """
    Loads all files from the template directory.
    Returns a dictionary with file paths and their base64 encoded contents.
    """
    if not TEMPLATE_DIR.exists():
        raise FileNotFoundError(f"Template directory not found: {TEMPLATE_DIR}")

    files = {}
    required_files = ['dockerfile', 'main.py', 'requirements.txt', 'app.yaml']
    found_files = []

    print(f"Loading template files from: {TEMPLATE_DIR}")

    for file_path in TEMPLATE_DIR.glob("*"):
        if file_path.is_file():
            with open(file_path, 'rb') as f:
                content = f.read()
                # Encode content to base64 for API
                encoded_content = base64.b64encode(content).decode('utf-8')
                # Store with relative filename
                files[file_path.name] = encoded_content
                found_files.append(file_path.name.lower())
                print(f"  - Loaded: {file_path.name} ({len(content)} bytes)")

    # Verify all required files are present
    missing_files = [f for f in required_files if f not in found_files]
    if missing_files:
        raise FileNotFoundError(f"Missing required template files: {', '.join(missing_files)}")

    return files

def create_files_in_repository(client: QuixApiClient, workspace_id: str, app_id: str, app_path: str):
    """
    Creates files directly in the workspace repository from template, returning the commit SHA.
    Uses the application ID to create a proper session.
    """
    print("Creating files directly in the repository via an IDE session...")
    session_id, commit_sha = None, None
    try:
        # Load template files
        template_files = load_template_files()

        if not template_files:
            raise ValueError("No files found in template directory")

        print("  - Creating IDE session for application...")
        session_payload = {
            "workspaceId": workspace_id,
            "applicationId": app_id,
            "branchName": "main",
            "cpuMillicores": 500,
            "memoryInMb": 1000
        }
        session_data = client.post("/sessions", session_payload)
        session_id = session_data['sessionId']
        print(f"  - Session created with ID: {session_id}")

        print("  - Updating application files from template...")

        # Create actions for all template files
        actions = []
        for filename, encoded_content in template_files.items():
            # Keep dockerfile lowercase - this is the correct one!
            actions.append({
                "action": "Update",  # Use Update since app already exists
                "filePath": filename,  # Use the exact filename (lowercase dockerfile)
                "content": encoded_content
            })
            print(f"    - Updating {filename}")

        # Commit all files in a single operation
        commit_payload = {
            "commitMessage": f"Deploy {APP_NAME} from template",
            "actions": actions
        }
        commit_data = client.post(f"/sessions/{session_id}/commit", commit_payload)
        commit_sha = commit_data['reference']
        print(f"  - Files committed. Commit SHA: {commit_sha}")

    finally:
        if session_id:
            print("  - Terminating session...")
            client.delete(f"/sessions/{session_id}")
            print("  - Session terminated successfully.")

    return commit_sha

def check_existing_application(client: QuixApiClient, workspace_id: str, app_path: str):
    """Check if an application already exists at the given path."""
    try:
        endpoint = f"/{workspace_id}/applications"
        apps = client.get(endpoint)
        for app in apps:
            if app.get('path') == app_path:
                return app['applicationId']
        return None
    except:
        return None

def register_application(client: QuixApiClient, workspace_id: str, app_name: str, app_path: str):
    """Registers an application from an existing folder in the repository."""
    # Check if app already exists
    existing_app_id = check_existing_application(client, workspace_id, app_path)
    if existing_app_id:
        print(f"ℹ️  Application already exists at path '{app_path}'. Using existing app ID: {existing_app_id}")
        return existing_app_id

    print(f"Registering folder as application '{app_name}'...")
    endpoint = f"/{workspace_id}/applications"
    payload = {"applicationName": app_name, "path": app_path, "language": "python"}
    app_data = client.post(endpoint, payload)
    print(f"Successfully registered application. ID: {app_data['applicationId']}")
    return app_data['applicationId']

def create_deployment(client: QuixApiClient, workspace_id: str, app_id: str, deployment_name: str, git_commit_sha: str):
    """Creates a deployment from a specific git commit."""
    print(f"Creating deployment '{deployment_name}'...")
    payload = {
        "workspaceId": workspace_id,
        "applicationId": app_id,
        "name": deployment_name,
        "gitReference": git_commit_sha,
        "deploymentType": "Service",
        "replicas": 1,
        "cpuMillicores": 500,
        "memoryInMb": 1000,
        "stateEnabled": False,
        "stateSize": 1,
        "publicAccess": True,
        "urlPrefix": "clickhousedb",
        "network": {
            "serviceName": "demo-clickhouse",
            "ports": [
                {"port": 80, "targetPort": 8123},
                {"port": 9000, "targetPort": 9000},
                {"port": 8123, "targetPort": 8123}
            ]
        },
        "variables": {}
    }
    deployment_data = client.post("/deployments", payload)
    print(f"Successfully initiated deployment. ID: {deployment_data['deploymentId']}")
    return deployment_data['deploymentId']

def poll_deployment_status(client: QuixApiClient, deployment_id: str):
    """Polls the deployment status until it's in a terminal state."""
    print(f"Polling status for deployment '{deployment_id}'...")
    running_statuses = ["Running", "Completed"]
    failed_statuses = ["DeploymentFailed", "BuildFailed", "RuntimeError", "Stopped"]
    while True:
        try:
            status_data = client.get(f"/deployments/{deployment_id}")
            status = status_data['status']
            print(f"  - Current status: {status}")
            if status in running_statuses:
                print("\n✅ Deployment is running successfully!")
                break
            if status in failed_statuses:
                print(f"\n❌ Deployment entered a failed state: {status}")
                print(f"   Reason: {status_data.get('statusReason', 'No reason provided.')}")
                break
            time.sleep(10)
        except Exception as e:
            print(f"An error occurred while polling: {e}")
            break

def main():
    """Main script execution."""
    try:
        print("="*60)
        print("🚀 Clickhouse Deployment Script")
        print("="*60)
        print(f"\n📁 Template directory: {TEMPLATE_DIR}")

        # Verify template directory exists
        if not TEMPLATE_DIR.exists():
            print(f"\n❌ Error: Template directory not found at {TEMPLATE_DIR}")
            print("Please ensure the _demo-clickhouse-db directory exists in resources/")
            return

        # Verify environment variables
        if not all([QUIX_TOKEN, QUIX_BASE_URL, QUIX_WORKSPACE_ID]):
            print("\n❌ Error: Missing required environment variables.")
            print("Please ensure the following are set in your .env file:")
            print("  - QUIX_TOKEN")
            print("  - QUIX_BASE_URL")
            print("  - QUIX_WORKSPACE_ID")
            return

        print(f"\n🌍 Workspace ID: {QUIX_WORKSPACE_ID}")
        print(f"🔗 API Base URL: {QUIX_BASE_URL}")
        print(f"📦 App will be deployed to: {APP_PATH}/")
        print("\n" + "="*60 + "\n")

        client = QuixApiClient(QUIX_TOKEN, QUIX_BASE_URL, QUIX_WORKSPACE_ID)

        # Step 1: Register the application first (creates empty app structure)
        application_id = register_application(client, QUIX_WORKSPACE_ID, APP_NAME, APP_PATH)

        # Step 2: Now update the application files from template using a session
        commit_sha = create_files_in_repository(client, QUIX_WORKSPACE_ID, application_id, APP_PATH)
        if not commit_sha:
            raise Exception("Failed to commit files to the repository.")

        # Step 3: Create the deployment
        deployment_id = create_deployment(client, QUIX_WORKSPACE_ID, application_id, DEPLOYMENT_NAME, commit_sha)

        # Step 4: Poll for the final status
        poll_deployment_status(client, deployment_id)

        print("\n" + "="*60)
        print("✅ Clickhouse deployment completed successfully!")
        print("\n🔗 Access your Clickhouse database:")
        print(f"   Internal access:")
        print(f"   - Service name: demo-clickhouse")
        print("   - Ports: 80 (HTTP), 8123 (HTTP), 9000 (Native)")
        print(f"\n   Public access:")
        print(f"   - URL: https://clickhousedb-[unique-id].deployments.quix.io")
        print("   - Default user: default (no password)")
        print("="*60 + "\n")
    except FileNotFoundError as e:
        print(f"\n❌ File Error: {e}")
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    main()