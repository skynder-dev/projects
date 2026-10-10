'use strict';
const fs = require('node:fs'), path = require('node:path');
const { writeJson, readJson, sha256File, nowIso } = require('./util');
const { runGates } = require('./gates');
const { scoreCandidate, rank, GLOBAL_PROFILE, SCORING_VERSION } = require('./scoring');
const { decide } = require('./decide');
const { verifyCandidate } = require('./evidence');
const { discoverFamily, DiscoveryAborted } = require('./discover');
const { deepScreen } = require('./deep');
const { collect } = require('./sources');
const { buildSnapshot, markdown } = require('./report');
const { FAMILIES_REQUIRED, FAMILIES_EXTRA } = require('./schema');

const EVIDENCE_ONLY = new Set(['evidence_depth']);
function evaluateAll(candidates, cfg, provisional) {
  const gateById = {}, scored = [];
  for (const c of candidates) {
    gateById[c.id] = runGates(c, { ...(cfg.gates || {}), provisional });
    let s; try { s = scoreCandidate(c, GLOBAL_PROFILE); } catch (e) { s = null; }
    if (s) scored.push(s);
  }
  return { gateById, scored };
}
// Deep pool: survivors plus candidates whose ONLY failure is evidence depth (deep screen can repair that), best pre-scores first, equal depth for all.
function deepPool(candidates, gateById, scored, topK) {
  const sc = Object.fromEntries(scored.map(r => [r.id, r]));
  const pool = candidates.filter(c => { const g = gateById[c.id]; return g.passed || (g.failed.length > 0 && g.failed.every(f => EVIDENCE_ONLY.has(f))); });
  return pool.sort((a, b) => ((sc[b.id] || {}).adjusted || 0) - ((sc[a.id] || {}).adjusted || 0) || (a.id < b.id ? -1 : 1)).slice(0, topK);
}
const evidenceClasses = (provisional, usage) => ({
  'source/static verified': 'engine code + frozen G280 vendor hashes checked at load',
  'internal tests verified': 'see test results in checkpoint (node --test)',
  'runtime verified': provisional ? 'NOT for market data in this run' : 'evidence = quotes matched against the provider web-search citation text (engine opened no third-party pages)',
  'live-provider verified': usage && usage.calls ? `provider calls this run: ${usage.calls}` : 'NOT RUN (no provider calls in this run)',
  'market validated': 'NO — research evidence only; no customer/commercial test performed',
  'commercial result observed': 'NO',
});

