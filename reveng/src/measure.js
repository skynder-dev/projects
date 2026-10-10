'use strict';
// Phase E hook: after the smallest prototype of a leader exists, its entrant edge must be MEASURED, not hypothesised.
// This delegates to the frozen G280 entrant_advantage contract (needs exact artifact SHA-256 + sourced incumbent measurement).
const { load } = require('../vendor/load');
const ea = load('entrant_advantage');
function evaluateMeasured(candidateId, raw) {
  const shim = { contract: 'reveng_discovery_candidate_normalization_v1', identityKey: 'opp:engine:' + candidateId };
  return ea.evaluate(shim, raw);
}
module.exports = { evaluateMeasured };
