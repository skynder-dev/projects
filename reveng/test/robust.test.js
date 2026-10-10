'use strict';
// Regression tests for the failure seen in the first live cloud run: every discovery answer was unparseable and the run silently continued.
const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), os = require('node:os'), path = require('node:path');
const { FakeProvider } = require('./helpers');
const { discoverFamily, DiscoveryAborted } = require('../src/discover'), { run } = require('../src/pipeline'), { smoke } = require('../src/smoke');
const { AnthropicProvider } = require('../src/llm/anthropic'), { Budget, SpendNotAuthorized } = require('../src/budget'), { Fetcher } = require('../src/fetcher');
const tmp = () => fs.mkdtempSync(path.join(os.tmpdir(), 'rv-r-'));
const URLS = (n) => Array.from({ length: n }, (_, i) => 'https://v.com/p' + i);
const good = (n = 2) => JSON.stringify(Array.from({ length: n }, (_, i) => ({ name: 'I' + i, category: 'c', buyer: 'b', pain: 'p', entrant_wedge: 'w w w w', evidence: [{ ref: 'C' + (i + 1), kind: 'incumbent_price', shows: 's' }],
  substitutes: [], entrant_edge: { criterion: 'cash_cost', direction: 'lower_is_better', unit: 'u', incumbent_value: 10, incumbent_ref: 'C' + (i + 1), entrant_value: 5, entrant_basis: 'b'.repeat(25), falsifier: 'f' }, startup_cash_usd: 1, time_to_first_revenue_days: 1, owner_hours_per_week_steady: 1, automation_potential_pct: 50, unit_economics: {},
  dimension_scores: { demand_signal: 2, acquisition_efficiency: 2, competition_gap: 2, defensibility: 2, platform_resilience: 2, scale_without_hiring: 2, fulfillment_simplicity: 2, regulatory_simplicity: 2 } })));
const cit = (n = 2) => URLS(n).map((u, i) => ({ url: u, title: 't', cited_text: 'excerpt ' + i }));
// two-phase fake: phase 1 (search) returns notes+citations; phase 2 returns `json`
const twoPhaseFake = (json, o = {}) => new FakeProvider(({ webSearch }) => webSearch ? { text: 'Research notes. '.repeat(20), finalText: 'Research notes. '.repeat(20), citations: o.citations ?? cit(2), searchResults: URLS(2).map(url => ({ url, title: 't' })) } : { text: json, stop_reason: o.stop_reason || 'end_turn' });

test('narration brackets before the JSON no longer break discovery; evidence resolved from citations', async () => {
  const p = twoPhaseFake('I converted notes [1] and [2].\nHere: ' + good(2));
  const r = await discoverFamily({ provider: p, family: 'games', perFamily: 2, signalsEnabled: false });
  assert.equal(r.candidates.length, 2); assert.equal(p.calls.length, 2); assert.equal(p.calls[0].webSearch, true); assert.equal(p.calls[1].webSearch, false, 'JSON phase runs WITHOUT search');
  assert.equal(r.candidates[0].evidence[0].verify.status, 'verified'); assert.equal(r.candidates[0].evidence[0].quote, 'excerpt 0'); assert.equal(r.candidates[0].entrant_edge.incumbent_source_url, 'https://v.com/p0');
  assert.equal(r.research[0].excerpts.length, 2);
});
test('FAIL-FAST: two consecutive unparseable answers abort the run, save raw diagnostics, and stop spending', async () => {
  const p = twoPhaseFake('I could not produce JSON, sorry.'), dir = tmp();
  await assert.rejects(run({ runDir: dir, cfg: { families: ['games', 'services', 'marketplaces'], per_family: 2, sources: { enabled: false } }, provider: p, fetcher: new Fetcher({ allowHosts: [] }) }), DiscoveryAborted);
  assert.equal(p.calls.length, 4, 'two failed attempts x (research+json) = 4 calls, not dozens');
  const d = JSON.parse(fs.readFileSync(path.join(dir, '01_diagnostics.json'), 'utf8')); assert.ok(d.length >= 2 && d[0].text_head.includes('could not produce')); assert.equal(d[0].stop_reason, 'end_turn'); assert.equal(d[0].phase, 2);
  const chk = JSON.parse(fs.readFileSync(path.join(dir, 'checkpoint.json'), 'utf8')); assert.ok(chk.blockers.some(b => b.startsWith('discovery_aborted')));
});
test('truncation (stop_reason=max_tokens in JSON phase) halves the requested candidate count on retry', async () => {
  let n = 0; const asked = [];
  const p = new FakeProvider(({ system, user, webSearch }) => { if (webSearch) return { text: 'notes '.repeat(30), finalText: 'notes '.repeat(30), citations: cit(2), searchResults: [] }; asked.push(+user.match(/exactly (\d+) candidates/)[1]); n++; return n === 1 ? { text: '[{"name":"cut off', stop_reason: 'max_tokens' } : { text: good(2) }; });
  const r = await discoverFamily({ provider: p, family: 'games', perFamily: 4, signalsEnabled: false, breaker: { fails: 0, max: 3 } });
  assert.deepEqual(asked.slice(0, 2), [4, 2]); assert.ok(r.candidates.length >= 2); assert.equal(r.diags[0].stop_reason, 'max_tokens');
});
test('SpendNotAuthorized is never swallowed by the failure breaker', async () => {
  const p = twoPhaseFake(good()); p.budget = new Budget({});
  await assert.rejects(discoverFamily({ provider: p, family: 'games', perFamily: 2, signalsEnabled: false }), SpendNotAuthorized);
});
test('smoke(): 2 calls (research+json), reports excerpts/evidence; flags missing citations; failure path returns diagnostics', async () => {
  const p = twoPhaseFake(good(2)); const ok = await smoke({ provider: p }); assert.equal(p.calls.length, 2); assert.equal(ok.ok, true); assert.equal(ok.parsed_candidates, 2); assert.equal(ok.excerpts_returned, 2);
  assert.deepEqual(ok.evidence, { total: 2, verified: 2, search_confirmed: 0 });
  const nocite = await smoke({ provider: twoPhaseFake(good(2), { citations: [] }) }); assert.equal(nocite.ok, false); assert.match(nocite.error, /no_citation_excerpts/);
  const bad = await smoke({ provider: twoPhaseFake('nope') }); assert.equal(bad.ok, false); assert.match(bad.error, /discovery failed/); assert.ok(bad.diags[0].text_head);
});
test('Anthropic request: web_search tool with max_uses override and 16000 default tokens', () => {
  const p = new AnthropicProvider({ apiKey: 'k', model: 'm' }); const b = p.buildRequest({ system: 's', user: 'u', webSearch: true, maxUses: 3 });
  assert.equal(b.tools[0].max_uses, 3); assert.equal(b.max_tokens, 16000);
  const r = p.parseResponse({ content: [{ type: 'text', text: 'Let me search [1].' }, { type: 'server_tool_use', name: 'web_search' }, { type: 'web_search_tool_result', content: [{ url: 'https://a.com', title: 'A', page_age: '1 day' }] }, { type: 'text', text: '[{"x":1}]', citations: [{ type: 'web_search_result_location', url: 'https://a.com', title: 'A', cited_text: 'excerpt' }] }], stop_reason: 'max_tokens', usage: { input_tokens: 5, output_tokens: 6 } });
  assert.equal(r.finalText, '[{"x":1}]'); assert.equal(r.stop_reason, 'max_tokens'); assert.equal(r.citations[0].cited_text, 'excerpt'); assert.ok(r.diag.block_types.includes('web_search_tool_result'));
});
