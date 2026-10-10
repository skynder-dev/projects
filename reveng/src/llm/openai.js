'use strict';
// OpenAI Responses API provider (web_search tool). Best-effort adapter; NOT exercised live; Anthropic is the primary path.
const { Budget } = require('../budget');
class OpenAIProvider {
  constructor({ apiKey = process.env.OPENAI_API_KEY, model, baseUrl = 'https://api.openai.com', budget } = {}) {
    if (!model) throw new Error('openai provider needs config.llm.model');
    Object.assign(this, { apiKey, model, baseUrl, budget: budget || new Budget(), name: 'openai' });
  }
  buildRequest({ system, user, webSearch }) { const b = { model: this.model, instructions: system, input: user }; if (webSearch) b.tools = [{ type: 'web_search' }]; return b; }
  parseResponse(j) {
    let text = '', urls = new Set();
    for (const o of j.output || []) if (o.type === 'message') for (const c of o.content || []) { if (c.type === 'output_text') { text += c.text + '\n'; for (const a of c.annotations || []) if (a.url) urls.add(a.url); } }
    const u = j.usage || {};
    return { text, searchUrls: urls, usage: { input_tokens: u.input_tokens || 0, output_tokens: u.output_tokens || 0, search_requests: (j.output || []).filter(o => o.type === 'web_search_call').length } };
  }
  async complete(req) {
    this.budget.authorize(); if (!this.apiKey) throw new Error('OPENAI_API_KEY not set');
    const r = await fetch(this.baseUrl + '/v1/responses', { method: 'POST', headers: { 'content-type': 'application/json', authorization: 'Bearer ' + this.apiKey }, body: JSON.stringify(this.buildRequest(req)) });
    const j = await r.json(); if (!r.ok) throw new Error(`openai_http_${r.status}`);
    const out = this.parseResponse(j); this.budget.record(out.usage); return out;
  }
}
module.exports = { OpenAIProvider };
