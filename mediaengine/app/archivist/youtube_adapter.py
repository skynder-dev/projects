from __future__ import annotations

import hashlib
from dataclasses import dataclass

YOUTUBE_DATA_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"
YOUTUBE_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"

SCOPE_UPLOAD = "https://www.googleapis.com/auth/youtube.upload"
SCOPE_READONLY = "https://www.googleapis.com/auth/youtube.readonly"
SCOPE_ANALYTICS = "https://www.googleapis.com/auth/yt-analytics.readonly"
REQUIRED_SCOPES = (SCOPE_UPLOAD, SCOPE_READONLY, SCOPE_ANALYTICS)

CURRENT_STATS_FIELDS = ("viewCount", "likeCount", "commentCount")
ANALYTICS_METRICS = (
    "engagedViews",
    "views",
    "comments",
    "likes",
    "shares",
    "estimatedMinutesWatched",
    "averageViewDuration",
    "averageViewPercentage",
    "subscribersGained",
    "subscribersLost",
)


class YouTubeAdapterError(ValueError):
    pass


def verify_scopes(granted_scopes) -> dict:
    granted = {str(x).strip() for x in (granted_scopes or []) if str(x).strip()}
    required = set(REQUIRED_SCOPES)
    missing = sorted(required.difference(granted))
    return {
        "ok": not missing,
        "granted": sorted(granted),
        "required": list(REQUIRED_SCOPES),
        "missing": missing,
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def channels_list_request() -> dict:
    return {
        "operation": "channels.list",
        "method": "GET",
        "url": YOUTUBE_DATA_BASE + "/channels",
        "params": {
            "part": "id,snippet",
            "mine": "true",
        },
        "required_scope": SCOPE_READONLY,
        "live_enabled": False,
    }


def videos_insert_request(
    *,
    title: str,
    description: str = "",
    privacy_status: str = "private",
    media_bytes: bytes,
    content_type: str = "video/mp4",
) -> dict:
    if privacy_status not in {"private", "unlisted", "public"}:
        raise YouTubeAdapterError("invalid privacy status")
    if not isinstance(media_bytes, (bytes, bytearray)) or not media_bytes:
        raise YouTubeAdapterError("synthetic media bytes required")
    payload = bytes(media_bytes)
    return {
        "operation": "videos.insert",
        "method": "POST",
        "url": YOUTUBE_UPLOAD_BASE + "/videos",
        "params": {
            "part": "snippet,status",
            "uploadType": "resumable",
        },
        "json": {
            "snippet": {
                "title": str(title),
                "description": str(description),
            },
            "status": {
                "privacyStatus": privacy_status,
            },
        },
        "media": {
            "content_type": str(content_type),
            "bytes": len(payload),
            "sha256": _sha256_bytes(payload),
        },
        "required_scope": SCOPE_UPLOAD,
        "live_enabled": False,
    }


def videos_list_stats_request(video_ids) -> dict:
    ids = [str(x).strip() for x in (video_ids or []) if str(x).strip()]
    if not ids:
        raise YouTubeAdapterError("video ids required")
    return {
        "operation": "videos.list",
        "method": "GET",
        "url": YOUTUBE_DATA_BASE + "/videos",
        "params": {
            "part": "statistics",
            "id": ",".join(ids),
        },
        "required_scope": SCOPE_READONLY,
        "live_enabled": False,
    }


def analytics_reports_request(
    *,
    video_id: str,
    start_date: str,
    end_date: str,
) -> dict:
    video_id = str(video_id or "").strip()
    if not video_id:
        raise YouTubeAdapterError("video id required")
    return {
        "operation": "reports.query",
        "method": "GET",
        "url": YOUTUBE_ANALYTICS_BASE + "/reports",
        "params": {
            "ids": "channel==MINE",
            "startDate": str(start_date),
            "endDate": str(end_date),
            "metrics": ",".join(ANALYTICS_METRICS),
            "dimensions": "video",
            "filters": "video==" + video_id,
        },
        "required_scope": SCOPE_ANALYTICS,
        "freshness": "provider_delayed",
        "missing_row_semantics": "unknown_not_zero",
        "live_enabled": False,
    }


def normalize_channels_list(response: dict) -> list[dict]:
    out = []
    for item in list((response or {}).get("items") or []):
        channel_id = str(item.get("id") or "").strip()
        title = str(((item.get("snippet") or {}).get("title")) or "").strip()
        if channel_id:
            out.append({"channel_id": channel_id, "display_name": title})
    return out


def normalize_current_stats(response: dict) -> list[dict]:
    rows = []
    for item in list((response or {}).get("items") or []):
        video_id = str(item.get("id") or "").strip()
        stats = item.get("statistics") or {}
        if not video_id:
            continue
        row = {"video_id": video_id}
        for key in CURRENT_STATS_FIELDS:
            value = stats.get(key)
            row[key] = int(value) if value is not None else None
        rows.append(row)
    return rows


def normalize_analytics_report(response: dict) -> dict:
    headers = [
        str(x.get("name") or "")
        for x in list((response or {}).get("columnHeaders") or [])
    ]
    rows = list((response or {}).get("rows") or [])
    parsed = []
    for raw in rows:
        parsed.append({headers[i]: raw[i] for i in range(min(len(headers), len(raw)))})
    return {
        "rows": parsed,
        "freshness": "provider_delayed",
        "missing_row_semantics": "unknown_not_zero",
        "provider_semantics_preserved": True,
    }


@dataclass
class MockYouTubeTransport:
    fixtures: dict

    live_network = False

    def __post_init__(self):
        self.calls = []

    def send(self, request: dict) -> dict:
        if request.get("live_enabled"):
            raise YouTubeAdapterError("mock transport refuses live-enabled request")
        operation = str(request.get("operation") or "")
        self.calls.append(operation)
        if operation not in self.fixtures:
            raise YouTubeAdapterError("missing synthetic fixture: " + operation)
        return self.fixtures[operation]


def run_contract_self_test() -> dict:
    granted = list(REQUIRED_SCOPES)
    scope_state = verify_scopes(granted)
    if not scope_state["ok"]:
        raise YouTubeAdapterError("required scopes unexpectedly missing")

    incomplete = verify_scopes([SCOPE_READONLY])
    if incomplete["ok"] or SCOPE_UPLOAD not in incomplete["missing"] or SCOPE_ANALYTICS not in incomplete["missing"]:
        raise YouTubeAdapterError("scope verification failed")

    synthetic_video = b"synthetic-youtube-video-fixture-v1"
    upload_request = videos_insert_request(
        title="Synthetic fixture",
        description="No live provider call",
        privacy_status="private",
        media_bytes=synthetic_video,
    )
    if upload_request["media"]["sha256"] != _sha256_bytes(synthetic_video):
        raise YouTubeAdapterError("upload request hash mismatch")

    channel_request = channels_list_request()
    stats_request = videos_list_stats_request(["vid-synthetic-001"])
    analytics_request = analytics_reports_request(
        video_id="vid-synthetic-001",
        start_date="2026-09-01",
        end_date="2026-09-02",
    )

    fixtures = {
        "channels.list": {
            "items": [
                {
                    "id": "UC_SYNTHETIC_001",
                    "snippet": {"title": "Synthetic Channel"},
                }
            ]
        },
        "videos.insert": {
            "id": "vid-synthetic-001",
            "status": {"uploadStatus": "uploaded", "privacyStatus": "private"},
        },
        "videos.list": {
            "items": [
                {
                    "id": "vid-synthetic-001",
                    "statistics": {
                        "viewCount": "123",
                        "likeCount": "11",
                        "commentCount": "4",
                    },
                }
            ]
        },
        "reports.query": {
            "columnHeaders": [
                {"name": "video"},
                {"name": "engagedViews"},
                {"name": "views"},
                {"name": "comments"},
                {"name": "likes"},
                {"name": "shares"},
                {"name": "estimatedMinutesWatched"},
                {"name": "averageViewDuration"},
                {"name": "averageViewPercentage"},
                {"name": "subscribersGained"},
                {"name": "subscribersLost"},
            ],
            "rows": [
                [
                    "vid-synthetic-001",
                    100,
                    123,
                    4,
                    11,
                    3,
                    88.5,
                    43.0,
                    71.2,
                    2,
                    1,
                ]
            ],
        },
    }
    transport = MockYouTubeTransport(fixtures)

    channels = normalize_channels_list(transport.send(channel_request))
    upload_response = transport.send(upload_request)
    current_stats = normalize_current_stats(transport.send(stats_request))
    analytics = normalize_analytics_report(transport.send(analytics_request))

    if channels != [{"channel_id": "UC_SYNTHETIC_001", "display_name": "Synthetic Channel"}]:
        raise YouTubeAdapterError("channels.list discovery contract failed")
    if upload_response.get("id") != "vid-synthetic-001":
        raise YouTubeAdapterError("videos.insert response contract failed")
    if current_stats[0]["viewCount"] != 123 or current_stats[0]["likeCount"] != 11:
        raise YouTubeAdapterError("Data API current stats contract failed")
    if not analytics["rows"] or analytics["rows"][0].get("views") != 123:
        raise YouTubeAdapterError("Analytics report contract failed")
    if analytics["freshness"] != "provider_delayed" or analytics["missing_row_semantics"] != "unknown_not_zero":
        raise YouTubeAdapterError("Analytics delayed-report semantics failed")

    return {
        "adapter_version": "youtube_synthetic_v1",
        "provider": "youtube",
        "transport": "mock",
        "live_network": False,
        "live_oauth": False,
        "real_client_id": False,
        "real_token": False,
        "provider_network_calls": 0,
        "mock_calls": list(transport.calls),
        "required_scopes": list(REQUIRED_SCOPES),
        "scope_verification": True,
        "channels_list_mine": channel_request["params"]["mine"] == "true",
        "channel_id": channels[0]["channel_id"],
        "upload_operation": upload_request["operation"],
        "upload_privacy": upload_request["json"]["status"]["privacyStatus"],
        "upload_sha256_verified": True,
        "data_api_current_stats": list(CURRENT_STATS_FIELDS),
        "analytics_metrics": list(ANALYTICS_METRICS),
        "analytics_freshness": analytics["freshness"],
        "missing_row_semantics": analytics["missing_row_semantics"],
    }
