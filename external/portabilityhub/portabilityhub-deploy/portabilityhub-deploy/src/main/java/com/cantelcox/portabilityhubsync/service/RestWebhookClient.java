package com.cantelcox.portabilityhubsync.service;

import org.springframework.http.HttpHeaders;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.Optional;

@Component
public class RestWebhookClient implements WebhookClient {

    private final RestClient restClient;
    private final Optional<WebhookJwtSigner> jwtSigner;

    public RestWebhookClient(RestClient.Builder restClientBuilder, Optional<WebhookJwtSigner> jwtSigner) {
        this.restClient = restClientBuilder.build();
        this.jwtSigner = jwtSigner;
    }

    @Override
    public void deliver(String callbackUrl, Object event) {
        RestClient.RequestBodySpec request = restClient.post().uri(callbackUrl);
        if (jwtSigner.isPresent()) {
            request = request.header(HttpHeaders.AUTHORIZATION, "Bearer " + jwtSigner.get().sign(event));
        }
        request.body(event).retrieve().toBodilessEntity();
    }
}
