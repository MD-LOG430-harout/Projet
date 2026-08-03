package com.cantelcox.portabilityhubsync.web.dto;

import com.cantelcox.portabilityhubsync.domain.PortabilityOrderStatus;

import java.time.OffsetDateTime;

public class NumberPortabilityOrderView {

    public String orderId;
    public String requestType;
    public String number;
    public String recipientOperator;
    public String currentOperator;
    public CustomerInfo customerInfo;
    public OffsetDateTime requestedPortDate;
    public PortabilityOrderStatus status;
    public OffsetDateTime confirmedPortDate;
    public String rejectionReason;
    public String notes;
    public OffsetDateTime createdAt;
    public OffsetDateTime lastUpdate;
}
