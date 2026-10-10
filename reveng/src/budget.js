'use strict';
class SpendNotAuthorized extends Error { constructor(m) { super(m); this.name = 'SpendNotAuthorized'; } }
class BudgetExceeded extends Error { constructor(m) { super(m); this.name = 'BudgetExceeded'; } }
// Hard spend guard. Paid LLM calls are refused unless allow_spend === true AND at least one cap is set.
class Budget {
  constructor(cfg = {}) {
    this.cfg = { allow_spend: false, max_calls: null, max_input_tokens: null, max_output_tokens: null, max_search_requests: null, max_usd: null,
      price_in_per_mtok: null, price_out_per_mtok: null, price_per_search: 0, ...cfg };
    this.used = { calls: 0, input_tokens: 0, output_tokens: 0, search_requests: 0, usd: 0 };
  }
  authorize() {
    const c = this.cfg;
    if (c.allow_spend !== true) throw new SpendNotAuthorized('LLM calls are paid spend: set budget.allow_spend=true in config to authorize.');
    if (![c.max_calls, c.max_input_tokens, c.max_output_tokens, c.max_usd].some(x => Number.isFinite(x))) throw new SpendNotAuthorized('Refusing: set at least one cap (max_calls / max_*_tokens / max_usd).');
    if (Number.isFinite(c.max_usd) && !(Number.isFinite(c.price_in_per_mtok) && Number.isFinite(c.price_out_per_mtok))) throw new SpendNotAuthorized('max_usd needs price_in_per_mtok and price_out_per_mtok in config (engine does not guess prices).');
    const u = this.used, lim = (v, cap, n) => { if (Number.isFinite(cap) && v >= cap) throw new BudgetExceeded(`${n} cap reached (${v}/${cap})`); };
    lim(u.calls, c.max_calls, 'max_calls'); lim(u.input_tokens, c.max_input_tokens, 'max_input_tokens'); lim(u.output_tokens, c.max_output_tokens, 'max_output_tokens');
    lim(u.search_requests, c.max_search_requests, 'max_search_requests'); lim(u.usd, c.max_usd, 'max_usd');
  }
  record({ input_tokens = 0, output_tokens = 0, search_requests = 0 } = {}) {
    const u = this.used, c = this.cfg; u.calls++; u.input_tokens += input_tokens; u.output_tokens += output_tokens; u.search_requests += search_requests;
    if (Number.isFinite(c.price_in_per_mtok) && Number.isFinite(c.price_out_per_mtok))
      u.usd = +(u.input_tokens / 1e6 * c.price_in_per_mtok + u.output_tokens / 1e6 * c.price_out_per_mtok + u.search_requests * (c.price_per_search || 0)).toFixed(6);
  }
}
module.exports = { Budget, SpendNotAuthorized, BudgetExceeded };
