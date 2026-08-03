package com.cantelcox.portabilityhubsync.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "portabilityhubsync.simulator")
public class SimulatorProperties {

    private boolean enabled = false;
    private String publicBaseUrl = "http://localhost:8082";
    private boolean useBssGateway = false;
    private String bss1GatewayPublicUrl = "http://localhost:8291";
    private String bss2GatewayPublicUrl = "http://localhost:8292";
    private String bss1GatewayInternalUrl = "http://localhost:8291";
    private String bss2GatewayInternalUrl = "http://localhost:8292";

    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }

    public String getPublicBaseUrl() { return publicBaseUrl; }
    public void setPublicBaseUrl(String publicBaseUrl) { this.publicBaseUrl = publicBaseUrl; }

    public boolean isUseBssGateway() { return useBssGateway; }
    public void setUseBssGateway(boolean useBssGateway) { this.useBssGateway = useBssGateway; }

    public String getBss1GatewayPublicUrl() { return bss1GatewayPublicUrl; }
    public void setBss1GatewayPublicUrl(String bss1GatewayPublicUrl) { this.bss1GatewayPublicUrl = bss1GatewayPublicUrl; }

    public String getBss2GatewayPublicUrl() { return bss2GatewayPublicUrl; }
    public void setBss2GatewayPublicUrl(String bss2GatewayPublicUrl) { this.bss2GatewayPublicUrl = bss2GatewayPublicUrl; }

    public String getBss1GatewayInternalUrl() { return bss1GatewayInternalUrl; }
    public void setBss1GatewayInternalUrl(String bss1GatewayInternalUrl) { this.bss1GatewayInternalUrl = bss1GatewayInternalUrl; }

    public String getBss2GatewayInternalUrl() { return bss2GatewayInternalUrl; }
    public void setBss2GatewayInternalUrl(String bss2GatewayInternalUrl) { this.bss2GatewayInternalUrl = bss2GatewayInternalUrl; }

    public String bss1WebhookCallbackUrl() {
        return trimTrailingSlash(useBssGateway ? bss1GatewayInternalUrl : publicBaseUrl)
                + (useBssGateway ? "/webhooks/portability" : "/simulator/api/webhooks/bss1");
    }

    public String bss2WebhookCallbackUrl() {
        return trimTrailingSlash(useBssGateway ? bss2GatewayInternalUrl : publicBaseUrl)
                + (useBssGateway ? "/webhooks/portability" : "/simulator/api/webhooks/bss2");
    }

    public String bss1WebhookPublicUrl() {
        return trimTrailingSlash(useBssGateway ? bss1GatewayPublicUrl : publicBaseUrl)
                + (useBssGateway ? "/webhooks/portability" : "/simulator/api/webhooks/bss1");
    }

    public String bss2WebhookPublicUrl() {
        return trimTrailingSlash(useBssGateway ? bss2GatewayPublicUrl : publicBaseUrl)
                + (useBssGateway ? "/webhooks/portability" : "/simulator/api/webhooks/bss2");
    }

    private static String trimTrailingSlash(String url) {
        return url == null ? "" : url.replaceAll("/$", "");
    }
}
