package com.cantelcox.portabilityhubsync;

import com.cantelcox.portabilityhubsync.repository.HubRepository;
import com.cantelcox.portabilityhubsync.repository.OutboxEventRepository;
import com.cantelcox.portabilityhubsync.repository.PortabilityOrderRepository;
import com.cantelcox.portabilityhubsync.service.OutboxDispatcher;
import com.cantelcox.portabilityhubsync.simulator.SimulatorActivityLog;
import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;

import static org.hamcrest.Matchers.is;
import static org.hamcrest.Matchers.startsWith;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class PortabilityOrderFlowTest {

    private static final String ORDERS = "/portability/order";
    private static final String HUB = "/portability/hub";
    private static final String SIMULATOR = "/simulator/api";

    @Autowired private MockMvc mvc;
    @Autowired private ObjectMapper mapper;
    @Autowired private PortabilityOrderRepository orderRepository;
    @Autowired private HubRepository hubRepository;
    @Autowired private OutboxEventRepository outboxRepository;
    @Autowired private OutboxDispatcher outboxDispatcher;
    @Autowired private SimulatorActivityLog activityLog;

    @BeforeEach
    void reset() throws Exception {
        orderRepository.deleteAll();
        hubRepository.deleteAll();
        outboxRepository.deleteAll();
        activityLog.clear();
        registerSimulatorHubs();
    }

    private void dispatchOutbox() {
        outboxDispatcher.dispatchPending();
    }

    private void registerSimulatorHubs() throws Exception {
        mvc.perform(post(HUB)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "callback": "http://localhost/simulator/api/webhooks/bss1",
                                  "query": "PortabilityOrderStateChangeEvent",
                                  "@type": "Hub"
                                }
                                """))
                .andExpect(status().isCreated());

        mvc.perform(post(HUB)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "callback": "http://localhost/simulator/api/webhooks/bss2",
                                  "query": "PortabilityOrderOutValidationNeededEvent,PortabilityOrderStateChangeEvent",
                                  "@type": "Hub"
                                }
                                """))
                .andExpect(status().isCreated());
    }

    @Test
    void createValidateOutAndCompletePort() throws Exception {
        OffsetDateTime portDate = OffsetDateTime.now(ZoneOffset.UTC).withHour(0).withMinute(0).withSecond(0).withNano(0);
        String createBody = """
                {
                  "requestType": "port-in",
                  "number": "5145551234",
                  "recipientOperator": "BSS1",
                  "currentOperator": "BSS2",
                  "customerInfo": {
                    "name": "Pierre Gauthier",
                    "accountId": "CUST-98765"
                  },
                  "requestedPortDate": "%s"
                }
                """.formatted(portDate);

        mvc.perform(post(ORDERS)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(createBody))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.orderId", startsWith("PORT-")))
                .andExpect(jsonPath("$.status", is("pending_out_validation")));

        dispatchOutbox();

        String orderId = mapper.readTree(mvc.perform(get(SIMULATOR + "/pending-orders"))
                        .andReturn().getResponse().getContentAsString())
                .get(0).get("orderId").asText();

        assertTrue(activityLog.list().stream()
                .anyMatch(e -> EventNotification.OUT_VALIDATION_NEEDED.equals(e.label())));

        mvc.perform(post(ORDERS + "/" + orderId + "/validate-out")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "status": "approved",
                                  "confirmedPortDate": "%s",
                                  "rejectionReason": null,
                                  "notes": "Tout est conforme de notre côté"
                                }
                                """.formatted(portDate)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("port_completed")));

        dispatchOutbox();

        mvc.perform(get(ORDERS + "/" + orderId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("port_completed")));

        JsonNode activity = mapper.readTree(mvc.perform(get(SIMULATOR + "/activity"))
                .andReturn().getResponse().getContentAsString());

        assertTrue(streamContainsStateChange(activity, "approved"));
        assertTrue(streamContainsStateChange(activity, "port_completed"));
        assertTrue(webhookDateFieldsAreIsoStrings(activity));
    }

    private static boolean webhookDateFieldsAreIsoStrings(JsonNode activity) {
        for (JsonNode entry : activity) {
            JsonNode payload = entry.get("payload");
            if (payload == null || !payload.has("timeOccurred")) {
                continue;
            }
            String timeOccurred = payload.path("timeOccurred").asText();
            String eventTime = payload.path("eventTime").asText();
            return timeOccurred.contains("T")
                    && eventTime.contains("T")
                    && !timeOccurred.matches("^[0-9.]+$")
                    && !eventTime.matches("^[0-9.]+$");
        }
        return false;
    }

    @Test
    void listAllOrders() throws Exception {
        mvc.perform(get(ORDERS))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isArray())
                .andExpect(jsonPath("$.length()").value(0));

        mvc.perform(post(ORDERS)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "requestType": "port-in",
                                  "number": "5145550000",
                                  "recipientOperator": "BSS1",
                                  "currentOperator": "BSS2",
                                  "customerInfo": {
                                    "name": "List Test",
                                    "accountId": "CUST-LIST"
                                  },
                                  "requestedPortDate": "2026-07-21T12:00:00Z"
                                }
                                """))
                .andExpect(status().isCreated());

        mvc.perform(get(ORDERS))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1))
                .andExpect(jsonPath("$[0].status", is("pending_out_validation")));

        mvc.perform(get(ORDERS).param("status", "pending_out_validation"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(1));

        mvc.perform(get(ORDERS).param("status", "approved"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(0));
    }

    @Test
    void validateOutRejected() throws Exception {
        OffsetDateTime portDate = OffsetDateTime.now(ZoneOffset.UTC).plusDays(7).withHour(0).withMinute(0).withSecond(0).withNano(0);
        String createBody = """
                {
                  "requestType": "port-in",
                  "number": "5145559999",
                  "recipientOperator": "BSS1",
                  "currentOperator": "BSS2",
                  "customerInfo": {
                    "name": "Test User",
                    "accountId": "CUST-00001"
                  },
                  "requestedPortDate": "%s"
                }
                """.formatted(portDate);

        mvc.perform(post(ORDERS)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(createBody))
                .andExpect(status().isCreated());

        String orderId = mapper.readTree(mvc.perform(get(SIMULATOR + "/pending-orders"))
                        .andReturn().getResponse().getContentAsString())
                .get(0).get("orderId").asText();

        mvc.perform(post(ORDERS + "/" + orderId + "/validate-out")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "status": "rejected",
                                  "rejectionReason": "Account mismatch",
                                  "notes": "Invalid authorization"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status", is("rejected")));

        dispatchOutbox();

        JsonNode activity = mapper.readTree(mvc.perform(get(SIMULATOR + "/activity"))
                .andReturn().getResponse().getContentAsString());
        assertTrue(streamContainsStateChange(activity, "rejected"));
    }

    private static boolean streamContainsStateChange(JsonNode activity, String status) {
        for (JsonNode entry : activity) {
            JsonNode payload = entry.get("payload");
            if (payload != null
                    && EventNotification.STATE_CHANGE.equals(payload.path("eventType").asText())
                    && status.equals(payload.path("event").path("portabilityOrder").path("status").asText())) {
                return true;
            }
        }
        return false;
    }

    private static boolean streamContainsEvent(JsonNode activity, String eventType) {
        for (JsonNode entry : activity) {
            JsonNode payload = entry.get("payload");
            if (payload != null && eventType.equals(payload.path("eventType").asText())) {
                return true;
            }
        }
        return false;
    }
}
