'use strict';
// Evidence verification: the ENGINE fetches each cited URL itself and checks the quote is really on the page.
// LLM-claimed evidence is never trusted. Statuses: verified | search_confirmed | quote_not_found | fetch_failed | agent_reported
const { htmlToText, quoteInText, sha256 } = require('./util');
const { load } = require('../vendor/load');
const iso = load('untrusted_source_isolation');

async function verifyEvidenceItem(item, fetcher, searchUrls = new Set()) {
  const out = { ...item, verify: { checked_at: new Date().toISOString().replace(/\.\d+Z$/, 'Z') } };
  const f = await fetcher.get(item.url);
  out.verify.http_status = f.status; out.verify.error = f.error || null;
  if (f.ok) {
    const text = /html|xml/i.test(f.contentType || '') || /^\s*</.test(f.body.subarray(0, 64).toString()) ? htmlToText(f.body.toString('utf8')) : f.body.toString('utf8');
    out.verify.content_sha256 = f.sha256; out.verify.text_chars = text.length;
    const sig = iso.instructionSignals(text.slice(0, 20000));
    if (sig.length) out.verify.instruction_like_content = sig;
    if (item.quote && quoteInText(item.quote, text)) out.verify.status = 'verified';
    else { out.verify.status = 'quote_not_found'; out.verify.note = item.quote ? 'quote absent from fetched page' : 'no quote supplied'; }
    out._text = text; // kept in-memory only (stripped before persisting)
  } else if (searchUrls.has(item.url)) { out.verify.status = 'search_confirmed'; out.verify.note = 'URL returned by provider web search; page not fetchable by engine'; }
  else out.verify.status = 'fetch_failed';
  return out;
}
async function verifyCandidate(c, fetcher, searchUrls = new Set()) {
  const ev = [];
  for (let i = 0; i < (c.evidence || []).length; i++) {
    const it = { ...c.evidence[i] }; if (!it.id) it.id = `${c.id}-E${i + 1}`;
    const v = await verifyEvidenceItem(it, fetcher, searchUrls); delete v._text; ev.push(v);
  }
  return { ...c, evidence: ev };
}
// Imported (already-researched, not engine-fetched) evidence is explicitly labelled and carries zero weight.
function markAgentReported(c) {
  return { ...c, evidence: (c.evidence || []).map((x, i) => ({ id: x.id || `${c.id}-E${i + 1}`, ...x, verify: { status: 'agent_reported', note: 'imported; not fetched by engine' } })) };
}
// Wrap page text for LLM use via the frozen G280 untrusted-source isolation contract.
function isolatedBlock(url, text) {
  const p = iso.build({ sourceText: text, url }, {});
  return { url, flagged: p.instructionLikeContentDetected, signals: p.instructionSignals, text: p.content.sourceText };
}
module.exports = { verifyCandidate, verifyEvidenceItem, markAgentReported, isolatedBlock };
