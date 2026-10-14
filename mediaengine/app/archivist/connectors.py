from __future__ import annotations
import json
from pathlib import Path
from .config import HOME,load_config
from .db import now_iso,db
from .platform_adapter import secret_store_capabilities
from .secret_store import delete_secret
from .social_lab import candidate_from_composition,evaluate_composition

PROVIDERS=(
    {"id":"youtube","name":"YouTube"},
    {"id":"instagram","name":"Instagram"},
    {"id":"tiktok","name":"TikTok"},
    {"id":"facebook","name":"Facebook"},
)
BLOCK_STATES={"too_similar_block","exact_duplicate_block"}

def _social_config(cfg=None):
    cfg=cfg if isinstance(cfg,dict) else load_config()
    return ((cfg.get("connections") or {}).get("social") or {})

def youtube_public_client_id(cfg=None):
    social=_social_config(cfg)
    providers=social.get("providers") or {}
    return str(((providers.get("youtube") or {}).get("client_id") or "")).strip()

def provider_connection_gate(provider,cfg=None):
    provider=str(provider or "").strip().lower()
    if provider not in {x["id"] for x in PROVIDERS}:
        raise ValueError("Unknown provider")
    secure=bool(secret_store_capabilities().get("implemented"))
    if not secure:
        return {"connect_available":False,"connection_prerequisites_ready":False,"public_client_id_configured":False,"connection_blocker":"os_secret_store_unavailable"}
    if provider=="youtube":
        configured=bool(youtube_public_client_id(cfg))
        return {
            "connect_available":configured,
            "connection_prerequisites_ready":configured,
            "public_client_id_configured":configured,
            "connection_blocker":None if configured else "youtube_client_id_missing",
        }
    if provider=="tiktok":
        return {"connect_available":False,"connection_prerequisites_ready":False,"public_client_id_configured":False,"connection_blocker":"backend_token_broker_not_configured"}
    return {"connect_available":False,"connection_prerequisites_ready":False,"public_client_id_configured":False,"connection_blocker":"meta_secret_flow_not_enabled"}

def connection_secret_ref(provider,connection_id,kind="refresh_token"):
    provider=str(provider or "").strip().lower()
    if provider not in {x["id"] for x in PROVIDERS}:raise ValueError("Unknown provider")
    return f"social/{provider}/{int(connection_id)}/{str(kind or 'refresh_token').strip()}"

def list_provider_connections(provider=None):
    with db() as con:
        if provider:
            rows=con.execute("SELECT * FROM social_provider_connections WHERE provider=? ORDER BY id",(str(provider).lower(),)).fetchall()
        else:
            rows=con.execute("SELECT * FROM social_provider_connections ORDER BY provider,id").fetchall()
    return [dict(x) for x in rows]

def save_provider_connection(provider,account_id,display_name="",granted_scopes=None,status="connected",secret_store_ref=None):
    provider=str(provider or "").strip().lower()
    if provider not in {x["id"] for x in PROVIDERS}:raise ValueError("Unknown provider")
    account_id=str(account_id or "").strip()
    if not account_id:raise ValueError("Provider account id is required")
    scopes=[str(x) for x in (granted_scopes or []) if str(x)]
    ts=now_iso()
    with db() as con:
        row=con.execute("SELECT id,created_at FROM social_provider_connections WHERE provider=? AND account_id=?",(provider,account_id)).fetchone()
        if row:
            con.execute("""UPDATE social_provider_connections
                           SET display_name=?,granted_scopes_json=?,status=?,secret_store_ref=?,updated_at=?,last_authenticated_at=?
                           WHERE id=?""",
                        (str(display_name or "")[:200],json.dumps(scopes,separators=(",",":")),str(status or "connected"),secret_store_ref,ts,ts,row["id"]))
            cid=int(row["id"])
        else:
            cur=con.execute("""INSERT INTO social_provider_connections(
                               provider,account_id,display_name,granted_scopes_json,status,secret_store_ref,created_at,updated_at,last_authenticated_at
                               ) VALUES(?,?,?,?,?,?,?,?,?)""",
                            (provider,account_id,str(display_name or "")[:200],json.dumps(scopes,separators=(",",":")),str(status or "connected"),secret_store_ref,ts,ts,ts))
            cid=int(cur.lastrowid)
        con.commit()
    return cid