async function run({ runDir, cfg, provider = null, fetcher = null, candidates = null, provisional = false, log = () => {}, force = false }) {
  fs.mkdirSync(runDir, { recursive: true });
  const runId = path.basename(runDir), P = (f) => path.join(runDir, f), has = (f) => !force && fs.existsSync(P(f));
  const chk = has('checkpoint.json') ? readJson(P('checkpoint.json')) : { run_id: runId, stages_done: [], assumptions: [], blockers: [] };
  const done = (s) => { if (!chk.stages_done.includes(s)) chk.stages_done.push(s); chk.updated_at = nowIso(); writeJson(P('checkpoint.json'), chk); };
  chk.objective = 'reveng_v6_independent broad scan -> gates -> score -> deep screen -> decision'; chk.scoring_version = SCORING_VERSION; chk.provisional = provisional;
  const families = (cfg.families && cfg.families.length ? cfg.families : [...FAMILIES_REQUIRED, ...FAMILIES_EXTRA]);

  // 1 discover
  let raw;
  if (candidates) { raw = candidates; writeJson(P('01_raw.json'), raw); done('import'); }
  else if (has('01_raw.json')) raw = readJson(P('01_raw.json'));
  else {
    if (!provider) throw new Error('discover stage needs an LLM provider (see config.llm). Use `reveng import` for pre-researched candidates.');
    raw = []; const cites = {}, srs = {}, dlog = [], diags = [], breaker = { fails: 0, max: (cfg.discovery || {}).max_consecutive_failures || 2 };
    try {
      for (const family of families) {
        log(`discover ${family}`);
        const r = await discoverFamily({ provider, fetcher, collect, family, perFamily: cfg.per_family || 4, signalsEnabled: (cfg.sources || {}).enabled !== false, bases: (cfg.sources || {}).bases, breaker, maxUses: (cfg.llm || {}).web_search_max_uses });
        raw.push(...r.candidates); cites[family] = r.citations; srs[family] = r.searchResults; dlog.push({ family, got: r.candidates.length, dropped: r.dropped, log: r.log }); diags.push(...r.diags);
        writeJson(P('01_raw.partial.json'), { raw, dlog }); writeJson(P('01_diagnostics.json'), diags);
      }
    } catch (e) {
      if (e instanceof DiscoveryAborted) { diags.push(...(e.diags || [])); writeJson(P('01_diagnostics.json'), diags); chk.blockers.push('discovery_aborted:' + e.message); chk.updated_at = nowIso(); writeJson(P('checkpoint.json'), chk); }
      throw e;
    }
    writeJson(P('01_raw.json'), raw); writeJson(P('01_discovery_log.json'), { dlog, citations: cites, searchResults: srs }); done('discover');
  }
  // 2 verify (engine fetches every cited URL)
  let ver;
  if (has('02_verified.json')) ver = readJson(P('02_verified.json'));
  else if (provisional) { ver = raw; writeJson(P('02_verified.json'), ver); }
  else {
    const dl = has('01_discovery_log.json') ? readJson(P('01_discovery_log.json')) : { citations: {}, searchResults: {} };
    ver = raw.map(c => verifyCandidate(c, dl.citations[c.family] || [], dl.searchResults[c.family] || []));
    writeJson(P('02_verified.json'), ver); done('verify');
  }
  // 3 gate + score
  let { gateById, scored } = evaluateAll(ver, cfg, provisional);
  writeJson(P('03_gates.json'), gateById); writeJson(P('04_scored.json'), scored); done('gate_score');
  // 4 deep screen (equal depth)
  let cand = ver;
  const dcfg = cfg.deep || {};
  if (has('05_deep.json')) { cand = readJson(P('05_deep.json')); ({ gateById, scored } = evaluateAll(cand, cfg, provisional)); writeJson(P('03_gates.json'), gateById); writeJson(P('04_scored.json'), scored); }
  else if (provider && !provisional && dcfg.enabled !== false) {
    const pool = deepPool(ver, gateById, scored, dcfg.top_k || 8).map(c => c.id);
    log(`deep screen pool: ${pool.join(',')}`);
    const out = [];
    for (const c of ver) {
      if (!pool.includes(c.id)) { out.push(c); continue; }
      try { out.push(await deepScreen({ provider, candidate: c, minVerified: dcfg.min_verified || 3 })); }
      catch (e) { log(`deep FAILED ${c.id}: ${e.message}`); chk.blockers.push(`deep_failed:${c.id}:${e.message}`); out.push(c); }
    }
    cand = out; writeJson(P('05_deep.json'), cand); done('deep');
    ({ gateById, scored } = evaluateAll(cand, cfg, provisional)); writeJson(P('03_gates.json'), gateById); writeJson(P('04_scored.json'), scored);
  }
  // 5 decide + report
  const decision = decide({ candidates: cand, scored, gateById, cfg: cfg.decide, provisional });
  writeJson(P('06_decision.json'), decision); done('decide');
  const usage = provider ? provider.budget.used : null;
  const md = markdown({ runId, decision, candidates: cand, scored, gateById, provisional, stats: usage, evidenceClasses: evidenceClasses(provisional, usage) });
  fs.writeFileSync(P('REPORT.md'), md);
  const snapshots = [];
  const sc = Object.fromEntries(scored.map(r => [r.id, r]));
  for (const r of decision.ranking.slice(0, 3)) {
    const s = buildSnapshot(cand.find(c => c.id === r.id), sc[r.id], runId);
    writeJson(P(`snapshot_${r.id}.json`), s); snapshots.push(`snapshot_${r.id}.json`);
  }
  chk.verdict = decision.verdict; chk.leader = decision.leader; chk.unmet = decision.unmet_conditions; chk.usage = usage;
  chk.next_exact_action = decision.verdict === 'no_winner' ? ('Resolve hard blockers: ' + decision.hard_blockers.join(' | ')) : 'Phase E: build smallest internal prototype for leader and measure entrant edge with G280 entrant_advantage.evaluate';
  done('report');
  const files = fs.readdirSync(runDir).filter(f => !f.endsWith('.tmp') && f !== 'MANIFEST.json').sort();
  writeJson(P('MANIFEST.json'), Object.fromEntries(files.map(f => [f, sha256File(P(f))])));
  return { runId, decision, snapshots, candidates: cand, scored, gateById };
}
module.exports = { run, evaluateAll, deepPool };
