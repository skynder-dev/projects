'use strict';
// Anthropic Messages API provider with the server-side web search tool. The search itself is performed by Anthropic under its own terms;
// the engine never fetches third-party pages. Citations (url + cited_text) returned by the API are the evidence basis.
const { Budget } = require('../budget');
class AnthropicProvider {
  constructor({ apiKey = process.env.ANTHROPIC_API_KEY, model, baseUrl = 'https://api.anthropic.com', budget, maxTokens = 16000, webSearchMaxUses = 6, version = '2023-06-01', timeoutMs = 600000 } = {}) {
    if (!model) throw new Error('anthropic provider needs config.llm.model');
    Object.assign(this, { apiKey, model, baseUrl, budget: budget || new Budget(), maxTokens, webSearchMaxUses, version, timeoutMs, name: 'anthropic' });
  }
  buildRequest({ system, user, webSearch, maxUses }) {
    const body = { model: this.model, max_tokens: this.maxTokens, system, messages: [{ role: 'user', content: user }] };
    if (webSearch) body.tools = [{ type: 'web_search_20250305', name: 'web_search', max_uses: maxUses || this.webSearchMaxUses }];
    return body;
  }
  parseResponse(j) {
    const blocks = j.content || [], texts = blocks.filter(b => b.type === 'text');
    const text = texts.map(b => b.text).join('\n');
    let lastTool = -1; blocks.forEach((b, i) => { if (b.type === 'web_search_tool_result' || b.type === 'server_tool_use') lastTool = i; });
    const finalText = blocks.slice(lastTool + 1).filter(b => b.type === 'text').map(b => b.text).join('\n');
    const citations = [], searchResults = [], seen = new Set();
    for (const b of blocks) {
      if (b.type === 'web_search_tool_result' && Array.isArray(b.content)) for (const r of b.content) if (r && r.url) searchResults.push({ url: r.url, title: r.title || '', page_age: r.page_age || null });
      if (b.type === 'text' && Array.isArray(b.citations)) for (const c of b.citations) if (c && c.url) { const k = c.url + '|' + c.cited_text; if (!seen.has(k)) { seen.add(k); citations.push({ url: c.url, title: c.title || '', cited_text: c.cited_text || '' }); } }
    }
    const u = j.usage || {};
    return { text, finalText, citations, searchResults, searchUrls: new Set([...searchResults.map(r => r.url), ...citations.map(c => c.url)]),
      usage: { input_tokens: u.input_tokens || 0, output_tokens: u.output_tokens || 0, search_requests: (u.server_tool_use || {}).web_search_requests || 0 }, stop_reason: j.stop_reason || null,
      diag: { stop_reason: j.stop_reason || null, block_types: blocks.map(b => b.type), text_chars: text.length, text_head: text.slice(0, 1500), text_tail: text.slice(-1500) } };
  }
  async complete(req) {
    this.budget.authorize();
    if (!this.apiKey) throw new Error('ANTHROPIC_API_KEY not set');
    const ac = new AbortController(), timer = setTimeout(() => ac.abort(), this.timeoutMs);
    let r, raw;
    try { r = await fetch(this.baseUrl + '/v1/messages', { method: 'POST', signal: ac.signal, headers: { 'content-type': 'application/json', 'x-api-key': this.apiKey, 'anthropic-version': this.version }, body: JSON.stringify(this.buildRequest(req)) }); raw = await r.text(); }
    finally { clearTimeout(timer); }
    let j; try { j = JSON.parse(raw); } catch (_) { throw new Error(`anthropic_non_json_response_${r.status}:${raw.slice(0, 200)}`); }
    if (!r.ok) throw new Error(`anthropic_http_${r.status}:${(j.error && j.error.message) || raw.slice(0, 200)}`);
    const out = this.parseResponse(j); this.budget.record(out.usage); return out;
  }
}
module.exports = { AnthropicProvider };
