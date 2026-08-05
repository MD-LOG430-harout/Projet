import { Counter, Rate, Trend } from 'k6/metrics';
import { bootstrap, orderRequest } from './lib.js';
const accepted = new Counter('accepted_commands'); const success = new Rate('acceptance_success'); const latency = new Trend('acceptance_latency', true);
const d = __ENV.STAGE_DURATION || '30s';
export const options = { scenarios: { load: { executor: 'ramping-arrival-rate', startRate: 50, timeUnit: '1s', preAllocatedVUs: Number(__ENV.VUS || 500), maxVUs: Number(__ENV.MAX_VUS || 3000), stages: [
  { target: 50, duration: d }, { target: 200, duration: d }, { target: 500, duration: d }, { target: 1000, duration: d }, { target: Number(__ENV.STRESS_RATE || 1200), duration: d }, { target: 50, duration: d },
] } }, thresholds: { acceptance_success: ['rate>=0.99'], http_req_failed: ['rate<0.01'] } };
export function setup() { return bootstrap(); }
export default function (data) { const r = orderRequest(data, { test: 'load_stages' }); latency.add(r.response.timings.duration); success.add(r.valid); if (r.valid) accepted.add(1); }
