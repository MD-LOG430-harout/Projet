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

## Manual Postman / curl Checks

The official CanTelcoX Postman collection does not expose the free5GC WebConsole subscriber endpoints directly. Those calls are normally made automatically by `svc-lignes-services` during UC-03 when `HLR_ENABLED=true`.

For manual free5GC checks, import the simulator collection:

```text
docs/free5gc-udm-min-max (2)/free5gc-udm-min-max/postman/webconsole-provisioning.postman_collection.json
```

Default WebConsole credentials for the provided simulator:

```text
username: admin
password: free5gc
```

Manual login:

```bash
curl -i -X POST http://localhost:5050/api/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"free5gc"}'
```

Copy the returned `access_token` or `token`, then call subscriber endpoints with:

```text
Token: <token>
Content-Type: application/json
```

Example lookup:

```bash
curl -i http://localhost:5050/api/subscriber/imsi-208930000000001/20893 \
  -H "Token: <token>"
```

If this returns `200`, the subscriber already exists. If it returns `404` or `400`, the adapter can create or complete it during activation.

Example minimal provisioning call:

```bash
curl -i -X POST http://localhost:5050/api/subscriber/imsi-208930000000001/20893 \
  -H "Token: <token>" \
  -H "Content-Type: application/json" \
  -d @subscriber-example.json
```

Prefer testing through CanTelcoX UC-03 instead of hand-crafting `subscriber-example.json`, because `Free5gcHlrAdapter` already sends the full payload expected by the WebConsole.

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
