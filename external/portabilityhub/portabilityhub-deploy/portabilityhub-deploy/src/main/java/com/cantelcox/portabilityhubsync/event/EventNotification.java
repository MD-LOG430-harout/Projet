package com.cantelcox.portabilityhubsync.event;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

/** TMF Event Management v4 notification emitted by the Hub (webhooks). */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EventNotification {

    public static final String BASE_TYPE = "Event";
    public static final String OUT_VALIDATION_NEEDED = "PortabilityOrderOutValidationNeededEvent";
    public static final String STATE_CHANGE = "PortabilityOrderStateChangeEvent";
    public static final String DOMAIN = "portability";

    @JsonProperty("@type")
    public String atType;

    @JsonProperty("@baseType")
    public String atBaseType = BASE_TYPE;

    public String id;
    public String href;
    public String eventId;
    public OffsetDateTime eventTime;
    public String eventType;
    public String correlationId;
    public String domain;
    public String title;
    public String description;
    public String priority;
    public OffsetDateTime timeOccurred;
    public EventSourceRef source;
    public EventPayload event;

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public static class EventPayload {
        public PortabilityOrderEventRef portabilityOrder;
    }
}
