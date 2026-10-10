'use strict';
// One cheap, bounded live call (1 model call, <=3 searches, 2 candidates). Run BEFORE any full scan so provider/format problems surface in minutes.
const { discoverFamily } = require('./discover');
const { verifyCandidate } = require('./evidence');
async function smoke({ provider, family = 'saas_or_micro_saas', n = 2, maxUses = 3 }) {
  const rep = { ok: false, family, requested_candidates: n, max_searches: maxUses };
  let r = null;
  try { r = await discoverFamily({ provider, fetcher: null, collect: null, family, perFamily: n, signalsEnabled: false, breaker: { fails: 0, max: 1 }, maxUses, maxAttempts: 1 }); }
  catch (e) { rep.error = e.message; rep.diags = e.diags || []; rep.usage = provider.budget.used; return rep; }
  const ver = r.candidates.map(c => verifyCandidate(c, r.citations, r.searchResults)), ev = ver.flatMap(c => c.evidence), cnt = (st) => ev.filter(e => e.verify.status === st).length;
  Object.assign(rep, { parsed_candidates: r.candidates.length, schema_dropped: r.dropped, citations: r.citations.length, search_results: r.searchResults.length,
    evidence: { total: ev.length, verified: cnt('verified'), search_confirmed: cnt('search_confirmed'), unverified: cnt('unverified') }, usage: provider.budget.used,
    diags: r.diags, sample: ver.slice(0, 2).map(c => ({ id: c.id, name: c.name, evidence: c.evidence.map(e => ({ url: e.url, kind: e.kind, status: e.verify.status, quote: e.quote })) })) });
  rep.ok = r.candidates.length >= 1;
  return rep;
}
module.exports = { smoke };
