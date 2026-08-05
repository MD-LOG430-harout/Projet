import { Counter, Rate, Trend } from 'k6/metrics';
import { bootstrap, orderRequest } from './lib.js';

const accepted = new Counter('accepted_commands');
const failed = new Counter('failed_commands');
const success = new Rate('acceptance_success');
const latency = new Trend('acceptance_latency', true);

export const options = {
  scenarios: { acceptance: { executor: 'constant-arrival-rate', rate: Number(__ENV.RATE || 50), timeUnit: '1s', duration: __ENV.DURATION || '30s', preAllocatedVUs: Number(__ENV.VUS || 500), maxVUs: Number(__ENV.MAX_VUS || 3000) } },
  thresholds: { acceptance_latency: ['p(95)<=250'], acceptance_success: ['rate>=0.99'], http_req_failed: ['rate<0.01'] },
};
export function setup() { return bootstrap(); }
export default function (data) {
  const result = orderRequest(data, { test: 'acceptance' });
  latency.add(result.response.timings.duration);
  success.add(result.valid); result.valid ? accepted.add(1) : failed.add(1);
}
