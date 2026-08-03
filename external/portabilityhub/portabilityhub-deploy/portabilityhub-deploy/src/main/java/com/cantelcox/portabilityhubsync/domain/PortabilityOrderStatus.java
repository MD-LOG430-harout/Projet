package com.cantelcox.portabilityhubsync.domain;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;

public enum PortabilityOrderStatus {
    PENDING_OUT_VALIDATION("pending_out_validation"),
    APPROVED("approved"),
    REJECTED("rejected"),
    PORT_COMPLETED("port_completed"),
    CANCELLED("cancelled");

    private final String value;

    PortabilityOrderStatus(String value) {
        this.value = value;
    }

    @JsonValue
    public String getValue() {
        return value;
    }

    @JsonCreator
    public static PortabilityOrderStatus fromValue(String value) {
        if (value == null || value.isBlank()) {
            return null;
        }
        for (PortabilityOrderStatus status : values()) {
            if (status.value.equalsIgnoreCase(value)) {
                return status;
            }
        }
        throw new IllegalArgumentException("Unknown portability order status: " + value);
    }
}
