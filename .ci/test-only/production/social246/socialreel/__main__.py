import argparse
import os
import json
import sys
import unittest
from pathlib import Path

from .common import ROOT, PipelineError, read_json


def main(argv=None):
    ap = argparse.ArgumentParser(prog="socialreel")
    from . import __version__
    ap.add_argument('--version',action='version',version='Social '+__version__+' | SOCIAL_REAL_REELS_V1')
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="produce one Reel end-to-end")
    r.add_argument("--config", default=str(ROOT / "config.json"))
    r.add_argument("--out", default=str(ROOT / "runs"))
    r.add_argument("--fixture", help="use exported records instead of live Grants.gov (never accepted)")
    r.add_argument("--opportunity", help="force a specific Grants.gov opportunity id")
    r.add_argument("--history", help="history.json used to avoid repeating topics")
    r.add_argument("--timeout", type=int, default=900)
    r.add_argument("--cancel-file")
    r.add_argument("--voice", help="override voice backend (kokoro|piper|espeak|silent_test)")
    r.add_argument('--visual-revision',help='immutable verified visual-only source recipe; source/script target only')
    r.add_argument("--resume-prepared",help="reuse verified saved source pack without rediscovery; regenerate grounded script then continue")
    r.add_argument("--stop-after",choices=["script"],help="save source pack, grounded template script and unstarted production tasks; no model calls")
    r.add_argument("--writer", help="override writer (auto|template|ollama|llm)")
    b = sub.add_parser("rebuild", help="re-render a finished run and compare hashes")
    b.add_argument("run_dir")
    sub.add_parser("selftest", help="run unit tests")
    ix = sub.add_parser("index", help="write README.md index for a results folder")
    ix.add_argument("results_dir")
    doctor = sub.add_parser('doctor', help='check local readiness without downloading or loading models')
    doctor.add_argument('--hashes', action='store_true')
    doctor.add_argument('--config')
    integrity = sub.add_parser('verify-package', help='verify actual stored package bytes')
    integrity.add_argument('run_dir')
    repair = sub.add_parser('repair-citations',help='copy-on-repair a proven citation-only defect without altering media')
    repair.add_argument('run_dir')
    repair.add_argument('--out')
    recheck = sub.add_parser('check-delivery', help='recheck stored delivery against official current status')
    recheck.add_argument('run_dir')
    recheck.add_argument('--offline',action='store_true')
    export = sub.add_parser('export-package', help='atomically export a complete verified package')
    export.add_argument('run_dir')
    export.add_argument('--out')
    jobs = sub.add_parser('jobs', help='durable local production queue; no autostart')
    jobs.add_argument('--root')
    js = jobs.add_subparsers(dest='action', required=True)
    submit = js.add_parser('submit')
    submit.add_argument('--config')
    submit.add_argument('--opportunity')
    submit.add_argument('--key')
    submit.add_argument('--timeout', type=int, default=900)
    submit.add_argument('--resume-job',help='reuse this queue prepared job by pinned ID')
    submit.add_argument('--prepare-only',action='store_true')
    submit.add_argument('--writer',choices=['template'])
    for action in ('status', 'cancel', 'retry', 'artifact-preview', 'export'):
        parser = js.add_parser(action)
        parser.add_argument('job_id')
        if action=='retry':parser.add_argument('--key')
    workflow=js.add_parser('workflow',help='restore selected durable workflow without starting work')
    workflow.add_argument('job_id',nargs='?');workflow.add_argument('--remember',action='store_true')
    opening=js.add_parser('open-preview',help='verify preview; opens Windows player only with --launch')
    opening.add_argument('job_id');opening.add_argument('--launch',action='store_true')
    review=js.add_parser('review',help='record explicit package-bound editorial decision, never publication')
    review.add_argument('job_id');review.add_argument('--package-id',required=True)
    review.add_argument('--decision',choices=['approved','pending','changes_requested','rejected'],required=True)
    review.add_argument('--reviewer',required=True);review.add_argument('--reason',required=True)
    review.add_argument('--listened',action='store_true');review.add_argument('--visual-reviewed',action='store_true');review.add_argument('--revision')
    pp=js.add_parser('plan-publication',help='local draft/slot only; no dispatcher, network or sending')
    pp.add_argument('job_id');pp.add_argument('--package-id',required=True);pp.add_argument('--when');pp.add_argument('--timezone');pp.add_argument('--destination');pp.add_argument('--revision');pp.add_argument('--clear-time',action='store_true')
    js.add_parser('publication-plan').add_argument('job_id')
    history=js.add_parser('history',help='fast paginated queue metadata; no artifact integrity claim')
    history.add_argument('--limit',type=int,default=50);history.add_argument('--cursor')
    for action in ('list', 'work', 'recover'):
        js.add_parser(action)
    prod = sub.add_parser("produce", help="submit and produce one durable local job; no UI or publication")
    prod.add_argument("--config")
    prod.add_argument("--root")
    prod.add_argument("--opportunity")
    prod.add_argument("--key")
    prod.add_argument("--timeout", type=int, default=900)
    prod.add_argument("--resume-job",help="reuse a verified prepared job; inherit its pinned settings unless --config is supplied")
    prod.add_argument("--prepare-only",action="store_true")
    prod.add_argument("--writer",choices=["template"])
    batch=sub.add_parser('batch',help='sequential durable reuse of existing artifacts; never starts models')
    batch.add_argument('--root');bs=batch.add_subparsers(dest='action',required=True)
    bs.add_parser('list')
    bc=bs.add_parser('create');bc.add_argument('--jobs',nargs='+');bc.add_argument('--limit',type=int,default=3);bc.add_argument('--key')
    recovery=bs.add_parser('recover-paths');recovery.add_argument('batch_id');recovery.add_argument('--mode',choices=['continue','rollback'],default='continue')
    br=bs.add_parser('rebind-paths');br.add_argument('batch_id');br.add_argument('--previous-root',required=True)
    for action in ('status','pause','cancel','resume','work'):
        bp=bs.add_parser(action);bp.add_argument('batch_id',nargs='?')
        if action=='work':bp.add_argument('--max-items',type=int)
    release=sub.add_parser('release',help='local release check/list/preview/export; no inference')
    release.add_argument('--root');rs=release.add_subparsers(dest='action',required=True)
    rs.add_parser('check');rl=rs.add_parser('list');rl.add_argument('--limit',type=int,default=100);rl.add_argument('--cursor')
    for name in ('preview','export'):rs.add_parser(name).add_argument('job_id')
    rw=rs.add_parser('workflow');rw.add_argument('job_id',nargs='?');rw.add_argument('--remember',action='store_true')
    ro=rs.add_parser('open-preview');ro.add_argument('job_id');ro.add_argument('--launch',action='store_true')
    rr=rs.add_parser('review');rr.add_argument('job_id');rr.add_argument('--package-id',required=True)
    rr.add_argument('--decision',choices=['approved','pending','changes_requested','rejected'],required=True)
    rr.add_argument('--reviewer',required=True);rr.add_argument('--reason',required=True)
    rr.add_argument('--listened',action='store_true');rr.add_argument('--visual-reviewed',action='store_true');rr.add_argument('--revision')
    pp=rs.add_parser('plan-publication');pp.add_argument('job_id');pp.add_argument('--package-id',required=True);pp.add_argument('--when');pp.add_argument('--timezone');pp.add_argument('--destination');pp.add_argument('--revision');pp.add_argument('--clear-time',action='store_true')
    rs.add_parser('publication-plan').add_argument('job_id')
    relocate=sub.add_parser('relocate',help='copy existing verified CPU backend/artifacts without models or installs')
    relocate.add_argument('--root',required=True);relocate.add_argument('--out',required=True);relocate.add_argument('--jobs',nargs='+',required=True)
    motion=sub.add_parser('motion',help='registered CPU motion preparation; never starts GPU')
    ms=motion.add_subparsers(dest='action',required=True)
    ms.add_parser('list')
    mp=ms.add_parser('prepare');mp.add_argument('template_id');mp.add_argument('--reference');mp.add_argument('--start-frame',type=int,default=0);mp.add_argument('--repair-cache',action='store_true')
    mi=ms.add_parser('inspect');mi.add_argument('template_id');mi.add_argument('--repair-cache',action='store_true')
    mr=ms.add_parser('recover');mr.add_argument('--repair-cache',action='store_true')
    a = ap.parse_args(argv)
    if a.cmd=='release':
        from .release_candidate import run
        try:
            editorial={k:getattr(a,k) for k in ('package_id','decision','reviewer','reason','listened','visual_reviewed')} if a.action=='review' else None
            if editorial is not None:editorial['expected_revision']=a.revision
            value,code=run(a.action,getattr(a,'job_id',None),a.root,limit=getattr(a,'limit',100),cursor=getattr(a,'cursor',None),remember=getattr(a,'remember',False),launch=getattr(a,'launch',False),editorial=editorial,publication={k:getattr(a,k,None) for k in ('package_id','when','timezone','destination','revision','clear_time')} if a.action=='plan-publication' else None)
        except (PipelineError,OSError,ValueError,KeyError,TypeError,ImportError) as error:
            print(json.dumps({'version':__version__,'state':'blocked','detail':str(error),'error_type':type(error).__name__,'ui_connected':False,'inference_started':False,'downloads_attempted':False}));return 2
        print(json.dumps(value,indent=2));return code
    if a.cmd=='relocate':
        from .jobs import JobStore
        from .relocation import copy_backend
        try:value=copy_backend(JobStore(a.root),a.out,a.jobs)
        except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:
            print(json.dumps({'state':'blocked','detail':str(error),'originals_preserved':True,'new_generation':False}));return 2
        print(json.dumps(value,indent=2));return 0
    if a.cmd=='batch':
        if os.environ.get('SOCIAL_CACHE_ONLY')=='1':
            from .asr_cache import install_cache_only_guard
            install_cache_only_guard(os.environ['SOCIAL_MODEL_IMPORT_AUDIT_FILE'])
        if os.environ.get('SOCIAL_NETWORK_AUDIT_FILE'):
            from .network import install_audit
            install_audit(os.environ['SOCIAL_NETWORK_AUDIT_FILE'])
        from .jobs import JobStore
        from .artifact_batch import ArtifactBatch
        try:
            batch=ArtifactBatch(JobStore(a.root))
            if a.action=='create':value=batch.create(a.jobs,a.limit,a.key)
            elif a.action=='list':value=batch.list()
            elif a.action=='recover-paths':value=batch.recover_paths(a.batch_id,a.mode)
            elif a.action=='rebind-paths':value=batch.rebind_paths(a.batch_id,a.previous_root)
            elif a.action=='work':value=batch.work(a.batch_id,a.max_items)
            else:value=getattr(batch,a.action)(a.batch_id)
        except (PipelineError,OSError,ValueError,KeyError,TypeError) as error:
            print(json.dumps({'state':'blocked','detail':str(error),'new_generation':False,'worker_started':False}));return 2
        print(json.dumps(value,indent=2));return 0
    if a.cmd == 'repair-citations':
        from .citation_repair import repair_citations
        try:value=repair_citations(a.run_dir,a.out)
        except (PipelineError,OSError,ValueError,KeyError) as error:
            print(json.dumps({'repaired':False,'detail':str(error)}));return 2
        print(json.dumps(value,indent=2));return 0
    if a.cmd == 'check-delivery':
        from .recheck import main as recheck_main
        return recheck_main([a.run_dir]+(['--offline'] if a.offline else []))
    if a.cmd == 'export-package':
        from .export import export_package
        try:
            value=export_package(a.run_dir,a.out)
        except (PipelineError,OSError,ValueError) as error:
            print(json.dumps({'exported':False,'error_type':type(error).__name__,'detail':str(error)}))
            return 2
        print(json.dumps(value,indent=2));return 0
    if a.cmd == 'motion':
        from .motion_catalog import MotionCatalog
        try:
            catalog=MotionCatalog()
            if a.action=='list':value=catalog.list()
            elif a.action=='recover':value=catalog.recover(a.repair_cache)
            elif a.action=='inspect':value=catalog.inspect(a.template_id,a.repair_cache)
            else:value=catalog.prepare(a.template_id,a.reference,start_frame=a.start_frame,repair_cache=a.repair_cache)
        except (PipelineError,OSError,ValueError,TypeError) as error:
            print(json.dumps({'prepared':False,'error_type':type(error).__name__,'detail':str(error),'gpu_started':False}))
            return 2
        print(json.dumps(value,indent=2));return 0
    if a.cmd == 'produce':
        from .jobs import JobStore
        from .production import produce
        try:
            value=produce(JobStore(a.root),a.config or (None if a.resume_job else str(ROOT/"config.ai-local.json")),a.opportunity,a.key,a.timeout,on_submitted=lambda event: print(json.dumps(event),file=sys.stderr,flush=True),stop_after="script" if a.prepare_only else None,writer=a.writer,resume_job=a.resume_job)
        except (PipelineError,OSError,ValueError,TypeError) as error:
            print(json.dumps({'state':'failed','error_type':type(error).__name__,'detail':str(error)[:1000],'ui_connected':False}))
            return 2
        print(json.dumps(value,indent=2))
        return 0 if value['state'] in {'completed','prepared'} else (3 if value['state'] in {'queued','running'} else 2)
    if a.cmd == 'doctor':
        from .runtime import doctor,load_config
        try:value = doctor(cfg=load_config(a.config) if a.config else None,hashes=a.hashes)
        except (PipelineError,OSError,ValueError,TypeError) as error:
            print(json.dumps({'ready':False,'checks':[{'check':'configuration','pass':False,'detail':str(error)}]}));return 2
        print(json.dumps(value, indent=2))
        return 0 if value['ready'] else 2
    if a.cmd == 'verify-package':
        from .packages import verify_package
        value = verify_package(a.run_dir)
        value.update(integrity_only=True,current_status_confirmed=False)
        print(json.dumps(value, indent=2))
        return 0 if value['pass'] else 2
    if a.cmd == 'jobs':
        from .jobs import JobStore
        try:
            store = JobStore(a.root)
            if a.action == 'submit':
                value = store.submit(a.config, a.opportunity, a.key, a.timeout,stop_after="script" if a.prepare_only else None,writer=a.writer,resume_job=a.resume_job)
            elif a.action in {'status','artifact-preview'}:
                value = store.get(a.job_id)
            elif a.action == 'workflow':
                from .workflow import restore_workflow
                value=restore_workflow(store,a.job_id,a.remember)
            elif a.action == 'open-preview':
                from .workflow import preview_open
                value=preview_open(store,a.job_id,a.launch)
            elif a.action == 'review':
                from .workflow import record_editorial
                value=record_editorial(store,a.job_id,a.package_id,a.decision,a.reviewer,a.reason,a.listened,a.visual_reviewed,a.revision)
            elif a.action in {'plan-publication','publication-plan'}:
                from .publication_plan import prepare_plan,get_plan
                value=prepare_plan(store,a.job_id,a.package_id,a.when,a.timezone,a.destination,a.revision,a.clear_time) if a.action=='plan-publication' else get_plan(store,a.job_id)
            elif a.action == 'export':
                from .production import deliver_existing
                value=deliver_existing(store,a.job_id,online=False)
            elif a.action == 'retry':
                value=store.retry(a.job_id,a.key)
            elif a.action == 'cancel':
                value=store.cancel(a.job_id)
            elif a.action == 'history':
                value=store.history(a.limit,a.cursor)
            elif a.action == 'work':
                value = store.work_once()
            else:
                value = getattr(store, a.action)()
            from .backend_contract import describe
            if isinstance(value,list):value=[describe(store,j) for j in value]
            elif isinstance(value,dict) and 'id' in value and 'backend_contract' not in value:value=describe(store,value)
        except (PipelineError,OSError,ValueError,TypeError,KeyError,AttributeError) as e:
            from .backend_contract import error
            print(json.dumps(error(e,locals().get('store'),getattr(a,'job_id',None))))
            return 2
        print(json.dumps(value, indent=2))
        return 0 if not isinstance(value, dict) or value.get('state') not in {'failed', 'rejected', 'interrupted', 'review_required', 'open_failed', 'plan_review_required'} else 2

    if a.cmd == "selftest":
        suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), top_level_dir=str(ROOT))
        res = unittest.TextTestRunner(verbosity=2).run(suite)
        return 0 if res.wasSuccessful() else 1
    if a.cmd == "index":
        write_index(Path(a.results_dir))
        return 0
    if a.cmd == "rebuild":
        from .pipeline import rebuild
        res = rebuild(Path(a.run_dir))
        print(json.dumps(res, indent=2))
        return 0 if res["byte_identical"] else 3
    if os.environ.get("SOCIAL_MANAGED_WORKER") != "1":
        from .watchdog import managed_run
        return managed_run(a.out, a.timeout, a.cancel_file)
    from .runtime import load_config
    cfg = load_config(a.config)
    if a.voice:
        cfg["voice"]["backend"] = a.voice
    if a.writer:
        cfg["writer"] = a.writer
    if os.environ.get('SOCIAL_MODEL_OBSERVATION_FILE'):
        from .model_observation import install as observe_models
        observe_models(os.environ['SOCIAL_MODEL_OBSERVATION_FILE'])
    if os.environ.get('SOCIAL_CACHE_ONLY')=='1':
        from .asr_cache import install_cache_only_guard
        install_cache_only_guard(os.environ['SOCIAL_MODEL_IMPORT_AUDIT_FILE'])
    if os.environ.get('SOCIAL_NETWORK_AUDIT_FILE'):
        from .network import install_audit
        install_audit(os.environ['SOCIAL_NETWORK_AUDIT_FILE'])
    from .pipeline import run
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    try:
        d = run(cfg, out, Path(a.fixture) if a.fixture else None, a.opportunity, Path(a.history) if a.history else None, stop_after=a.stop_after,resume_prepared=Path(a.resume_prepared) if a.resume_prepared else None,visual_revision=read_json(Path(a.visual_revision)) if a.visual_revision else None)
    except Exception as e:
        from .common import write_json, utc_now
        write_json(out / ("failure_" + utc_now().strftime("%Y%m%dT%H%M%S%f") + ".json"),
                   {"accepted": False, "error_type": type(e).__name__, "detail": str(e)[:1000]})
        print(f"PIPELINE FAILED: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if a.stop_after:
        prepared=read_json(d/"prepared.json")
        print(json.dumps({"run_dir":str(d),**{k:v for k,v in prepared.items() if k!="files"}},indent=2))
        return 0
    res = read_json(d / "result.json")
    print(json.dumps({"run_dir": str(d), "accepted": res["accepted"], "video_sha256": res["video"]["sha256"],
                      "duration_s": res["verification"].get("duration_s"), "writer": res["writer"],
                      "failed_checks": [c["check"] for c in res["verification"]["checks"] if not c["pass"]]}, indent=2))
    return 0 if res["accepted"] else 1


def write_index(pub: Path):
    rows = []
    runs = pub / "runs"
    found = [(read_json(d / "result.json"), d) for d in (runs.iterdir() if runs.is_dir() else []) if (d / "result.json").exists()]
    for r, d in sorted(found, key=lambda x: x[0].get("finished_at", ""), reverse=True):
        if r.get("accepted") is True:
            rows.append(f"| [{d.name}](runs/{d.name}/REVIEW.md) | {r['verification'].get('duration_s')} s | {r['writer']} "
                        f"| `{r['video']['sha256'][:16]}` | [mp4](runs/{d.name}/reel.mp4) |")
    extra = "\nRetracted runs: see [RETRACTED.md](RETRACTED.md).\n" if (pub / "RETRACTED.md").exists() else ""
    (pub / "README.md").write_text(
        "# Social Reels — results\n\nAccepted Reels (newest first). `latest/` = full package of the newest one; "
        "full packages of every run are in that run's Actions artifact.\n" + extra + "\n"
        "| Run | Length | Writer | Video SHA-256 | Video |\n|---|---|---|---|---|\n" + "\n".join(rows) + "\n")


if __name__ == "__main__":
    sys.exit(main())

