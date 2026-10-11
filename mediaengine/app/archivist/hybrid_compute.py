from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid


SCHEMA_VERSION = "hybrid_compute_v1"
VALID_STATUSES = (
    "queued",
    "staging",
    "ready",
    "running",
    "cancelling",
    "succeeded",
    "failed",
    "expired",
    "cleanup_pending",
    "cleaned",
)


class ComputeContractError(ValueError):
    pass


class ComputeCancelled(RuntimeError):
    pass


class RetryableComputeError(RuntimeError):
    pass


def _canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_hex_sha256(value: str, label: str = "sha256") -> str:
    value = str(value or "").lower()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise ComputeContractError(f"invalid {label}")
    return value


def make_asset_ref(
    data: bytes,
    *,
    asset_id: str | None = None,
    transfer: str = "proxy",
    mime: str = "application/octet-stream",
    byte_range: tuple[int, int] | None = None,
) -> dict:
    if not isinstance(data, (bytes, bytearray)):
        raise ComputeContractError("asset data must be bytes")
    payload = bytes(data)
    if transfer not in {"proxy", "range", "full"}:
        raise ComputeContractError("invalid transfer mode")
    ref = {
        "asset_id": asset_id or f"asset-{uuid.uuid4().hex}",
        "sha256": _sha256_bytes(payload),
        "bytes": len(payload),
        "transfer": transfer,
        "mime": str(mime or "application/octet-stream")[:160],
    }
    if byte_range is not None:
        start, end = int(byte_range[0]), int(byte_range[1])
        if start < 0 or end < start or end > len(payload):
            raise ComputeContractError("invalid byte range")
        ref["byte_range"] = [start, end]
    return ref


def validate_asset_ref(ref: dict) -> dict:
    if not isinstance(ref, dict):
        raise ComputeContractError("asset ref must be object")
    asset_id = str(ref.get("asset_id") or "")
    if not asset_id or "/" in asset_id or chr(92) in asset_id:
        raise ComputeContractError("invalid asset id")
    _require_hex_sha256(ref.get("sha256"), "asset sha256")
    size = int(ref.get("bytes", -1))
    if size < 0:
        raise ComputeContractError("invalid asset size")
    if ref.get("transfer") not in {"proxy", "range", "full"}:
        raise ComputeContractError("invalid transfer mode")
    return ref


def build_job_envelope(
    *,
    job_id: str,
    idempotency_key: str,
    job_type: str,
    input_assets: list[dict],
    requested_outputs: list[str],
    settings: dict | None = None,
    worker_version: str = "local-fake-v1",
    resource_class: dict | None = None,
    privacy_classification: str = "synthetic",
    full_original_allowed: bool = False,
    paid_cloud_approved: bool = False,
    cost_ceiling_usd: float = 0.0,
    max_runtime_seconds: int = 300,
    max_attempts: int = 2,
    created_at: int | None = None,
) -> dict:
    for ref in input_assets:
        validate_asset_ref(ref)
    if not job_id or not idempotency_key or not job_type:
        raise ComputeContractError("job identity fields required")
    if not requested_outputs:
        raise ComputeContractError("requested outputs required")
    if max_runtime_seconds <= 0 or max_runtime_seconds > 7 * 24 * 3600:
        raise ComputeContractError("invalid max runtime")
    if max_attempts < 1 or max_attempts > 8:
        raise ComputeContractError("invalid retry policy")
    if cost_ceiling_usd < 0:
        raise ComputeContractError("invalid cost ceiling")
    now = int(time.time()) if created_at is None else int(created_at)
    return {
        "schema_version": SCHEMA_VERSION,
        "job_id": str(job_id),
        "idempotency_key": str(idempotency_key),
        "job_type": str(job_type),
        "worker_version": str(worker_version),
        "inputs": [dict(ref) for ref in input_assets],
        "requested_outputs": [str(x) for x in requested_outputs],
        "settings": dict(settings or {}),
        "resource_class": dict(resource_class or {"cpu": 1, "gpu": False, "min_memory_mb": 256}),
        "deadline": now + int(max_runtime_seconds),
        "max_runtime_seconds": int(max_runtime_seconds),
        "retry_policy": {"max_attempts": int(max_attempts), "retryable": ["synthetic_transient"]},
        "privacy": {
            "classification": str(privacy_classification),
            "full_original_allowed": bool(full_original_allowed),
        },
        "cost": {
            "ceiling_usd": float(cost_ceiling_usd),
            "paid_cloud_approved": bool(paid_cloud_approved),
        },
        "control_scope": ["progress", "cancel"],
        "timestamps": {
            "created": now,
            "started": None,
            "heartbeat": None,
            "finished": None,
        },
        "status": "queued",
    }


