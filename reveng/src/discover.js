'use strict';
const { discoverMemoPrompts, discoverJsonPrompts } = require('./prompts');
const { twoPhase, resolveEvidence } = require('./research');
const { validateCandidate } = require('./schema');
const CODES = { games: 'GAM', saas_or_micro_saas: 'SAS', ecommerce_or_dropshipping: 'ECO', services: 'SVC', marketplaces: 'MKT', digital_or_data_products: 'DAT', physical_products: 'PHY', media_or_content: 'MED', education_training: 'EDU', b2b_api_devtools: 'DEV' };
const LENSES = ['current unmet needs: recent complaints, workarounds, people paying for manual solutions', 'pricing gaps: where incumbents leave a clearly underserved price/feature tier', 'platform or policy changes in the last 12 months that opened or closed a gap', 'public data or free resources that lack a good paid, packaged product'];
const SIGNAL_PLAN = { games: [['itunes', 'puzzle game']], saas_or_micro_saas: [['hackernews', 'Ask HN looking for a tool'], ['github', 'self-hosted alternative']], b2b_api_devtools: [['npm', 'webhook'], ['stackexchange', 'api rate limit']],
  digital_or_data_products: [['hackernews', 'dataset api'], ['github', 'open data']], education_training: [['hackernews', 'learn course'], ['itunes', 'learn app']], media_or_content: [['hackernews', 'newsletter niche']], marketplaces: [['hackernews', 'marketplace niche']], services: [['hackernews', 'productized service']] };
class DiscoveryAborted extends Error { constructor(msg, diags) { super(msg); this.name = 'DiscoveryAborted'; this.diags = diags; } }
// Turn one model-produced candidate into an engine candidate: evidence resolved from provider-returned refs, edge source resolved from incumbent_ref.
function buildCandidate(raw, family, id, idx) {
  const { evidence, map, dropped } = resolveEvidence(raw.evidence, idx, `${id}-E`);
  const c = { ...raw, family, id, evidence, source: 'llm_discovery', unknowns: raw.unknowns || [], _dropped_refs: dropped };
  if (raw.entrant_edge && typeof raw.entrant_edge === 'object') { const e = { ...raw.entrant_edge }, src = idx.byId[String(e.incumbent_ref || '')]; e.incumbent_source_url = src ? src.url : ''; delete e.incumbent_ref; c.entrant_edge = e; }
  const de = {}; for (const [d, refs] of Object.entries(raw.dimension_evidence || {})) de[d] = (Array.isArray(refs) ? refs : []).map(r => map[String(r)]).filter(Boolean);
  c.dimension_evidence = de;
  return c;
}
async function discoverFamily({ provider, fetcher, collect, family, perFamily, signalsEnabled = true, bases, breaker = { fails: 0, max: 2 }, maxUses, maxAttempts = LENSES.length }) {
  const code = CODES[family] || family.slice(0, 3).toUpperCase(), found = [], dropped = [], log = [], diags = [], research = [];
  let signals = [];
  if (signalsEnabled && SIGNAL_PLAN[family] && fetcher) {
    const r = await collect(fetcher, SIGNAL_PLAN[family].map(([source, query]) => ({ source, query })), { bases });
    signals = r.signals; log.push({ signals: signals.length, signal_errors: r.errors });
  }
  let want = perFamily;
  for (let attempt = 0; attempt < Math.min(LENSES.length, maxAttempts) && found.length < perFamily; attempt++) {
    const need = Math.min(want, perFamily - found.length);
    const p1 = discoverMemoPrompts({ family, n: need, lens: LENSES[attempt], signals, avoid: found.map(c => c.name) });
    let r;
    try { r = await twoPhase({ provider, p1, buildP2: (memo, idx) => discoverJsonPrompts({ family, code, n: need, memo, idx }), maxUses, expect: 'array' }); }
    catch (e) { if (e.name === 'SpendNotAuthorized' || e.name === 'BudgetExceeded') throw e; r = { ok: false, error: e.message, diags: [{ error: e.message }] }; }
    if (!r.ok) {
      diags.push({ family, attempt, error: r.error, ...(r.diags && r.diags[0]) }); log.push({ attempt, error: r.error });
      if (r.r2 && r.r2.stop_reason === 'max_tokens') want = Math.max(1, Math.ceil(want / 2));
      breaker.fails++; if (breaker.fails >= breaker.max) throw new DiscoveryAborted(`discovery failed x${breaker.fails}: ${r.error}`, diags);
      continue;
    }
    breaker.fails = 0; research.push({ family, attempt, memo: r.memo, excerpts: r.idx.excerpts, results: r.idx.results });
    for (const raw of r.data) {
      if (found.length >= perFamily) break;
      const c = buildCandidate(raw, family, `${code}-${String(found.length + 1).padStart(2, '0')}`, r.idx), errs = validateCandidate(c);
      if (errs.length) dropped.push({ name: raw && raw.name, errors: errs.slice(0, 4) }); else found.push(c);
    }
    log.push({ attempt, lens: LENSES[attempt], got: found.length, excerpts: r.idx.excerpts.length, search_results: r.idx.results.length, usage: [r.r1 && r.r1.usage, r.r2 && r.r2.usage] });
  }
  return { family, candidates: found, dropped, research, log, diags };
}
module.exports = { discoverFamily, buildCandidate, CODES, LENSES, DiscoveryAborted };
