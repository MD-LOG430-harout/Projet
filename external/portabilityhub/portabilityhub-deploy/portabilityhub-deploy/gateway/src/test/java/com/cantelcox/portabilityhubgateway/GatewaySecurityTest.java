package com.cantelcox.portabilityhubgateway;

import com.github.tomakehurst.wiremock.junit5.WireMockExtension;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.RegisterExtension;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.reactive.AutoConfigureWebTestClient;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.reactive.server.WebTestClient;

import static com.github.tomakehurst.wiremock.client.WireMock.aResponse;
import static com.github.tomakehurst.wiremock.client.WireMock.get;
import static com.github.tomakehurst.wiremock.client.WireMock.urlEqualTo;
import static com.github.tomakehurst.wiremock.core.WireMockConfiguration.wireMockConfig;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureWebTestClient
class GatewaySecurityTest {

    @RegisterExtension
    static WireMockExtension hub = WireMockExtension.newInstance()
            .options(wireMockConfig().dynamicPort())
            .build();

    @DynamicPropertySource
    static void gatewayProperties(DynamicPropertyRegistry registry) {
        registry.add("portabilityhubgateway.hub-uri", hub::baseUrl);
    }

    @Autowired
    private WebTestClient webTestClient;

    @Test
    void portabilityApiIsPublic() {
        hub.stubFor(get(urlEqualTo("/portability/order/PORT-TEST"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "application/json")
                        .withBody("""
                                {"orderId":"PORT-TEST","status":"approved"}
                                """)));

        webTestClient.get()
                .uri("/portability/order/PORT-TEST")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.orderId").isEqualTo("PORT-TEST");
    }

    @Test
    void simulatorIsPublic() {
        hub.stubFor(get(urlEqualTo("/simulator/api/config"))
                .willReturn(aResponse()
                        .withStatus(200)
                        .withHeader("Content-Type", "application/json")
                        .withBody("""
                                {"hubGatewayUrl":"http://hub"}
                                """)));

        webTestClient.get()
                .uri("/simulator/api/config")
                .exchange()
                .expectStatus().isOk()
                .expectBody()
                .jsonPath("$.hubGatewayUrl").isEqualTo("http://hub");
    }
}
