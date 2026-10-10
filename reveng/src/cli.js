#!/usr/bin/env node
'use strict';
const fs = require('node:fs'), path = require('node:path');
const { run } = require('./pipeline');
const { Budget } = require('./budget');
const { Fetcher } = require('./fetcher');
const { AnthropicProvider } = require('./llm/anthropic');
const { OpenAIProvider } = require('./llm/openai');
const { markAgentReported } = require('./evidence');
const { readJson } = require('./util');
const { discoverMemoPrompts } = require('./prompts');
const { FAMILIES_REQUIRED, FAMILIES_EXTRA } = require('./schema');

function args(argv) { const a = { _: [] }; for (let i = 0; i < argv.length; i++) { const t = argv[i]; if (t.startsWith('--')) { const k = t.slice(2); const nx = argv[i + 1]; if (nx === undefined || nx.startsWith('--')) a[k] = true; else { a[k] = nx; i++; } } else a._.push(t); } return a; }
function loadCfg(p) { return p ? readJson(p) : {}; }
function makeProvider(cfg) {
  const l = cfg.llm || {}, budget = new Budget(cfg.budget || {});
  if (!l.provider) return null;
  if (l.provider === 'anthropic') return new AnthropicProvider({ model: l.model, budget, maxTokens: l.max_tokens, webSearchMaxUses: l.web_search_max_uses });
  if (l.provider === 'openai') return new OpenAIProvider({ model: l.model, budget });
  throw new Error('unknown llm.provider ' + l.provider);
}
const stamp = () => new Date().toISOString().replace(/[-:]/g, '').replace(/\..*/, '').replace('T', '_');
async function main() {
  const a = args(process.argv.slice(2)), cmd = a._[0], log = (m) => console.error('[reveng] ' + m);
  const cfg = loadCfg(a.config);
  const out = a.out || path.join(__dirname, '..', 'runs');
  if (cmd === 'run') {
    const runDir = a.resume ? a.resume : path.join(out, 'run_' + stamp());
    if (a.families) cfg.families = String(a.families).split(','); if (a['per-family']) cfg.per_family = +a['per-family'];
    const fetcher = new Fetcher({ cacheDir: path.join(runDir, 'cache'), userAgent: (cfg.http || {}).user_agent || undefined, allowHosts: (cfg.http || {}).allow_hosts || undefined });
    if (a['dry-run']) {
      fs.mkdirSync(runDir, { recursive: true }); const fams = cfg.families || [...FAMILIES_REQUIRED, ...FAMILIES_EXTRA];
      const prompts = fams.map(f => ({ family: f, phase1: discoverMemoPrompts({ family: f, n: cfg.per_family || 4, lens: 'dry-run', signals: [] }) }));
      fs.writeFileSync(path.join(runDir, 'dryrun_prompts.json'), JSON.stringify(prompts, null, 2)); console.log('dry-run prompts written to ' + runDir); return;
    }
    const provider = makeProvider(cfg);
    if (!provider) { console.error('config.llm.provider is required for `run` (anthropic|openai). For pre-researched candidates use `import`.'); process.exit(2); }
    const r = await run({ runDir, cfg, provider, fetcher, log });
    console.log(`verdict=${r.decision.verdict} leader=${r.decision.leader} runDir=${runDir}`); return;
  }
  if (cmd === 'smoke') {
    const provider = makeProvider(cfg); if (!provider) { console.error('config.llm.provider required'); process.exit(2); }
    const { smoke } = require('./smoke'); const dir = path.join(out, 'smoke_' + stamp()); fs.mkdirSync(dir, { recursive: true });
    const rep = await smoke({ provider, family: a.family || 'saas_or_micro_saas' }); rep.finished_at = new Date().toISOString();
    fs.writeFileSync(path.join(dir, 'smoke_result.json'), JSON.stringify(rep, null, 2));
    console.log(JSON.stringify({ ok: rep.ok, parsed_candidates: rep.parsed_candidates, excerpts_returned: rep.excerpts_returned, evidence: rep.evidence, usage: rep.usage, error: rep.error }, null, 2)); process.exit(rep.ok ? 0 : 4);
  }
  if (cmd === 'import') {
    const files = String(a.raw || '').split(',').filter(Boolean); if (!files.length) { console.error('usage: import --raw a.json,b.json'); process.exit(2); }
    const cands = files.flatMap(f => readJson(f)).map(markAgentReported);
    const runDir = path.join(out, 'import_' + stamp());
    const r = await run({ runDir, cfg, candidates: cands, provisional: true, log });
    console.log(`PROVISIONAL verdict=${r.decision.verdict} runDir=${runDir}`); return;
  }
  if (cmd === 'measure') {
    const { evaluateMeasured } = require('./measure'); if (!a.id || !a.file) { console.error('usage: measure --id CAND-ID --file entrant_evidence.json'); process.exit(2); }
    const r = evaluateMeasured(a.id, readJson(a.file)); console.log(JSON.stringify(r, null, 2)); process.exit(r.supportedAdvantageHypothesis ? 0 : 3);
  }
  if (cmd === 'doctor') {
    const p = (() => { try { return makeProvider(cfg); } catch (e) { return e; } })();
    const b = cfg.budget || {};
    console.log(JSON.stringify({ node: process.version, llm_provider: (cfg.llm || {}).provider || null, key_present: { ANTHROPIC_API_KEY: !!process.env.ANTHROPIC_API_KEY, OPENAI_API_KEY: !!process.env.OPENAI_API_KEY },
      spend_authorized: b.allow_spend === true, caps: { max_calls: b.max_calls ?? null, max_usd: b.max_usd ?? null, max_input_tokens: b.max_input_tokens ?? null, max_output_tokens: b.max_output_tokens ?? null }, provider_ok: !(p instanceof Error), provider_error: p instanceof Error ? p.message : null }, null, 2)); return;
  }
  if (cmd === 'selftest') { const { spawnSync } = require('node:child_process'); const r = spawnSync(process.execPath, ['--test', ...fs.readdirSync(path.join(__dirname, '..', 'test')).filter(f => f.endsWith('.test.js')).map(f => path.join(__dirname, '..', 'test', f))], { stdio: 'inherit' }); process.exit(r.status); }
  console.log('reveng <smoke|run|import|measure|doctor|selftest> [--config cfg.json] [--out dir] [--families a,b] [--per-family N] [--dry-run] [--resume runDir]');
}
main().catch(e => { console.error('ERROR:', e.message); process.exit(1); });
