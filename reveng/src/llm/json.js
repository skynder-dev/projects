'use strict';
// Robust JSON extraction from model text (handles ```json fences and leading/trailing prose).
function extractJson(text) {
  const t = String(text || '').trim();
  try { return JSON.parse(t); } catch (_) {}
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/i); if (fence) { try { return JSON.parse(fence[1]); } catch (_) {} }
  for (const [o, c] of [['[', ']'], ['{', '}']]) {
    const s = t.indexOf(o); if (s < 0) continue;
    let depth = 0, inStr = false, esc = false;
    for (let i = s; i < t.length; i++) {
      const ch = t[i];
      if (inStr) { if (esc) esc = false; else if (ch === '\\') esc = true; else if (ch === '"') inStr = false; continue; }
      if (ch === '"') inStr = true; else if (ch === o) depth++; else if (ch === c && --depth === 0) { try { return JSON.parse(t.slice(s, i + 1)); } catch (_) { break; } }
    }
  }
  throw new Error('no_parseable_json_in_model_output');
}
module.exports = { extractJson };
