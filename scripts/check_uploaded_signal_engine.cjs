/* Small offline checks of reviewed pure source, without extension/browser/network. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const [file]=process.argv.slice(2);if(!file)throw Error('Supply reviewed local signalEngine.js');
const context=vm.createContext({});vm.runInContext(fs.readFileSync(file,'utf8'),context,{timeout:1000});
const engine=context.AvalisaSignalEngine;
const data={price:99.98,sma20:100,rsi14:50,volatility:.1,momentum5:.01,slope10:.1,lastCandle:'green',pair:'TEST'};
for(const [mode,tf] of [['low','S30'],['mid','M1'],['high','M3']]){
 const result=engine.evaluateSignal(data,mode);assert.equal(result.action,'CALL');assert.equal(result.snapshot.rulesMatched,4);assert.equal(result.snapshot.confidence,100);assert.equal(result.timeframe,tf);
}
const mid=engine.evaluateSignal({...data,price:100.03},'mid');assert.equal(mid.snapshot.confidence,75);assert.equal(mid.snapshot.rulesMatched,3);assert.equal(mid.action,'CALL');
assert.equal(engine.evaluateSignal({...data,price:100.03},'high').action,'SKIP');
assert.equal(engine.evaluateSignal({...data,volatility:1},'low').reason,'vol_too_high');
assert.equal(engine.evaluateSignal({...data,rsi14:null},'mid').reason,'missing_indicators');
console.log('Pure source checks passed: rule-count confidence, intensity/expiry mapping, insufficient agreement, volatility veto, missing-data veto. No predictive accuracy claim.');
