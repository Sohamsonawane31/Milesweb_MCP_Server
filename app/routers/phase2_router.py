"""Mock implementation of the Phase 2 Enhance read-only GET API catalog."""

import hmac
import re
from collections.abc import Callable

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.config import Settings, get_settings
from app.services.phase2_catalog import Phase2Catalog, catalog
from app.services.token_service import decode_access_token

router = APIRouter(tags=["Phase 2 Enhance mock"])


def parse_test_tokens(value: str) -> dict[str, int]:
    """Parse opaque development token mappings without logging their values."""
    mappings: dict[str, int] = {}
    for item in value.split(","):
        token, separator, client_id = item.strip().partition(":")
        if separator and token and client_id.isdigit():
            mappings[token] = int(client_id)
    return mappings


def authenticated_client(
    authorization: str | None = Header(default=None, include_in_schema=False),
    connector_key: str | None = Header(default=None, alias="X-Connector-Key", include_in_schema=False),
    settings: Settings = Depends(get_settings),
) -> int:
    """Require the MCP bearer identity and the server-to-server connector key."""
    if not connector_key or not settings.connector_api_key or not hmac.compare_digest(connector_key, settings.connector_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    scheme, _, bearer_token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not bearer_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    client_id: int | None = None
    # 1. Dynamically verify and decode token as signed JWT
    claims = decode_access_token(bearer_token, settings=settings)
    if claims:
        raw_id = claims.get("clientId") or claims.get("sub")
        if raw_id is not None and str(raw_id).isdigit():
            client_id = int(raw_id)

    # 2. Fallback to static test tokens for backwards compatibility
    if client_id is None:
        client_id = parse_test_tokens(settings.phase2_test_tokens).get(bearer_token)

    if client_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return client_id


def get_catalog() -> Phase2Catalog:
    return catalog


def phase2_handler(operation: str) -> Callable:
    async def handler(
        request: Request,
        client_id: int = Depends(authenticated_client),
        data: Phase2Catalog = Depends(get_catalog),
    ) -> dict:
        customer = data.authorize(client_id, dict(request.path_params))
        if customer is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
        return data.response(operation, customer, dict(request.query_params), dict(request.path_params))

    handler.__name__ = operation
    handler.__doc__ = f"Mock read-only response for Enhance operation {operation}."
    return handler


# Every GET operation in the Enhance customer-facing read API catalog. This
# explicit allow-list prevents accidentally exposing unreviewed write methods.
OPERATIONS = [
    ("getDomains", "/orgs/{org_id}/domains"),
    ("getDomainAuthNs", "/orgs/{org_id}/domains/{domain_id}/auth-ns"),
    ("getDomainLocalRemote", "/orgs/{org_id}/websites/{website_id}/domains/{domain_id}/local_remote"),
    ("getFtpUsers", "/orgs/{org_id}/websites/{website_id}/ftp/users"),
    ("getInstallableApps", "/orgs/{org_id}/subscriptions/{subscription_id}/installable-apps"),
    ("getLogin", "/login"),
    ("getLoginMemberships", "/login/memberships"),
    ("getOrg", "/orgs/{org_id}"),
    ("getOrgActivities", "/v2/orgs/{org_id}/activities"),
    ("getSubscription", "/orgs/{org_id}/subscriptions/{subscription_id}"),
    ("getSubscriptionBandwidthUsage", "/orgs/{org_id}/subscriptions/{subscription_id}/bandwidth"),
    ("getSubscriptionsToParent", "/orgs/{org_id}/subscriptions"),
    ("getWebsite", "/orgs/{org_id}/websites/{website_id}"),
    ("getWebsiteApps", "/orgs/{org_id}/websites/{website_id}/apps"),
    ("getWebsiteBackup", "/orgs/{org_id}/websites/{website_id}/backups/{backup_id}"),
    ("getWebsiteBackups", "/orgs/{org_id}/websites/{website_id}/backups"),
    ("getWebsiteBackupStatus", "/orgs/{org_id}/websites/{website_id}/status/backup"),
    ("getWebsiteCgroupLimits", "/orgs/{org_id}/websites/{website_id}/cgroup_limits"),
    ("getWebsiteDomainDnsZone", "/orgs/{org_id}/websites/{website_id}/domains/{domain_id}/dns-zone"),
    ("getWebsiteDomainMapping", "/orgs/{org_id}/websites/{website_id}/domains/{domain_id}"),
    ("getWebsiteDomainMappingDnsStatus", "/orgs/{org_id}/websites/{website_id}/domains/{domain_id}/dns-status"),
    ("getWebsiteDomainMappings", "/orgs/{org_id}/websites/{website_id}/domains"),
    ("getWebsiteDomainSslCert", "/v2/domains/{domain_id}/ssl"),
    ("getWebsiteEmails", "/orgs/{org_id}/websites/{website_id}/emails"),
    ("getWebsiteEnabledPhpExtensions", "/websites/{website_id}/php_extensions"),
    ("getWebsiteFsQuotaLimits", "/orgs/{org_id}/websites/{website_id}/fs_quota_limits"),
    ("getWebsiteGitDeploys", "/orgs/{org_id}/websites/{website_id}/git/deploys"),
    ("getWebsiteGitInfo", "/orgs/{org_id}/websites/{website_id}/git"),
    ("getWebsiteLsphpSettings", "/websites/{website_id}/lsphp_settings"),
    ("getWebsiteMetrics", "/orgs/{org_id}/websites/{website_id}/metrics"),
    ("getWebsiteMySQLDBs", "/orgs/{org_id}/websites/{website_id}/mysql-dbs"),
    ("getWebsiteMySQLUsers", "/orgs/{org_id}/websites/{website_id}/mysql-users"),
    ("getWebsitePhpErrorLog", "/websites/{website_id}/php_error_log"),
    ("getWebsitePostgresqlDbs", "/orgs/{org_id}/websites/{website_id}/postgresql-dbs"),
    ("getWebsitePostgresqlUsers", "/orgs/{org_id}/websites/{website_id}/postgresql-users"),
    ("getWebsiteRestoreStatus", "/orgs/{org_id}/websites/{website_id}/backups/{backup_id}/restore_status"),
    ("getWebsiteSshKeys", "/orgs/{org_id}/websites/{website_id}/ssh/keys"),
    ("getWebsites", "/orgs/{org_id}/websites"),
    ("getWordpressAppVersion", "/orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/version"),
    ("getWordpressInfo", "/orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/info"),
    ("getWordpressPlugins", "/orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/plugins"),
    ("getWordpressThemes", "/orgs/{org_id}/websites/{website_id}/apps/{app_id}/wordpress/themes"),
]

for operation_name, operation_path in OPERATIONS:
    # Dynamic handlers read path values from Request.path_params, so declare
    # them explicitly for OpenAPI/Swagger even though they are not Python
    # function parameters.
    path_parameters = [
        {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
        for name in re.findall(r"{([^}]+)}", operation_path)
    ]
    router.add_api_route(
        operation_path,
        phase2_handler(operation_name),
        methods=["GET"],
        name=operation_name,
        openapi_extra={"parameters": path_parameters} if path_parameters else None,
    )
