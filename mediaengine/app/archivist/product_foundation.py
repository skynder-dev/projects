from __future__ import annotations

from .platform_adapter import platform_capabilities


TARGET_PLATFORMS = ("Windows", "macOS", "Android", "iOS")


def platform_snapshot() -> dict:
    return platform_capabilities()

def setup_catalog(cfg: dict) -> list[dict]:
    source_count = len(cfg.get("sources") or [])
    return [
        {
            "id": "core",
            "name": "Core & Local AI",
            "why": "Local ingest, search, analysis, conversion and composition.",
            "required": True,
            "status": "Ready",
            "cost": "Included",
            "data": "Media stays on this device by default.",
            "action": "Open Media",
            "href": "/media",
        },
        {
            "id": "sources",
            "name": "Media Sources",
            "why": "Folders, removable media and supported phone ingest.",
            "required": True,
            "status": f"{source_count} folder source(s) configured",
            "cost": "No MediaEngine fee",
            "data": "Discovery is local. Source originals are never auto-deleted.",
            "action": "Manage sources",
            "href": "/import",
        },
        {
            "id": "cloud",
            "name": "Cloud Vault",
            "why": "Optional backup, mirror and cross-device recovery.",
            "required": False,
            "status": "Not connected",
            "cost": "Provider charges may apply",
            "data": "Disabled by default. Only explicitly selected upload modes may leave the device.",
            "action": "Review Cloud",
            "href": "/cloud",
        },
        {
            "id": "social",
            "name": "Social Accounts",
            "why": "Future publishing, analytics and experiment feedback.",
            "required": False,
            "status": "Not connected",
            "cost": "Platform/provider rules apply",
            "data": "No social account credentials are configured in this release.",
            "action": "Open Social Lab",
            "href": "/social",
        },
        {
            "id": "devices",
            "name": "Devices",
            "why": "Media-source phones and future Social Device Lab handoff/QA.",
            "required": False,
            "status": "Manage locally",
            "cost": "No MediaEngine fee",
            "data": "Device registration is per installation; no personal device is hard-coded.",
            "action": "Open Devices",
            "href": "/devices",
        },
        {
            "id": "online_ai",
            "name": "Optional Online AI",
            "why": "Future opt-in tasks that cannot or should not run locally.",
            "required": False,
            "status": "Disabled",
            "cost": "Provider/model charges may apply",
            "data": "No user media is sent to online AI by this foundation release.",
            "action": "Review privacy",
            "href": "/settings",
        },
    ]
