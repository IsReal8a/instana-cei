
"""
This module contains the API endpoint configuration for the Instana Migrator.
"""

API_CONFIG = {
    # Working API endpoints
    "applications": {
        "export_path": "/application-monitoring/settings/application",
        "import_path": "/application-monitoring/settings/application",
        "import_method": "POST",
        "id_key": "id"
    },
    "services": {
        "export_path": "/application-monitoring/services",
        "import_path": "/application-monitoring/settings/service",
        "import_method": "POST",
        "id_key": "id"
    },
    "manual-services": {
        "export_path": "/application-monitoring/settings/manual-service",
        "import_path": "/application-monitoring/settings/manual-service",
        "import_method": "POST"
    },
    "alert-channels": {
        "export_path": "/events/settings/alertingChannels",
        "import_path": "/events/settings/alertingChannels",
        "import_method": "POST",
        "id_key": "id"
    },
    "alert-configs": {
        "export_path": "/events/settings/alerts",
        "import_path": "/events/settings/alerts",
        "import_method": "PUT_ITERATE",
        "id_key": "id"
    },
    "global-application-smart-alerts": {
        "export_path": "/events/settings/global-alert-configs/applications",
        "import_path": "/events/settings/global-alert-configs/applications",
        "import_method": "POST",
        "id_key": "id"
    },
    "custom-event-specifications": {
        "export_path": "/events/settings/event-specifications/custom",
        "import_path": "/events/settings/event-specifications/custom",
        "import_method": "POST"
    },
    "global-custom-payloads": {
        "export_path": "/events/settings/custom-payload-configurations",
        "import_path": "/events/settings/custom-payload-configurations",
        "import_method": "PUT"
    },
    "maintenance": {
        "export_path": "/settings/v2/maintenance",
        "import_path": "/settings/v2/maintenance",
        "import_method": "PUT_ITERATE",
        "id_key": "id"
    },
    "api-tokens": {
        "export_path": "/settings/api-tokens",
        "import_path": "/settings/api-tokens",
        "import_method": "POST"
    },
    "groups": {
        "export_path": "/settings/rbac/groups",
        "import_path": "/settings/rbac/groups",
        "import_method": "POST"
    },
    "custom-dashboards": {
        "export_path": "/custom-dashboard",
        "import_path": "/custom-dashboard",
        "import_method": "POST",
        "id_key": "id"
    },
    # Not working API endpoints
    "synthetic-tests": {
        "export_path": "/synthetics/settings/tests",
        "import_path": "/synthetics/settings/tests",
        "import_method": "POST"
    },
    "synthetic-credentials": {
        "export_path": "/synthetics/settings/credentials/associations",
        "import_path": "/synthetics/settings/credentials/associations",
        "import_method": "POST"
    },
    "slo": {
        "export_path": "/settings/slo",
        "import_path": "/settings/slo",
        "import_method": "POST"
    },
    "sli": {
        "export_path": "/settings/sli",
        "import_path": "/settings/sli",
        "import_method": "POST"
    },
    "website-config": {
        "export_path": "/website-monitoring/config",
        "import_path": "/website-monitoring/config",
        "import_method": "POST"
    },
    "mobile-app-config": {
        "export_path": "/mobile-app-monitoring/config",
        "import_path": "/mobile-app-monitoring/config",
        "import_method": "POST"
    }
}
