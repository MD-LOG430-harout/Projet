import { Counter, Rate } from 'k6/metrics';
import { bootstrap, orderRequest } from './lib.js';
const accepted = new Counter('accepted_commands'); const success = new Rate('acceptance_success');
export const options = { scenarios: { steady: { executor: 'constant-arrival-rate', rate: Number(__ENV.RATE || 50), timeUnit: '1s', duration: __ENV.DURATION || '2m', preAllocatedVUs: 100, maxVUs: 500 } } };
export function setup() { return bootstrap(); }
export default function (data) { const r = orderRequest(data, { test: 'failure_recovery' }); success.add(r.valid); if (r.valid) accepted.add(1); }
