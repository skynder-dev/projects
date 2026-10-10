'use strict';
// Evidence verification WITHOUT fetching third-party pages. The basis is the citation text returned by the provider's own web-search tool:
//   verified          = quote found inside a provider citation (cited_text) whose URL matches the evidence URL
//   search_confirmed  = URL was returned by the provider's search but no citation text contains the quote (weight 0.5)
//   unverified        = neither; carries zero weight
//   agent_reported    = imported from outside, never checked by this engine (zero weight)
const { quoteInText } = require('./util');
const { load } = require('../vendor/load');
const iso = load('untrusted_source_isolation');
const normUrl = (u) => { try { const x = new URL(u); return (x.hostname.replace(/^www\./, '') + x.pathname.replace(/\/+$/, '')).toLowerCase(); } catch (_) { return String(u).toLowerCase(); } };
function verifyAgainstCitations(item, citations = [], searchResults = []) {
  const out = { ...item, verify: { method: 'provider_search_citation', checked_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z') } };
  const nu = normUrl(item.url), mine = citations.filter(c => normUrl(c.url) === nu);
  const hit = item.quote && mine.find(c => quoteInText(item.quote, c.cited_text, 0.8) || quoteInText(c.cited_text, item.quote, 0.8));
  if (hit) {
    out.verify.status = 'verified'; out.verify.cited_text = hit.cited_text.slice(0, 300);
    const sig = iso.instructionSignals(hit.cited_text); if (sig.length) out.verify.instruction_like_content = sig;
  } else if (searchResults.some(r => normUrl(r.url) === nu) || mine.length) { out.verify.status = 'search_confirmed'; out.verify.note = 'URL returned by provider search; quote not found in any cited text'; }
  else { out.verify.status = 'unverified'; out.verify.note = 'URL not among provider search results/citations'; }
  return out;
}
function verifyCandidate(c, citations, searchResults) {
  return { ...c, evidence: (c.evidence || []).map((x, i) => verifyAgainstCitations({ ...x, id: x.id || `${c.id}-E${i + 1}` }, citations, searchResults)) };
}
function markAgentReported(c) {
  return { ...c, evidence: (c.evidence || []).map((x, i) => ({ id: x.id || `${c.id}-E${i + 1}`, ...x, verify: { status: 'agent_reported', note: 'imported; not checked by engine' } })) };
}
function isolatedBlock(url, text) { const p = iso.build({ sourceText: text, url }, {}); return { url, flagged: p.instructionLikeContentDetected, signals: p.instructionSignals, text: p.content.sourceText }; }
module.exports = { verifyAgainstCitations, verifyCandidate, markAgentReported, isolatedBlock, normUrl };
