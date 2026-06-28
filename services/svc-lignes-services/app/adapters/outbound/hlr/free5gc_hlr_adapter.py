import requests


class Free5gcHlrAdapter:
    def __init__(self, base_url, username, password, plmn_id):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.plmn_id = plmn_id
        self._token = None

    def provision(self, line, trace_id=None):
        token = self._login(trace_id)
        headers = {"Token": token, "Content-Type": "application/json"}
        if trace_id:
            headers["TraceId"] = trace_id
        get_url = f"{self.base_url}/api/subscriber/{line.supi}/{self.plmn_id}"
        existing = requests.get(get_url, headers={"Token": token}, timeout=5)
        if existing.status_code == 200:
            if self._subscriber_is_complete(existing.json()):
                return True
            response = requests.put(get_url, headers=headers, json=self._subscriber_payload(line), timeout=10)
            if response.status_code not in {200, 201, 204}:
                raise RuntimeError(f"free5GC subscriber update failed: HTTP {response.status_code}")
            return True
        if existing.status_code not in {404, 400}:
            raise RuntimeError(f"free5GC subscriber lookup failed: HTTP {existing.status_code}")

        response = requests.post(get_url, headers=headers, json=self._subscriber_payload(line), timeout=10)
        if response.status_code not in {200, 201, 204}:
            raise RuntimeError(f"free5GC subscriber create failed: HTTP {response.status_code}")
        return True

    def _subscriber_is_complete(self, payload):
        auth = payload.get("AuthenticationSubscription") or {}
        access = payload.get("AccessAndMobilitySubscriptionData") or {}
        return bool(
            auth.get("authenticationMethod")
            and auth.get("permanentKey")
            and access.get("gpsis")
        )

    def _login(self, trace_id=None):
        if self._token:
            return self._token
        headers = {"Content-Type": "application/json"}
        if trace_id:
            headers["TraceId"] = trace_id
        response = requests.post(
            f"{self.base_url}/api/login",
            headers=headers,
            json={"username": self.username, "password": self.password},
            timeout=5,
        )
        if response.status_code != 200:
            raise RuntimeError(f"free5GC login failed: HTTP {response.status_code}")
        payload = response.json()
        self._token = payload.get("access_token") or payload.get("token")
        if not self._token:
            raise RuntimeError("free5GC login did not return a token")
        return self._token

    def _subscriber_payload(self, line):
        return {
            "plmnID": self.plmn_id,
            "ueId": line.supi,
            "AuthenticationSubscription": {
                "authenticationMethod": "5G_AKA",
                "permanentKey": {
                    "permanentKeyValue": "8baf473f2f8fd09487cccbd7097c6862",
                    "encryptionKey": 0,
                    "encryptionAlgorithm": 0,
                },
                "sequenceNumber": "16f3b3f70fc2",
                "authenticationManagementField": "8000",
                "milenage": {"op": {"opValue": "", "encryptionKey": 0, "encryptionAlgorithm": 0}},
                "opc": {
                    "opcValue": "8e27b6af0e692e750f32667a3b14605d",
                    "encryptionKey": 0,
                    "encryptionAlgorithm": 0,
                },
            },
            "AccessAndMobilitySubscriptionData": {
                "gpsis": [f"msisdn-{line.msisdn}"],
                "subscribedUeAmbr": {"uplink": "1 Gbps", "downlink": "2 Gbps"},
                "nssai": {
                    "defaultSingleNssais": [{"sst": 1, "sd": "010203"}],
                    "singleNssais": [{"sst": 1, "sd": "112233"}],
                },
            },
            "SessionManagementSubscriptionData": [
                {
                    "singleNssai": {"sst": 1, "sd": "010203"},
                    "dnnConfigurations": {
                        "internet": {
                            "sscModes": {"defaultSscMode": "SSC_MODE_1", "allowedSscModes": ["SSC_MODE_2", "SSC_MODE_3"]},
                            "pduSessionTypes": {"defaultSessionType": "IPV4", "allowedSessionTypes": ["IPV4"]},
                            "sessionAmbr": {"uplink": "200 Mbps", "downlink": "100 Mbps"},
                            "5gQosProfile": {"5qi": 9, "arp": {"priorityLevel": 8, "preemptCap": "", "preemptVuln": ""}, "priorityLevel": 8},
                        }
                    },
                }
            ],
            "SmfSelectionSubscriptionData": {"subscribedSnssaiInfos": {"01010203": {"dnnInfos": [{"dnn": "internet"}]}}},
            "AmPolicyData": {"subscCats": ["free5gc"]},
            "SmPolicyData": {
                "smPolicySnssaiData": {
                    "01010203": {
                        "snssai": {"sst": 1, "sd": "010203"},
                        "smPolicyDnnData": {"internet": {"dnn": "internet"}},
                    }
                }
            },
            "FlowRules": [],
            "QosFlows": [],
            "ChargingDatas": [],
        }
