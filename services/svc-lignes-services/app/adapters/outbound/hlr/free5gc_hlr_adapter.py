import time

import requests

from services.shared.tracing import traceparent_from_trace_id


class HlrProvisioningError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class Free5gcHlrAdapter:
    def __init__(
        self,
        base_url,
        username,
        password,
        plmn_id,
        permanent_key,
        opc,
        sequence_number,
        amf="8000",
        timeout_seconds=3,
        max_attempts=3,
        session=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.plmn_id = plmn_id
        self.permanent_key = permanent_key
        self.opc = opc
        self.sequence_number = sequence_number
        self.amf = amf
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.session = session or requests.Session()
        self._token = None

    def provision(self, line, trace_id=None, traceparent=None):
        traceparent = traceparent or traceparent_from_trace_id(trace_id)
        expected = self._subscriber_payload(line)
        token = self._login(traceparent)
        url = f"{self.base_url}/api/subscriber/{line.supi}/{self.plmn_id}"
        response = self._request("GET", url, traceparent, token=token)
        if response.status_code == 401:
            self._token = None
            token = self._login(traceparent)
            response = self._request("GET", url, traceparent, token=token)
        if response.status_code == 200:
            if self._subscriber_matches(response.json(), expected):
                return {"hlrReference": line.supi, "created": False}
            raise HlrProvisioningError(
                "SUBSCRIBER_CONFLICT",
                "existing free5GC subscriber conflicts with the required profile",
            )
        if response.status_code not in {400, 404}:
            raise HlrProvisioningError("SUBSCRIBER_LOOKUP_FAILED", f"free5GC lookup HTTP {response.status_code}")
        response = self._request("POST", url, traceparent, token=token, json=expected)
        if response.status_code not in {200, 201, 204}:
            raise HlrProvisioningError("SUBSCRIBER_CREATE_FAILED", f"free5GC create HTTP {response.status_code}")
        return {"hlrReference": line.supi, "created": True}

    def _login(self, traceparent):
        if self._token:
            return self._token
        response = self._request(
            "POST",
            f"{self.base_url}/api/login",
            traceparent,
            json={"username": self.username, "password": self.password},
        )
        if response.status_code != 200:
            raise HlrProvisioningError("LOGIN_FAILED", f"free5GC login HTTP {response.status_code}")
        self._token = response.json().get("access_token") or response.json().get("token")
        if not self._token:
            raise HlrProvisioningError("LOGIN_FAILED", "free5GC login did not return a token")
        return self._token

    def _request(self, method, url, traceparent, token=None, json=None):
        headers = {"Content-Type": "application/json", "traceparent": traceparent}
        if token:
            headers["Token"] = token
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.request(method, url, headers=headers, json=json, timeout=self.timeout_seconds)
            except requests.RequestException as exc:
                if attempt == self.max_attempts:
                    raise HlrProvisioningError("NETWORK_FAILURE", "free5GC request failed") from exc
            else:
                if response.status_code < 500 or attempt == self.max_attempts:
                    return response
            time.sleep(min(0.25 * (2 ** (attempt - 1)), 1.0))
        raise HlrProvisioningError("NETWORK_FAILURE", "free5GC retry budget exhausted")

    def _subscriber_matches(self, actual, expected):
        actual_auth = actual.get("AuthenticationSubscription") or {}
        expected_auth = expected["AuthenticationSubscription"]
        actual_access = actual.get("AccessAndMobilitySubscriptionData") or {}
        expected_access = expected["AccessAndMobilitySubscriptionData"]
        return (
            actual.get("ueId") in {None, expected["ueId"]}
            and actual_auth.get("authenticationMethod") == expected_auth["authenticationMethod"]
            and (actual_auth.get("permanentKey") or {}).get("permanentKeyValue")
            == expected_auth["permanentKey"]["permanentKeyValue"]
            and (actual_auth.get("opc") or {}).get("opcValue") == expected_auth["opc"]["opcValue"]
            and actual_access.get("gpsis") == expected_access["gpsis"]
        )

    def _subscriber_payload(self, line):
        return {
            "plmnID": self.plmn_id,
            "ueId": line.supi,
            "AuthenticationSubscription": {
                "authenticationMethod": "5G_AKA",
                "permanentKey": {"permanentKeyValue": self.permanent_key, "encryptionKey": 0, "encryptionAlgorithm": 0},
                "sequenceNumber": self.sequence_number,
                "authenticationManagementField": self.amf,
                "milenage": {"op": {"opValue": "", "encryptionKey": 0, "encryptionAlgorithm": 0}},
                "opc": {"opcValue": self.opc, "encryptionKey": 0, "encryptionAlgorithm": 0},
            },
            "AccessAndMobilitySubscriptionData": {
                "gpsis": [f"msisdn-{line.msisdn}"],
                "subscribedUeAmbr": {"uplink": "1 Gbps", "downlink": "2 Gbps"},
                "nssai": {"defaultSingleNssais": [{"sst": 1, "sd": "010203"}], "singleNssais": [{"sst": 1, "sd": "112233"}]},
            },
            "SessionManagementSubscriptionData": [],
            "SmfSelectionSubscriptionData": {},
            "AmPolicyData": {"subscCats": ["free5gc"]},
            "SmPolicyData": {},
            "FlowRules": [],
            "QosFlows": [],
            "ChargingDatas": [],
        }
