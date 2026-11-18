"""Enhance-compliant dummy organizations, domains & plans.

Redesigned to match:
 - Enhance API domain schema (id, orgId, domain, dkim, spf, cloudflareStatus, cloudflareTokenFriendlyName)
 - MilesWeb hosting plans (Starter / Premium / Unlimited / Cloud Startup)
 - Full plan schema (cgroupLimits, fsQuotaLimit, allowedPhpVersions, allowedApps, etc.)
 - Dual-currency pricing (INR ₹ / USD $)
 - Domain-check suggestions with per-TLD pricing
"""

from datetime import datetime, timezone
from uuid import UUID

# ---------------------------------------------------------------------------
# Single Organization UUID (acts as security gatepass)
# ---------------------------------------------------------------------------
ORG_ID = UUID("c1a2b3d4-e5f6-7890-abcd-ef1234567890")

VALID_ORGS = {ORG_ID}

# ---------------------------------------------------------------------------
# Server Groups
# ---------------------------------------------------------------------------
SERVER_GROUP_INDIA  = UUID("5a000000-0000-0000-0000-000000000001")
SERVER_GROUP_US     = UUID("5a000000-0000-0000-0000-000000000002")
SERVER_GROUP_EU     = UUID("5a000000-0000-0000-0000-000000000003")

# ---------------------------------------------------------------------------
# Globally taken domains (used by domain-check to block)
# ---------------------------------------------------------------------------
GLOBALLY_TAKEN_DOMAINS = {
    "google.com",
    "milesweb.com",
    "milesweb.in",
    "enhance.com",
    "facebook.com",
    "amazon.com",
    "flipkart.com",
    "flipkart.in",
    "example.com",
    "example.in",
    "example.co.in",
    "taken-by-other-tenant.in",
}

# ---------------------------------------------------------------------------
# Mock Domains  (Enhance schema)
# ---------------------------------------------------------------------------
MOCK_DOMAINS = [
    {
        "id": UUID("a1000000-0000-0000-0000-000000000001"),
        "orgId": ORG_ID,
        "domain": "milesweb.com",
        "websiteId": UUID("01000000-0000-0000-0000-000000000001"),
        "dkim": True,
        "spf": True,
        "cloudflareStatus": "Connected",
        "cloudflareTokenFriendlyName": "MilesWeb Primary CF Token",
    },
    {
        "id": UUID("a1000000-0000-0000-0000-000000000002"),
        "orgId": ORG_ID,
        "domain": "milesweb.in",
        "websiteId": UUID("01000000-0000-0000-0000-000000000001"),
        "dkim": True,
        "spf": True,
        "cloudflareStatus": "Connected",
        "cloudflareTokenFriendlyName": "MilesWeb India CF Token",
    },
    {
        "id": UUID("a1000000-0000-0000-0000-000000000003"),
        "orgId": ORG_ID,
        "domain": "shop.milesweb.com",
        "websiteId": UUID("01000000-0000-0000-0000-000000000002"),
        "dkim": False,
        "spf": True,
        "cloudflareStatus": "Connected",
        "cloudflareTokenFriendlyName": "MilesWeb Shop CF Token",
    },
    {
        "id": UUID("a1000000-0000-0000-0000-000000000004"),
        "orgId": ORG_ID,
        "domain": "blog.milesweb.com",
        "websiteId": UUID("01000000-0000-0000-0000-000000000003"),
        "dkim": True,
        "spf": False,
        "cloudflareStatus": "Pending",
        "cloudflareTokenFriendlyName": "MilesWeb Blog CF Token",
    },
    {
        "id": UUID("a1000000-0000-0000-0000-000000000005"),
        "orgId": ORG_ID,
        "domain": "support.milesweb.in",
        "websiteId": UUID("01000000-0000-0000-0000-000000000001"),
        "dkim": False,
        "spf": False,
        "cloudflareStatus": "Disconnected",
        "cloudflareTokenFriendlyName": "",
    },
]

