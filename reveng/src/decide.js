'use strict';
const { FAMILIES_REQUIRED } = require('./schema');
const { PROFILES, rank, GLOBAL_PROFILE, verifyIntegrity } = require('./scoring');
const DEF = { min_raw: 30, min_families: 8, min_per_family: 3, min_margin: 5, min_deep: 5 };
function decide({ candidates, scored, gateById, cfg = {}, provisional = false }) {
  const t = { ...DEF, ...cfg }, by = Object.fromEntries(candidates.map(c => [c.id, c])), reasons = [], hard = [];
  const fam = {}; for (const c of candidates) fam[c.family] = (fam[c.family] || 0) + 1;
  const missingFam = FAMILIES_REQUIRED.filter(f => (fam[f] || 0) < t.min_per_family);
  const survivors = scored.filter(r => gateById[r.id] && gateById[r.id].passed);
  const ranking = rank(survivors, GLOBAL_PROFILE);
  const integrity = verifyIntegrity(by, scored, rank(scored).map(r => r.id));
  const chk = (ok, msg, isHard = true) => { if (!ok) { reasons.push(msg); if (isHard) hard.push(msg); } };
  chk(candidates.length >= t.min_raw, `raw_candidates ${candidates.length}<${t.min_raw}`);
  chk(Object.keys(fam).filter(f => fam[f] > 0).length >= t.min_families, `families ${Object.keys(fam).length}<${t.min_families}`);
  chk(!missingFam.length, `required_families_underrepresented(<${t.min_per_family}): ${missingFam.join(',')}`);
  chk(!integrity.length, `score_integrity_violations: ${integrity.slice(0, 3).join('|')}`);
  chk(!provisional, 'provisional_run: evidence not engine-verified');
  chk(survivors.length > 0, 'no_candidate_survived_hard_gates');
  const top = ranking[0], second = ranking[1];
  let margin = null, robust = null, tc = null;
  if (top) {
    tc = by[top.id];
    chk(!!(tc.deep && tc.deep.done && tc.deep.complete), `top_candidate_not_deep_screened_to_equal_depth(${top.id})`);
    const deepCount = candidates.filter(c => c.deep && c.deep.complete).length;
    chk(deepCount >= Math.min(t.min_deep, survivors.length), `deep_screened ${deepCount}<${Math.min(t.min_deep, survivors.length)}`);
    margin = second ? +(top.adjusted - second.adjusted).toFixed(3) : null;
    chk(second === undefined || margin >= t.min_margin, `margin_over_runner_up ${margin}<${t.min_margin}`, false);
    robust = {}; for (const p of Object.keys(PROFILES)) { const r = rank(survivors, p).map(x => x.id); robust[p] = r.indexOf(top.id) + 1; }
    chk(Object.values(robust).every(r => r <= 2), `not_top2_in_all_profiles ${JSON.stringify(robust)}`, false);
    chk(!!(tc.deep && tc.deep.economics && tc.deep.economics.survives_pessimistic), 'top_fails_or_lacks_pessimistic_economics', false);
  }
  const verdict = hard.length ? 'no_winner' : (reasons.length ? 'conditional_winner' : 'winner');
  return { verdict, leader: verdict === 'no_winner' ? null : (top ? top.id : null), unmet_conditions: reasons, hard_blockers: hard, margin_adjusted_points: margin, rank_by_profile: robust,
    survivors: survivors.length, families: fam, ranking: ranking.map(r => ({ id: r.id, family: r.family, adjusted: r.adjusted, raw: r.raw })), integrity_violations: integrity };
}
module.exports = { decide, DEF };
