package com.cantelcox.portabilityhubbssgateway.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "bssgateway")
public class BssGatewayProperties {

    private String backendHost = "http://localhost:8082";
    private String backendPath = "/simulator/api/webhooks/bss1";
    private String operator = "BSS1";
    private Jwt jwt = new Jwt();

    public String getBackendHost() { return backendHost; }
    public void setBackendHost(String backendHost) { this.backendHost = backendHost; }

    public String getBackendPath() { return backendPath; }
    public void setBackendPath(String backendPath) { this.backendPath = backendPath; }

    public String getOperator() { return operator; }
    public void setOperator(String operator) { this.operator = operator; }

    public Jwt getJwt() { return jwt; }
    public void setJwt(Jwt jwt) { this.jwt = jwt; }

    public static class Jwt {
        private String hubPublicKeyLocation = "classpath:jwt/hub-webhook-public.pem";
        private String expectedIssuer = "PortabilityHub";
        private String expectedAudience = "portability-webhook";

        public String getHubPublicKeyLocation() { return hubPublicKeyLocation; }
        public void setHubPublicKeyLocation(String hubPublicKeyLocation) { this.hubPublicKeyLocation = hubPublicKeyLocation; }

        public String getExpectedIssuer() { return expectedIssuer; }
        public void setExpectedIssuer(String expectedIssuer) { this.expectedIssuer = expectedIssuer; }

        public String getExpectedAudience() { return expectedAudience; }
        public void setExpectedAudience(String expectedAudience) { this.expectedAudience = expectedAudience; }
    }
}
