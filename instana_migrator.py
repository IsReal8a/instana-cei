
import argparse
import json
import logging
import os
import sys
import yaml
import urllib3

from api_endpoints import API_CONFIG
from instana_api import InstanaAPI
from utils import InstanaMigratorError, ConfigError, APIError

# --- Configuration ---

CONFIG_FILE = "config.yaml"
EXPORT_DIR = "export"
DRY_RUN_LOG_FILE = "dry_run_output.log"

# --- Setup ---

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


# --- Helper Functions ---

def setup_logging(log_level, log_file=None):
    """Sets up the logging configuration."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate logs
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Define the formatter
    log_format = "%(asctime)s [%(levelname)s] - %(message)s"
    formatter = logging.Formatter(log_format)

    # Always add the console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add the file handler if a filename is provided
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='w')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


def load_config(config_file):
    """Loads the YAML configuration file."""
    try:
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise ConfigError(f"Configuration file '{config_file}' not found.")
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing YAML file: {e}")


def clean_for_import(item, config_type):
    """Removes backend-specific keys from an object before import."""
    keys_to_remove = ['scope']

    if config_type == 'global-custom-payloads':
        keys_to_remove.extend(['lastUpdated', 'version'])
    elif (config_type == 'sli' or config_type == 'custom-event-specifications'):
        keys_to_remove.append('lastUpdated')
    # elif config_type == 'custom-event-specifications':
    #     keys_to_remove.append('lastUpdated')
    elif config_type == 'maintenance':
        # Keep the 'id' for the PUT_ITERATE method, but remove other server-generated fields
        keys_to_remove.extend(['lastUpdated', 'state', 'validVersion', 'occurrence', 'invalid'])
    elif config_type == 'groups':
        keys_to_remove.append('id')

    for key in keys_to_remove:
        if key in item:
            del item[key]

    if config_type == 'custom-dashboards':
        logger.debug("    - Cleaning custom dashboard-specific fields...")
        if 'ownerId' in item:
            del item['ownerId']
            logger.debug("      - Removed ownerId")

        if 'accessRules' in item and isinstance(item['accessRules'], list):
            original_rules_count = len(item['accessRules'])
            item['accessRules'] = [rule for rule in item['accessRules'] if rule.get('relationType') != 'USER']
            new_rules_count = len(item['accessRules'])
            if original_rules_count != new_rules_count:
                logger.debug(f"      - Removed {original_rules_count - new_rules_count} USER access rules.")

            has_global_read = any(rule.get('relationType') == 'GLOBAL' and rule.get('accessType') == 'READ' for rule in item['accessRules'])
            if not has_global_read:
                item['accessRules'].append({'accessType': 'READ', 'relationType': 'GLOBAL'})
                logger.debug("      - Added default GLOBAL READ access rule.")

            has_write_access = any(rule.get('accessType') == 'READ_WRITE' for rule in item['accessRules'])
            if not has_write_access:
                item['accessRules'].append({'accessType': 'READ_WRITE', 'relationType': 'GLOBAL'})
                logger.debug("      - Added default GLOBAL READ_WRITE access rule.")

    if config_type == 'manual-services':
        tfe = item.get('tagFilterExpression')
        is_invalid = False
        if tfe is not None:
            if not isinstance(tfe, dict) or tfe.get('operator') is None:
                is_invalid = True
        
        if is_invalid:
            logger.debug("    - Cleaning manual-service-specific fields...")
            if 'tagFilterExpression' in item:
                del item['tagFilterExpression']
                logger.debug("      - Removed invalid tagFilterExpression.")

    return item


# --- Core Functions ---

def export_config(config_type, backend_config, export_dir):
    """Exports a specific configuration type from a backend."""
    if config_type not in API_CONFIG:
        raise ConfigError(f"Unknown configuration type '{config_type}'")

    api = InstanaAPI(backend_config)
    cfg = API_CONFIG[config_type]
    
    logger.info(f"Exporting '{config_type}' from {api.base_url}...")

    data_to_save = []

    if config_type == 'custom-dashboards':
        logger.debug(f"  - Fetching dashboard list from {cfg['export_path']}")
        dashboard_summaries = api.get(cfg['export_path'])
        logger.info(f"  - Found {len(dashboard_summaries)} dashboards to export.")

        for summary in dashboard_summaries:
            dashboard_id = summary.get('id')
            if not dashboard_id:
                continue
            
            detail_path = f"{cfg['export_path']}/{dashboard_id}"
            logger.debug(f"    - Fetching full details for dashboard ID: {dashboard_id}")
            try:
                data_to_save.append(api.get(detail_path))
            except APIError as e:
                logger.warning(f"    - Could not fetch details for dashboard ID {dashboard_id}. Error: {e}")

    else:
        data_to_save = api.get(cfg['export_path'])

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    file_path = os.path.join(export_dir, f"{config_type}.json")
    with open(file_path, 'w') as f:
        json.dump(data_to_save, f, indent=2)

    count = 0
    if isinstance(data_to_save, list):
        count = len(data_to_save)
    elif isinstance(data_to_save, dict):
        # Handle case where services are nested under 'items'
        count = len(data_to_save.get('items', [1]))

    logger.info(f"Successfully exported {count} item(s) to {file_path}")


def import_config(config_type, backend_config, export_dir, dry_run=False):
    """Imports a specific configuration type to a backend."""
    if config_type not in API_CONFIG:
        raise ConfigError(f"Unknown configuration type '{config_type}'")

    file_path = os.path.join(export_dir, f"{config_type}.json")
    if not os.path.exists(file_path):
        raise InstanaMigratorError(f"Export file not found at '{file_path}'. Please run the export first.")

    with open(file_path, 'r') as f:
        data = json.load(f)
    
    if config_type == 'services' and isinstance(data, dict) and 'items' in data:
        data = data['items']

    api = InstanaAPI(backend_config)
    cfg = API_CONFIG[config_type]
    id_key = cfg.get('id_key')

    logger.info(f"Importing '{config_type}' to {api.base_url}...")
    if dry_run:
        logger.info("DRY RUN: No actual changes will be made.")

    if cfg['import_method'] == 'PUT':
        logger.info("Using PUT method to replace entire configuration...")
        payload = clean_for_import(data.copy(), config_type)
        
        if not dry_run:
            api.put(cfg['import_path'], json=payload)
        else:
            logger.info(f"  - (Dry Run) Would replace configuration for '{config_type}'")
            logger.info(f"    Payload: {json.dumps(payload, indent=2)}")

        logger.info(f"Successfully imported '{config_type}'.")
    
    elif cfg['import_method'] == 'POST':
        if not isinstance(data, list):
            data = [data]
        
        success_count = 0
        for item in data:
            item_id = 'N/A'
            """ Search for the id_key, if not found then we need to use the name (if available) """
            if id_key and item.get(id_key):
                item_id = item.get(id_key)
            elif 'name' in item:
                item_id = item.get('name')
            elif 'title' in item:
                item_id = item.get('title')

            payload = clean_for_import(item.copy(), config_type)
            
            logger.info(f"  - Preparing to import item: {item_id}")
            if not dry_run:
                try:
                    api.post(cfg['import_path'], json=payload)
                    success_count += 1
                    logger.info(f"  - Successfully imported item: {item_id}")
                except APIError as e:
                    logger.error(f"  - Failed to import item: {item_id}")
                    logger.error(f"    Error: {e}")
            else:
                success_count +=1
                logger.info(f"  - (Dry Run) Would import item: {item_id}")
                logger.info(f"    Payload: {json.dumps(payload, indent=2)}")

        logger.info(f"Import complete. Successfully imported {success_count}/{len(data)} items.")


    elif cfg['import_method'] == 'PUT_ITERATE':
        if not isinstance(data, list):
            data = [data]

        logger.info(f"Using PUT_ITERATE method to update items individually...")
        success_count = 0
        for item in data:
            # Use the primary id_key to get the ID for the URL
            item_id_for_url = item.get(id_key)
            if not item_id_for_url:
                logger.warning(f"  - Skipping item due to missing ID (using id_key: '{id_key}'). Item data: {item}")
                continue
            
            # Use 'name' for logging if available, otherwise fall back to the ID
            item_name_for_log = item.get('name', item_id_for_url)
            
            # The 'id' key must be in the payload for the PUT request to be valid
            payload = clean_for_import(item.copy(), config_type)
            import_url = f"{cfg['import_path']}/{item_id_for_url}"

            logger.info(f"  - Preparing to update item: {item_name_for_log} (ID: {item_id_for_url})")
            if not dry_run:
                try:
                    # The payload sent to the API for an update must contain the ID
                    payload['id'] = item_id_for_url
                    api.put(import_url, json=payload)
                    success_count += 1
                    logger.info(f"  - Successfully updated item: {item_name_for_log}")
                except APIError as e:
                    logger.error(f"  - Failed to update item: {item_name_for_log}")
                    logger.error(f"    Error: {e}")
            else:
                success_count += 1
                # The payload sent to the API for an update must contain the ID
                payload['id'] = item_id_for_url
                logger.info(f"  - (Dry Run) Would update item: {item_name_for_log}")
                logger.info(f"    URL: PUT {import_url}")
                logger.info(f"    Payload: {json.dumps(payload, indent=2)}")

        logger.info(f"Import complete. Successfully processed {success_count}/{len(data)} items.")

    logger.info(f"You can find all output on the dry_run_output.log file for reference.")

# --- Main Execution ---

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Instana Configuration Migrator")
    parser.add_argument("--config", default=CONFIG_FILE, help=f"Path to the configuration file (default: {CONFIG_FILE})")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Set the logging level (default: INFO)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_export = subparsers.add_parser("export", help="Export configuration from the source backend.")
    parser_export.add_argument("--type", required=True, help=f"The type of configuration to export. One of: {', '.join(list(API_CONFIG.keys()) + ['all'])}")
    parser_export.add_argument("--export-dir", default=EXPORT_DIR, help=f"Directory to store exported files (default: {EXPORT_DIR})")

    parser_import = subparsers.add_parser("import", help="Import configuration to the destination backend.")
    parser_import.add_argument("--type", required=True, help=f"The type of configuration to import. One of: {', '.join(list(API_CONFIG.keys()) + ['all'])}")
    parser_import.add_argument("--export-dir", default=EXPORT_DIR, help=f"Directory to read exported files from (default: {EXPORT_DIR})")
    parser_import.add_argument("--dry-run", action="store_true", help="Simulate an import without making any changes.")

    args = parser.parse_args()
    
    log_file = None
    if args.command == "import" and args.dry_run:
        log_file = DRY_RUN_LOG_FILE
        print(f"Dry run is enabled. Output will be logged to the console and to '{log_file}'.")

    setup_logging(args.log_level.upper(), log_file=log_file)

    try:
        config = load_config(args.config)
        types_to_process = list(API_CONFIG.keys()) if args.type == 'all' else [args.type]

        if args.command == "export":
            backend_config = config.get('source')
            if not backend_config:
                raise ConfigError("'source' configuration not found in config.yaml")
            for config_type in types_to_process:
                export_config(config_type, backend_config, args.export_dir)

        elif args.command == "import":
            backend_config = config.get('destination')
            if not backend_config:
                raise ConfigError("'destination' configuration not found in config.yaml")
            for config_type in types_to_process:
                import_config(config_type, backend_config, args.export_dir, args.dry_run)

    except (InstanaMigratorError, ConfigError, APIError) as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
