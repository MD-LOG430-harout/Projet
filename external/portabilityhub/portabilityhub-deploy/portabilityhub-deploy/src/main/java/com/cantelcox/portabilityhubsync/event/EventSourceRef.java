package com.cantelcox.portabilityhubsync.event;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;

@JsonInclude(JsonInclude.Include.NON_NULL)
public class EventSourceRef {

    @JsonProperty("@type")
    public String atType = "EntityRef";

    public String id;
    public String href;

    @JsonProperty("@referredType")
    public String referredType = "Application";
}
