package com.cantelcox.portabilityhubgateway.config;

import com.cantelcox.portabilityhubgateway.dev.JwtDevTokenService;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusReactiveJwtDecoder;
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
import java.util.Base64;

import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import com.nimbusds.jose.jwk.source.JWKSource;
import com.nimbusds.jose.proc.SecurityContext;

@Configuration
public class JwtConfig {

    private final GatewayProperties properties;
    private final ResourceLoader resourceLoader;

    public JwtConfig(GatewayProperties properties, ResourceLoader resourceLoader) {
        this.properties = properties;
        this.resourceLoader = resourceLoader;
    }

    @Bean
    ReactiveJwtDecoder reactiveJwtDecoder() throws Exception {
        RSAPublicKey publicKey = loadPublicKey(properties.getJwt().getPublicKeyLocation());
        return NimbusReactiveJwtDecoder.withPublicKey(publicKey).build();
    }

    @Bean
    @ConditionalOnProperty(name = "portabilityhubgateway.dev-token-enabled", havingValue = "true")
    JwtEncoder jwtEncoder() throws Exception {
        RSAPublicKey publicKey = loadPublicKey(properties.getJwt().getPublicKeyLocation());
        RSAPrivateKey privateKey = loadPrivateKey(properties.getJwt().getPrivateKeyLocation());
        RSAKey rsaKey = new RSAKey.Builder(publicKey)
                .privateKey(privateKey)
                .keyID("hub-gateway-dev")
                .build();
        JWKSource<SecurityContext> jwkSource = new ImmutableJWKSet<>(new com.nimbusds.jose.jwk.JWKSet(rsaKey));
        return new NimbusJwtEncoder(jwkSource);
    }

    @Bean
    @ConditionalOnProperty(name = "portabilityhubgateway.dev-token-enabled", havingValue = "true")
    JwtDevTokenService jwtDevTokenService(JwtEncoder jwtEncoder) {
        return new JwtDevTokenService(jwtEncoder, properties);
    }

    private RSAPublicKey loadPublicKey(String location) throws Exception {
        String pem = readPem(location);
        byte[] decoded = Base64.getDecoder().decode(stripPemHeaders(pem, "PUBLIC KEY", "RSA PUBLIC KEY"));
        KeyFactory keyFactory = KeyFactory.getInstance("RSA");
        return (RSAPublicKey) keyFactory.generatePublic(new X509EncodedKeySpec(decoded));
    }

    private RSAPrivateKey loadPrivateKey(String location) throws Exception {
        String pem = readPem(location);
        byte[] decoded = Base64.getDecoder().decode(stripPemHeaders(pem, "PRIVATE KEY", "RSA PRIVATE KEY"));
        KeyFactory keyFactory = KeyFactory.getInstance("RSA");
        return (RSAPrivateKey) keyFactory.generatePrivate(new PKCS8EncodedKeySpec(decoded));
    }

    private String readPem(String location) throws IOException {
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
