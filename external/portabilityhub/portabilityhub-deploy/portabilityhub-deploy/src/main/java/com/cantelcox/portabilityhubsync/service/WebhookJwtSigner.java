package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.config.WebhookJwtProperties;
import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import com.nimbusds.jose.jwk.source.JWKSource;
import com.nimbusds.jose.proc.SecurityContext;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.stereotype.Component;
import org.springframework.util.FileCopyUtils;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.PKCS8EncodedKeySpec;
import java.security.spec.X509EncodedKeySpec;
import java.time.Instant;
import java.util.Base64;
import java.util.List;

@Component
@ConditionalOnProperty(name = "portabilityhubsync.webhook.jwt.enabled", havingValue = "true")
public class WebhookJwtSigner {

    private final WebhookJwtProperties properties;
    private final JwtEncoder jwtEncoder;

    public WebhookJwtSigner(WebhookJwtProperties properties, ResourceLoader resourceLoader) throws Exception {
        this.properties = properties;
        RSAPublicKey publicKey = loadPublicKey(resourceLoader, properties.getPublicKeyLocation());
        RSAPrivateKey privateKey = loadPrivateKey(resourceLoader, properties.getPrivateKeyLocation());
        RSAKey rsaKey = new RSAKey.Builder(publicKey)
                .privateKey(privateKey)
                .keyID("hub-webhook")
                .build();
        JWKSource<SecurityContext> jwkSource = new ImmutableJWKSet<>(new com.nimbusds.jose.jwk.JWKSet(rsaKey));
        this.jwtEncoder = new NimbusJwtEncoder(jwkSource);
    }

    public String sign(Object event) {
        Instant now = Instant.now();
        JwtClaimsSet.Builder claims = JwtClaimsSet.builder()
                .issuer(properties.getIssuer())
                .subject(properties.getIssuer())
                .audience(List.of(properties.getAudience()))
                .issuedAt(now)
                .expiresAt(now.plusSeconds(properties.getTtlSeconds()));

        if (event instanceof EventNotification notification) {
            if (notification.eventType != null) {
                claims.claim("eventType", notification.eventType);
            }
            if (notification.correlationId != null) {
                claims.claim("correlationId", notification.correlationId);
            }
        }

        return jwtEncoder.encode(JwtEncoderParameters.from(claims.build())).getTokenValue();
    }

    private static RSAPublicKey loadPublicKey(ResourceLoader resourceLoader, String location) throws Exception {
        String pem = readPem(resourceLoader, location);
        byte[] decoded = Base64.getDecoder().decode(stripPemHeaders(pem, "PUBLIC KEY", "RSA PUBLIC KEY"));
        return (RSAPublicKey) KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(decoded));
    }

    private static RSAPrivateKey loadPrivateKey(ResourceLoader resourceLoader, String location) throws Exception {
        String pem = readPem(resourceLoader, location);
        byte[] decoded = Base64.getDecoder().decode(stripPemHeaders(pem, "PRIVATE KEY", "RSA PRIVATE KEY"));
        return (RSAPrivateKey) KeyFactory.getInstance("RSA").generatePrivate(new PKCS8EncodedKeySpec(decoded));
    }

    private static String readPem(ResourceLoader resourceLoader, String location) throws IOException {
        Resource resource = resourceLoader.getResource(location);
        try (Reader reader = new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8)) {
            return FileCopyUtils.copyToString(reader);
        }
    }

    private static String stripPemHeaders(String pem, String... labels) {
        String normalized = pem.replace("\r", "");
        for (String label : labels) {
            normalized = normalized
                    .replace("-----BEGIN " + label + "-----", "")
                    .replace("-----END " + label + "-----", "");
        }
        return normalized.replaceAll("\\s", "");
    }
}
