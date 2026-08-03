package com.cantelcox.portabilityhubsync.web.dto;

import jakarta.validation.constraints.NotBlank;

public class CustomerInfo {

    @NotBlank(message = "customerInfo.name is required")
    public String name;

    @NotBlank(message = "customerInfo.accountId is required")
    public String accountId;
}
