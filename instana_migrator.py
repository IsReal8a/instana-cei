
import argparse
import json
import os
import sys
import requests
import yaml
import urllib3

# --- Configuration ---
CONFIG_FILE = "config.yaml"
EXPORT_DIR = "export"

# Maps CLI --type argument to API endpoints and methods
API_CONFIG = {
    "applications": {
        "export_path": "/application-monitoring/settings/application",
        "import_path": "/application-monitoring/settings/application",
        "import_method": "POST",
        "id_key": "name"
    },
    "services": {
        "export_path": "/application-monitoring/settings/services",
        "import_path": "/application-monitoring/settings/services",
        "import_method": "PUT"
    },
    "manual-services": {
        "export_path": "/application-monitoring/settings/manual-service",
        "import_path": "/application-monitoring/settings/manual-service",
        "import_method": "PUT"
    },
    "endpoints": {
        "export_path": "/application-monitoring/settings/endpoints",
        "import_path": "/application-monitoring/settings/endpoints",
        "import_method": "POST"
    },
    "http-endpoints": {
        "export_path": "/application-monitoring/settings/http-endpoints",
        "import_path": "/application-monitoring/settings/http-endpoints",
        "import_method": "POST"
    },
    "alert-channels": {
        "export_path": "/events/settings/alertingChannels",
        "import_path": "/events/settings/alertingChannels",
        "import_method": "POST",
        "id_key": "name"
    },
    "alert-configs": {
        "export_path": "/events/settings/alert-configs",
        "import_path": "/events/settings/alert-configs",
        "import_method": "PUT"
    },
    "global-smart-alerts": {
        "export_path": "/application-monitoring/settings/global-smart-alerts",
        "import_path": "/application-monitoring/settings/global-smart-alerts",
        "import_method": "POST"
    },
    "custom-event-specifications": {
        "export_path": "/events/settings/custom-event-specifications",
        "import_path": "/events/settings/custom-event-specifications",
        "import_method": "POST",
        "id_key": "name"
    },
    "global-custom-payloads": {
        "export_path": "/events/settings/global-custom-payloads",
        "import_path": "/events/settings/global-custom-payloads",
        "import_method": "PUT"
    },
    "synthetic-tests": {
        "export_path": "/synthetics/settings/tests",
        "import_path": "/synthetics/settings/tests",
        "import_method": "POST",
        "id_key": "label"
    },
    "synthetic-credentials": {
        "export_path": "/synthetics/settings/credentials",
        "import_path": "/synthetics/settings/credentials",
        "import_method": "POST",
        "id_key": "label"
    },
    "slo": {
        "export_path": "/sli/slo",
        "import_path": "/sli/slo",
        "import_method": "POST",
        "id_key": "name"
    },
    "sli": {
        "export_path": "/sli",
        "import_path": "/sli",
        "import_method": "POST",
        "id_key": "name"
    },
    "custom-dashboards": {
        "export_path": "/custom-dashboard",
        "import_path": "/custom-dashboard",
        "import_method": "POST",
        "id_key": "title"
    },
    "maintenance": {
        "export_path": "/settings/maintenance",
        "import_path": "/settings/maintenance",
        "import_method": "PUT"
    },
    "api-tokens": {
        "export_path": "/settings/api-tokens",
        "import_path": "/settings/api-tokens",
        "import_method": "POST",
        "id_key": "name"
    },
    "groups": {
        "export_path": "/settings/groups",
        "import_path": "/settings/groups",
        "import_method": "POST",
        "id_key": "name"
    },
    "website-config": {
        "export_path": "/website-monitoring/config",
        "import_path": "/website-monitoring/config",
        "import_method": "POST",
        "id_key": "label"
    },
    "mobile-app-config": {
        "export_path": "/mobile-app-monitoring/config",
        "import_path": "/mobile-app-monitoring/config",
        "import_method": "POST",
        "id_key": "label"
    }
}

# --- Helper Functions ---