def validate_job_envelope(job: dict) -> dict:
    if not isinstance(job, dict):
        raise ComputeContractError("job envelope must be object")
    required = {
        "schema_version",
        "job_id",
        "idempotency_key",
        "job_type",
        "worker_version",
        "inputs",
        "requested_outputs",
        "settings",
        "resource_class",
        "deadline",
        "max_runtime_seconds",
        "retry_policy",
        "privacy",
        "cost",
        "control_scope",
        "timestamps",
        "status",
    }
    missing = sorted(required.difference(job))
    if missing:
        raise ComputeContractError("missing fields: " + ",".join(missing))
    if job["schema_version"] != SCHEMA_VERSION:
        raise ComputeContractError("unsupported schema version")
    if job["status"] not in VALID_STATUSES:
        raise ComputeContractError("invalid job status")
    for ref in job["inputs"]:
        validate_asset_ref(ref)
    if bool(job["cost"].get("paid_cloud_approved")):
        if float(job["cost"].get("ceiling_usd", 0.0)) <= 0:
            raise ComputeContractError("paid cloud requires positive cost ceiling")
    return job


def _manifest_payload(manifest: dict) -> dict:
    return {k: manifest[k] for k in sorted(manifest) if k != "signature"}


def sign_staged_asset(
    asset_ref: dict,
    signing_key: bytes,
    *,
    job_id: str,
    now: int | None = None,
    ttl_seconds: int = 300,
) -> dict:
    validate_asset_ref(asset_ref)
    if not isinstance(signing_key, (bytes, bytearray)) or len(signing_key) < 16:
        raise ComputeContractError("signing key too short")
    if ttl_seconds < 1 or ttl_seconds > 3600:
        raise ComputeContractError("invalid staging ttl")
    ts = int(time.time()) if now is None else int(now)
    manifest = {
        "job_id": str(job_id),
        "asset_id": asset_ref["asset_id"],
        "sha256": asset_ref["sha256"],
        "bytes": int(asset_ref["bytes"]),
        "transfer": asset_ref["transfer"],
        "scope": "read",
        "uri": f"staged://{job_id}/{asset_ref['asset_id']}",
        "issued_at": ts,
        "expires_at": ts + int(ttl_seconds),
    }
    manifest["signature"] = hmac.new(bytes(signing_key), _canonical_json(manifest), hashlib.sha256).hexdigest()
    return manifest