# ---------------------------------------------------------------------------
# TLD pricing for domain registration/renewal  (used by domain-check flow)
#
#   registration_price = first-year price
#   renewal_price      = subsequent years
#   free_with_plan     = True means 1st year free when buying a hosting plan
# ---------------------------------------------------------------------------
DOMAIN_TLD_PRICING = {
    ".com": {
        "inr": {"registration": 1199, "renewal": 1499},
        "usd": {"registration": 12.99, "renewal": 15.99},
        "free_with_plan": True,
    },
    ".in": {
        "inr": {"registration": 599, "renewal": 899},
        "usd": {"registration": 6.99, "renewal": 9.99},
        "free_with_plan": True,
    },
    ".co.in": {
        "inr": {"registration": 299, "renewal": 599},
        "usd": {"registration": 3.49, "renewal": 6.99},
        "free_with_plan": True,
    },
    ".net": {
        "inr": {"registration": 1399, "renewal": 1699},
        "usd": {"registration": 14.99, "renewal": 17.99},
        "free_with_plan": False,
    },
    ".org": {
        "inr": {"registration": 999, "renewal": 1299},
        "usd": {"registration": 10.99, "renewal": 13.99},
        "free_with_plan": False,
    },
    ".dev": {
        "inr": {"registration": 1599, "renewal": 1899},
        "usd": {"registration": 16.99, "renewal": 19.99},
        "free_with_plan": False,
    },
    ".io": {
        "inr": {"registration": 3499, "renewal": 3999},
        "usd": {"registration": 39.99, "renewal": 44.99},
        "free_with_plan": False,
    },
    ".ai": {
        "inr": {"registration": 6999, "renewal": 7999},
        "usd": {"registration": 79.99, "renewal": 89.99},
        "free_with_plan": False,
    },
}

# Default TLDs to suggest during domain-check
DOMAIN_SUGGESTION_TLDS = [".com", ".in", ".co.in", ".net", ".org"]

# Registration period options (years)
DOMAIN_REGISTRATION_PERIODS = [1, 2, 3, 5]

# ---------------------------------------------------------------------------
# Hosting Plan Pricing  (per billing cycle)
#
#   Billing cycles: monthly, annually (12mo), triennially (36mo)
#   Each has: original_price, discounted_price, renewal_price
#   All per-month values
# ---------------------------------------------------------------------------
PLAN_PRICING = {
    # plan_id -> pricing
    1001: {  # Starter
        "inr": {
            "monthly":      {"original": 399, "discounted": 199, "renewal": 299},
            "annually":     {"original": 399, "discounted": 159, "renewal": 229},
            "triennially":  {"original": 399, "discounted": 129, "renewal": 199},
        },
        "usd": {
            "monthly":      {"original": 4.99, "discounted": 2.99, "renewal": 3.99},
            "annually":     {"original": 4.99, "discounted": 2.49, "renewal": 3.49},
            "triennially":  {"original": 4.99, "discounted": 1.99, "renewal": 3.99},
        },
        "discount_pct": {"monthly": 50, "annually": 60, "triennially": 60},
        "extra_months":  {"monthly": 0,  "annually": 0,  "triennially": 0},
        "free_domain":   {"annually": True, "triennially": True, "monthly": False},
    },
    1002: {  # Premium
        "inr": {
            "monthly":      {"original": 799, "discounted": 299, "renewal": 549},
            "annually":     {"original": 799, "discounted": 249, "renewal": 499},
            "triennially":  {"original": 799, "discounted": 199, "renewal": 449},
        },
        "usd": {
            "monthly":      {"original": 9.99, "discounted": 4.49, "renewal": 7.99},
            "annually":     {"original": 9.99, "discounted": 3.49, "renewal": 6.99},
            "triennially":  {"original": 9.99, "discounted": 2.49, "renewal": 7.99},
        },
        "discount_pct": {"monthly": 63, "annually": 69, "triennially": 75},
        "extra_months":  {"monthly": 0,  "annually": 0,  "triennially": 2},
        "free_domain":   {"annually": True, "triennially": True, "monthly": False},
    },
    1003: {  # Unlimited
        "inr": {
            "monthly":      {"original": 1199, "discounted": 399, "renewal": 799},
            "annually":     {"original": 1199, "discounted": 349, "renewal": 699},
            "triennially":  {"original": 1199, "discounted": 279, "renewal": 649},
        },
        "usd": {
            "monthly":      {"original": 14.99, "discounted": 5.99, "renewal": 11.99},
            "annually":     {"original": 14.99, "discounted": 4.99, "renewal": 9.99},
            "triennially":  {"original": 14.99, "discounted": 3.49, "renewal": 11.99},
        },
        "discount_pct": {"monthly": 67, "annually": 71, "triennially": 77},
        "extra_months":  {"monthly": 0,  "annually": 0,  "triennially": 2},
        "free_domain":   {"annually": True, "triennially": True, "monthly": False},
        "best_value":    True,
    },
    1004: {  # Cloud Startup
        "inr": {
            "monthly":      {"original": 1999, "discounted": 799, "renewal": 1399},
            "annually":     {"original": 1999, "discounted": 699, "renewal": 1299},
            "triennially":  {"original": 1999, "discounted": 559, "renewal": 1199},
        },
        "usd": {
            "monthly":      {"original": 24.99, "discounted": 9.99, "renewal": 19.99},
            "annually":     {"original": 24.99, "discounted": 8.99, "renewal": 17.99},
            "triennially":  {"original": 24.99, "discounted": 6.99, "renewal": 19.99},
        },
        "discount_pct": {"monthly": 60, "annually": 65, "triennially": 72},
        "extra_months":  {"monthly": 0,  "annually": 0,  "triennially": 2},
        "free_domain":   {"annually": True, "triennially": True, "monthly": False},
    },
}

