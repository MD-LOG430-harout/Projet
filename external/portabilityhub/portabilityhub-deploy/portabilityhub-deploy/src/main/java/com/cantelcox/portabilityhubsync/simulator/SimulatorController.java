package com.cantelcox.portabilityhubsync.simulator;

import com.cantelcox.portabilityhubsync.config.SimulatorProperties;
import com.cantelcox.portabilityhubsync.repository.OutboxEventRepository;
import com.cantelcox.portabilityhubsync.service.HubService;
import com.cantelcox.portabilityhubsync.service.PortabilityHubService;
import com.cantelcox.portabilityhubsync.service.PortabilityOrderService;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderRequest;
import com.cantelcox.portabilityhubsync.web.dto.CreatePortabilityOrderResponse;
import com.cantelcox.portabilityhubsync.web.dto.Hub;
import com.cantelcox.portabilityhubsync.web.dto.HubCreate;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import com.cantelcox.portabilityhubsync.web.dto.ValidateOutRequest;
import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.cantelcox.portabilityhubsync.event.EventNotificationFactory;
import com.cantelcox.portabilityhubsync.service.WebhookClient;
import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;
import com.cantelcox.portabilityhubsync.web.dto.CustomerInfo;
import jakarta.validation.Valid;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/simulator/api")
@ConditionalOnProperty(name = "portabilityhubsync.simulator.enabled", havingValue = "true")
public class SimulatorController {

    public record SimulatorConfig(
            String hubGatewayUrl,
            String hubOrderUrl,
            String hubSubscriptionUrl,
            String devTokenUrl,
            String bss1GatewayUrl,
            String bss2GatewayUrl,
            String bss1WebhookUrl,
            String bss2WebhookUrl,
            String bss1HubCallback,
            String bss2HubCallback,
            String bss1ListenerUrl,
            String bss2ListenerUrl,
            boolean useBssGateway,
            boolean devTokenEnabled) {}

    public record PendingOrderSummary(
            String orderId,
            String number,
            String recipientOperator,
            String currentOperator,
            String customerName,
            String status) {}

    public record HubRegistrationSummary(
            boolean bss1Registered,
            boolean bss2Registered,
            String bss1Callback,
            String bss2Callback) {}

    public record WebhookEndpointInfo(
            String operator,
            String publicWebhookUrl,
            String callbackUrl,
            String listenerPath,
            String defaultEventType) {}

    public record WebhookSimulationResult(
            String operator,
            String eventType,
            String publicWebhookUrl,
            String callbackUrl,
            String listenerPath,
            String status) {}

    private final SimulatorProperties properties;
    private final PortabilityOrderService orderService;
    private final PortabilityHubService hubService;
    private final HubService hubSubscriptionService;
    private final OutboxEventRepository outboxRepository;
    private final SimulatorActivityLog activityLog;
    private final WebhookClient webhookClient;
    private final EventNotificationFactory eventFactory;

    public SimulatorController(SimulatorProperties properties,
                               PortabilityOrderService orderService,
                               PortabilityHubService hubService,
                               HubService hubSubscriptionService,
                               OutboxEventRepository outboxRepository,
                               SimulatorActivityLog activityLog,
                               WebhookClient webhookClient,
                               EventNotificationFactory eventFactory) {
        this.properties = properties;
        this.orderService = orderService;
        this.hubService = hubService;
        this.hubSubscriptionService = hubSubscriptionService;
        this.outboxRepository = outboxRepository;
        this.activityLog = activityLog;
        this.webhookClient = webhookClient;
        this.eventFactory = eventFactory;
    }

    @GetMapping("/config")
    public SimulatorConfig config() {
        String hubGateway = trimTrailingSlash(properties.getPublicBaseUrl());
        return new SimulatorConfig(
                hubGateway,
                hubGateway + "/portability/order",
                hubGateway + "/portability/hub",
                hubGateway + "/gateway/dev/token",
                trimTrailingSlash(properties.getBss1GatewayPublicUrl()),
                trimTrailingSlash(properties.getBss2GatewayPublicUrl()),
                properties.bss1WebhookPublicUrl(),
                properties.bss2WebhookPublicUrl(),
                properties.bss1WebhookCallbackUrl(),
                properties.bss2WebhookCallbackUrl(),
                listenerPath("bss1"),
                listenerPath("bss2"),
                properties.isUseBssGateway(),
                false);
    }

