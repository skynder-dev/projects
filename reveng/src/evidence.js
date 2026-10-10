'use strict';
// Evidence is resolved from provider-returned references in src/research.js (verified = provider citation excerpt; search_confirmed = search-result URL only).
// This module keeps the helpers for imported (unchecked) evidence and for isolating untrusted text with the frozen G280 contract.
const { load } = require('../vendor/load');
const iso = load('untrusted_source_isolation');
function markAgentReported(c) {
  return { ...c, evidence: (c.evidence || []).map((x, i) => ({ id: x.id || `${c.id}-E${i + 1}`, ...x, verify: { status: 'agent_reported', note: 'imported; not checked by engine' } })) };
}
function isolatedBlock(url, text) { const p = iso.build({ sourceText: text, url }, {}); return { url, flagged: p.instructionLikeContentDetected, signals: p.instructionSignals, text: p.content.sourceText }; }
module.exports = { markAgentReported, isolatedBlock };