# Tax rates
TAX_RATES = {
    "inr": {"name": "GST", "rate": 18.0},   # 18% GST for India
    "usd": {"name": "Tax", "rate": 0.0},     # no extra tax for USD
}

# ---------------------------------------------------------------------------
# Mock Plans  (Enhance-compatible, MilesWeb-branded)
# ---------------------------------------------------------------------------
MOCK_PLANS = [
    # ── Starter ──────────────────────────────────────────────
    {
        "id": 1001,
        "name": "Starter",
        "orgId": ORG_ID,
        "resources": [
            {"name": "customers", "total": 100},
        ],
        "allowances": [
            {"name": "ssh"},
            {"name": "ssl"},
            {"name": "dailyBackups"},
        ],
        "selections": [
            {"name": "websites", "value": "1"},
            {"name": "storage", "value": "10 GB NVMe"},
            {"name": "emailAccounts", "value": "1"},
            {"name": "bandwidth", "value": "Unmetered"},
            {"name": "aiCredits", "value": "40"},
        ],
        "subscriptionsCount": 342,
        "serverGroupIds": [str(SERVER_GROUP_INDIA), str(SERVER_GROUP_US)],
        "allowServerGroupSelection": False,
        "createdAt": "2024-01-15T08:00:00Z",
        "planType": "shared",
        "cgroupLimits": {
            "nproc": 100,
            "memoryLimit": 1073741824,     # 1 GB
            "iops": 2048,
            "ioBandwidth": 52428800,       # 50 MB/s
            "virtualCpus": 1,
            "swapLimit": 536870912,        # 512 MB
        },
        "fsQuotaLimit": {
            "totalAvailable": 10737418240,  # 10 GB
            "inodesAvailable": 500000,
        },
        "allowedPhpVersions": ["php74", "php80", "php81", "php82", "php83", "php84"],
        "defaultPhpVersion": "php82",
        "redisAllowed": False,
        "preinstallWordpressTheme": "flavor",
        "persistentAppsAllowed": False,
        "allowedApps": ["wordpress"],
        # ── Extra MilesWeb display fields (non-Enhance, for client UI) ──
        "_display": {
            "tagline": "Great for first-time users.",
            "highlight": None,
            "features": [
                "1 website",
                "10 GB NVMe storage",
                "1 email account Free",
                "Free domain for 1 year",
            ],
            "features_full": [
                "1 website",
                "10 GB NVMe storage",
                "1 email account",
                "Free domain for 1 year",
                "Free SSL",
                "Daily backups",
                "Unmetered bandwidth",
                "WordPress ready",
                "AI Builder (40 credits)",
                "AI agent for WordPress",
                "LiteSpeed Web Server",
                "CDN",
                "Free website migration",
                "Malware scan & cleanup",
                "30-day money-back guarantee",
                "Priority 24/7 expert support",
            ],
            "nodejs_apps": 0,
            "openclaw_ready": False,
        },
    },

    # ── Premium ──────────────────────────────────────────────
    {
        "id": 1002,
        "name": "Premium",
        "orgId": ORG_ID,
        "resources": [
            {"name": "customers", "total": 500},
        ],
        "allowances": [
            {"name": "ssh"},
            {"name": "ssl"},
            {"name": "dailyBackups"},
        ],
        "selections": [
            {"name": "websites", "value": "25"},
            {"name": "storage", "value": "50 GB NVMe"},
            {"name": "emailAccounts", "value": "50"},
            {"name": "bandwidth", "value": "Unmetered"},
            {"name": "aiCredits", "value": "50"},
        ],
        "subscriptionsCount": 578,
        "serverGroupIds": [str(SERVER_GROUP_INDIA), str(SERVER_GROUP_US), str(SERVER_GROUP_EU)],
        "allowServerGroupSelection": True,
        "createdAt": "2024-01-15T08:05:00Z",
        "planType": "shared",
        "cgroupLimits": {
            "nproc": 200,
            "memoryLimit": 2147483648,     # 2 GB
            "iops": 4096,
            "ioBandwidth": 104857600,      # 100 MB/s
            "virtualCpus": 2,
            "swapLimit": 1073741824,       # 1 GB
        },
        "fsQuotaLimit": {
            "totalAvailable": 53687091200,  # 50 GB
            "inodesAvailable": 1000000,
        },
        "allowedPhpVersions": ["php74", "php80", "php81", "php82", "php83", "php84"],
        "defaultPhpVersion": "php82",
        "redisAllowed": False,
        "preinstallWordpressTheme": "flavor",
        "persistentAppsAllowed": False,
        "allowedApps": ["wordpress"],
        "_display": {
            "tagline": "Best for managing multiple websites.",
            "highlight": None,
            "features": [
                "25 websites",
                "50 GB NVMe storage",
                "50 email accounts Free",
                "Free domain for 1 year",
            ],
            "features_full": [
                "25 websites",
                "50 GB NVMe storage",
                "50 email accounts",
                "Free domain for 1 year",
                "Free SSL",
                "Daily backups",
                "Unmetered bandwidth",
                "WordPress ready",
                "AI Builder (50 credits)",
                "AI agent for WordPress",
                "LiteSpeed Web Server",
                "CDN",
                "Free website migration",
                "Malware scan & cleanup",
                "30-day money-back guarantee",
                "Priority 24/7 expert support",
            ],
            "nodejs_apps": 0,
            "openclaw_ready": False,
        },
    },

    # ── Unlimited (Best Value) ───────────────────────────────
    {
        "id": 1003,
        "name": "Unlimited",
        "orgId": ORG_ID,
        "resources": [
            {"name": "customers", "total": 0},  # 0 = unlimited
        ],
        "allowances": [
            {"name": "ssh"},
            {"name": "ssl"},
            {"name": "dailyBackups"},
            {"name": "onDemandBackups"},
        ],
        "selections": [
            {"name": "websites", "value": "Unlimited"},
            {"name": "storage", "value": "75 GB NVMe"},
            {"name": "emailAccounts", "value": "Unlimited"},
            {"name": "bandwidth", "value": "Unmetered"},
            {"name": "aiCredits", "value": "65"},
        ],
        "subscriptionsCount": 1247,
        "serverGroupIds": [str(SERVER_GROUP_INDIA), str(SERVER_GROUP_US), str(SERVER_GROUP_EU)],
        "allowServerGroupSelection": True,
        "createdAt": "2024-01-15T08:10:00Z",
        "planType": "shared",
        "cgroupLimits": {
            "nproc": 300,
            "memoryLimit": 3221225472,     # 3 GB
            "iops": 6144,
            "ioBandwidth": 157286400,      # 150 MB/s
            "virtualCpus": 2,
            "swapLimit": 1610612736,       # 1.5 GB
        },
        "fsQuotaLimit": {
            "totalAvailable": 80530636800,  # 75 GB
            "inodesAvailable": 2000000,
        },
        "allowedPhpVersions": ["php74", "php80", "php81", "php82", "php83", "php84"],
        "defaultPhpVersion": "php83",
        "redisAllowed": True,
        "preinstallWordpressTheme": "flavor",
        "persistentAppsAllowed": True,
        "allowedApps": ["wordpress"],
        "_display": {
            "tagline": "eCommerce & Node.js ready hosting.",
            "highlight": "Best Value",
            "features": [
                "Unlimited websites",
                "75 GB NVMe storage",
                "Unlimited email accounts Free",
                "Free domain for 1 year",
                "Daily & On-Demand Backups",
                "1 Node.js web app New",
            ],
            "features_full": [
                "Unlimited websites",
                "75 GB NVMe storage",
                "Unlimited email accounts",
                "Free domain for 1 year",
                "Free SSL",
                "Daily & On-Demand Backups",
                "Unmetered bandwidth",
                "WordPress ready",
                "WooCommerce ready",
                "AI Builder (65 credits)",
                "AI agent for WordPress",
                "1 Node.js web app",
                "LiteSpeed Web Server",
                "CDN",
                "Free website migration",
                "Malware scan & cleanup",
                "30-day money-back guarantee",
                "Priority 24/7 expert support",
            ],
            "nodejs_apps": 1,
            "openclaw_ready": False,
        },
    },

    # ── Cloud Startup ────────────────────────────────────────
    {
        "id": 1004,
        "name": "Cloud Startup",
        "orgId": ORG_ID,
        "resources": [
            {"name": "customers", "total": 0},
        ],
        "allowances": [
            {"name": "ssh"},
            {"name": "ssl"},
            {"name": "dailyBackups"},
            {"name": "onDemandBackups"},
            {"name": "dedicatedResources"},
        ],
        "selections": [
            {"name": "websites", "value": "Unlimited"},
            {"name": "storage", "value": "100 GB NVMe"},
            {"name": "emailAccounts", "value": "Unlimited"},
            {"name": "bandwidth", "value": "Unmetered"},
            {"name": "aiCredits", "value": "75"},
            {"name": "cpu", "value": "5"},
            {"name": "ram", "value": "5 GB"},
        ],
        "subscriptionsCount": 213,
        "serverGroupIds": [str(SERVER_GROUP_INDIA), str(SERVER_GROUP_US), str(SERVER_GROUP_EU)],
        "allowServerGroupSelection": True,
        "createdAt": "2024-03-20T10:00:00Z",
        "planType": "shared",
        "cgroupLimits": {
            "nproc": 500,
            "memoryLimit": 5368709120,     # 5 GB
            "iops": 8192,
            "ioBandwidth": 209715200,      # 200 MB/s
            "virtualCpus": 5,
            "swapLimit": 2147483648,       # 2 GB
        },
        "fsQuotaLimit": {
            "totalAvailable": 107374182400,  # 100 GB
            "inodesAvailable": 3000000,
        },
        "allowedPhpVersions": ["php74", "php80", "php81", "php82", "php83", "php84"],
        "defaultPhpVersion": "php83",
        "redisAllowed": True,
        "preinstallWordpressTheme": "flavor",
        "persistentAppsAllowed": True,
        "allowedApps": ["wordpress"],
        "_display": {
            "tagline": "Built for high-traffic sites and apps.",
            "highlight": None,
            "features": [
                "5 CPU, 5 GB RAM Turbo boost",
                "Unlimited websites",
                "100 GB NVMe storage",
                "Unlimited email accounts Free",
                "Free domain for 1 year",
                "Daily & On-Demand Backups",
                "3 Node.js web apps New",
                "OpenClaw AI ready",
            ],
            "features_full": [
                "5 CPU, 5 GB RAM",
                "Unlimited websites",
                "100 GB NVMe storage",
                "Unlimited email accounts",
                "Free domain for 1 year",
                "Free SSL",
                "Daily & On-Demand Backups",
                "Unmetered bandwidth",
                "WordPress ready",
                "WooCommerce ready",
                "AI Builder (75 credits)",
                "AI agent for WordPress",
                "3 Node.js web apps",
                "OpenClaw AI ready",
                "LiteSpeed Web Server",
                "CDN",
                "Free website migration",
                "Malware scan & cleanup",
                "30-day money-back guarantee",
                "Priority 24/7 expert support",
            ],
            "nodejs_apps": 3,
            "openclaw_ready": True,
        },
    },
]

