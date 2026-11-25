"""Static, tenant-aware data provider for the Phase 2 Enhance GET catalog."""

import json
from pathlib import Path
from typing import Any


class Phase2Catalog:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(__file__).resolve().parents[2] / "data" / "customers.json"

    def _customers(self) -> list[dict[str, Any]]:
        with self.path.open(encoding="utf-8") as source:
            return json.load(source)["customers"]

    def customer(self, client_id: int) -> dict[str, Any] | None:
        item = next((entry for entry in self._customers() if entry["clientId"] == client_id), None)
        if item is not None:
            return item

        # Fallback to general customer repository so any registered customer has an account identity
        try:
            from app.customer_repository import repository
            cust = repository.get_customer(client_id)
            if cust is not None:
                return {
                    "clientId": cust["clientId"],
                    "login": {
                        "id": f"login-{cust['clientId']}-001",
                        "email": cust["email"],
                        "name": cust["name"],
                        "colorCode": "#6b7280",
                        "registeredAt": "2025-01-01T00:00:00Z",
                        "authMethod": "basic",
                        "locale": "en-IN",
                    },
                    "organization": None,
                    "subscription": None,
                    "website": None,
                }
        except Exception:
            pass

        return None

    def authorize(self, client_id: int, path: dict[str, str]) -> dict[str, Any] | None:
        """Return a record only when all supplied resource IDs belong to caller."""
        customer = self.customer(client_id)
        if customer is None:
            return None

        org = customer.get("organization")
        website = customer.get("website")
        subscription = customer.get("subscription")

        if "org_id" in path:
            if not org or path["org_id"] != org.get("id"):
                return None
        if "website_id" in path:
            if not website or path["website_id"] != website.get("id"):
                return None
        if "subscription_id" in path:
            if not subscription or str(path["subscription_id"]) != str(subscription.get("id")):
                return None
        if "app_id" in path:
            if not website or path["app_id"] != website.get("appId"):
                return None
        if "domain_id" in path:
            if not website:
                return None
            # Accept the primary domain ID or any additional domain mapping IDs
            # registered on this website (multi-domain support).
            allowed = {website.get("domainId")}
            allowed.update(website.get("additionalDomainIds", []))
            if path["domain_id"] not in allowed:
                return None

        return customer

    def response(self, operation: str, customer: dict[str, Any], query: dict[str, str]) -> dict[str, Any]:
        login = customer.get("login") or {
            "id": f"login-{customer.get('clientId', 'unknown')}-001",
            "email": customer.get("email", ""),
            "name": customer.get("name", ""),
            "colorCode": "#6b7280",
            "registeredAt": "2025-01-01T00:00:00Z",
            "authMethod": "basic",
            "locale": "en-IN",
        }
        org = customer.get("organization")
        subscription = customer.get("subscription")
        website = customer.get("website")

        # Identity operations (work for all users, with or without hosting)
        if operation == "getLogin":
            return login

        if operation == "getLoginMemberships":
            if org:
                return {
                    "memberships": [
                        {
                            "memberId": login["id"],
                            "orgId": org["id"],
                            "orgName": org["name"],
                            "isMasterOrg": True,
                            "roles": ["Owner"],
                            "siteAccessCount": 1 if website else 0,
                        }
                    ]
                }
            # User without active hosting organization has 0 memberships
            return {"memberships": []}

        if operation == "getOrg":
            return org or {}

        if operation == "getSubscriptionsToParent":
            if subscription:
                return {"total": 1, "items": [subscription]}
            return {"total": 0, "items": []}

        if operation == "getSubscription":
            return subscription or {}

        if operation == "getSubscriptionBandwidthUsage":
            return subscription.get("bandwidthUsage", {}) if subscription else {}

        if operation == "getWebsites":
            if website and org and subscription:
                website_item = {
                    "id": website["id"],
                    "orgId": org["id"],
                    "subscriptionId": subscription["id"],
                    "domain": website["domain"],
                    "status": website["status"],
                    "server": website["server"],
                }
                return {"total": 1, "items": [website_item]}
            return {"total": 0, "items": []}

        if not website:
            return {"total": 0, "items": []}

        website_item = {
            "id": website["id"],
            "orgId": org["id"] if org else "",
            "subscriptionId": subscription["id"] if subscription else 0,
            "domain": website["domain"],
            "status": website["status"],
            "server": website["server"],
        }
        domain = {
            "id": website["domainId"],
            "domain": website["domain"],
            "isPrimary": True,
            "mappingKind": "primary",
        }

        if operation == "getWebsite": return website_item
        if operation == "getWebsiteDomainMappings": return {"total": 1, "items": [domain]}
        if operation == "getWebsiteDomainMappingDnsStatus": return {"status": "Connected", "lastCheckedAt": "2026-11-23T07:30:00Z"}
        if operation == "getWebsiteDomainDnsZone": return {"domain": website["domain"], "records": [{"id": "dns-001", "kind": "A", "name": "@", "value": "198.51.100.42", "ttl": 3600}]}
        if operation == "getWebsiteDomainSslCert": return {"cn": website["domain"], "expires": "2027-11-23T00:00:00Z", "issued": "2026-11-23T00:00:00Z", "issuer": "Mock Let's Encrypt", "sans": [website["domain"]], "forceHttps": True}
        if operation == "getWebsiteApps": return {"total": 1, "items": [{"id": website["appId"], "name": "WordPress", "kind": "wordpress", "status": "active"}]}
        if operation == "getWordpressInfo": return {"id": website["appId"], "name": "WordPress", "url": f"https://{website['domain']}", "version": "6.7.1"}
        if operation == "getWordpressAppVersion": return {"version": "6.7.1"}
        if operation == "getWordpressPlugins": return {"total": 1, "items": [{"name": "akismet", "status": "active", "version": "5.3", "updateAvailable": "none"}]}
        if operation == "getWordpressThemes": return {"total": 1, "items": [{"name": "twentytwentyfour", "status": "active", "version": "1.3", "autoUpdate": "on"}]}
        if operation == "getWebsiteBackups": return {"total": 1, "items": [{"id": 9001, "createdAt": "2026-11-20T01:00:00Z", "size": 10485760, "status": "completed"}]}
        if operation == "getWebsiteBackup": return {"id": 9001, "createdAt": "2026-11-20T01:00:00Z", "size": 10485760, "status": "completed"}
        if operation == "getWebsiteEmails": return {"total": 1, "items": [{"email": f"hello@{website['domain']}", "status": "active", "quota": {"usage": 5242880, "total": 1073741824}}]}
        if operation == "getFtpUsers": return {"items": [{"account": "siteuser", "homeDir": f"/home/siteuser/{website['domain']}"}]}
        if operation == "getWebsiteMySQLDBs": return {"total": 1, "items": [{"name": "site_db", "size": 12582912}]}
        if operation == "getWebsiteMySQLUsers": return {"total": 1, "items": [{"name": "site_user", "host": "localhost"}]}
        if operation == "getWebsitePostgresqlDbs": return {"total": 1, "items": [{"name": "site_postgres", "size": 0}]}
        if operation == "getWebsitePostgresqlUsers": return {"total": 1, "items": [{"name": "site_pg_user"}]}
        if operation == "getWebsiteSshKeys": return {"items": [{"id": "ssh-001", "name": "deployment-key", "fingerprint": "SHA256:mockfingerprint"}]}
        if operation == "getWebsiteGitInfo": return {"repository": "https://git.example/mock/site.git", "branch": "main", "connected": True}
        if operation == "getWebsiteGitDeploys": return {"total": 1, "items": [{"id": "deploy-001", "status": "success", "createdAt": "2026-11-22T10:00:00Z"}]}
        if operation == "getWebsiteMetrics": return {"granularity": query.get("granularity", "day"), "items": [{"timestamp": "2026-11-23T00:00:00Z", "pageViews": 42, "transfer": 1048576}]}
        if operation == "getWebsiteFsQuotaLimits": return {"usage": 73400320, "total": 1073741824}
        if operation == "getWebsiteCgroupLimits": return {"cpu": 100, "memory": 536870912, "processes": 50}
        if operation == "getWebsiteEnabledPhpExtensions": return {"items": ["curl", "mbstring", "mysqli", "openssl"]}
        if operation == "getWebsiteLsphpSettings": return {"version": "8.3", "memoryLimit": "256M", "maxExecutionTime": 60}
        if operation == "getWebsitePhpErrorLog": return {"items": []}
        if operation == "getOrgActivities": return {"total": 1, "items": [{"id": "activity-001", "orgId": org["id"] if org else "", "kind": "added", "createdAt": "2026-11-20T10:00:00Z", "message": "Mock website created"}]}

        return {"success": True, "data": []}


catalog = Phase2Catalog()