def disconnect_provider_connection(connection_id):
    with db() as con:
        row=con.execute("SELECT id,secret_store_ref FROM social_provider_connections WHERE id=?",(int(connection_id),)).fetchone()
        if not row:return False
        ref=row["secret_store_ref"]
        if ref:
            delete_secret(ref)
        con.execute("UPDATE social_provider_connections SET status='disconnected',secret_store_ref=NULL,updated_at=? WHERE id=?",(now_iso(),int(connection_id)))
        con.commit()
    return True


PROVIDER_CONTRACTS={
    "youtube":{
        "official_documentation_validation":"verified_2026-09-22",
        "official_api_validation":"pending_live_validation",
        "oauth_flow":"desktop_authorization_code_pkce_loopback",
        "auth_runtime":"local_desktop_pkce",
        "token_exchange_location":"local_device",
        "confidential_credential_boundary":"no_confidential_secret_in_installed_client",
        "publish_mode":"youtube_data_api_v3_videos_insert_resumable",
        "publish_scopes":["https://www.googleapis.com/auth/youtube.upload"],
        "analytics_mode":"youtube_analytics_reports_query",
        "analytics_scopes":["https://www.googleapis.com/auth/youtube.readonly","https://www.googleapis.com/auth/yt-analytics.readonly"],
        "analytics_validation":"documented",
        "account_requirement":"authorized_youtube_channel",
        "media_transfer":"local_file_resumable_upload",
        "provider_review_gate":"unverified_upload_projects_are_private_until_youtube_audit",
        "connection_blocker":"oauth_not_implemented_and_provider_audit_not_completed",
        "source_notes":["Google YouTube Data API videos.insert","Google OAuth for desktop apps","YouTube Analytics reports.query"],
    },
    "tiktok":{
        "official_documentation_validation":"verified_2026-09-22",
        "official_api_validation":"pending_live_validation",
        "oauth_flow":"desktop_authorization_code_pkce_loopback",
        "auth_runtime":"desktop_pkce_with_server_token_exchange",
        "token_exchange_location":"backend_broker_required",
        "confidential_credential_boundary":"server_only",
        "publish_mode":"content_posting_api_direct_post_or_upload_draft",
        "publish_scopes":["video.publish"],
        "draft_scopes":["video.upload"],
        "analytics_mode":"display_api_video_query",
        "analytics_scopes":["video.list"],
        "analytics_validation":"documented_public_video_metrics",
        "account_requirement":"authorized_tiktok_user",
        "media_transfer":"file_upload_or_verified_domain_pull_from_url",
        "creator_info_required":True,
        "explicit_user_consent_required":True,
        "provider_review_gate":"video_publish_scope_approval_and_content_posting_audit_required_for_public_direct_post",
        "connection_blocker":"oauth_not_implemented_and_scope_audit_not_completed",
        "source_notes":["TikTok Login Kit Desktop","TikTok Content Posting API Direct Post","TikTok Display API video.query"],
    },
    "instagram":{
        "official_documentation_validation":"verified_2026-09-22",
        "official_api_validation":"pending_live_validation",
        "oauth_flow":"meta_oauth_user_authorization",
        "auth_runtime":"disabled_pending_exact_secret_flow_contract",
        "token_exchange_location":"disabled_until_verified",
        "confidential_credential_boundary":"never_embed_in_desktop",
        "preferred_login":"instagram_login_for_professional_accounts",
        "publish_mode":"instagram_api_reels_container_then_media_publish",
        "publish_scopes":["instagram_business_basic","instagram_business_content_publish"],
        "alternate_facebook_login_scopes":["pages_show_list","instagram_basic","instagram_content_publish","pages_read_engagement"],
        "analytics_mode":"provider_insights_contract_pending_exact_minimal_scope",
        "analytics_scopes":[],
        "analytics_validation":"pending_exact_minimal_scope_review",
        "account_requirement":"instagram_professional_business_or_creator",
        "media_transfer":"public_https_video_url_for_reels_container",
        "provider_review_gate":"app_review_or_advanced_access_required_before_general_external_user_rollout",
        "connection_blocker":"oauth_not_implemented_and_app_review_not_completed",
        "source_notes":["Meta official Instagram Postman workspace","Instagram Reels Publishing","Instagram API with Instagram Login"],
    },
    "facebook":{
        "official_documentation_validation":"verified_2026-09-22",
        "official_api_validation":"pending_live_validation",
        "oauth_flow":"meta_oauth_user_to_page_access_token",
        "auth_runtime":"disabled_pending_exact_secret_flow_contract",
        "token_exchange_location":"disabled_until_verified",
        "confidential_credential_boundary":"never_embed_in_desktop",
        "publish_mode":"facebook_page_reels_start_upload_finish",
        "publish_scopes":["pages_show_list","pages_read_engagement","pages_manage_posts"],
        "analytics_mode":"page_insights_contract_pending_exact_minimal_scope",
        "analytics_scopes":[],
        "analytics_validation":"pending_exact_minimal_scope_review",
        "account_requirement":"facebook_page_managed_by_authorized_user",
        "media_transfer":"local_binary_upload_or_hosted_cdn_url",
        "provider_review_gate":"pages_manage_posts_requires_review_for_external_user_rollout",
        "connection_blocker":"oauth_not_implemented_and_page_permission_review_not_completed",
        "source_notes":["Meta official Facebook Postman workspace","Facebook Page Reels Publishing","Meta pages_manage_posts permissions reference"],
    },
}