    @GetMapping("/webhook-endpoints")
    public Map<String, WebhookEndpointInfo> webhookEndpoints() {
        return Map.of(
                "bss1", webhookEndpointInfo("BSS1"),
                "bss2", webhookEndpointInfo("BSS2"));
    }

    @PostMapping("/simulate-webhook/{operator}")
    public WebhookSimulationResult simulateWebhook(@PathVariable String operator,
                                                   @RequestParam(required = false) String eventType) {
        String normalized = normalizeOperator(operator);
        WebhookEndpointInfo endpoint = webhookEndpointInfo(normalized);
        EventNotification event = buildSimulationEvent(normalized, eventType, endpoint.defaultEventType());
        webhookClient.deliver(endpoint.callbackUrl(), event);
        return new WebhookSimulationResult(
                normalized,
                event.eventType,
                endpoint.publicWebhookUrl(),
                endpoint.callbackUrl(),
                endpoint.listenerPath(),
                "delivered");
    }

    @PostMapping("/simulate-webhooks")
    public Map<String, WebhookSimulationResult> simulateWebhooks() {
        return Map.of(
                "bss1", simulateWebhook("bss1", EventNotification.STATE_CHANGE),
                "bss2", simulateWebhook("bss2", EventNotification.OUT_VALIDATION_NEEDED));
    }

    @GetMapping("/hub-registrations")
    public HubRegistrationSummary hubRegistrations() {
        String bss1Callback = properties.bss1WebhookCallbackUrl();
        String bss2Callback = properties.bss2WebhookCallbackUrl();
        boolean bss1 = hubSubscriptionService.listCallbacks().contains(bss1Callback);
        boolean bss2 = hubSubscriptionService.listCallbacks().contains(bss2Callback);
        return new HubRegistrationSummary(bss1, bss2,
                properties.bss1WebhookPublicUrl(),
                properties.bss2WebhookPublicUrl());
    }

