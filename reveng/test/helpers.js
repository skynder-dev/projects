'use strict';
const http = require('node:http');
const { Budget } = require('../src/budget');
function startServer(routes) {
  return new Promise(res => {
    const hits = [];
    const s = http.createServer((req, rsp) => {
      hits.push(req.url);
      const r = routes[req.url.split('?')[0]] || routes['*'];
      if (!r) { rsp.statusCode = 404; return rsp.end('nope'); }
      const o = typeof r === 'function' ? r(req) : r;
      rsp.statusCode = o.status || 200; rsp.setHeader('content-type', o.type || 'text/html');
      rsp.end(typeof o.body === 'string' ? o.body : JSON.stringify(o.body));
    });
    s.listen(0, '127.0.0.1', () => res({ base: `http://127.0.0.1:${s.address().port}`, hits, close: () => new Promise(r => s.close(r)) }));
  });
}
const page = (t) => `<html><head><title>x</title><script>var a=1</script></head><body><p>${t}</p></body></html>`;
function cand(o = {}) {
  const id = o.id || 'SAS-01', url = o.url || 'https://example.com/pricing';
  const ev = o.evidence || [
    { id: id + '-E1', url, kind: 'incumbent_price', quote: 'Plan costs 49 dollars per month', verify: { status: 'verified' } },
    { id: id + '-E2', url: url + '/d', kind: 'demand', quote: 'q', verify: { status: 'verified' } },
    { id: id + '-E3', url: url + '/c', kind: 'constraint', quote: 'q', verify: { status: 'verified' } }];
  return {
    id, name: 'Cand ' + id, family: o.family || 'saas_or_micro_saas', buyer: 'small teams', pain: 'manual work', entrant_wedge: 'automated import that removes three manual steps',
    evidence: ev, substitutes: [], startup_cash_usd: 500, time_to_first_revenue_days: 30, owner_hours_per_week_steady: 6, automation_potential_pct: 80,
    unit_economics: { contribution_margin_pct: 75, price_usd: 29, variable_cost_usd: 3, notes: '', class: 'model' },
    entrant_edge: { criterion: 'cash_cost', direction: 'lower_is_better', unit: 'usd_month', incumbent_value: 49, incumbent_source_url: url, entrant_value: 19, entrant_basis: 'serverless hosting with no per-seat licence cost', falsifier: 'Reject if a $19 plan cannot cover hosting cost' },
    dimension_scores: { demand_signal: 3, acquisition_efficiency: 3, competition_gap: 3, defensibility: 2, platform_resilience: 3, scale_without_hiring: 4, fulfillment_simplicity: 5, regulatory_simplicity: 4 },
    dimension_evidence: {}, regulatory_or_platform_dependency: 'none', major_uncertainty: 'demand', unknowns: [], ...o.over,
  };
}
// Test-only provider: returns scripted text. Labelled FAKE in every use; proves wiring, never market truth.
class FakeProvider {
  constructor(handler) { this.handler = handler; this.budget = new Budget({ allow_spend: true, max_calls: 1000 }); this.calls = []; this.name = 'fake'; }
  async complete(req) { this.budget.authorize(); this.calls.push(req); const r = this.handler(req, this.calls.length); this.budget.record({ input_tokens: 10, output_tokens: 10 }); return { text: r.text, searchUrls: r.searchUrls || new Set(), usage: { input_tokens: 10, output_tokens: 10, search_requests: 0 } }; }
}
module.exports = { startServer, page, cand, FakeProvider };
