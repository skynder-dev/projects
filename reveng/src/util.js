'use strict';
const fs = require('node:fs'), path = require('node:path'), crypto = require('node:crypto');
const sha256 = (b) => crypto.createHash('sha256').update(b).digest('hex');
const sha256File = (p) => sha256(fs.readFileSync(p));
const nowIso = () => new Date().toISOString().replace(/\.\d+Z$/, 'Z');
function stable(v) { if (Array.isArray(v)) return v.map(stable); if (v && typeof v === 'object') return Object.fromEntries(Object.keys(v).sort().map(k => [k, stable(v[k])])); return v; }
function writeJson(p, obj) { fs.mkdirSync(path.dirname(path.resolve(p)), { recursive: true }); const t = p + '.tmp'; fs.writeFileSync(t, JSON.stringify(stable(obj), null, 2)); fs.renameSync(t, p); }
const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
function htmlToText(raw) {
  return String(raw).replace(/<(script|style|noscript|svg|head)[\s\S]*?<\/\1>/gi, ' ').replace(/<!--[\s\S]*?-->/g, ' ').replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#0*39;|&apos;/g, "'")
    .replace(/&#x?[0-9a-f]+;/gi, ' ').replace(/\s+/g, ' ').trim();
}
const norm = (s) => String(s).toLowerCase().replace(/[‘’“”]/g, "'").replace(/[^a-z0-9$%.' ]+/g, ' ').replace(/\s+/g, ' ').trim();
function quoteInText(quote, text, ratio = 0.9) {
  const q = norm(quote), t = norm(text);
  if (q.length < 12) return false;
  if (t.includes(q)) return true;
  const w = q.split(' '); if (w.length < 6) return false;
  const grams = []; for (let i = 0; i + 4 <= w.length; i++) grams.push(w.slice(i, i + 4).join(' '));
  return grams.filter(g => t.includes(g)).length / grams.length >= ratio;
}
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
module.exports = { sha256, sha256File, nowIso, stable, writeJson, readJson, htmlToText, norm, quoteInText, sleep };