# ---------------------------------------------------------------------------
# Plan comparison table data (for client-side comparison grid)
# ---------------------------------------------------------------------------
PLAN_COMPARISON = {
    "categories": [
        {
            "name": "Core",
            "features": [
                {
                    "label": "Websites",
                    "values": {"1001": "1", "1002": "25", "1003": "Unlimited", "1004": "Unlimited"},
                },
                {
                    "label": "Free domain",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "NVMe storage",
                    "values": {"1001": "10 GB", "1002": "50 GB", "1003": "75 GB", "1004": "100 GB"},
                },
                {
                    "label": "Backups",
                    "values": {"1001": "Daily", "1002": "Daily", "1003": "Daily & On-Demand", "1004": "Daily & On-Demand"},
                },
                {
                    "label": "Email accounts",
                    "values": {"1001": "1", "1002": "50", "1003": "Unlimited", "1004": "Unlimited"},
                },
            ],
        },
        {
            "name": "Platform",
            "features": [
                {
                    "label": "WordPress ready",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "Free SSL",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "AI website builder",
                    "values": {"1001": "40 credits", "1002": "50 credits", "1003": "65 credits", "1004": "75 credits"},
                },
                {
                    "label": "AI agent for WordPress",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "Node.js web apps",
                    "values": {"1001": None, "1002": None, "1003": "1", "1004": "3"},
                },
                {
                    "label": "Priority 24/7 expert support",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "OpenClaw AI ready",
                    "values": {"1001": None, "1002": None, "1003": None, "1004": True},
                },
            ],
        },
        {
            "name": "Infrastructure",
            "features": [
                {
                    "label": "LiteSpeed Server",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "CDN",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "Free website migration",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "Instant malware cleanup",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
                {
                    "label": "Powerful control panel",
                    "values": {"1001": True, "1002": True, "1003": True, "1004": True},
                },
            ],
        },
    ],
}

# ---------------------------------------------------------------------------
# Domain availability simulation data
#
# For domain-check: given a base name (e.g. "mysite"), we check each TLD.
# These simulate known registrations so some TLD combos come back unavailable.
# ---------------------------------------------------------------------------
REGISTERED_DOMAINS_DB = {
    # base_name -> set of registered TLDs
    "google":    {".com", ".in", ".co.in", ".net", ".org", ".dev", ".io", ".ai"},
    "milesweb":  {".com", ".in", ".co.in"},
    "enhance":   {".com"},
    "facebook":  {".com", ".in", ".net", ".org"},
    "amazon":    {".com", ".in", ".co.in"},
    "flipkart":  {".com", ".in"},
    "example":   {".com", ".in", ".co.in", ".net", ".org"},
    "test":      {".com", ".in"},
    "demo":      {".com"},
    "hello":     {".com", ".in"},
    "mysite":    {".com"},
    "startup":   {".com", ".io"},
    "shopify":   {".com", ".in", ".dev"},
}

# ---------------------------------------------------------------------------
# Money-back guarantee & misc constants
# ---------------------------------------------------------------------------
MONEY_BACK_DAYS = 30
SUPPORTED_CURRENCIES = ["inr", "usd"]
BILLING_CYCLES = ["monthly", "annually", "triennially"]
BILLING_CYCLE_MONTHS = {
    "monthly": 1,
    "annually": 12,
    "triennially": 36,
}
