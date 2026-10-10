(() => {
  const CONTRACT_ID='reveng_scoring_profiles_v1';
  const PROFILE_VERSION=1;
  const VERSION_LABEL=`v${PROFILE_VERSION}`;
  const DEFAULT_KEY='autonomy_first';
  const ORDER=Object.freeze(['autonomy_first','balanced','defensibility_growth']);

  const freezeRows=rows=>Object.freeze(rows.map(([label,weight])=>Object.freeze([String(label),Number(weight)])));
  const makeProfile=(key,label,text,topWeights,fullWeights)=>Object.freeze({
    key,
    contractId:CONTRACT_ID,
    version:PROFILE_VERSION,
    versionLabel:VERSION_LABEL,
    label,
    text,
    topWeights:freezeRows(topWeights),
    fullWeights:freezeRows(fullWeights)
  });

  const PROFILES=Object.freeze({
    autonomy_first:makeProfile(
      'autonomy_first',
      'Autonomy First',
      'Favors automation, low owner time, and faster launch. Ranking lens only — raw opportunity facts stay unchanged.',
      [['Automation',14],['Owner time',14],['Contribution economics',10],['Launch speed',10]],
      [['Automation',14],['Owner time efficiency',14],['Contribution economics',10],['Launch speed',10],['Capital efficiency',9],['Demand signal',8],['Acquisition efficiency',7],['Scale without hiring',6],['Competition gap',5],['Fulfillment simplicity',5],['Regulatory simplicity',5],['Platform resilience',4],['Defensibility',3]]
    ),
    balanced:makeProfile(
      'balanced',
      'Balanced',
      'Balances automation, economics, demand, and execution burden. Ranking lens only — raw opportunity facts stay unchanged.',
      [['Contribution economics',12],['Demand signal',12],['Acquisition efficiency',10],['Automation',8]],
      [['Contribution economics',12],['Demand signal',12],['Acquisition efficiency',10],['Automation',8],['Competition gap',8],['Defensibility',8],['Owner time efficiency',8],['Capital efficiency',6],['Launch speed',6],['Platform resilience',6],['Scale without hiring',6],['Fulfillment simplicity',5],['Regulatory simplicity',5]]
    ),
    defensibility_growth:makeProfile(
      'defensibility_growth',
      'Defensibility + Growth',
      'Favors durable advantage, growth capacity, and stronger long-term economics. Ranking lens only — raw opportunity facts stay unchanged.',
      [['Defensibility',15],['Demand signal',12],['Scale without hiring',11],['Competition gap',10]],
      [['Defensibility',15],['Demand signal',12],['Scale without hiring',11],['Competition gap',10],['Contribution economics',10],['Acquisition efficiency',8],['Platform resilience',8],['Automation',5],['Owner time efficiency',5],['Regulatory simplicity',5],['Capital efficiency',4],['Fulfillment simplicity',4],['Launch speed',3]]
    )
  });

  const EXCLUSION=Object.freeze({
    label:'Supply-demand match quality',
    reason:'Dimension introduced after v1; requires explicit new profile version.',
    excludedInVersion:PROFILE_VERSION
  });

  function resolveKey(key){ return Object.prototype.hasOwnProperty.call(PROFILES,String(key||'')) ? String(key) : DEFAULT_KEY; }
  function get(key){ return PROFILES[resolveKey(key)]; }
  function list(){ return ORDER.map(key=>PROFILES[key]); }
  function totalWeight(key){ return get(key).fullWeights.reduce((sum,row)=>sum+Number(row[1]||0),0); }
  function verify(){
    const failures=[];
    for(const key of ORDER){
      const p=PROFILES[key];
      if(!p||p.key!==key) failures.push(`${key}:identity`);
      if(p.version!==PROFILE_VERSION) failures.push(`${key}:version`);
      if(p.fullWeights.length!==13) failures.push(`${key}:dimension_count`);
      if(totalWeight(key)!==100) failures.push(`${key}:weight_total`);
      if(p.topWeights.length!==4) failures.push(`${key}:top_weight_count`);
      if(new Set(p.fullWeights.map(row=>row[0])).size!==p.fullWeights.length) failures.push(`${key}:duplicate_dimension`);
    }
    return Object.freeze({ok:failures.length===0,contractId:CONTRACT_ID,profileVersion:PROFILE_VERSION,profileCount:ORDER.length,failures:Object.freeze(failures)});
  }

  const verification=verify();
  if(!verification.ok) throw new Error(`REVENG_SCORING_PROFILE_CONTRACT_INVALID:${verification.failures.join(',')}`);

  window.RevEngScoringProfiles=Object.freeze({
    contractId:CONTRACT_ID,
    profileVersion:PROFILE_VERSION,
    versionLabel:VERSION_LABEL,
    defaultKey:DEFAULT_KEY,
    order:ORDER,
    exclusion:EXCLUSION,
    resolveKey,
    get,
    list,
    totalWeight,
    verification
  });
})();
