/* Pure numerical functions shared by the offline atlas and its Node checks. */
(function (root) {
  'use strict';
  function scenarioFor(properties, settings, models, support) {
    if (['E_TOTPOP', 'cafe_count', 'cafe_per_10k'].some(key => properties[key] === null || properties[key] === undefined || properties[key] === '')) return null;
    if (!['count', 'percent'].includes(settings.kind) || settings.amount === null || settings.amount === undefined || settings.amount === '') return null;
    const population = Number(properties.E_TOTPOP);
    const count = Number(properties.cafe_count);
    const base = Number(properties.cafe_per_10k);
    const model = models[settings.model];
    if (![population, count, base].every(Number.isFinite) || !(population > 0) || !(base >= 0) || !(count >= 0) || !model) return null;
    const amount = Number(settings.amount);
    if (!Number.isFinite(amount)) return null;
    const requestedCount = settings.kind === 'count' ? count + amount : null;
    const target = amount === 0 ? base : settings.kind === 'count'
      ? Math.max(0, requestedCount) / population * 10000
      : base * Math.max(0, 1 + amount / 100);
    const dx = Math.log2(1 + target) - Math.log2(1 + base);
    const ends = [model.lower * dx, model.upper * dx].map(value => value === 0 ? 0 : value).sort((a, b) => a - b);
    const supported = target >= support.min && target <= support.max;
    return {
      baseline: base, target, dx,
      contrast: dx === 0 ? 0 : model.beta * dx,
      lower: ends[0], upper: ends[1],
      supported,
      aboveP99: target > support.p99,
      clippedAtZero: requestedCount !== null && requestedCount < 0,
      targetCount: settings.kind === 'count' ? Math.max(0, requestedCount) : null
    };
  }
  function percentile(sorted, value) {
    if (!Number.isFinite(value) || !sorted.length) return null;
    let lo = 0, hi = sorted.length;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (sorted[mid] <= value) lo = mid + 1;
      else hi = mid;
    }
    return lo / sorted.length * 100;
  }
  const api = Object.freeze({scenarioFor, percentile});
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.CafeAtlasCore = api;
})(typeof window === 'object' ? window : globalThis);
