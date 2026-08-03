package com.cantelcox.portabilityhubsync.web.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;

/** TMF Hub_FVO — payload accepted when registering an event subscription. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class HubCreate {

    @NotBlank(message = "callback is required")
    public String callback;

    /** Optional filter: event name or comma-separated event names (blank = all events). */
    public String query;

    @JsonProperty("@type")
    public String atType = "Hub";
}
