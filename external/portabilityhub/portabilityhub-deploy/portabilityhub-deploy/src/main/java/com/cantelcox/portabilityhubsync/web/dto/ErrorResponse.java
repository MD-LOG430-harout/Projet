package com.cantelcox.portabilityhubsync.web.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/** TMF standard Error structure. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ErrorResponse {
    public String code;
    public String reason;
    public String message;
    public String status;
    public String referenceError;

    @JsonProperty("@type")
    public String atType = "Error";

    public ErrorResponse() {}

    public ErrorResponse(String code, String reason, String message, String status) {
        this.code = code;
        this.reason = reason;
        this.message = message;
        this.status = status;
    }
}
