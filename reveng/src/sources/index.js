'use strict';
// Keyless public-data adapters. Each returns Signal[]: {source,url,title,text,date,metrics}. Response shapes follow the public docs;
// they are tested against local fixtures (shape parsing), NOT live (egress closed in build env).
const q = encodeURIComponent;
const A = {
  hackernews: { urlFor: (query, o) => `${o.base || 'https://hn.algolia.com'}/api/v1/search?query=${q(query)}&tags=story&hitsPerPage=${o.limit || 10}`,
    parse: (j) => (j.hits || []).map(h => ({ source: 'hackernews', url: h.url || `https://news.ycombinator.com/item?id=${h.objectID}`, title: h.title || '', text: h.story_text || '', date: h.created_at || null, metrics: { points: h.points, comments: h.num_comments } })) },
  github: { urlFor: (query, o) => `${o.base || 'https://api.github.com'}/search/repositories?q=${q(query)}&sort=stars&per_page=${o.limit || 10}`,
    parse: (j) => (j.items || []).map(r => ({ source: 'github', url: r.html_url, title: r.full_name, text: r.description || '', date: r.pushed_at || null, metrics: { stars: r.stargazers_count, forks: r.forks_count } })) },
  stackexchange: { urlFor: (query, o) => `${o.base || 'https://api.stackexchange.com'}/2.3/search/advanced?order=desc&sort=votes&q=${q(query)}&site=${o.site || 'stackoverflow'}&pagesize=${o.limit || 10}`,
    parse: (j) => (j.items || []).map(i => ({ source: 'stackexchange', url: i.link, title: i.title, text: '', date: i.creation_date ? new Date(i.creation_date * 1000).toISOString() : null, metrics: { score: i.score, views: i.view_count, answers: i.answer_count } })) },
  npm: { urlFor: (query, o) => `${o.base || 'https://registry.npmjs.org'}/-/v1/search?text=${q(query)}&size=${o.limit || 10}`,
    parse: (j) => (j.objects || []).map(o => ({ source: 'npm', url: `https://www.npmjs.com/package/${o.package.name}`, title: o.package.name, text: o.package.description || '', date: o.package.date || null, metrics: { score: o.score && o.score.final } })) },
  steam: { urlFor: (query, o) => `${o.base || 'https://store.steampowered.com'}/api/storesearch/?term=${q(query)}&cc=us&l=en`,
    parse: (j) => (j.items || []).slice(0, 10).map(i => ({ source: 'steam', url: `https://store.steampowered.com/app/${i.id}`, title: i.name, text: '', date: null, metrics: { price_cents: i.price && i.price.final, metascore: i.metascore } })) },
  itunes: { urlFor: (query, o) => `${o.base || 'https://itunes.apple.com'}/search?term=${q(query)}&entity=software&limit=${o.limit || 10}`,
    parse: (j) => (j.results || []).map(r => ({ source: 'itunes', url: r.trackViewUrl, title: r.trackName, text: r.description ? String(r.description).slice(0, 300) : '', date: r.currentVersionReleaseDate || null, metrics: { price: r.price, rating: r.averageUserRating, ratings: r.userRatingCount } })) },
};
async function collect(fetcher, plan, opts = {}) {
  // plan: [{source, query}] ; opts.bases: {source: baseUrlOverride}
  const out = [], errors = [];
  for (const p of plan) {
    const a = A[p.source]; if (!a) { errors.push({ ...p, error: 'unknown_source' }); continue; }
    const url = a.urlFor(p.query, { base: (opts.bases || {})[p.source], limit: opts.limit });
    const r = await fetcher.get(url, { headers: p.source === 'github' && process.env.GITHUB_TOKEN ? { Authorization: 'Bearer ' + process.env.GITHUB_TOKEN } : {} });
    if (!r.ok) { errors.push({ ...p, url, error: r.error || 'http_' + r.status }); continue; }
    try { for (const s of a.parse(JSON.parse(r.body.toString('utf8')))) out.push({ ...s, query: p.query, fetched_at: new Date(r.fetchedAt).toISOString() }); }
    catch (e) { errors.push({ ...p, url, error: 'parse:' + e.message }); }
  }
  return { signals: out, errors };
}
module.exports = { collect, ADAPTERS: A };
