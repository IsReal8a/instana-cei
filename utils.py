
import json

# --- Custom Exceptions ---

class InstanaMigratorError(Exception):
    """Base exception for the Instana Migrator."""
    pass

class ConfigError(InstanaMigratorError):
    """Exception for configuration-related errors."""
    pass

class APIError(InstanaMigratorError):
    """Exception for API-related errors."""
    pass


# --- Helper Functions ---

def get_api_headers(token):
    """Returns the standard API headers."""
    return {
        "Authorization": f"apiToken {token}",
        "Content-Type": "application/json"
    }

def handle_api_error(response, url):
    """Raises a formatted APIError from an API response."""
    try:
        details = json.dumps(response.json(), indent=2)
    except json.JSONDecodeError:
        details = response.text
    raise APIError(f"API Error: {response.status_code} for URL: {url}\n{details}")