def connector_catalog():
    sec=secret_store_capabilities()
    secure=bool(sec.get("implemented"))
    out=[]
    cfg=load_config()
    for p in PROVIDERS:
        contract=dict(PROVIDER_CONTRACTS[p["id"]])
        gate=provider_connection_gate(p["id"],cfg)
        out.append({
            "id":p["id"],"name":p["name"],
            **contract,
            **gate,
            "official_connection_enabled":False,
            "credential_storage_ready":secure,
            "credential_status":"not_configured" if secure else "blocked_until_os_secret_store",
            "manual_export_available":True,
            "analytics_csv_import_available":True,
            "auto_publish":False,
            "data_transfer":"none_until_user_connects_a_validated_provider",
        })
    return out

def connector_summary():
    rows=connector_catalog()
    return {
        "providers":len(rows),
        "documentation_contracts_verified":sum(1 for x in rows if x["official_documentation_validation"].startswith("verified_")),
        "official_connections_enabled":sum(1 for x in rows if x["official_connection_enabled"]),
        "connect_available":sum(1 for x in rows if x.get("connect_available")),
        "manual_export_available":all(x["manual_export_available"] for x in rows),
        "analytics_csv_import_available":all(x["analytics_csv_import_available"] for x in rows),
        "credential_storage_ready":all(x["credential_storage_ready"] for x in rows),
        "auto_publish":False,
    }

def create_manual_handoff(media_path,title="",platform_target="",caption_text="",novelty_state="new",composition_id=None):
    state=str(novelty_state or "new")
    if state in BLOCK_STATES:raise ValueError("Novelty Guard blocks manual handoff for state: "+state)
    composition_exists=False
    if composition_id is not None:
        try:
            with db() as con:
                composition_exists=con.execute("SELECT 1 FROM compositions WHERE id=?",(int(composition_id),)).fetchone() is not None
        except Exception:
            composition_exists=False
    if composition_exists:
        current=candidate_from_composition(int(composition_id))
        p=Path(current["output_path"])
        if Path(media_path).resolve()!=p.resolve():raise ValueError("Composition output path no longer matches current validated render")
    else:
        p=Path(media_path)
    if not p.exists() or not p.is_file():raise ValueError("Rendered media is unavailable")
    target=str(platform_target or "other").strip().lower()[:80] or "other"
    allowed={x["id"] for x in PROVIDERS}|{"other"}
    if target not in allowed:raise ValueError("Unknown manual handoff target")
    root=HOME/"exports"/"social_handoffs";root.mkdir(parents=True,exist_ok=True)
    stamp=now_iso().replace(":","-").replace("+","_")
    stem=f"composition-{int(composition_id)}" if composition_id is not None else p.stem
    dest=root/f"{stem}-{target}-{stamp}.json"
    payload={
        "schema":"archivist_manual_social_handoff_v1",
        "created_at":now_iso(),
        "composition_id":int(composition_id) if composition_id is not None else None,
        "title":str(title or "")[:160],
        "platform_target":target,
        "caption_text":str(caption_text or "")[:2000],
        "novelty_state":state,
        "media_path":str(p),
        "upload_performed":False,
        "official_connector_used":False,
        "credentials_used":False,
        "instructions":"Use the rendered media path and metadata in this manifest for manual upload. MediaEngine did not contact a social platform."
    }
    tmp=dest.with_suffix(dest.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(dest)
    return {"manifest_path":str(dest),"media_path":str(p),"platform_target":target,"novelty_state":state,"upload_performed":False,"official_connector_used":False}

def create_manual_handoff_for_composition(composition_id,platform_target="",caption_text=""):
    c=candidate_from_composition(composition_id)
    novelty=evaluate_composition(composition_id,caption_text)
    return create_manual_handoff(c["output_path"],c["title"],platform_target,caption_text,novelty["state"],c["composition_id"])
