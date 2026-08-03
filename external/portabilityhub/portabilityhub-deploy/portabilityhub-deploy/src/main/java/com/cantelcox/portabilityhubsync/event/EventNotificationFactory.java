package com.cantelcox.portabilityhubsync.event;

import com.cantelcox.portabilityhubsync.config.HubEventProperties;
import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;
import com.cantelcox.portabilityhubsync.web.dto.NumberPortabilityOrderView;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.format.DateTimeFormatter;
import java.util.UUID;

@Component
public class EventNotificationFactory {

    private static final DateTimeFormatter EVENT_ID_DATE = DateTimeFormatter.BASIC_ISO_DATE;

    private final HubEventProperties hubEventProperties;

    public EventNotificationFactory(HubEventProperties hubEventProperties) {
        this.hubEventProperties = hubEventProperties;
    }

    public EventNotification outValidationNeeded(NumberPortabilityOrderView order) {
        EventNotification notification = hubOrderEvent(order, EventNotification.OUT_VALIDATION_NEEDED);
        notification.title = "Validation OUT requise";
        notification.description = "Le BSS donneur doit valider la portabilité";
        notification.priority = "2";
        notification.timeOccurred = coalesce(order.createdAt, order.lastUpdate);
        return notification;
    }

    public EventNotification stateChange(NumberPortabilityOrderView order) {
        EventNotification notification = hubOrderEvent(order, EventNotification.STATE_CHANGE);
        notification.priority = "3";
        notification.timeOccurred = coalesce(order.lastUpdate, order.createdAt);

        if (order.status == PortabilityOrderStatus.APPROVED) {
            notification.title = "Portabilité approuvée";
            notification.description = "La validation OUT a été approuvée";
        } else if (order.status == PortabilityOrderStatus.REJECTED) {
            notification.title = "Portabilité refusée";
            notification.description = "La validation OUT a été refusée";
            notification.priority = "2";
        } else if (order.status == PortabilityOrderStatus.PORT_COMPLETED) {
            notification.title = "Portabilité terminée";
            notification.description = "Le transfert du numéro est complété";
        } else if (order.status == PortabilityOrderStatus.CANCELLED) {
            notification.title = "Portabilité annulée";
            notification.description = "L'ordre de portabilité a été annulé";
            notification.priority = "2";
        } else {
            notification.title = "Changement d'état de portabilité";
            notification.description = "L'ordre de portabilité a changé d'état";
        }
        return notification;
    }

    private EventNotification hubOrderEvent(NumberPortabilityOrderView order, String eventType) {
        OffsetDateTime now = OffsetDateTime.now();
        String base = hubEventProperties.trimBaseUrl();

        EventNotification notification = baseEnvelope(
                "evt-hub",
                eventType,
                businessEventId(),
                order.orderId,
                now,
                source("PortabilityHub", base));
        notification.event = new EventNotification.EventPayload();
        notification.event.portabilityOrder = toOrderRef(order, base);
        return notification;
    }

    private EventNotification baseEnvelope(String idPrefix,
                                           String eventType,
                                           String eventId,
                                           String correlationId,
                                           OffsetDateTime eventTime,
                                           EventSourceRef source) {
        String base = hubEventProperties.trimBaseUrl();
        String resourceId = resourceId(idPrefix);

        EventNotification notification = new EventNotification();
        notification.atType = eventType;
        notification.id = resourceId;
        notification.href = base + "/tmf-api/eventManagement/v4/event/" + resourceId;
        notification.eventId = eventId;
        notification.eventTime = eventTime;
        notification.eventType = eventType;
        notification.correlationId = correlationId;
        notification.domain = EventNotification.DOMAIN;
        notification.source = source;
        return notification;
    }

    private static EventSourceRef source(String id, String href) {
        EventSourceRef source = new EventSourceRef();
        source.id = id;
        source.href = href;
        return source;
    }

    private static PortabilityOrderEventRef toOrderRef(NumberPortabilityOrderView order, String base) {
        PortabilityOrderEventRef ref = new PortabilityOrderEventRef();
        ref.id = order.orderId;
        ref.href = base + "/portability/order/" + order.orderId;
        ref.number = order.number;
        ref.status = order.status != null ? order.status.getValue() : null;
        ref.recipientOperator = order.recipientOperator;
        ref.currentOperator = order.currentOperator;
        ref.requestedPortDate = order.requestedPortDate;
        ref.confirmedPortDate = order.confirmedPortDate;
        ref.rejectionReason = order.rejectionReason;
        if (order.customerInfo != null) {
            ref.applyCustomerInfo(order.customerInfo);
        }
        return ref;
    }

    private static String resourceId(String prefix) {
        return prefix + "-" + UUID.randomUUID().toString().substring(0, 6);
    }

    private static String businessEventId() {
        String date = LocalDate.now().format(EVENT_ID_DATE);
        String suffix = UUID.randomUUID().toString().substring(0, 3).toUpperCase();
        return "PORT-EVT-" + date + "-" + suffix;
    }

    private static OffsetDateTime coalesce(OffsetDateTime primary, OffsetDateTime fallback) {
        return primary != null ? primary : fallback != null ? fallback : OffsetDateTime.now();
    }
}
