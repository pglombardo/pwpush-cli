from typing import Any

from dateutil import parser

from pwpush.api.capabilities import API_PROFILE_LEGACY, API_PROFILE_V2

_DURATION_BY_DAYS = {
    1: 6,
    2: 7,
    3: 8,
    4: 9,
    5: 10,
    6: 11,
    7: 12,
    14: 13,
    21: 14,
    30: 15,
    60: 16,
    90: 17,
}


def validation_paths(api_profile: str, *, expired: bool = False) -> list[str]:
    """Return candidate list/login validation paths in priority order."""
    legacy_path = "/p/expired.json" if expired else "/p/active.json"
    legacy_alt_path = "/en/d/expired.json" if expired else "/en/d/active.json"
    v2_path = "/api/v2/pushes/expired" if expired else "/api/v2/pushes/active"

    if api_profile == API_PROFILE_V2:
        return [v2_path, legacy_path, legacy_alt_path]
    return [legacy_path, v2_path, legacy_alt_path]


def push_create_path(api_profile: str, kind: str) -> str:
    """Return create endpoint for text/url/qr/file push."""
    if api_profile == API_PROFILE_V2:
        return "/api/v2/pushes"
    if kind == "file":
        return "/f.json"
    return "/p.json"


def push_preview_path(api_profile: str, url_token: str, kind: str) -> str:
    """Return preview endpoint for created push."""
    if api_profile == API_PROFILE_V2:
        return f"/api/v2/pushes/{url_token}/preview"
    if kind == "file":
        return f"/f/{url_token}/preview.json"
    return f"/p/{url_token}/preview.json"


def push_expire_path(api_profile: str, url_token: str) -> str:
    """Return expire endpoint path."""
    if api_profile == API_PROFILE_V2:
        return f"/api/v2/pushes/{url_token}"
    return f"/p/{url_token}.json"


def push_audit_path(api_profile: str, url_token: str) -> str:
    """Return audit endpoint path."""
    if api_profile == API_PROFILE_V2:
        return f"/api/v2/pushes/{url_token}/audit"
    return f"/p/{url_token}/audit.json"


def adapt_text_payload_for_profile(
    payload: dict[str, Any], api_profile: str
) -> dict[str, Any]:
    """Convert text payload between legacy and v2 formats."""
    if api_profile == API_PROFILE_LEGACY:
        return payload

    source = payload["password"]
    push_payload = {
        "payload": source["payload"],
        "kind": source.get("kind", "text"),
    }
    if "expire_after_views" in source:
        push_payload["expire_after_views"] = source["expire_after_views"]
    if "note" in source:
        push_payload["note"] = source["note"]
    if "deletable_by_viewer" in source:
        push_payload["deletable_by_viewer"] = source["deletable_by_viewer"]
    if "retrieval_step" in source:
        push_payload["retrieval_step"] = source["retrieval_step"]
    if "passphrase" in source:
        push_payload["passphrase"] = source["passphrase"]

    if "expire_after_days" in source:
        days = int(source["expire_after_days"])
        if days in _DURATION_BY_DAYS:
            push_payload["expire_after_duration"] = _DURATION_BY_DAYS[days]
        else:
            # Keep backward value for instances that still accept day-style field.
            push_payload["expire_after_days"] = days

    return {"push": push_payload}


def adapt_file_payload_for_profile(
    payload: dict[str, Any], api_profile: str
) -> dict[str, Any]:
    """Convert file payload between legacy and v2 formats."""
    if api_profile == API_PROFILE_LEGACY:
        return payload

    source = payload["file_push"]
    push_payload = {
        "payload": source.get("payload", ""),
        "kind": "file",
    }
    if "expire_after_views" in source:
        push_payload["expire_after_views"] = source["expire_after_views"]
    if "note" in source:
        push_payload["note"] = source["note"]
    if "deletable_by_viewer" in source:
        push_payload["deletable_by_viewer"] = source["deletable_by_viewer"]
    if "retrieval_step" in source:
        push_payload["retrieval_step"] = source["retrieval_step"]

    if "expire_after_days" in source:
        days = int(source["expire_after_days"])
        if days in _DURATION_BY_DAYS:
            push_payload["expire_after_duration"] = _DURATION_BY_DAYS[days]
        else:
            push_payload["expire_after_days"] = days

    return {"push": push_payload}


def adapt_file_uploads_for_profile(
    upload_files: dict[str, Any], api_profile: str
) -> dict[str, Any]:
    """Rename multipart file key for v2 when required."""
    if api_profile == API_PROFILE_LEGACY:
        return upload_files
    if "file_push[files][]" in upload_files:
        return {"push[files][]": upload_files["file_push[files][]"]}
    return upload_files


def normalize_audit_events(body: dict[str, Any]) -> list[dict[str, str]]:
    """Normalize legacy and v2 audit payloads into one renderable schema."""
    if "views" in body:
        rows = []
        for event in body["views"]:
            kind = event.get("kind")
            if kind == 0:
                kind_label = "View"
            elif kind == 1:
                kind_label = "Manual Deletion"
            else:
                kind_label = str(kind)

            rows.append(
                {
                    "ip": event.get("ip", "Unknown"),
                    "user_agent": event.get("user_agent", "Unknown"),
                    "referrer": event.get("referrer") or "None",
                    "successful": str(event.get("successful", True)),
                    "created_at": parser.isoparse(event["created_at"]).strftime(
                        "%m/%d/%Y, %H:%M:%S UTC"
                    ),
                    "kind": kind_label,
                }
            )
        return rows

    rows = []
    for event in body.get("logs", []):
        rows.append(
            {
                "ip": event.get("ip", "Unknown"),
                "user_agent": event.get("user_agent", "Unknown"),
                "referrer": event.get("referrer") or "None",
                "successful": "True",
                "created_at": parser.isoparse(event["created_at"]).strftime(
                    "%m/%d/%Y, %H:%M:%S UTC"
                ),
                "kind": str(event.get("kind", "unknown")).replace("_", " ").title(),
            }
        )
    return rows
