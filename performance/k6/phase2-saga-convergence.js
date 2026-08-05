import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';
import { sleep } from 'k6';
import { authHeaders, BASE_URL, bootstrap, orderRequest } from './lib.js';

const duration = new Trend('saga_convergence', true);
const initiated = new Counter('sagas_initiated'); const confirmed = new Counter('sagas_confirmed');
const cancelled = new Counter('sagas_cancelled'); const timedOut = new Counter('sagas_timed_out');
const unknown = new Counter('sagas_unknown'); const terminal = new Rate('saga_terminal_rate');
export const options = { vus: Number(__ENV.VUS || 10), iterations: Number(__ENV.ITERATIONS || 30), thresholds: { saga_convergence: ['p(95)<=3000'], saga_terminal_rate: ['rate==1'] } };
export function setup() { return bootstrap(); }
export default function (data) {
  const created = orderRequest(data, { test: 'saga' }); if (!created.valid) { terminal.add(false); return; }
  initiated.add(1); const started = Date.now(); const timeoutMs = Number(__ENV.SAGA_TIMEOUT_MS || 65000);
  while (Date.now() - started < timeoutMs) {
    const res = http.get(`${BASE_URL}/v1/orders/${created.orderId}/status`, { headers: authHeaders(data), tags: { test: 'saga_poll' } });
    if (res.status === 200) {
      const state = res.json('status');
      if (state === 'CONFIRMEE' || state === 'ANNULEE') {
        duration.add(Date.now() - started); terminal.add(true); state === 'CONFIRMEE' ? confirmed.add(1) : cancelled.add(1); return;
      }
      if (state !== 'EN_COURS') { unknown.add(1); terminal.add(false); return; }
    }
    sleep(Number(__ENV.POLL_SECONDS || 0.1));
  }
  timedOut.add(1); terminal.add(false);
}
