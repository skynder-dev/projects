create or replace function reveng.guard_global_catalog_candidate_metadata_v1() returns trigger language plpgsql set search_path to '' as $function$
declare v_key text;
begin
  for v_key in select jsonb_object_keys(coalesce(new.metadata,'{}'::jsonb)) loop
    if lower(v_key) in ('workspace_id','workspace_key','user_id','owner_id','owner_name','private_context','private_notes','personalization','personal_context','profile','profile_context','mandate','mandate_context','memory','connector_payload','connector_context')
    or lower(v_key) like 'private\_%' escape '\' or lower(v_key) like 'personal\_%' escape '\' or lower(v_key) like 'workspace\_%' escape '\' or lower(v_key) like 'owner\_%' escape '\' or lower(v_key) like 'user\_%' escape '\'
    then raise exception using errcode='42501', message='REVENG_GLOBAL_CATALOG_PRIVATE_METADATA_FORBIDDEN', detail='Global candidate metadata must remain tenant-neutral and may not contain owner/workspace/private-context fields.';
    end if;
  end loop;
  return new;
end; $function$;
create trigger catalog_candidate_inbox_private_metadata_guard before insert or update of metadata on reveng.catalog_candidate_inbox for each row execute function reveng.guard_global_catalog_candidate_metadata_v1();
