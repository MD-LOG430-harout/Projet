package com.cantelcox.portabilityhubsync.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "portabilityhubsync.hub")
public class HubEventProperties {

    private String publicBaseUrl = "http://localhost:8082";

    public String getPublicBaseUrl() {
        return publicBaseUrl;
    }

    public void setPublicBaseUrl(String publicBaseUrl) {
        this.publicBaseUrl = publicBaseUrl;
    }

    public String trimBaseUrl() {
        return publicBaseUrl == null ? "" : publicBaseUrl.replaceAll("/$", "");
    }
}
