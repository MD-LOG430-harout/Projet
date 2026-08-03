package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.cantelcox.portabilityhubsync.event.EventNotificationFactory;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import org.springframework.stereotype.Service;

import java.util.Arrays;

@Service
public class WebhookService {

    public static final String OUT_VALIDATION_NEEDED = EventNotification.OUT_VALIDATION_NEEDED;
    public static final String STATE_CHANGE = EventNotification.STATE_CHANGE;

    private final EventNotificationFactory eventFactory;
    private final OutboxService outboxService;

    public WebhookService(EventNotificationFactory eventFactory, OutboxService outboxService) {
        this.eventFactory = eventFactory;
        this.outboxService = outboxService;
    }

    public void notifyOutValidationNeeded(NumberPortabilityOrderView order) {
        EventNotification notification = eventFactory.outValidationNeeded(order);
        outboxService.enqueue(OUT_VALIDATION_NEEDED, notification);
    }

    public void notifyOrderApproved(NumberPortabilityOrderView order) {
        enqueueStateChange(order);
    }

    public void notifyOrderRejected(NumberPortabilityOrderView order) {
        enqueueStateChange(order);
    }

    public void notifyPortCompleted(NumberPortabilityOrderView order) {
        enqueueStateChange(order);
    }

    private void enqueueStateChange(NumberPortabilityOrderView order) {
        EventNotification notification = eventFactory.stateChange(order);
        outboxService.enqueue(STATE_CHANGE, notification);
    }

    static boolean matchesQuery(String query, String eventType) {
        if (query == null || query.isBlank()) {
            return true;
        }
        return Arrays.stream(query.split(","))
                .map(String::trim)
                .anyMatch(filter -> filter.equals(eventType));
    }
}
