package com.cantelcox.portabilityhubsync.web.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.time.OffsetDateTime;

public class CreatePortabilityOrderRequest {

    @NotBlank(message = "requestType is required")
    public String requestType;

    @NotBlank(message = "number is required")
    public String number;

    @NotBlank(message = "recipientOperator is required")
    public String recipientOperator;

    @NotBlank(message = "currentOperator is required")
    public String currentOperator;

    @NotNull(message = "customerInfo is required")
    @Valid
    public CustomerInfo customerInfo;

    @NotNull(message = "requestedPortDate is required")
    public OffsetDateTime requestedPortDate;
}
