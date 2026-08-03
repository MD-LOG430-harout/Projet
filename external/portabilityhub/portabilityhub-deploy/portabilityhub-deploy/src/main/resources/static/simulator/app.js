(() => {
  const ORDER_PATH = '/portability/order';
  const HUB_PATH = '/portability/hub';
  const SIM_API = '/simulator/api';

  let simulatorConfig = null;
  let selectedOrderId = null;
  let hubRegistrations = { bss1Registered: false, bss2Registered: false };

  const $ = (id) => document.getElementById(id);

  function hubGatewayBase() {
    return ($('hubGatewayBase').value || simulatorConfig?.hubGatewayUrl || window.location.origin).replace(/\/$/, '');
  }

  function ordersUrl(path = '') {
    return `${hubGatewayBase()}${ORDER_PATH}${path}`;
  }

  function hubUrl() {
    return `${hubGatewayBase()}${HUB_PATH}`;
  }

  function simUrl(path) {
    return `${hubGatewayBase()}${SIM_API}${path}`;
  }

  function toast(msg, type = 'success') {
    const el = $('toast');
    el.textContent = msg;
    el.className = `toast ${type}`;
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.add('hidden'), 4000);
  }

  async function fetchJson(url, options = {}) {
    const { headers: optionHeaders, ...rest } = options;
    const res = await fetch(url, {
      ...rest,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...optionHeaders,
      },
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status} ${res.statusText}: ${text || url}`);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  async function fetchWithOperator(operator, url, options = {}) {
    return fetchJson(url, {
      ...options,
      headers: {
        ...options.headers,
        'X-Simulator-Party': operator,
      },
    });
  }

  function pretty(obj) {
    if (typeof obj === 'string') {
      try { return JSON.stringify(JSON.parse(obj), null, 2); } catch { return obj; }
    }
    return JSON.stringify(obj, null, 2);
  }

  function todayDateTimeLocal() {
    const now = new Date();
    now.setSeconds(0, 0);
    return toDateTimeLocalValue(now);
  }

  function toDateTimeLocalValue(date) {
    const pad = (n) => String(n).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
  }

  function dateTimeLocalToIso(value) {
    if (!value) return new Date().toISOString();
    return new Date(value).toISOString();
  }

  function formatDateTime(value) {
    if (!value) return '—';
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
  }

  function orderCreateBody() {
    return {
      requestType: 'port-in',
      number: $('phone').value.trim(),
      recipientOperator: 'BSS1',
      currentOperator: $('currentOperator').value.trim(),
      customerInfo: {
        name: $('customerName').value.trim(),
        accountId: $('accountId').value.trim(),
      },
      requestedPortDate: dateTimeLocalToIso($('requestedPortDate').value),
    };
  }

  function updateBssAStatus(order) {
    $('hubOrderId').textContent = order.orderId || '—';
    const stateEl = $('hubOrderState');
    stateEl.textContent = order.status || '—';
    stateEl.className = 'state ' + (order.status || '');
    $('hubOrderPhone').textContent = order.number || '—';
    $('hubConfirmedDate').textContent = formatDateTime(order.confirmedPortDate);
  }

  function updateHubRegistrationUi() {
    updateActorStatus('bss1HubStatus', hubRegistrations.bss1Registered, 'BSS1');
    updateActorStatus('bss2HubStatus', hubRegistrations.bss2Registered, 'BSS2');
    $('btnSubmitOrder').disabled = !hubRegistrations.bss1Registered || !hubRegistrations.bss2Registered;
  }

  function updateActorStatus(elementId, registered, label) {
    const el = $(elementId);
    if (!el) return;
    el.innerHTML = `
      <span class="status-dot ${registered ? 'ok' : 'pending'}"></span>
      <span>Abonnement Hub ${label} : ${registered ? 'enregistré' : 'non enregistré'}</span>
    `;
  }

  async function loadSimulatorConfig() {
    simulatorConfig = await fetchJson(simUrl('/config'));
    if ($('hubGatewayBase').value === '' || $('hubGatewayBase').dataset.auto === 'true') {
      $('hubGatewayBase').value = simulatorConfig.hubGatewayUrl || window.location.origin;
    }
    updateEndpointUrls();
    updateGatewayBanner();
  }

  function updateGatewayBanner() {
    const banner = $('statusBanner');
    if (!simulatorConfig) return;
    const parts = [
      `Hub GW → ${simulatorConfig.hubGatewayUrl}`,
      simulatorConfig.useBssGateway
        ? `BSS1 GW ${simulatorConfig.bss1GatewayUrl} · BSS2 GW ${simulatorConfig.bss2GatewayUrl}`
        : 'Webhooks directs (sans BSS Gateway)',
    ];
    banner.textContent = parts.join(' · ');
    banner.className = 'status-banner ok';
  }

  async function refreshHubRegistrations() {
    try {
      hubRegistrations = await fetchJson(simUrl('/hub-registrations'));
    } catch {
      hubRegistrations = { bss1Registered: false, bss2Registered: false };
    }
    updateHubRegistrationUi();
  }

  function updateEndpointUrls() {
    const cfg = simulatorConfig;
    $('hubGatewayDisplay').textContent = hubGatewayBase();
    $('bss1GatewayDisplay').textContent = cfg?.bss1GatewayUrl || '—';
    $('bss2GatewayDisplay').textContent = cfg?.bss2GatewayUrl || '—';
    $('bssAApiUrl').textContent = ordersUrl();
    $('validateOutUrl').textContent = ordersUrl('/{orderId}/validate-out');
    $('hubSubscriptionUrl').textContent = hubUrl();
    $('bss1WebhookUrl').textContent = cfg?.bss1WebhookUrl || '—';
    $('bss2WebhookUrl').textContent = cfg?.bss2WebhookUrl || '—';
    $('bss1ListenerUrl').textContent = cfg?.bss1ListenerUrl || '—';
    $('bss2ListenerUrl').textContent = cfg?.bss2ListenerUrl || '—';
  }

  async function simulateWebhook(operator) {
    const result = await fetchJson(simUrl(`/simulate-webhook/${operator.toLowerCase()}`), { method: 'POST' });
    toast(`Webhook ${result.eventType} simulé vers ${result.operator} (via BSS GW)`);
    refreshTimeline();
    return result;
  }

  async function simulateAllWebhooks() {
    const results = await fetchJson(simUrl('/simulate-webhooks'), { method: 'POST' });
    toast(`Webhooks simulés : BSS1 (${results.bss1.eventType}) · BSS2 (${results.bss2.eventType})`);
    refreshTimeline();
    return results;
  }

  async function registerAllHubs() {
    await registerSingleHub('BSS1');
    await registerSingleHub('BSS2');
    toast('Abonnements Hub BSS1 + BSS2 enregistrés (via Hub Gateway)');
  }

  async function registerSingleHub(party) {
    if (party === 'all') return registerAllHubs();

    const callback = party === 'BSS1'
      ? (simulatorConfig?.bss1HubCallback)
      : (simulatorConfig?.bss2HubCallback);
    const query = party === 'BSS1'
      ? 'PortabilityOrderStateChangeEvent'
      : 'PortabilityOrderOutValidationNeededEvent,PortabilityOrderStateChangeEvent';

    await fetchWithOperator(party, hubUrl(), {
      method: 'POST',
      body: JSON.stringify({ callback, query, '@type': 'Hub' }),
    });

    await refreshHubRegistrations();
    await refreshTimeline();
    toast(`Abonnement Hub ${party} enregistré via Hub Gateway`);
  }

  function orderIdOrError() {
    const id = $('hubOrderId').textContent;
    if (!id || id === '—') throw new Error('Créez un ordre d\'abord');
    return id;
  }

  async function refreshOrder() {
    const order = await fetchWithOperator('BSS1', ordersUrl('/' + orderIdOrError()));
    updateBssAStatus(order);
    return order;
  }

  async function submitOrder() {
    if (!hubRegistrations.bss1Registered || !hubRegistrations.bss2Registered) {
      throw new Error('Enregistrez d\'abord les abonnements Hub (BSS1 + BSS2)');
    }
    const created = await fetchWithOperator('BSS1', ordersUrl(), {
      method: 'POST',
      body: JSON.stringify(orderCreateBody()),
    });

    $('hubOrderId').textContent = created.orderId;
    $('hubOrderState').textContent = created.status;
    $('hubOrderState').className = 'state ' + created.status;
    toast(`Ordre créé via Hub Gateway: ${created.orderId}`);
    refreshPendingOrders();
    refreshTimeline();
  }

  async function refreshPendingOrders() {
    const orders = await fetchJson(simUrl('/pending-orders'));
    const container = $('pendingOrders');

    if (!orders.length) {
      container.className = 'donor-list empty';
      container.textContent = 'Aucune demande en attente…';
      $('respondForm').classList.add('hidden');
      return;
    }

    container.className = 'donor-list';
    container.innerHTML = orders.map((o) => `
      <div class="donor-card ${o.orderId === selectedOrderId ? 'selected' : ''}" data-id="${o.orderId}">
        <div class="title">${escapeHtml(o.number)} · ${escapeHtml(o.status)}</div>
        <div class="meta">${escapeHtml(o.orderId)} · ${escapeHtml(o.customerName || '')}</div>
        <div class="meta">${escapeHtml(o.recipientOperator)} ← ${escapeHtml(o.currentOperator)}</div>
      </div>
    `).join('');

    container.querySelectorAll('.donor-card').forEach((card) => {
      card.addEventListener('click', () => selectOrder(card.dataset.id, orders));
    });

    if (selectedOrderId && orders.some((o) => o.orderId === selectedOrderId)) {
      selectOrder(selectedOrderId, orders);
    }
  }

  function selectOrder(id, orders) {
    selectedOrderId = id;
    const order = orders.find((o) => o.orderId === id);
    if (!order) return;

    $('selectedOrderId').value = id;
    $('selectedOrderSummary').textContent = `${order.number} · ${order.orderId}`;
    $('respondForm').classList.remove('hidden');
    $('confirmedPortDate').value = $('requestedPortDate').value || todayDateTimeLocal();

    document.querySelectorAll('.donor-card').forEach((c) => {
      c.classList.toggle('selected', c.dataset.id === id);
    });
  }

  function toggleValidationFields() {
    const approved = $('validationStatus').value === 'approved';
    $('confirmedDateField').classList.toggle('hidden', !approved);
    $('rejectionField').classList.toggle('hidden', approved);
  }

  async function validateOut(e) {
    e.preventDefault();
    const orderId = $('selectedOrderId').value;
    if (!orderId) return;

    const approved = $('validationStatus').value === 'approved';
    const body = {
      status: $('validationStatus').value,
      notes: $('validationNotes').value.trim(),
      rejectionReason: approved ? null : $('rejectionReason').value.trim(),
      confirmedPortDate: approved ? dateTimeLocalToIso($('confirmedPortDate').value) : null,
    };

    const order = await fetchWithOperator('BSS2', ordersUrl(`/${orderId}/validate-out`), {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if ($('hubOrderId').textContent === orderId) {
      updateBssAStatus(order);
    }

    toast(`Validate-out via Hub Gateway: ${order.status}`);
    refreshPendingOrders();
    refreshTimeline();
  }

  function eventClass(label) {
    const l = String(label || '');
    if (l.includes('PortabilityOrderOutValidationNeededEvent')) return 'evt-out';
    if (l.includes('PortabilityOrderStateChangeEvent')) return 'evt-approved';
    if (l.includes('Hub subscription') || l.includes('/portability/hub')) return 'evt-hub';
    if (l.includes('Created') || l.includes('/portability/order')) return 'evt-order';
    if (l.includes('validate-out')) return 'evt-validate';
    if (l.includes('BSS Gateway')) return 'evt-gateway';
    if (l.includes('Hub Gateway')) return 'evt-gateway';
    return 'evt-default';
  }

  function eventChip(label, payload) {
    const cls = eventClass(label);
    let text = label;
    if (payload?.eventType === 'PortabilityOrderStateChangeEvent') {
      const status = payload?.event?.portabilityOrder?.status;
      if (status) text = `${label} · ${status}`;
    }
    return `<span class="event-chip ${cls}">${escapeHtml(text)}</span>`;
  }

  function partyClass(party) {
    if (party === 'BSS1') return 'party-bss1';
    if (party === 'BSS2') return 'party-bss2';
    return 'party-hub';
  }

  function renderEventEntry(e) {
    return `
      <div class="log-entry">
        <div class="head">
          <span class="direction ${partyClass(e.fromParty)}">${escapeHtml(e.fromParty)} → ${escapeHtml(e.toParty)}</span>
          <span>${new Date(e.timestamp).toLocaleTimeString()}</span>
        </div>
        <div class="entry-label">${eventChip(e.label, e.payload)}</div>
        ${e.payload ? `<pre>${escapeHtml(pretty(e.payload))}</pre>` : ''}
      </div>
    `;
  }

  function renderEventList(containerId, entries, emptyText) {
    const el = $(containerId);
    if (!entries.length) {
      el.className = 'event-log empty';
      el.textContent = emptyText;
      return;
    }
    el.className = 'event-log';
    el.innerHTML = entries.slice().reverse().map(renderEventEntry).join('');
  }

  function stateInPayload(payload, status) {
    if (typeof payload === 'string') {
      try { payload = JSON.parse(payload); } catch { return false; }
    }
    return payload?.event?.portabilityOrder?.status === status
      || payload?.status === status;
  }

  function updateFlowSteps(entries) {
    const labels = entries.map((e) => String(e.label || '')).join(' ');
    const steps = {
      hub: hubRegistrations.bss1Registered && hubRegistrations.bss2Registered,
      create: labels.includes('/portability/order') || labels.includes('Created'),
      'out-needed': labels.includes('PortabilityOrderOutValidationNeededEvent'),
      validate: labels.includes('validate-out'),
      approved: entries.some((e) => stateInPayload(e.payload, 'approved') || stateInPayload(e.payload, 'port_completed')),
      completed: entries.some((e) => stateInPayload(e.payload, 'port_completed')),
    };

    document.querySelectorAll('.flow-step').forEach((step) => {
      const key = step.dataset.step;
      step.classList.toggle('done', !!steps[key]);
      step.classList.toggle('active', !!steps[key] && key === lastActiveStep(steps));
    });
  }

  function lastActiveStep(steps) {
    const order = ['completed', 'approved', 'validate', 'out-needed', 'create', 'hub'];
    return order.find((k) => steps[k]) || 'hub';
  }

  function renderTimeline(entries) {
    const el = $('timeline');
    if (!entries.length) {
      el.className = 'timeline empty';
      el.textContent = 'Aucun événement — enregistrez les abonnements Hub puis créez un ordre port-in.';
      return;
    }
    el.className = 'timeline';
    el.innerHTML = entries.slice().reverse().map((e) => `
      <article class="timeline-entry ${partyClass(e.fromParty)}">
        <div class="timeline-meta">
          <time>${new Date(e.timestamp).toLocaleTimeString()}</time>
          <span class="timeline-route">${escapeHtml(e.fromParty)} → ${escapeHtml(e.toParty)}</span>
        </div>
        <div class="timeline-body">
          ${eventChip(e.label, e.payload)}
          ${e.payload ? `<pre>${escapeHtml(pretty(e.payload))}</pre>` : ''}
        </div>
      </article>
    `).join('');
  }

  async function refreshTimeline() {
    const entries = await fetchJson(simUrl('/activity'));
    renderEventList('bssAEventsReceived', entries.filter((e) => e.toParty === 'BSS1'), 'Aucun webhook BSS1.');
    renderEventList('bssBEventsReceived', entries.filter((e) => e.toParty === 'BSS2'), 'Aucun webhook BSS2.');
    renderTimeline(entries);
    updateFlowSteps(entries);
    await refreshHubRegistrations();
  }

  function resetUiDefaults() {
    $('hubGatewayBase').value = window.location.origin;
    $('hubGatewayBase').dataset.auto = 'true';
    $('phone').value = '5145551234';
    $('currentOperator').value = 'BSS2';
    $('customerName').value = 'Pierre Gauthier';
    $('accountId').value = 'CUST-98765';
    $('requestedPortDate').value = todayDateTimeLocal();
    $('validationStatus').value = 'approved';
    $('validationNotes').value = 'Tout est conforme de notre côté';
    toggleValidationFields();
    updateEndpointUrls();
  }

  async function resetSimulator() {
    await fetchJson(simUrl('/reset'), { method: 'DELETE' });
    selectedOrderId = null;
    hubRegistrations = { bss1Registered: false, bss2Registered: false };
    resetUiDefaults();
    $('hubOrderId').textContent = '—';
    $('hubOrderState').textContent = '—';
    $('hubOrderState').className = 'state';
    $('hubOrderPhone').textContent = '—';
    $('hubConfirmedDate').textContent = '—';
    $('respondForm').classList.add('hidden');
    updateHubRegistrationUi();
    await loadSimulatorConfig();
    refreshPendingOrders();
    refreshTimeline();
    toast('Simulateur réinitialisé');
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function setStatus(message, ok) {
    const banner = $('statusBanner');
    banner.textContent = message;
    banner.className = 'status-banner ' + (ok ? 'ok' : 'error');
  }

  async function init() {
    $('requestedPortDate').value = todayDateTimeLocal();
    $('confirmedPortDate').value = todayDateTimeLocal();
    $('validationStatus').addEventListener('change', toggleValidationFields);
    toggleValidationFields();

    $('hubGatewayBase').addEventListener('input', () => {
      $('hubGatewayBase').dataset.auto = 'false';
      updateEndpointUrls();
    });
    $('hubGatewayBase').addEventListener('change', updateEndpointUrls);

    $('btnRegisterAllHubs').addEventListener('click', () => registerAllHubs().catch((e) => toast(e.message, 'error')));
    $('btnRegisterBss1').addEventListener('click', () => registerSingleHub('BSS1').catch((e) => toast(e.message, 'error')));
    $('btnRegisterBss2').addEventListener('click', () => registerSingleHub('BSS2').catch((e) => toast(e.message, 'error')));
    $('btnSimulateBss1Webhook').addEventListener('click', () => simulateWebhook('BSS1').catch((e) => toast(e.message, 'error')));
    $('btnSimulateBss2Webhook').addEventListener('click', () => simulateWebhook('BSS2').catch((e) => toast(e.message, 'error')));
    $('btnSimulateAllWebhooks').addEventListener('click', () => simulateAllWebhooks().catch((e) => toast(e.message, 'error')));
    $('btnSubmitOrder').addEventListener('click', () => submitOrder().catch((e) => toast(e.message, 'error')));
    $('btnRefreshOrder').addEventListener('click', () => refreshOrder().then(() => toast('Statut rafraîchi')).catch((e) => toast(e.message, 'error')));
    $('btnRefreshTimeline').addEventListener('click', () => refreshTimeline().catch((e) => toast(e.message, 'error')));
    $('btnClearEvents').addEventListener('click', () => fetchJson(simUrl('/activity'), { method: 'DELETE' }).then(refreshTimeline));
    $('btnReset').addEventListener('click', () => resetSimulator().catch((e) => toast(e.message, 'error')));
    $('respondForm').addEventListener('submit', (e) => validateOut(e).catch((err) => toast(err.message, 'error')));

    try {
      resetUiDefaults();
      await loadSimulatorConfig();
      await refreshHubRegistrations();
      setStatus('Chargement…', true);
      refreshPendingOrders();
      refreshTimeline();
      setInterval(() => {
        refreshPendingOrders().catch(() => {});
        refreshTimeline().catch(() => {});
      }, 2500);
    } catch (e) {
      setStatus('Simulateur indisponible — lancez docker compose ou Hub + gateways.', false);
      toast(e.message || 'Simulateur indisponible', 'error');
    }
  }

  init();
})();
