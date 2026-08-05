import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';
import { BASE_URL, bootstrap, OFFER_ID, authHeaders } from './lib.js';
const hits = new Counter('cache_hits'); const misses = new Counter('cache_misses'); const hitRate = new Rate('cache_hit_rate'); const latency = new Trend('cache_latency', true);
export const options = { vus: Number(__ENV.VUS || 20), duration: __ENV.DURATION || '30s' };
export function setup() { return bootstrap(); }
export default function (data) { const r = http.get(`${BASE_URL}/v1/offers/${OFFER_ID}`, { headers: authHeaders(data), tags: { test: 'cache' } }); const value = r.headers['X-Cache']; const hit = value === 'HIT'; hitRate.add(hit); latency.add(r.timings.duration); hit ? hits.add(1) : misses.add(1); }
