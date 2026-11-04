"""Owner-facing commands for the existing durable ConceptStore."""
import json
import sys
from pathlib import Path

from . import concept_choose as choose
from .common import PipelineError
from .concept_store import ConceptStore


def add_parser(sub):
    parser = sub.add_parser('concepts', help='save, review, choose and export concept trials offline')
    commands = parser.add_subparsers(dest='concept_command', required=True)
    for name in ('import', 'list', 'show', 'decide', 'edit', 'export', 'handoff'):
        cmd = commands.add_parser(name)
        cmd.add_argument('--store', type=Path, required=True, help='explicit ConceptStore directory')
        if name == 'import':
            cmd.add_argument('trial', type=Path)
        elif name != 'list':
            cmd.add_argument('job')
        if name in ('decide', 'edit'):
            cmd.add_argument('--revision', help='expected latest revision from show; stale writes are refused')
        if name == 'decide':
            action = cmd.add_mutually_exclusive_group(required=True)
            action.add_argument('--pick', choices=('C1', 'C2', 'C3'))
            action.add_argument('--reject-all', action='store_true')
            cmd.add_argument('--note', required=True)
        elif name == 'edit':
            cmd.add_argument('concept')
            cmd.add_argument('--field', required=True)
            cmd.add_argument('--value', required=True)
        elif name == 'export':
            cmd.add_argument('--md', type=Path, required=True)
        elif name == 'handoff':
            cmd.add_argument('--out', type=Path, required=True, help='directory for the immutable <id>.json')


def run(args):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        store = ConceptStore(args.store)
        command = args.concept_command
        if command == 'import':
            result = choose.import_trial(store, args.trial)
        elif command == 'list':
            for job in choose.list_jobs(store):
                title = str(job.get('source', job.get('import', {}).get('source', {})).get('title') or 'Источник без заголовка')
                title = title.replace('\r', '\\r').replace('\n', '\\n').replace('\t', '\\t')
                date = job['history'][-1]['created_at'] if job['history'] else 'import_incomplete'
                latest = job.get('latest_decision')
                decision = (latest['action'] + ':' + str(latest.get('selected') or 'all')) if latest else 'none'
                print('\t'.join((job['job_id'], date, title, job['state'],
                                  str(len(job.get('proposal', {}).get('concepts', []))), decision)))
            return 0
        elif command == 'show':
            result = choose.show(store, args.job)
        elif command in ('decide', 'edit'):
            revision = args.revision if args.revision is not None else choose.show(store, args.job)['revision']
            if command == 'decide':
                result = choose.decide(store, args.job, revision, pick=args.pick, reject_all=args.reject_all, note=args.note)
            else:
                result = choose.edit(store, args.job, args.concept, args.field, args.value, revision)
        elif command == 'export':
            result = choose.export_markdown(store, args.job, args.md)
        else:
            result = choose.handoff(store, args.job, args.out)
    except (PipelineError, OSError, ValueError, UnicodeError) as error:
        print('CONCEPTS FAILED: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0
