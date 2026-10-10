'use strict';
// Robust JSON extraction. Tries: whole text, every ``` fence, then EVERY '[' / '{' start position (model narration often contains
// brackets like "[1]" before the real JSON). Returns the largest valid parse of the expected kind.
function balancedFrom(t, s) {
  const o = t[s], c = o === '[' ? ']' : '}'; let depth = 0, inStr = false, esc = false;
  for (let i = s; i < t.length; i++) {
    const ch = t[i];
    if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === '"') inStr = false; continue; }
    if (ch === '"') inStr = true; else if (ch === o) depth++; else if (ch === c && --depth === 0) return t.slice(s, i + 1);
  }
  return null;
}
function extractJson(text, expect = null) {
  const t = String(text || '').trim(), ok = (v) => v !== null && typeof v === 'object' && (!expect || (expect === 'array') === Array.isArray(v));
  const tries = [t]; for (const m of t.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi)) tries.push(m[1]);
  for (const x of tries) { try { const v = JSON.parse(x); if (ok(v)) return v; } catch (_) {} }
  let best = null, bestLen = -1;
  for (let s = 0; s < t.length; s++) {
    if (t[s] !== '[' && t[s] !== '{') continue;
    if (expect && ((expect === 'array') !== (t[s] === '['))) continue;
    const seg = balancedFrom(t, s); if (!seg || seg.length <= bestLen) continue;
    try { const v = JSON.parse(seg); if (ok(v)) { best = v; bestLen = seg.length; } } catch (_) {}
  }
  if (best !== null) return best;
  throw new Error('no_parseable_json_in_model_output');
}
module.exports = { extractJson };
