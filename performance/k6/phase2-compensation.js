import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';
import { sleep } from 'k6';
import { authHeaders, BASE_URL, bootstrap, orderRequest } from './lib.js';

const compensation = new Trend('compensation_duration', true); const compensated = new Counter('sagas_compensated'); const coherent = new Rate('compensation_coherent');
export const options = { vus: Number(__ENV.VUS || 5), iterations: Number(__ENV.ITERATIONS || 20), thresholds: { compensation_duration: ['p(95)<=5000'], compensation_coherent: ['rate==1'] } };
export function setup() { return bootstrap(); }
export default function (data) {
  const created = orderRequest(data, { test: 'compensation' }); if (!created.valid) { coherent.add(false); return; }
  const started = Date.now(); const timeoutMs = Number(__ENV.SAGA_TIMEOUT_MS || 65000);
  while (Date.now() - started < timeoutMs) {
    const res = http.get(`${BASE_URL}/v1/orders/${created.orderId}/status`, { headers: authHeaders(data) });
    if (res.status === 200 && res.json('status') === 'ANNULEE') { compensation.add(Date.now() - started); compensated.add(1); coherent.add(true); return; }
    if (res.status === 200 && res.json('status') === 'CONFIRMEE') { coherent.add(false); return; }
    sleep(0.1);
  }
  coherent.add(false);
}
