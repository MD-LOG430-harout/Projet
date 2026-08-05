import http from 'k6/http';
import { check } from 'k6';
import { Counter } from 'k6/metrics';

export const BASE_URL = __ENV.BASE_URL || 'http://api-gateway';
export const OFFER_ID = __ENV.OFFER_ID || 'forfait-5g-20gb';
export const requestsStarted = new Counter('requests_started');
export const requestsCompleted = new Counter('requests_completed');
export const status202 = new Counter('status_202');
export const status400 = new Counter('status_400');
export const status401403 = new Counter('status_401_403');
export const status409 = new Counter('status_409');
export const status429 = new Counter('status_429');
export const status500 = new Counter('status_500');
export const status502 = new Counter('status_502');
export const status503 = new Counter('status_503');
export const status504 = new Counter('status_504');
export const otherStatus = new Counter('status_other');
export const clientTimeouts = new Counter('client_timeouts');
export const connectionFailures = new Counter('connection_failures');

export function unique(prefix = 'p2') {
  const vu = typeof __VU === 'undefined' ? 0 : __VU;
  const iter = typeof __ITER === 'undefined' ? 0 : __ITER;
  return `${prefix}-${vu}-${iter}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function bootstrap() {
  const suffix = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const email = `phase2-${suffix}@example.test`;
  const password = 'Stronger123';
  const register = http.post(`${BASE_URL}/v1/customers/register`, JSON.stringify({
    email, password, displayName: 'Phase 2 Test', legalName: 'Phase 2 Test',
    address: { line1: '123 Rue Test', city: 'Montreal', province: 'QC', postalCode: 'H1A1A1' },
    identityDocument: { type: 'driver_license', number: `P2-${suffix}` }, customerType: 'individual',
  }), { headers: { 'Content-Type': 'application/json', TraceId: unique('register') } });
  if (register.status !== 201) throw new Error(`registration failed: ${register.status} ${register.body}`);
  const customerId = register.json('customerId');
  const login = http.post(`${BASE_URL}/v1/auth/login`, JSON.stringify({ email, password }), {
    headers: { 'Content-Type': 'application/json', TraceId: unique('login') },
  });
  if (login.status !== 202) throw new Error(`login failed: ${login.status} ${login.body}`);
  const verify = http.post(`${BASE_URL}/v1/auth/mfa/verify`, JSON.stringify({
    challengeId: login.json('challengeId'), otp: login.json('devOtp'),
  }), { headers: { 'Content-Type': 'application/json', TraceId: unique('mfa') } });
  if (verify.status !== 200) throw new Error(`MFA failed: ${verify.status} ${verify.body}`);
  const data = { customerId, token: verify.json('sessionToken') };
  if ((__ENV.WARMUP_CACHE || 'true').toLowerCase() === 'true') {
    orderRequest(data, { test: 'warmup' });
  }
  return data;
}

export function orderRequest(data, tags = {}) {
  const key = unique('order');
  requestsStarted.add(1);
  const response = http.post(`${BASE_URL}/v1/orders`, JSON.stringify({
    customerId: data.customerId, offerId: OFFER_ID, quantity: 1, orderType: 'NEW_PLAN', numberMode: 'NEW',
  }), { headers: {
    'Content-Type': 'application/json', Authorization: `Bearer ${data.token}`,
    'Idempotency-Key': key, TraceId: unique('trace'),
  }, tags, timeout: __ENV.REQUEST_TIMEOUT || '30s' });
  requestsCompleted.add(1);
  if (response.status === 202) status202.add(1);
  else if (response.status === 400) status400.add(1);
  else if (response.status === 401 || response.status === 403) status401403.add(1);
  else if (response.status === 409) status409.add(1);
  else if (response.status === 429) status429.add(1);
  else if (response.status === 500) status500.add(1);
  else if (response.status === 502) status502.add(1);
  else if (response.status === 503) status503.add(1);
  else if (response.status === 504) status504.add(1);
  else if (response.status === 0) {
    const error = String(response.error || 'network error').toLowerCase();
    if (error.includes('timeout') || error.includes('deadline')) clientTimeouts.add(1);
    else connectionFailures.add(1);
  } else otherStatus.add(1);
  let body = {};
  try { body = response.json() || {}; } catch (_) { body = {}; }
  const valid = check(response, {
    'status is 202': (r) => r.status === 202,
    'order identifier returned': () => Boolean(body.orderId),
    'saga identifier returned': () => Boolean(body.sagaId),
    'initial state is asynchronous': () => body.status === 'EN_COURS',
  });
  const vu = typeof __VU === 'undefined' ? 0 : __VU;
  const iter = typeof __ITER === 'undefined' ? 0 : __ITER;
  if (!valid && vu <= 2 && iter < 3) {
    console.error(JSON.stringify({ sample: 'order_failure', status: response.status, error: response.error || null, errorCode: response.error_code || null, body: String(response.body || '').slice(0, 500) }));
  }
  return { response, valid, orderId: body.orderId, sagaId: body.sagaId, key };
}

export function authHeaders(data) {
  return { Authorization: `Bearer ${data.token}`, TraceId: unique('poll') };
}
