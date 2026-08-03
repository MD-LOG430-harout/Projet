package com.cantelcox.portabilityhubgateway.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "portabilityhubgateway")
public class GatewayProperties {

    private String hubUri = "http://localhost:8082";
    private boolean devTokenEnabled;
    private long devTokenTtlSeconds = 3600;
    private Jwt jwt = new Jwt();

    public String getHubUri() { return hubUri; }
    public void setHubUri(String hubUri) { this.hubUri = hubUri; }

    public boolean isDevTokenEnabled() { return devTokenEnabled; }
    public void setDevTokenEnabled(boolean devTokenEnabled) { this.devTokenEnabled = devTokenEnabled; }

    public long getDevTokenTtlSeconds() { return devTokenTtlSeconds; }
    public void setDevTokenTtlSeconds(long devTokenTtlSeconds) { this.devTokenTtlSeconds = devTokenTtlSeconds; }

    public Jwt getJwt() { return jwt; }
    public void setJwt(Jwt jwt) { this.jwt = jwt; }

    public static class Jwt {
        private String publicKeyLocation = "classpath:jwt/hub-gateway-public.pem";
        private String privateKeyLocation = "classpath:jwt/hub-gateway-private.pem";

        public String getPublicKeyLocation() { return publicKeyLocation; }
        public void setPublicKeyLocation(String publicKeyLocation) { this.publicKeyLocation = publicKeyLocation; }

        public String getPrivateKeyLocation() { return privateKeyLocation; }
        public void setPrivateKeyLocation(String privateKeyLocation) { this.privateKeyLocation = privateKeyLocation; }
    }
}
