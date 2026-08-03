package com.cantelcox.portabilityhubsync.web.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

/** TMF Hub resource returned after registering an event subscription. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Hub {

    public String id;
    public String href;
    public String callback;
    public String query;

    @JsonProperty("@type")
    public String atType = "Hub";
}
