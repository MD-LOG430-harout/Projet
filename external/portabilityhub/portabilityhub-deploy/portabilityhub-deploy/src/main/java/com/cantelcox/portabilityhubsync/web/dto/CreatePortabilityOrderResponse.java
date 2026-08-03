package com.cantelcox.portabilityhubsync.web.dto;

import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;

import java.time.OffsetDateTime;

public class CreatePortabilityOrderResponse {

    public String orderId;
    public PortabilityOrderStatus status;
    public OffsetDateTime createdAt;

    public CreatePortabilityOrderResponse() {}

    public CreatePortabilityOrderResponse(String orderId, PortabilityOrderStatus status, OffsetDateTime createdAt) {
        this.orderId = orderId;
        this.status = status;
        this.createdAt = createdAt;
    }
}
