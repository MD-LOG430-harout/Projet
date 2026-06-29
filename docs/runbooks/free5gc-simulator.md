# free5GC Simulator Runbook

The free5GC simulator is currently provided under `docs/free5gc-udm-min-max (2)`. It should be reused for UC-03 activation provisioning instead of replacing it with a new fake simulator. UC-04 usage consultation is out of the official Phase 1 implementation scope.

## What It Contains

| Component | Purpose |
|---|---|
| MongoDB | Stores free5GC subscriber data and simulator-internal data |
| NRF/UDR/UDM | Reduced free5GC core for subscriber-data management |
| WebConsole | REST provisioning interface used by UC-03 |
| `usage-api` | Python FastAPI facade included in the simulator bundle, not used by the official Phase 1 CanTelcoX API because UC-04 is out of scope |
| `fournisseur` | Python `httpx[http2]` smoke test for UDM reads |

## Startup

After extracting the archive without changing its internal files:

```bash
cd <extracted-free5gc-folder>
docker compose -f docker-compose.udm-min.yaml up -d db nrf udr udm webui
```

Expected local ports:

```text
WebConsole: http://localhost:5050
UDM:        http://localhost:8000
usage-api:  http://localhost:8090  (simulator bundle only; not used by official Phase 1)
MongoDB:    mongodb://localhost:27017/free5gc
```

## UC-03 Adapter Calls

`svc-lignes-services` should call the simulator through outbound adapters:

1. Login:
   - `POST /api/login`
   - body: `{"username":"admin","password":"free5gc"}`
   - response contains `access_token` or `token`
   - subsequent WebConsole calls use header `Token: <jwt>`

2. Idempotent subscriber lookup:
   - `GET /api/subscriber/{supi}/{plmnId}`
   - `200`: subscriber exists, do not recreate
   - `404`: subscriber can be created

3. Subscriber provisioning:
   - `POST /api/subscriber/{supi}/{plmnId}`
   - `supi = imsi-<imsi>`
   - `plmnId = 20893`
   - include `gpsis: ["msisdn-<number>"]`

4. Optional UDM verification:
   - `GET /nudm-sdm/v2/{supi}/am-data?plmn-id={"mcc":"208","mnc":"93"}`
   - HTTP/2 cleartext is required
   - verification should be best-effort; provisioning success remains the activation gate

## Docker Compose Integration Options

Preferred Phase 1 path:

1. Extract the simulator archive into a stable folder such as `simulators/free5gc-udm-min-max/`.
2. Keep the simulator files unchanged.
3. Add a separate `docker-compose.free5gc.yml` or document a two-compose startup:
   - start free5GC simulator first,
   - start CanTelcoX with `docker compose up --build`.
4. Configure BSS services to call:
   - `FREE5GC_WEBUI_URL=http://host.docker.internal:5050`
   - `FREE5GC_UDM_URL=http://host.docker.internal:8000`

If both stacks are merged into one Compose project, services can use Docker service names instead of `host.docker.internal`.
