/* KAOS AI Intelligence 1.6.36
Shadow/research schema. No execution authority.
Designed for KAOS Strategy + KAOS XGBoost + Pocket Option AI observations +
authorized external signal providers, scored against 5/10/15/30 second outcomes.
*/
(function(g){
  const HORIZONS=[5,10,15,30];
  function observation(x={}){
    return {
      schema:'KAOS_AI_INTELLIGENCE_V1',
      id:`KAI:${Date.now()}:${Math.random().toString(36).slice(2,8)}`,
      ts:Date.now(),
      asset:x.asset||null,
      entryPrice:Number.isFinite(+x.entryPrice)?+x.entryPrice:null,
      strategy:x.strategy||null,
      xgboost:x.xgboost||null,
      pocketOptionAi:x.pocketOptionAi||null,
      externalAi:x.externalAi||null,
      features:x.features||null,
      horizons:HORIZONS,
      outcomes:{},
      shadowOnly:true
    };
  }
  function score(obs,horizonSec,exitPrice){
    if(!obs||!HORIZONS.includes(+horizonSec)||!Number.isFinite(+exitPrice)||!Number.isFinite(+obs.entryPrice))return obs;
    const up=+exitPrice>+obs.entryPrice, down=+exitPrice<+obs.entryPrice;
    obs.outcomes[horizonSec]={exitPrice:+exitPrice,move:up?'UP':down?'DOWN':'TIE',scoredAt:Date.now()};
    return obs;
  }
  g.KAOS_AI_INTELLIGENCE={HORIZONS,observation,score};
})(typeof globalThis!=='undefined'?globalThis:this);
