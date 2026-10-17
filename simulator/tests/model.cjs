const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const M = require('../dist/assets/model.js');
const context = {window:{}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../dist/assets/calibration.js'),'utf8'),context);
const D = context.window.STORIES_DATA;
const near=(a,b)=>assert(Math.abs(a-b)<1e-6,`${a} != ${b}`);
const zero={...M.defaults,saving:0,attach:0,price:0,traffic:0,budget:0,setup:0,hours:0};
let r=M.calculate(D.totals,D.branches,zero);
near(r.revenue,305925.14);near(r.profit,179430.49);near(r.delta,0);near(r.orders,33887);
r=M.calculate(D.totals,D.branches,{...zero,saving:10});near(r.delta,5295.406);near(r.branches.find(b=>b.label==='Harbour').contributionDelta,0);
r=M.calculate(D.totals,D.branches,{...zero,price:5,elasticity:-1});near(r.revenue,305925.14);near(r.delta,126494.65*(1-1/1.05));
r=M.calculate(D.totals,D.branches,{...zero,hours:2,wage:6});near(r.delta,-2*6*181);
r=M.calculate(D.totals,D.branches,{...zero,budget:200,setup:1000});near(r.delta,-2200);
for(let i=0;i<100;i++){
 const s={...M.defaults,saving:i%31,attach:i%21,price:(i%26)-10,traffic:(i%51)-20,hours:i%25};r=M.calculate(D.totals,D.branches,s);
 near(r.delta,r.volume+r.price+r.food+r.saving+r.labor+r.spend+r.setup);
 near(r.delta,r.branches.reduce((n,b)=>n+b.contributionDelta,0));
 assert(r.branches.every(b=>b.orders>=0&&b.extraUnits>=0&&b.profit<=b.revenue));
}
const trials=M.prepareTrials(D,2000),out=M.stress(D,zero,trials);assert(out.every(x=>Math.abs(x)<1e-7));
const selected=M.stress(D,M.defaults,trials);assert(selected.every(Number.isFinite));assert.deepEqual(selected,M.stress(D,M.defaults,trials));
let cumulative=-M.defaults.setup;
for(let month=1;month<=6;month++){
 const days=D.days.filter(d=>+d.date.slice(5,7)===month);
 cumulative+=M.calculate(M.aggregate(days,3),D.branches,{...M.defaults,setup:0},days.length,1,{foodEconomics:D.totals}).delta;
}
near(cumulative,M.calculate(D.totals,D.branches,M.defaults).delta);
console.log('PASS: baseline totals, known cost savings, pricing response, labor, program costs, 100 component/branch reconciliations, paired no-change trials, deterministic stress draws and monthly timeline.');
