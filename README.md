# Instana Configuration Exporter/Importer

NOTE: This project has been archived in favor of the [Official Instana Configuration migration tool](https://github.com/instana/automation-with-apis)

This tool allows you to export/import Instana's backend configuration.

Useful for:
- Migrations
- Backup
- Disaster recovery

## Important 
This is a work in progress project and needs to be tested by more Instana users... it can be use in a test environment but the more feedback the better to promote it for Production environments.
Please check `api_endpoints.py` to see which API endpoints are working.
For some weird reason the Custom Dashboards stopped to work, need to throubleshoot that.

## Setup

1.  **Install Dependencies:**

    ```bash
    python3 -m venv path/to/venv
    source path/to/venv/bin/activate
    pip3 install -r requirements.txt
    ```

2.  **Configure Backends:**
    Create and edit the `config.yaml` file to include the full API URL (including the `/api` suffix) and an API token for both, your source and destination Instana backends.

    To connect to a backend with a self-signed SSL certificate, set `allow_self_signed_certs: true` for that backend configuration.

    ```yaml
    # Example:
    source:
      api_url: "https://your-unit-name.instana.io/api"
      api_token: "your_source_api_token"
      allow_self_signed_certs: false
    destination:
      api_url: "https://internal-instana-server/api"
      api_token: "your_destination_api_token"
      allow_self_signed_certs: true
    ```

## Usage

The tool uses an `export` and `import` command structure. An `export` directory will be created to store the configuration files. It will create a log file where you can see the full output (useful when using the `all` configuration type).

### Exporting

You can export a specific configuration type or all configurations at once.

While exporting the custom dashboards, if you have too many, it will take a while to export the configuration, just wait.

```bash
# Export a single type (e.g., custom dashboards)
python instana_migrator.py export --type custom-dashboards
```

```bash
# Export all available configurations
python instana_migrator.py export --type all
```

### Importing

You can import a specific configuration type or all configurations at once. It is important to note that you can use the `--dry-run` option and test before apply changes.

```bash
# Import a single type (e.g., custom dashboards)
python instana_migrator.py import --type custom-dashboards --dry-run
```

```bash
# Import all available configurations
python instana_migrator.py import --type all --dry-run
```

### Supported Configuration Types

The `--type` flag accepts the following values:
Working
- `applications`
- `services`
- `manual-services`
- `alert-channels`
- `alert-configs`
- `global-application-smart-alerts`
- `custom-event-specifications`
- `global-custom-payloads`
- `maintenance`
- `api-tokens`
- `groups`
- `custom-dashboards`
- `all`

Not Working
- `synthetic-tests`
- `synthetic-credentials`
- `slo`
- `sli`
- `website-config`
- `mobile-app-config`
