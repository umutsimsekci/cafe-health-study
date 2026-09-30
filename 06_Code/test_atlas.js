/* Run: node 06_Code/test_atlas.js [docs/index.html] */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const core = require('./atlas_core.js');
const file = process.argv[2] || path.join(__dirname, '../docs/index.html');
const html = fs.readFileSync(file, 'utf8');
const dataMatch = html.match(/const ATLAS_DATA=(.*?);const ATLAS_CONFIG=(.*?);<\/script>/s);
assert(dataMatch, 'Embedded data and configuration must be present');
const data = JSON.parse(dataMatch[1]), config = JSON.parse(dataMatch[2]);
assert.equal(data.features.length, 23527);
assert.equal(new Set(data.features.map(f=>f.properties.countyfips)).size, 50);
assert.equal(new Set(data.features.map(f=>f.properties.GEOID)).size, 23527);
assert.equal(data.features.reduce((sum,f)=>sum+f.properties.cafe_count,0), 13195);
assert.equal(data.features.reduce((sum,f)=>sum+f.properties.E_TOTPOP,0), 99313722);
assert(data.features.every(f=>/^\d{11}$/.test(f.properties.GEOID) && /^\d{5}$/.test(f.properties.countyfips)));
assert(data.features.some(f=>f.properties.GEOID.startsWith('0')), 'Leading-zero GEOIDs must remain strings');
let scenariosChecked=0, signReversalsChecked=0, clippedCount=0, unsupportedCount=0;
for (const f of data.features) {
  const p=f.properties;
  assert(Math.abs(p.cafe_per_10k-p.cafe_count/p.E_TOTPOP*10000)<1e-12);
  for (const model of ['extended','hospitality']) {
    for (const kind of ['count','percent']) {
      const zero=core.scenarioFor(p,{model,kind,amount:0},config.models,config.support);
      assert.equal(zero.dx,0);
      assert.equal(Math.abs(zero.contrast),0);
      assert.equal(Math.abs(zero.lower),0);
      assert.equal(Math.abs(zero.upper),0);
      assert.equal(Object.is(zero.contrast,-0),false);
      assert.equal(Object.is(zero.lower,-0),false);
      assert.equal(Object.is(zero.upper,-0),false);
      assert.equal(zero.target,p.cafe_per_10k);
      assert.equal(zero.supported,true);
      scenariosChecked++;
    }
    for (const settings of [{model,kind:'count',amount:1},{model,kind:'count',amount:-1},{model,kind:'percent',amount:25},{model,kind:'percent',amount:-50}]) {
      const result=core.scenarioFor(p,settings,config.models,config.support);
      assert(result.target>=0);
      assert(result.lower<=result.contrast && result.contrast<=result.upper);
      assert.equal(result.supported,result.target>=config.support.min && result.target<=config.support.max);
      if (settings.kind==='count') assert.equal(result.target,Math.max(0,p.cafe_count+settings.amount)/p.E_TOTPOP*10000);
      if (result.dx<0) {
        assert.equal(result.lower,config.models[model].upper*result.dx);
        assert.equal(result.upper,config.models[model].lower*result.dx);
        signReversalsChecked++;
      }
      if (result.clippedAtZero) clippedCount++;
      if (!result.supported) unsupportedCount++;
      scenariosChecked++;
    }
  }
}
assert(signReversalsChecked>0 && clippedCount>0 && unsupportedCount>0);
const first=data.features[0].properties;
for (const key of ['E_TOTPOP','cafe_count','cafe_per_10k']) {
  assert.equal(core.scenarioFor({...first,[key]:null},{model:'extended',kind:'count',amount:1},config.models,config.support),null);
  assert.equal(core.scenarioFor({...first,[key]:undefined},{model:'extended',kind:'count',amount:1},config.models,config.support),null);
  assert.equal(core.scenarioFor({...first,[key]:Infinity},{model:'extended',kind:'count',amount:1},config.models,config.support),null);
}
assert.equal(core.scenarioFor(first,{model:'extended',kind:'count',amount:''},config.models,config.support),null);
assert.equal(core.scenarioFor(first,{model:'missing',kind:'count',amount:1},config.models,config.support),null);
assert.equal(core.percentile([0,0,1,2],0),50);
assert.equal(core.percentile([0,0,1,2],2),100);
assert.equal(core.percentile([],1),null);
if (config.nearby) {
  assert(data.features.every(f=>f.properties.coverage_verified_1000m===true));
  assert(data.features.every(f=>f.properties.mapped_cafes_within_500m<=f.properties.mapped_cafes_within_1000m));
  assert(data.features.every(f=>f.properties.mapped_cafes_across_tract_boundary_1000m<=f.properties.mapped_cafes_within_1000m));
  assert.equal(data.features.filter(f=>f.properties.cafe_count===0).length,17331);
  assert.equal(data.features.filter(f=>f.properties.cafe_count===0 && f.properties.mapped_cafes_within_1000m>0).length,3843);
}
assert(!/<script[^>]+src=/i.test(html), 'No external script dependency');
assert(!/https?:\/\/[^\s"']+\.(?:png|jpg|pbf|geojson)(?:["'\s])/i.test(html), 'No external map tiles or data dependency');
console.log(JSON.stringify({status:'PASS',tracts:23527,counties:50,scenariosChecked,signReversalsChecked,clippedCount,unsupportedCount,nearbyLayer:config.nearby,allZeroChangeContrastsExactlyZero:true,missingValuesNotCoercedToZero:true,leadingZeroIdentifiersPreserved:true},null,2));
