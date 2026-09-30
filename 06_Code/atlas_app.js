'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const core = CafeAtlasCore;
  const F = ATLAS_DATA.features;
  const byId = new Map(F.map(f => [f.properties.GEOID, f]));
  const config = ATLAS_CONFIG;
  const fmt = (v, digits = 1) => Number.isFinite(v) ? (v === 0 ? 0 : v).toLocaleString('en-US', {minimumFractionDigits: digits, maximumFractionDigits: digits}) : 'Unavailable';
  const signed = v => (v > 0 ? '+' : '') + fmt(v, 3);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const metrics = {
    cafe_per_10k: {label:'Mapped cafes per 10,000 ACS residents', digits:2, palette:d3.interpolateViridis, cafe:true},
    cafe_count: {label:'Mapped cafe count', digits:0, palette:d3.interpolateViridis, cafe:true},
    cafe_per_km2: {label:'Mapped cafes per land km²', digits:2, palette:d3.interpolateViridis, cafe:true},
    MHLTH_CrudePrev: {label:'Modeled frequent mental distress (%)', digits:1, palette:d3.interpolateMagma, health:'MHLTH'},
    OBESITY_CrudePrev: {label:'Modeled obesity (%)', digits:1, palette:d3.interpolateMagma, health:'OBESITY'},
    LPA_CrudePrev: {label:'Modeled physical inactivity (%)', digits:1, palette:d3.interpolateMagma, health:'LPA'},
    EP_POV150: {label:'Below 150% of poverty threshold (%)', digits:1, palette:d3.interpolateYlGnBu, context:true},
    EP_UNEMP: {label:'Unemployment (%)', digits:1, palette:d3.interpolateYlGnBu, context:true},
    EP_NOVEH: {label:'Households without a vehicle (%)', digits:1, palette:d3.interpolateYlGnBu, context:true},
    pop_density: {label:'ACS residents per land km²', digits:0, palette:d3.interpolateCividis, density:true}
  };
  if (config.nearby) {
    Object.assign(metrics, {
      mapped_cafes_within_500m:{label:'Mapped cafes within 500 m of tract centroid', digits:0, palette:d3.interpolateViridis, cafe:true, nearby:true},
      mapped_cafes_within_1000m:{label:'Mapped cafes within 1 km of tract centroid', digits:0, palette:d3.interpolateViridis, cafe:true, nearby:true},
      mapped_cafes_across_tract_boundary_1000m:{label:'Nearby cafes outside own tract (within 1 km)', digits:0, palette:d3.interpolateViridis, cafe:true, nearby:true}
    });
    ['mapped_cafes_within_500m','mapped_cafes_within_1000m','mapped_cafes_across_tract_boundary_1000m'].forEach(key => $('proximityOptions').append(new Option(metrics[key].label, key)));
    $('proximitySource').hidden = false;
  } else $('proximityOptions').remove();
  const sortedValues = {}, scales = {};
  for (const [key, metric] of Object.entries(metrics)) {
    const values = F.map(f => f.properties[key]).filter(Number.isFinite).sort(d3.ascending);
    sortedValues[key] = values;
    const positive = values.filter(v => v > 0);
    const low = metric.cafe ? 0 : d3.quantile(values, .01);
    const high = d3.quantile(values, .99);
    const color = d3.scaleSequential(metric.palette).domain(metric.cafe ? [d3.min(positive) || 0, high || 1] : [low, high]).clamp(true);
    scales[key] = {low, high:high || 1, color};
  }
  const cafeCut = d3.quantile(sortedValues.cafe_per_10k.filter(v => v > 0), .5);
  const healthCuts = [d3.quantile(sortedValues.MHLTH_CrudePrev, 1/3), d3.quantile(sortedValues.MHLTH_CrudePrev, 2/3)];
  const bivColors = ['#e8e8e8','#ace4e4','#5ac8c8','#dfb0d6','#a5add3','#5698b9','#be64ac','#8c62aa','#3b4994'];
  const bivCell = f => {
    const p = f.properties, x = p.cafe_per_10k === 0 ? 0 : p.cafe_per_10k <= cafeCut ? 1 : 2;
    const y = p.MHLTH_CrudePrev <= healthCuts[0] ? 0 : p.MHLTH_CrudePrev <= healthCuts[1] ? 1 : 2;
    return y * 3 + x;
  };
  const counties = Array.from(d3.group(F, f => f.properties.countyfips), ([id, features]) => ({id, features:features.sort((a,b)=>a.properties.GEOID.localeCompare(b.properties.GEOID)), label:features[0].properties.CountyName+', '+features[0].properties.StateAbbr})).sort((a,b)=>a.label.localeCompare(b.label));
  $('county').append(new Option('All 50 study counties', 'all'));
  counties.forEach(c => $('county').append(new Option(c.label, c.id)));
  $('county').value = '06037';
  const state = {view:'data', selected:null, comparison:null, shown:[], county:'06037', key:'cafe_per_10k', scenario:{model:'extended',kind:'count',amount:1}};
  const svg = d3.select('#map');
  const defs = svg.append('defs');
  const hatch = defs.append('pattern').attr('id','outside-support').attr('patternUnits','userSpaceOnUse').attr('width',7).attr('height',7);
  hatch.append('rect').attr('width',7).attr('height',7).attr('fill','#e5eae6');
  hatch.append('path').attr('d','M0,7 L7,0 M-2,2 L2,-2 M5,9 L9,5').attr('stroke','#879b92').attr('stroke-width',1);
  const layer = svg.append('g');
  const paths = layer.append('g');
  const markers = layer.append('g');
  let projection, path, width, height, scenarioColors, scenarioRange = 0.01;
  const tooltip = $('tooltip');
  const zoom = d3.zoom().scaleExtent([1,40]).on('zoom', event => {layer.attr('transform', event.transform); markers.selectAll('circle').attr('r', d => (d === state.selected ? 4.2 : 3.8) / event.transform.k);});
  svg.call(zoom);
  function scenario(f) {return core.scenarioFor(f.properties, state.scenario, config.models, config.support);}
  function currentValue(f) {return state.view === 'scenario' ? scenario(f)?.contrast : f.properties[state.key === 'bivariate' ? 'MHLTH_CrudePrev' : state.key];}
  function currentMeta() {return state.view === 'scenario' ? {label:'Cafe-term association contrast (percentage points)',digits:3} : metrics[state.key === 'bivariate' ? 'MHLTH_CrudePrev' : state.key];}
  function color(f) {
    if (state.view === 'scenario') {const s = scenario(f); return !s || !s.supported ? 'url(#outside-support)' : scenarioColors(s.contrast);}
    if (state.key === 'bivariate') return bivColors[bivCell(f)];
    const v = f.properties[state.key];
    return !Number.isFinite(v) ? '#d6ded9' : metrics[state.key].cafe && v === 0 ? '#f0f0e9' : scales[state.key].color(v);
  }
  function fillTractPicker() {
    const fragment = document.createDocumentFragment();
    state.shown.forEach(f => fragment.append(new Option(f.properties.GEOID+' · '+f.properties.CountyName+', '+f.properties.StateAbbr, f.properties.GEOID)));
    $('tractPicker').replaceChildren(fragment);
  }
  function updateScenarioColors() {
    const contrasts = F.map(scenario).filter(s => s && s.supported).map(s => Math.abs(s.contrast)).sort(d3.ascending);
    scenarioRange = Math.max(d3.quantile(contrasts, .99) || 0, .001);
    scenarioColors = d3.scaleDiverging(d3.interpolateRdBu).domain([-scenarioRange,0,scenarioRange]).clamp(true);
  }
  function render(reset = false) {
    tooltip.style.display = 'none';
    state.key = $('metric').value;
    state.county = $('county').value;
    state.shown = state.county === 'all' ? F : counties.find(c => c.id === state.county).features;
    if (!state.selected || !state.shown.includes(state.selected)) state.selected = state.shown[0];
    if (reset || !projection) {
      width = $('map').clientWidth; height = $('map').clientHeight;
      svg.attr('viewBox', `0 0 ${width} ${height}`);
      projection = (state.county === 'all' ? d3.geoAlbersUsa() : d3.geoMercator()).fitExtent([[20,20],[width-20,height-20]],{type:'FeatureCollection',features:state.shown});
      path = d3.geoPath(projection);
      svg.call(zoom.transform,d3.zoomIdentity);
      fillTractPicker();
    }
    if (state.view === 'scenario') updateScenarioColors();
    paths.selectAll('path').data(state.shown,f=>f.properties.GEOID).join('path').attr('class','tract').attr('d',path).attr('fill',color).on('pointermove',showTip).on('pointerleave',()=>tooltip.style.display='none').on('click',(_event,f)=>select(f));
    $('maptitle').textContent = $('county').selectedOptions[0].textContent;
    $('mapSubtitle').textContent = state.view === 'scenario' ? 'Conditional algebraic contrast · not predicted health prevalence' : 'Scroll to zoom · drag to pan · click to select';
    $('ntracts').textContent = fmt(state.shown.length,0);
    $('ncafes').textContent = fmt(d3.sum(state.shown,f=>f.properties.cafe_count),0);
    $('nresidents').textContent = fmt(d3.sum(state.shown,f=>f.properties.E_TOTPOP),0);
    $('nzero').textContent = fmt(state.shown.filter(f=>f.properties.cafe_count===0).length/state.shown.length*100,1)+'%';
    renderLegend();
    renderStatus();
    select(state.selected);
    $('loading').hidden = true;
  }
  function renderLegend() {
    const biv = state.view === 'data' && state.key === 'bivariate';
    $('continuousLegend').hidden = biv;
    $('bivariateLegend').hidden = !biv;
    $('legendTitle').textContent = biv ? 'Joint geographical pattern' : currentMeta().label;
    if (biv) {
      $('bivgrid').replaceChildren(...[6,7,8,3,4,5,0,1,2].map(i=>{const span=document.createElement('span');span.style.background=bivColors[i];return span;}));
      $('bivThresholds').textContent = `Cafe categories: 0, >0–${fmt(cafeCut,2)}, >${fmt(cafeCut,2)} per 10,000. Health cuts: ${fmt(healthCuts[0])}% and ${fmt(healthCuts[1])}%.`;
      $('legendnote').textContent = 'Fixed pooled categories. Colors describe co-location, without contextual adjustment.';
      return;
    }
    const s = state.view === 'scenario' ? {low:-scenarioRange,high:scenarioRange,color:scenarioColors} : scales[state.key];
    $('ramp').style.background = `linear-gradient(to right,${d3.range(0,1.001,.1).map(t=>s.color(s.low+t*(s.high-s.low))).join(',')})`;
    const digits = currentMeta().digits;
    $('ticks').innerHTML = `<span>${fmt(s.low,digits)}</span><span>${fmt((s.low+s.high)/2,digits)}</span><span>${fmt(s.high,digits)}</span>`;
    if (state.view === 'scenario') $('legendnote').innerHTML = '<span class="support-swatch"></span>Outside pooled observed density range; no scenario color. Symmetric color cap: pooled 99th percentile of supported absolute contrasts. Negative values mean a lower fitted cafe term.';
    else $('legendnote').innerHTML = (metrics[state.key].cafe ? '<span class="zero-swatch"></span>No qualifying mapped cafe. Positive color cap: pooled 99th percentile.' : 'Pooled 1st–99th percentile color limits.')+' Values beyond color caps remain available in the profile and CSV.';
  }
  function renderStatus() {
    if (state.view === 'scenario') {
      const scenarios = state.shown.map(scenario);
      const outside = scenarios.filter(s=>!s || !s.supported).length;
      const sparse = scenarios.filter(s=>s?.supported && s.aboveP99).length;
      const clipped = scenarios.filter(s=>s?.clippedAtZero).length;
      $('mapStatus').textContent = `${fmt(state.shown.length,0)} tracts · ${fmt(outside,0)} outside observed range · ${fmt(sparse,0)} targets above observed 99th percentile${clipped ? ' · '+fmt(clipped,0)+' count targets bounded at zero' : ''}`;
    } else $('mapStatus').textContent = `${fmt(state.shown.length,0)} included tracts · fixed study-wide color scale · source values retain original precision`;
  }
  function showTip(event,f) {
    const p=f.properties, meta=currentMeta();
    const line = state.view === 'scenario' ? (()=>{const s=scenario(f);return s?.supported ? `${signed(s.contrast)} pp<br>Coefficient-only 95% interval: ${signed(s.lower)} to ${signed(s.upper)} pp` : 'Target outside pooled observed range';})() : `${esc(meta.label)}: <strong>${fmt(currentValue(f),meta.digits)}</strong>`;
    tooltip.innerHTML = `<span class="tooltip-label">Tract ${p.GEOID}</span><br>${esc(p.CountyName)}, ${esc(p.StateAbbr)}<br>${line}<br>Mapped cafes in own tract: ${fmt(p.cafe_count,0)}<br><small>Click to inspect and compare.</small>`;
    tooltip.style.display='block';
    const box=tooltip.getBoundingClientRect();
    tooltip.style.left=Math.max(8,Math.min(event.clientX+12,innerWidth-box.width-8))+'px';
    tooltip.style.top=Math.max(8,Math.min(event.clientY+12,innerHeight-box.height-8))+'px';
  }
  function select(f) {
    state.selected=f;
    $('tractPicker').value=f.properties.GEOID;
    paths.selectAll('path').classed('selected',d=>d===f).classed('comparison',d=>d===state.comparison);
    paths.selectAll('path').filter(d=>d===f || d===state.comparison).raise();
    const marked=[state.comparison,f].filter((d,i,arr)=>d && state.shown.includes(d) && arr.indexOf(d)===i);
    markers.selectAll('circle').data(marked,d=>d.properties.GEOID).join('circle').attr('class',d=>'selected-marker'+(d===state.comparison?' comparison-marker':'')).attr('cx',d=>projection(d3.geoCentroid(d))[0]).attr('cy',d=>projection(d3.geoCentroid(d))[1]).attr('r',d=>(d===state.selected?4.2:3.8)/d3.zoomTransform(svg.node()).k);
    renderProfile(); renderHistogram(); renderComparison();
  }
  function profileRow(label,value,note='') {return `<tr><td>${label}${note?'<small>'+note+'</small>':''}</td><td>${value}</td></tr>`;}
  function renderProfile() {
    const p=state.selected.properties;
    $('profileTitle').textContent='Tract '+p.GEOID;
    $('profileCounty').textContent=p.CountyName+', '+p.StateAbbr;
    const pct=core.percentile(sortedValues.cafe_per_10k,p.cafe_per_10k);
    let html=`<span class="pill">${p.cafe_count===0?'No cafe mapped in own tract':'Cafe mapped in own tract'}</span><table class="profile-table">`;
    html+=profileRow('Mapped cafes',fmt(p.cafe_count,0));
    html+=profileRow('Cafes / 10,000 residents',fmt(p.cafe_per_10k,2),`At or below ${fmt(pct,0)}% of study tracts (ties included)`);
    html+=profileRow('ACS residents',fmt(p.E_TOTPOP,0));
    html+=profileRow('Frequent mental distress',fmt(p.MHLTH_CrudePrev)+'%',`CDC model 95% interval: ${fmt(p.MHLTH_lower)}–${fmt(p.MHLTH_upper)}%`);
    html+=profileRow('Below 150% poverty threshold',fmt(p.EP_POV150)+'%');
    html+=profileRow('Unemployment',fmt(p.EP_UNEMP)+'%');
    html+=profileRow('Households without vehicle',fmt(p.EP_NOVEH)+'%');
    if (config.nearby) html+=profileRow('Cafes within 1 km of centroid',fmt(p.mapped_cafes_within_1000m,0),`${fmt(p.mapped_cafes_across_tract_boundary_1000m,0)} outside own tract · straight-line distance`);
    if (state.view==='data' && state.key!=='bivariate' && !['cafe_per_10k','cafe_count','MHLTH_CrudePrev','EP_POV150','EP_UNEMP','EP_NOVEH','mapped_cafes_within_1000m'].includes(state.key)) {
      const m=metrics[state.key];
      html+=profileRow(m.label,fmt(p[state.key],m.digits),m.health?`CDC model 95% interval: ${fmt(p[m.health+'_lower'])}–${fmt(p[m.health+'_upper'])}%`:'');
    }
    $('profile').innerHTML=html+'</table>';
    $('scenarioProfile').hidden=state.view!=='scenario';
    if (state.view==='scenario') {
      const s=scenario(state.selected), model=config.models[state.scenario.model];
      $('scenarioResult').innerHTML=s.supported?`<div class="note">Cafe-term contrast</div><div class="big">${signed(s.contrast)} pp</div><div class="ci">95% coefficient interval<br>${signed(s.lower)} to ${signed(s.upper)} pp</div><p class="note">Density: ${fmt(s.baseline,2)} → ${fmt(s.target,2)} per 10,000.${s.aboveP99?' Target above the observed 99th percentile.':''}${s.clippedAtZero?' Requested count removal was bounded at zero.':''}</p>`:`<strong>Outside observed density range</strong><p class="note">Density: ${fmt(s.baseline,2)} → ${fmt(s.target,2)} per 10,000. Observed range: ${fmt(config.support.min,2)}–${fmt(config.support.max,2)}. The association contrast is withheld from the map and summary.</p>`;
      $('scenarioFormula').textContent=`${fmt(model.beta,6)} × [log₂(1 + ${fmt(s.target,4)}) − log₂(1 + ${fmt(s.baseline,4)})] percentage points`;
      $('scenarioModelNote').textContent=`Coefficient: ${fmt(model.beta,3)} pp [${fmt(model.lower,3)}, ${fmt(model.upper,3)}] per 1-unit log₂(1 + density). Incremental model R²: ${fmt(model.deltaR2,6)}. Conditional coefficient uncertainty only; no independently observed health validation was established.`;
    }
  }
  function renderComparison() {
    const compare=state.comparison;
    $('comparison').hidden=!compare;
    $('clearCompare').disabled=!compare;
    if (!compare) return;
    const a=state.selected.properties,b=compare.properties;
    $('comparisonCaption').textContent=`Selected ${a.GEOID} (${a.CountyName}, ${a.StateAbbr}) vs comparison ${b.GEOID} (${b.CountyName}, ${b.StateAbbr}). Orange outline marks the comparison when in view.`;
    const keys=['cafe_count','cafe_per_10k','MHLTH_CrudePrev','EP_POV150'];
    if (config.nearby) keys.push('mapped_cafes_within_1000m');
    let rows=keys.map(k=>`<tr><td>${esc(k==='MHLTH_CrudePrev'?'Mental distress (%)':k==='EP_POV150'?'Poverty (%)':k==='cafe_per_10k'?'Cafes / 10k':k==='cafe_count'?'Own-tract cafes':'Cafes within 1 km')}</td><td>${fmt(a[k],metrics[k].digits)}</td><td>${fmt(b[k],metrics[k].digits)}</td></tr>`).join('');
    if (state.view==='scenario') {const sa=scenario(state.selected),sb=scenario(compare);rows+=`<tr><td>Contrast (pp)</td><td>${sa?.supported?signed(sa.contrast):'Outside range'}</td><td>${sb?.supported?signed(sb.contrast):'Outside range'}</td></tr>`;}
    $('comparisonValues').innerHTML='<table class="comparison-table"><thead><tr><th>Measure</th><th>Selected</th><th>Comparison</th></tr></thead><tbody>'+rows+'</tbody></table><p class="comparison-caption">Direct differences between two tracts do not represent covariate-adjusted or causal comparisons.</p>';
  }
  function renderHistogram() {
    const meta=currentMeta(), source=state.view==='scenario'?state.shown.filter(f=>scenario(f)?.supported):state.shown;
    const values=source.map(currentValue).filter(Number.isFinite);
    const s=state.view==='scenario'?{low:-scenarioRange,high:scenarioRange}:scales[state.key==='bivariate'?'MHLTH_CrudePrev':state.key];
    const w=$('hist').clientWidth,h=110,pad={left:6,right:6,top:7,bottom:25};
    const chart=d3.select('#hist').attr('viewBox',`0 0 ${w} ${h}`);chart.selectAll('*').remove();
    const x=d3.scaleLinear().domain([s.low,s.high]).range([pad.left,w-pad.right]);
    const bins=d3.bin().domain(x.domain()).thresholds(x.ticks(24))(values.map(v=>Math.max(s.low,Math.min(s.high,v))));
    const y=d3.scaleLinear().domain([0,d3.max(bins,b=>b.length)||1]).range([h-pad.bottom,pad.top]);
    chart.selectAll('rect').data(bins).join('rect').attr('x',d=>x(d.x0)+.5).attr('width',d=>Math.max(0,x(d.x1)-x(d.x0)-1)).attr('y',d=>y(d.length)).attr('height',d=>y(0)-y(d.length)).attr('fill','#aac7b9');
    chart.append('g').attr('transform',`translate(0,${h-pad.bottom})`).call(d3.axisBottom(x).tickValues([s.low,(s.low+s.high)/2,s.high]).tickFormat(v=>fmt(v,meta.digits)).tickSize(3)).call(g=>g.select('.domain').attr('stroke','#ccdcd2')).call(g=>g.selectAll('text').attr('font-size',9).attr('fill','#526b70'));
    [state.comparison,state.selected].filter(Boolean).forEach(f=>{const value=currentValue(f);if (!Number.isFinite(value) || (state.view==='scenario'&&!scenario(f)?.supported)) return;const xx=x(Math.max(s.low,Math.min(s.high,value)));chart.append('line').attr('x1',xx).attr('x2',xx).attr('y1',pad.top).attr('y2',h-pad.bottom).attr('stroke',f===state.selected?'#163c43':'#b75d28').attr('stroke-width',2).attr('stroke-dasharray',f===state.selected?null:'3 2');});
    $('histTitle').textContent=state.view==='scenario'?'Supported scenario contrasts':state.key==='bivariate'?'Frequent mental distress distribution':'Displayed tract distribution';
    $('histNote').textContent=`${fmt(values.length,0)} unweighted tract values. Selected tract: dark line${state.comparison?', comparison: orange dashed line':''}. Values beyond color limits are collected in edge bars.`;
  }
  function download(rows, filename) {
    const blob=new Blob(['\uFEFF'+d3.csvFormat(rows)],{type:'text/csv;charset=utf-8'});
    const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function exportRows(features) {
    return features.map(f=>{
      const row={...f.properties,atlas_version:config.version,OSM_snapshot:'2022-12-31T23:59:59Z',OSM_attribution:'OpenStreetMap contributors',OSM_data_license:'ODbL1.0',OSM_license_url:'https://www.openstreetmap.org/copyright',PLACES_release:2024,health_reference_year:2022,ACS_period:'2018-2022',health_estimate_type:'CDC PLACES modeled adult prevalence',GEOID_text:"'"+f.properties.GEOID,countyfips_text:"'"+f.properties.countyfips};
      if (state.view==='scenario') {const s=scenario(f),model=config.models[state.scenario.model];Object.assign(row,{scenario_model:state.scenario.model,scenario_kind:state.scenario.kind,scenario_amount:state.scenario.amount,scenario_target_cafes_per_10k:s.target,scenario_exposure_difference_log2:s.dx,scenario_within_observed_density_range:s.supported,scenario_target_above_p99:s.aboveP99,scenario_count_bounded_at_zero:s.clippedAtZero,scenario_association_contrast_pp:s.supported?s.contrast:null,scenario_coefficient_only_ci_lower_pp:s.supported?s.lower:null,scenario_coefficient_only_ci_upper_pp:s.supported?s.upper:null,scenario_coefficient_beta:model.beta,scenario_interpretation:'Conditional cafe-term association contrast; not intervention or health prevalence prediction'});}
      return row;
    });
  }
  function zoomToSelected() {
    const [[x0,y0],[x1,y1]]=path.bounds(state.selected),scale=Math.min(35,.8/Math.max((x1-x0)/width,(y1-y0)/height));
    svg.call(zoom.transform,d3.zoomIdentity.translate(width/2,height/2).scale(scale).translate(-(x0+x1)/2,-(y0+y1)/2));
  }
  function setView(view) {
    state.view=view;
    $('dataView').setAttribute('aria-pressed',String(view==='data'));
    $('scenarioView').setAttribute('aria-pressed',String(view==='scenario'));
    $('metricField').hidden=view==='scenario';
    $('scenarioControls').hidden=view!=='scenario';
    render();
  }
  $('county').addEventListener('change',()=>render(true));
  $('metric').addEventListener('change',()=>render());
  $('tractPicker').addEventListener('change',()=>select(byId.get($('tractPicker').value)));
  $('dataView').onclick=()=>setView('data');
  $('scenarioView').onclick=()=>setView('scenario');
  $('find').onclick=()=>{
    const id=$('tractSearch').value.trim(),f=byId.get(id);
    if (!/^\d{11}$/.test(id)||!f) {$('mapStatus').textContent='This 11-digit GEOID is not in the included analytical sample.';return;}
    $('county').value=f.properties.countyfips;state.selected=f;render(true);zoomToSelected();
  };
  $('tractSearch').addEventListener('keydown',e=>{if(e.key==='Enter') $('find').click();});
  $('prevTract').onclick=()=>select(state.shown[(state.shown.indexOf(state.selected)-1+state.shown.length)%state.shown.length]);
  $('nextTract').onclick=()=>select(state.shown[(state.shown.indexOf(state.selected)+1)%state.shown.length]);
  $('compare').onclick=()=>{state.comparison=state.selected;select(state.selected);};
  $('clearCompare').onclick=()=>{state.comparison=null;select(state.selected);};
  $('reset').onclick=()=>svg.call(zoom.transform,d3.zoomIdentity);
  $('zoomIn').onclick=()=>svg.call(zoom.scaleBy,1.6);
  $('zoomOut').onclick=()=>svg.call(zoom.scaleBy,1/1.6);
  $('zoomSelected').onclick=zoomToSelected;
  $('export').onclick=()=>download(exportRows(state.shown),`cafe_atlas_${state.view}_${state.county}.csv`);
  $('exportSelected').onclick=()=>download(exportRows([state.selected]),`cafe_atlas_${state.view}_${state.selected.properties.GEOID}.csv`);
  function readScenario() {
    const value=$('scenarioAmount').value;
    if (value===''||!Number.isFinite(Number(value))) return;
    const kind=$('scenarioKind').value;
    const amount=kind==='count'?Math.round(Math.max(-20,Math.min(20,Number(value)))):Math.max(-100,Math.min(500,Number(value)));
    $('scenarioAmount').value=amount;
    state.scenario={model:$('scenarioModel').value,kind,amount};
    render();
  }
  $('scenarioModel').onchange=readScenario;
  $('scenarioKind').onchange=()=>{
    const percent=$('scenarioKind').value==='percent';
    $('scenarioAmount').min=percent?-100:-20;$('scenarioAmount').max=percent?500:20;$('scenarioAmount').step=percent?5:1;
    $('scenarioAmount').value=percent?25:1;
    $('amountLabel').textContent=percent?'Availability change in each tract (%)':'Mapped cafes added to each tract';
    $('amountNote').textContent=percent?'Choose −100% to +500%. Zero-density tracts stay at zero. The density multiplier does not specify integer establishments.':'Choose −20 to +20 cafes per tract. Counts are bounded at zero; negative inputs remove counts in the algebraic scenario.';
    readScenario();
  };
  $('scenarioAmount').addEventListener('change',readScenario);
  $('scenarioAmount').addEventListener('input',readScenario);
  let resize;
  window.addEventListener('resize',()=>{clearTimeout(resize);resize=setTimeout(()=>render(true),120);});
  $('buildInfo').textContent=`Atlas ${config.version}, built from ${fmt(config.sample.tracts,0)} complete-case tracts, ${config.sample.counties} counties, ${fmt(config.sample.cafes,0)} own-tract mapped cafes and ${fmt(config.sample.residents,0)} ACS residents. Dataset fingerprints and build checks accompany the HTML.`;
  if (config.repository) {$('repositoryLine').hidden=false;$('repositoryLink').href=config.repository;}
  $('studySize').textContent=`${fmt(F.length,0)} tracts · ${counties.length} counties`;
  window.CAFE_ATLAS_QA=Object.freeze({version:config.version,features:F.length,counties:counties.length,metadata:config,scenarioFor:core.scenarioFor,exportRows,featuresData:F,state:()=>({view:state.view,county:state.county,key:state.key,shown:state.shown.length,selected:state.selected?.properties.GEOID,comparison:state.comparison?.properties.GEOID,scenario:{...state.scenario}})});
  try {render(true);} catch(error) {$('loadError').hidden=false;$('loadError').textContent='The atlas could not finish rendering. '+error.message;throw error;}
})();
