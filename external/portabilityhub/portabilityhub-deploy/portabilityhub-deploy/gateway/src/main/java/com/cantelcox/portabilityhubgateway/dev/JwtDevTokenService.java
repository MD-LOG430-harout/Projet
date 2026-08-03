package com.cantelcox.portabilityhubgateway.dev;

import com.cantelcox.portabilityhubgateway.config.GatewayProperties;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;

import java.time.Instant;
import java.util.List;

public class JwtDevTokenService {

    private static final String ISSUER = "portability-hub-gateway";
    private static final String AUDIENCE = "portability-hub";

    private final JwtEncoder jwtEncoder;
    private final GatewayProperties properties;

    public JwtDevTokenService(JwtEncoder jwtEncoder, GatewayProperties properties) {
        this.jwtEncoder = jwtEncoder;
        this.properties = properties;
    }

    public DevTokenResponse issueToken(String operator) {
        Instant now = Instant.now();
        long ttl = properties.getDevTokenTtlSeconds();
        JwtClaimsSet claims = JwtClaimsSet.builder()
                .issuer(ISSUER)
                .subject(operator)
                .audience(List.of(AUDIENCE))
                .issuedAt(now)
                .expiresAt(now.plusSeconds(ttl))
                .claim("operator", operator)
                .build();
        String token = jwtEncoder.encode(JwtEncoderParameters.from(claims)).getTokenValue();
        return new DevTokenResponse(token, operator, ttl);
    }

    public record DevTokenResponse(String token, String operator, long expiresInSeconds) {}
}
