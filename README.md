# Instana Configuration Migrator

This tool allows you to export configuration from one Instana backend and import it into another.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure Backends:**
    Edit the `config.yaml` file to include the full API URL (including the `/api` suffix) and a generated API token for both your source and destination Instana backends.

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

The tool uses an `export` and `import` command structure. An `export` directory will be created to store the configuration files.

### Exporting

You can export a specific configuration type or all configurations at once.

```bash
# Export a single type (e.g., custom dashboards)
python instana_migrator.py export --type custom-dashboards

# Export all available configurations
python instana_migrator.py export --type all
```

### Importing

You can import a specific configuration type or all configurations at once.

```bash
# Import a single type (e.g., custom dashboards)
python instana_migrator.py import --type custom-dashboards

# Import all available configurations
python instana_migrator.py import --type all
```

### Supported Configuration Types

The `--type` flag accepts the following values:
- `applications`
- `services`
- `manual-services`
- `endpoints`
- `http-endpoints`
- `alert-channels`
- `alert-configs`
- `global-smart-alerts`
- `custom-event-specifications`
- `global-custom-payloads`
- `synthetic-tests`
- `synthetic-credentials`
- `slo`
- `sli`
- `custom-dashboards`
- `maintenance`
- `api-tokens`
- `groups`
- `website-config`
- `mobile-app-config`
- `all`