    @PostMapping("/register-hubs")
    public ResponseEntity<Map<String, Hub>> registerHubs() {
        String bss1Callback = properties.bss1WebhookCallbackUrl();
        String bss2Callback = properties.bss2WebhookCallbackUrl();

        HubCreate bss1Request = new HubCreate();
        bss1Request.callback = bss1Callback;
        bss1Request.query = "PortabilityOrderStateChangeEvent";

        HubCreate bss2Request = new HubCreate();
        bss2Request.callback = bss2Callback;
        bss2Request.query = "PortabilityOrderOutValidationNeededEvent,PortabilityOrderStateChangeEvent";

        activityLog.record("BSS1", "HUB", "POST /portability/hub", bss1Request);
        Hub bss1Hub = hubSubscriptionService.create(bss1Request);
        activityLog.record("HUB", "BSS1", "201 Hub subscription", bss1Hub);

        activityLog.record("BSS2", "HUB", "POST /portability/hub", bss2Request);
        Hub bss2Hub = hubSubscriptionService.create(bss2Request);
        activityLog.record("HUB", "BSS2", "201 Hub subscription", bss2Hub);

        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                "bss1", bss1Hub,
                "bss2", bss2Hub));
    }

    @PostMapping("/bss1/order")
    public ResponseEntity<CreatePortabilityOrderResponse> bss1CreateOrder(
            @Valid @RequestBody CreatePortabilityOrderRequest request) {
        activityLog.record("BSS1", "HUB", "POST /portability/order", request);
        CreatePortabilityOrderResponse response = hubService.createPortIn(request);
        activityLog.record("HUB", "BSS1", "201 Created · " + response.status.getValue(), response);
        return ResponseEntity.status(HttpStatus.CREATED).body(response);
    }

    @PostMapping("/bss2/order/{orderId}/validate-out")
    public NumberPortabilityOrderView bss2ValidateOut(@PathVariable String orderId,
                                                      @Valid @RequestBody ValidateOutRequest request) {
        activityLog.record("BSS2", "HUB", "POST /portability/order/" + orderId + "/validate-out", request);
        NumberPortabilityOrderView order = hubService.validateOut(orderId, request);
        activityLog.record("HUB", "BSS2", "200 Updated · " + order.status.getValue(), order);
        return order;
    }

    @GetMapping("/pending-orders")
    public List<PendingOrderSummary> pendingOrders() {
        return orderService.findByStatus(
                        com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus.PENDING_OUT_VALIDATION)
                .stream()
                .map(this::toSummary)
                .toList();
    }

    @PostMapping("/webhooks/{operator}")
    public ResponseEntity<Map<String, String>> receiveWebhook(@PathVariable String operator,
                                                              @RequestBody EventNotification payload) {
        String label = eventLabel(payload);
        if (properties.isUseBssGateway()) {
            label = label + " (via BSS Gateway)";
        }
        activityLog.record("HUB", operator.toUpperCase(), label, payload);
        return ResponseEntity.ok(Map.of("status", "ok"));
    }

    private static String eventLabel(Object payload) {
        if (payload instanceof EventNotification notification) {
            return notification.eventType;
        }
        if (payload instanceof java.util.Map<?, ?> map && map.get("eventType") != null) {
            return String.valueOf(map.get("eventType"));
        }
        return "Webhook received";
    }

    @GetMapping("/activity")
    public List<SimulatorActivityLog.ActivityEntry> activity() {
        return activityLog.list();
    }

    @DeleteMapping("/activity")
    public ResponseEntity<Void> clearActivity() {
        activityLog.clear();
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/complete-due-ports")
    public Map<String, Integer> completeDuePorts() {
        return Map.of("completed", hubService.completeDuePorts());
    }

    @DeleteMapping("/reset")
    public ResponseEntity<Void> reset() {
        orderService.deleteAll();
        hubSubscriptionService.deleteAll();
        outboxRepository.deleteAll();
        activityLog.clear();
        return ResponseEntity.noContent().build();
    }

    private PendingOrderSummary toSummary(NumberPortabilityOrderView order) {
        return new PendingOrderSummary(
                order.orderId,
                order.number,
                order.recipientOperator,
                order.currentOperator,
                order.customerInfo != null ? order.customerInfo.name : null,
                order.status != null ? order.status.getValue() : null);
    }

    private static String trimTrailingSlash(String url) {
        return url == null ? "" : url.replaceAll("/$", "");
    }

    private WebhookEndpointInfo webhookEndpointInfo(String operator) {
        boolean bss1 = "BSS1".equals(operator);
        return new WebhookEndpointInfo(
                operator,
                bss1 ? properties.bss1WebhookPublicUrl() : properties.bss2WebhookPublicUrl(),
                bss1 ? properties.bss1WebhookCallbackUrl() : properties.bss2WebhookCallbackUrl(),
                listenerPath(bss1 ? "bss1" : "bss2"),
                bss1 ? EventNotification.STATE_CHANGE : EventNotification.OUT_VALIDATION_NEEDED);
    }

    private static String listenerPath(String operatorKey) {
        return "/simulator/api/webhooks/" + operatorKey;
    }

    private static String normalizeOperator(String operator) {
        String normalized = operator == null ? "" : operator.trim().toUpperCase();
        if (!"BSS1".equals(normalized) && !"BSS2".equals(normalized)) {
            throw new IllegalArgumentException("Operator must be bss1 or bss2");
        }
        return normalized;
    }

    private EventNotification buildSimulationEvent(String operator, String requestedType, String defaultType) {
        String eventType = requestedType != null && !requestedType.isBlank() ? requestedType : defaultType;
        NumberPortabilityOrderView order = sampleOrder(operator);
        if (EventNotification.OUT_VALIDATION_NEEDED.equals(eventType)) {
            return eventFactory.outValidationNeeded(order);
        }
        if (EventNotification.STATE_CHANGE.equals(eventType)) {
            return eventFactory.stateChange(order);
        }
        throw new IllegalArgumentException("Unsupported eventType: " + eventType);
    }

    private static NumberPortabilityOrderView sampleOrder(String operator) {
        NumberPortabilityOrderView order = new NumberPortabilityOrderView();
        order.orderId = "PORT-SIM-" + operator;
        order.requestType = "port-in";
        order.number = "5145551234";
        order.recipientOperator = "BSS1";
        order.currentOperator = "BSS2";
        order.status = "BSS2".equals(operator)
                ? PortabilityOrderStatus.PENDING_OUT_VALIDATION
                : PortabilityOrderStatus.APPROVED;
        order.createdAt = OffsetDateTime.now();
        order.lastUpdate = OffsetDateTime.now();
        CustomerInfo customer = new CustomerInfo();
        customer.name = "Simulation webhook";
        customer.accountId = "SIM-WH";
        order.customerInfo = customer;
        return order;
    }
}