def load_config():
    """Loads the YAML configuration file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}")
        sys.exit(1)

def get_api_headers(token):
    """Returns the standard API headers."""
    return {
        "Authorization": f"apiToken {token}",
        "Content-Type": "application/json"
    }

def handle_api_error(response, url):
    """Prints a formatted error from an API response and exits."""
    print(f"API Error: {response.status_code} for URL: {url}")
    try:
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print(response.text)
    sys.exit(1)

def clean_for_import(item, config_type):
    """Removes backend-specific keys from an object before import."""
    # General keys to remove for all types
    keys_to_remove = ['id', 'scope']
    for key in keys_to_remove:
        if key in item:
            del item[key]

    # Specific transformations for custom dashboards
    if config_type == 'custom-dashboards':
        print("    - Cleaning custom dashboard-specific fields...")
        if 'ownerId' in item:
            del item['ownerId']
            print("      - Removed ownerId")

        if 'accessRules' in item and isinstance(item['accessRules'], list):
            original_rules_count = len(item['accessRules'])
            item['accessRules'] = [rule for rule in item['accessRules'] if rule.get('relationType') != 'USER']
            new_rules_count = len(item['accessRules'])
            if original_rules_count != new_rules_count:
                print(f"      - Removed {original_rules_count - new_rules_count} USER access rules.")

            has_global_read = any(rule.get('relationType') == 'GLOBAL' and rule.get('accessType') == 'READ' for rule in item['accessRules'])
            if not has_global_read:
                item['accessRules'].append({'accessType': 'READ', 'relationType': 'GLOBAL'})
                print("      - Added default GLOBAL READ access rule.")

            has_write_access = any(rule.get('accessType') == 'READ_WRITE' for rule in item['accessRules'])
            if not has_write_access:
                item['accessRules'].append({'accessType': 'READ_WRITE', 'relationType': 'GLOBAL'})
                print("      - Added default GLOBAL READ_WRITE access rule.")

    # Specific transformations for manual services
    if config_type == 'manual-services':
        tfe = item.get('tagFilterExpression')
        is_invalid = False
        if tfe is not None:
            if not isinstance(tfe, dict) or tfe.get('operator') is None:
                is_invalid = True
        
        if is_invalid:
            print("    - Cleaning manual-service-specific fields...")
            if 'tagFilterExpression' in item:
                del item['tagFilterExpression']
                print("      - Removed invalid tagFilterExpression.")

    return item

def get_verify_option(backend_config):
    """Gets the verification option and disables warnings if needed."""
    verify = True
    if backend_config.get('allow_self_signed_certs', False):
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        verify = False
    return verify

# --- Core Functions ---

def export_config(config_type, backend_config):
    """Exports a specific configuration type from a backend."""
    if config_type not in API_CONFIG:
        print(f"Error: Unknown configuration type '{config_type}'")
        return

    cfg = API_CONFIG[config_type]
    base_url = backend_config['api_url'].rstrip('/')
    headers = get_api_headers(backend_config['api_token'])
    verify = get_verify_option(backend_config)
    
    print(f"Exporting '{config_type}' from {base_url}...")

    data_to_save = []

    if config_type == 'custom-dashboards':
        list_url = base_url + cfg['export_path']
        print(f"  - Fetching dashboard list from {list_url}")
        list_response = requests.get(list_url, headers=headers, verify=verify)
        if not list_response.ok:
            handle_api_error(list_response, list_url)
        
        dashboard_summaries = list_response.json()
        print(f"  - Found {len(dashboard_summaries)} dashboards to export.")

        for summary in dashboard_summaries:
            dashboard_id = summary.get('id')
            if not dashboard_id:
                continue
            
            detail_url = f"{list_url}/{dashboard_id}"
            print(f"    - Fetching full details for dashboard ID: {dashboard_id}")
            detail_response = requests.get(detail_url, headers=headers, verify=verify)
            
            if detail_response.ok:
                data_to_save.append(detail_response.json())
            else:
                print(f"    - Warning: Could not fetch details for dashboard ID {dashboard_id}. Status: {detail_response.status_code}")

    else:
        url = base_url + cfg['export_path']
        response = requests.get(url, headers=headers, verify=verify)
        if not response.ok:
            handle_api_error(response, url)
        data_to_save = response.json()

    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)

    file_path = os.path.join(EXPORT_DIR, f"{config_type}.json")
    with open(file_path, 'w') as f:
        json.dump(data_to_save, f, indent=2)

    count = len(data_to_save) if isinstance(data_to_save, list) else 1
    print(f"Successfully exported {count} item(s) to {file_path}")

def import_config(config_type, backend_config):
    """Imports a specific configuration type to a backend."""
    if config_type not in API_CONFIG:
        print(f"Error: Unknown configuration type '{config_type}'")
        return

    file_path = os.path.join(EXPORT_DIR, f"{config_type}.json")
    if not os.path.exists(file_path):
        print(f"Error: Export file not found at '{file_path}'. Please run the export first.")
        return

    with open(file_path, 'r') as f:
        data = json.load(f)

    cfg = API_CONFIG[config_type]
    url = backend_config['api_url'].rstrip('/') + cfg['import_path']
    headers = get_api_headers(backend_config['api_token'])
    id_key = cfg.get('id_key', 'id')
    verify = get_verify_option(backend_config)

    print(f"Importing '{config_type}' to {backend_config['api_url']}...")

    if cfg['import_method'] == 'PUT':
        print("Using PUT method to replace entire configuration...")
        response = requests.put(url, headers=headers, data=json.dumps(data), verify=verify)
        if not response.ok:
            handle_api_error(response, url)
        print(f"Successfully imported '{config_type}'.")
    
    elif cfg['import_method'] == 'POST':
        if not isinstance(data, list):
            data = [data]
        
        success_count = 0
        for item in data:
            item_id = item.get(id_key, 'N/A')
            payload = clean_for_import(item, config_type)
            response = requests.post(url, headers=headers, data=json.dumps(payload), verify=verify)
            if response.ok:
                success_count += 1
                print(f"  - Successfully imported item: {item_id}")
            else:
                print(f"  - Failed to import item: {item_id} (Status: {response.status_code})")
                try:
                    print(f"    Error: {json.dumps(response.json())}")
                except json.JSONDecodeError:
                    print(f"    Error: {response.text}")
        print(f"Import complete. Successfully imported {success_count}/{len(data)} items.")


# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(description="Instana Configuration Migrator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_export = subparsers.add_parser("export", help="Export configuration from the source backend.")
    parser_export.add_argument("--type", required=True, help=f"The type of configuration to export. One of: {', '.join(list(API_CONFIG.keys()) + ['all'])}")

    parser_import = subparsers.add_parser("import", help="Import configuration to the destination backend.")
    parser_import.add_argument("--type", required=True, help=f"The type of configuration to import. One of: {', '.join(list(API_CONFIG.keys()) + ['all'])}")

    args = parser.parse_args()
    
    config = load_config()
    types_to_process = list(API_CONFIG.keys()) if args.type == 'all' else [args.type]

    if args.command == "export":
        backend_config = config.get('source')
        if not backend_config:
            print("Error: 'source' configuration not found in config.yaml")
            sys.exit(1)
        for config_type in types_to_process:
            export_config(config_type, backend_config)

    elif args.command == "import":
        backend_config = config.get('destination')
        if not backend_config:
            print("Error: 'destination' configuration not found in config.yaml")
            sys.exit(1)
        for config_type in types_to_process:
            import_config(config_type, backend_config)

if __name__ == "__main__":
    main()
