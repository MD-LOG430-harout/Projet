import { Counter, Rate, Trend } from 'k6/metrics';
import { bootstrap, orderRequest } from './lib.js';
const accepted = new Counter('accepted_commands'); const success = new Rate('acceptance_success'); const latency = new Trend('acceptance_latency', true);
export const options = { scenarios: { balance: { executor: 'constant-arrival-rate', rate: Number(__ENV.RATE || 100), timeUnit: '1s', duration: __ENV.DURATION || '60s', preAllocatedVUs: 200, maxVUs: 1000 } }, thresholds: { acceptance_success: ['rate>=0.99'] } };
export function setup() { return bootstrap(); }
export default function (data) { const r = orderRequest(data, { test: 'load_balancing' }); latency.add(r.response.timings.duration); success.add(r.valid); if (r.valid) accepted.add(1); }
