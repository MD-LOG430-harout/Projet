package com.cantelcox.portabilityhubbssgateway.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.io.Resource;
import org.springframework.core.io.ResourceLoader;
import org.springframework.security.oauth2.core.DelegatingOAuth2TokenValidator;
import org.springframework.security.oauth2.core.OAuth2TokenValidator;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.jwt.JwtClaimValidator;
import org.springframework.security.oauth2.jwt.JwtValidators;
import org.springframework.security.oauth2.jwt.NimbusReactiveJwtDecoder;
import org.springframework.security.oauth2.jwt.ReactiveJwtDecoder;
import org.springframework.util.FileCopyUtils;

import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.security.KeyFactory;
import java.security.interfaces.RSAPublicKey;
import java.security.spec.X509EncodedKeySpec;
import java.util.Base64;
import java.util.List;

@Configuration
public class JwtConfig {

    private final BssGatewayProperties properties;
    private final ResourceLoader resourceLoader;

    public JwtConfig(BssGatewayProperties properties, ResourceLoader resourceLoader) {
        this.properties = properties;
        this.resourceLoader = resourceLoader;
    }

    @Bean
    ReactiveJwtDecoder reactiveJwtDecoder() throws Exception {
        RSAPublicKey publicKey = loadPublicKey(properties.getJwt().getHubPublicKeyLocation());
        NimbusReactiveJwtDecoder decoder = NimbusReactiveJwtDecoder.withPublicKey(publicKey).build();
        OAuth2TokenValidator<Jwt> issuer = JwtValidators.createDefaultWithIssuer(properties.getJwt().getExpectedIssuer());
        OAuth2TokenValidator<Jwt> audience = new JwtClaimValidator<>(
                "aud",
                aud -> aud instanceof List<?> list && list.contains(properties.getJwt().getExpectedAudience()));
        decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(issuer, audience));
        return decoder;
    }

    private RSAPublicKey loadPublicKey(String location) throws Exception {
        String pem = readPem(location);
        byte[] decoded = Base64.getDecoder().decode(stripPemHeaders(pem, "PUBLIC KEY", "RSA PUBLIC KEY"));
        return (RSAPublicKey) KeyFactory.getInstance("RSA").generatePublic(new X509EncodedKeySpec(decoded));
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