def verify_staged_asset(
    manifest: dict,
    asset_ref: dict,
    signing_key: bytes,
    *,
    now: int | None = None,
) -> bool:
    validate_asset_ref(asset_ref)
    if not isinstance(manifest, dict):
        raise ComputeContractError("staged manifest must be object")
    signature = str(manifest.get("signature") or "")
    payload = _manifest_payload(manifest)
    expected = hmac.new(bytes(signing_key), _canonical_json(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ComputeContractError("staged manifest signature mismatch")
    ts = int(time.time()) if now is None else int(now)
    if ts > int(manifest.get("expires_at", 0)):
        raise ComputeContractError("staged manifest expired")
    for key in ("asset_id", "sha256", "bytes", "transfer"):
        if manifest.get(key) != asset_ref.get(key):
            raise ComputeContractError("staged manifest asset mismatch")
    if manifest.get("scope") != "read":
        raise ComputeContractError("invalid staged scope")
    return True


class FakeComputeWorker:
    transport = "local_fake"
    worker_version = "local-fake-v1"

    def __init__(self, blobs: dict[str, bytes]):
        self._blobs = {str(k): bytes(v) for k, v in blobs.items()}
        self._failed_once: set[str] = set()

    def execute(
        self,
        job: dict,
        staged_inputs: list[dict],
        signing_key: bytes,
        *,
        progress_cb=None,
        cancel_cb=None,
        attempt: int = 1,
        fail_once: bool = False,
        now: int | None = None,
    ) -> dict:
        validate_job_envelope(job)
        if len(staged_inputs) != len(job["inputs"]):
            raise ComputeContractError("staged input count mismatch")

        def emit(value: float, stage: str):
            if progress_cb:
                progress_cb({"progress": float(value), "stage": stage, "attempt": int(attempt)})

        def check_cancel():
            if cancel_cb and cancel_cb():
                raise ComputeCancelled("cancel requested")

        emit(0.0, "staging")
        check_cancel()

        source_parts = []
        for ref, manifest in zip(job["inputs"], staged_inputs):
            verify_staged_asset(manifest, ref, signing_key, now=now)
            blob = self._blobs.get(ref["asset_id"])
            if blob is None:
                raise ComputeContractError("staged blob missing")
            if len(blob) != int(ref["bytes"]) or _sha256_bytes(blob) != ref["sha256"]:
                raise ComputeContractError("staged blob integrity mismatch")
            source_parts.append(blob)

        emit(0.25, "ready")
        check_cancel()

        idem = str(job["idempotency_key"])
        if fail_once and idem not in self._failed_once:
            self._failed_once.add(idem)
            raise RetryableComputeError("synthetic_transient")

        emit(0.6, "running")
        check_cancel()

        seed = b"|".join(source_parts) + b"|" + _canonical_json(job["settings"])
        output = b"FAKE-COMPUTE-V1" + bytes([10]) + hashlib.sha256(seed).hexdigest().encode("ascii") + bytes([10])
        manifest = {
            "artifact_id": "output-main",
            "sha256": _sha256_bytes(output),
            "bytes": len(output),
            "mime": "application/octet-stream",
            "worker_version": self.worker_version,
            "input_sha256": [ref["sha256"] for ref in job["inputs"]],
        }
        emit(1.0, "succeeded")
        return {
            "status": "succeeded",
            "transport": self.transport,
            "attempt": int(attempt),
            "output_bytes": output,
            "output_manifest": manifest,
        }


def run_fake_with_retry(
    worker: FakeComputeWorker,
    job: dict,
    staged_inputs: list[dict],
    signing_key: bytes,
    *,
    progress_cb=None,
    cancel_cb=None,
    fail_once: bool = False,
    now: int | None = None,
) -> dict:
    validate_job_envelope(job)
    max_attempts = int(job["retry_policy"]["max_attempts"])
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return worker.execute(
                job,
                staged_inputs,
                signing_key,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
                attempt=attempt,
                fail_once=fail_once,
                now=now,
            )
        except RetryableComputeError as exc:
            last_error = exc
            if attempt >= max_attempts:
                raise
    raise RetryableComputeError(str(last_error or "retry exhausted"))


def run_contract_self_test() -> dict:
    now = 1_700_000_000
    signing_key = b"synthetic-compute-contract-key-32b"
    blob = b"synthetic-only-media-fixture-v1"
    asset = make_asset_ref(blob, asset_id="asset-synthetic-001", transfer="proxy", mime="video/mp4")
    staged = sign_staged_asset(asset, signing_key, job_id="job-synthetic-001", now=now, ttl_seconds=300)
    verify_staged_asset(staged, asset, signing_key, now=now + 1)

    tamper_rejected = False
    tampered = dict(staged)
    tampered["bytes"] = int(tampered["bytes"]) + 1
    try:
        verify_staged_asset(tampered, asset, signing_key, now=now + 1)
    except ComputeContractError:
        tamper_rejected = True
    if not tamper_rejected:
        raise ComputeContractError("tamper test failed")

    expiry_rejected = False
    try:
        verify_staged_asset(staged, asset, signing_key, now=now + 301)
    except ComputeContractError:
        expiry_rejected = True
    if not expiry_rejected:
        raise ComputeContractError("expiry test failed")

    job = build_job_envelope(
        job_id="job-synthetic-001",
        idempotency_key="idem-synthetic-001",
        job_type="synthetic_hash",
        input_assets=[asset],
        requested_outputs=["main"],
        settings={"mode": "deterministic", "quality": 1},
        paid_cloud_approved=False,
        cost_ceiling_usd=0.0,
        full_original_allowed=False,
        max_attempts=2,
        created_at=now,
    )
    validate_job_envelope(job)
    if job["cost"]["paid_cloud_approved"]:
        raise ComputeContractError("synthetic test unexpectedly enables paid cloud")

    progress_events = []
    worker = FakeComputeWorker({asset["asset_id"]: blob})
    result = run_fake_with_retry(
        worker,
        job,
        [staged],
        signing_key,
        progress_cb=progress_events.append,
        now=now + 1,
    )
    values = [event["progress"] for event in progress_events]
    if not values or values != sorted(values) or values[-1] != 1.0:
        raise ComputeContractError("progress contract failed")
    if _sha256_bytes(result["output_bytes"]) != result["output_manifest"]["sha256"]:
        raise ComputeContractError("output hash contract failed")

    cancelled = False
    try:
        worker.execute(job, [staged], signing_key, cancel_cb=lambda: True, now=now + 1)
    except ComputeCancelled:
        cancelled = True
    if not cancelled:
        raise ComputeContractError("cancel contract failed")

    retry_events = []
    retry_job = dict(job)
    retry_job["idempotency_key"] = "idem-synthetic-retry-001"
    retry_result = run_fake_with_retry(
        worker,
        retry_job,
        [staged],
        signing_key,
        progress_cb=retry_events.append,
        fail_once=True,
        now=now + 1,
    )
    if retry_result["attempt"] != 2:
        raise ComputeContractError("retry contract failed")

    return {
        "schema_version": SCHEMA_VERSION,
        "transport": worker.transport,
        "synthetic_only": True,
        "paid_cloud": False,
        "asset_hash_verified": True,
        "signature_tamper_rejected": tamper_rejected,
        "expiry_rejected": expiry_rejected,
        "progress_monotonic": True,
        "cancelled_safely": cancelled,
        "retry_attempt": retry_result["attempt"],
        "output_hash_verified": True,
        "status_count": len(VALID_STATUSES),
    }
