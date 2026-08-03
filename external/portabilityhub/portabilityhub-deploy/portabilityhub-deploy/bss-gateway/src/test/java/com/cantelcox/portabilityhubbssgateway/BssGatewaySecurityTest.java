package com.cantelcox.portabilityhubbssgateway;

import com.github.tomakehurst.wiremock.junit5.WireMockExtension;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.RegisterExtension;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.post;
import static com.github.tomakehurst.wiremock.client.WireMock.postRequestedFor;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.wireMockConfig;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class BssGatewaySecurityTest {

    @RegisterExtension
    static WireMockExtension bssBackend = WireMockExtension.newInstance()
            .options(wireMockConfig().dynamicPort())
            .build();

    @DynamicPropertySource
    static void bssGatewayProperties(DynamicPropertyRegistry registry) {
        registry.add("bssgateway.backend-host", bssBackend::baseUrl);
        registry.add("bssgateway.backend-path", () -> "/");
    }

    @Autowired
    private WebTestClient webTestClient;

    @Test
    void webhookIsPublicWithoutJwt() {
        bssBackend.stubFor(post(urlEqualTo("/"))
                .willReturn(aResponse().withStatus(200)));

        webTestClient.post()
                .uri("/webhooks/portability")
                .contentType(MediaType.APPLICATION_JSON)
                .bodyValue("""
                        {"eventType":"PortabilityOrderStateChangeEvent","correlationId":"PORT-TEST"}
                        """)
                .exchange()
                .expectStatus().isOk();

        bssBackend.verify(postRequestedFor(urlEqualTo("/")));
    }
}
