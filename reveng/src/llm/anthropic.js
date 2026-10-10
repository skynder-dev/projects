'use strict';
// Anthropic Messages API provider with server-side web search tool. Build/parse logic is unit-tested against a local mock;
// a LIVE call has NOT been exercised from the build environment (no key / egress closed).
const { Budget } = require('../budget');
class AnthropicProvider {
  constructor({ apiKey = process.env.ANTHROPIC_API_KEY, model, baseUrl = 'https://api.anthropic.com', budget, maxTokens = 8000, webSearchMaxUses = 6, version = '2023-06-01' } = {}) {
    if (!model) throw new Error('anthropic provider needs config.llm.model');
    Object.assign(this, { apiKey, model, baseUrl, budget: budget || new Budget(), maxTokens, webSearchMaxUses, version, name: 'anthropic' });
  }
  buildRequest({ system, user, webSearch }) {
    const body = { model: this.model, max_tokens: this.maxTokens, system, messages: [{ role: 'user', content: user }] };
    if (webSearch) body.tools = [{ type: 'web_search_20250305', name: 'web_search', max_uses: this.webSearchMaxUses }];
    return body;
  }
  parseResponse(j) {
    const text = (j.content || []).filter(b => b.type === 'text').map(b => b.text).join('\n');
    const searchUrls = new Set();
    for (const b of j.content || []) {
      if (b.type === 'web_search_tool_result' && Array.isArray(b.content)) for (const r of b.content) if (r && r.url) searchUrls.add(r.url);
      if (b.type === 'text' && Array.isArray(b.citations)) for (const c of b.citations) if (c && c.url) searchUrls.add(c.url);
    }
    const u = j.usage || {};
    return { text, searchUrls, usage: { input_tokens: u.input_tokens || 0, output_tokens: u.output_tokens || 0, search_requests: (u.server_tool_use || {}).web_search_requests || 0 }, stop_reason: j.stop_reason };
  }
  async complete(req) {
    this.budget.authorize();
    if (!this.apiKey) throw new Error('ANTHROPIC_API_KEY not set');
    const r = await fetch(this.baseUrl + '/v1/messages', { method: 'POST', headers: { 'content-type': 'application/json', 'x-api-key': this.apiKey, 'anthropic-version': this.version }, body: JSON.stringify(this.buildRequest(req)) });
    const raw = await r.text(); let j; try { j = JSON.parse(raw); } catch (_) { throw new Error(`anthropic_non_json_response_${r.status}`); }
    if (!r.ok) throw new Error(`anthropic_http_${r.status}:${(j.error && j.error.message) || raw.slice(0, 200)}`);
    const out = this.parseResponse(j); this.budget.record(out.usage); return out;
  }
}
module.exports = { AnthropicProvider };
