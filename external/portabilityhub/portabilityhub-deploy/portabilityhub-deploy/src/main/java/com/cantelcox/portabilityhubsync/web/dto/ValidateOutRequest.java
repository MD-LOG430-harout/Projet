package com.cantelcox.portabilityhubsync.web.dto;

import jakarta.validation.constraints.NotBlank;

import java.time.OffsetDateTime;

public class ValidateOutRequest {

    @NotBlank(message = "status is required")
    public String status;

    public OffsetDateTime confirmedPortDate;
    public String rejectionReason;
    public String notes;
}
