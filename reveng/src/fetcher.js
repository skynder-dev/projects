'use strict';
const fs = require('node:fs'), path = require('node:path');
const { sha256, sleep } = require('./util');
class Fetcher {
  constructor({ cacheDir = null, minIntervalMs = 1000, timeoutMs = 20000, ttlMs = 86400000, maxBytes = 3_000_000,
                userAgent = 'RevEng-research/0.1 (public-data research)' } = {}) {
    Object.assign(this, { cacheDir, minIntervalMs, timeoutMs, ttlMs, maxBytes, userAgent }); this.last = new Map(); this.requests = 0;
    if (cacheDir) fs.mkdirSync(cacheDir, { recursive: true });
  }
  _cp(url) { return this.cacheDir ? path.join(this.cacheDir, sha256(url).slice(0, 40)) : null; }
  async get(url, { headers = {}, useCache = true } = {}) {
    if (!/^https?:\/\//i.test(url)) return { url, status: null, ok: false, body: Buffer.alloc(0), error: 'non_http_url', fetchedAt: Date.now() };
    const cp = this._cp(url);
    if (useCache && cp && fs.existsSync(cp + '.json')) {
      const meta = JSON.parse(fs.readFileSync(cp + '.json', 'utf8'));
      if (Date.now() - meta.fetchedAt < this.ttlMs) {
        const body = fs.readFileSync(cp + '.body');
        return { url, status: meta.status, ok: meta.status >= 200 && meta.status < 300, body, error: meta.error, fetchedAt: meta.fetchedAt, fromCache: true, sha256: sha256(body), contentType: meta.contentType };
      }
    }
    const host = new URL(url).host, wait = this.minIntervalMs - (Date.now() - (this.last.get(host) || 0));
    if (wait > 0) await sleep(wait);
    let status = null, body = Buffer.alloc(0), error = null, contentType = '';
    const ac = new AbortController(), timer = setTimeout(() => ac.abort(), this.timeoutMs);
    try {
      this.requests++;
      const r = await fetch(url, { headers: { 'User-Agent': this.userAgent, Accept: '*/*', ...headers }, signal: ac.signal, redirect: 'follow' });
      status = r.status; contentType = r.headers.get('content-type') || '';
      body = Buffer.from(await r.arrayBuffer()).subarray(0, this.maxBytes);
      if (!r.ok) error = 'http_' + r.status;
    } catch (e) { error = `${e.name}: ${e.message}`.slice(0, 200); } finally { clearTimeout(timer); }
    this.last.set(host, Date.now());
    const out = { url, status, ok: status !== null && status >= 200 && status < 300, body, error, fetchedAt: Date.now(), fromCache: false, sha256: body.length ? sha256(body) : null, contentType };
    if (cp && status !== null) { fs.writeFileSync(cp + '.body', body); fs.writeFileSync(cp + '.json', JSON.stringify({ status, error, fetchedAt: out.fetchedAt, contentType })); }
    return out;
  }
}
module.exports = { Fetcher };
