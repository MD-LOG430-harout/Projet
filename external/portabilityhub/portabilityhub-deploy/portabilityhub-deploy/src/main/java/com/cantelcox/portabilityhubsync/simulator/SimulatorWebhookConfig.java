package com.cantelcox.portabilityhubsync.simulator;

import com.cantelcox.portabilityhubsync.config.SimulatorProperties;
import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.cantelcox.portabilityhubsync.service.RestWebhookClient;
import com.cantelcox.portabilityhubsync.service.WebhookClient;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
@ConditionalOnProperty(name = "portabilityhubsync.simulator.enabled", havingValue = "true")
public class SimulatorWebhookConfig {

    @Bean
    @Primary
    WebhookClient simulatorWebhookClient(SimulatorProperties properties,
                                         RestWebhookClient restWebhookClient,
                                         SimulatorActivityLog activityLog) {
        if (properties.isUseBssGateway()) {
            return restWebhookClient;
        }
        return new RecordingSimulatorWebhookClient(activityLog);
    }

    static final class RecordingSimulatorWebhookClient implements WebhookClient {

        private final SimulatorActivityLog activityLog;

        RecordingSimulatorWebhookClient(SimulatorActivityLog activityLog) {
            this.activityLog = activityLog;
        }

        @Override
        public void deliver(String callbackUrl, Object event) {
            String operator = callbackUrl.contains("/webhooks/")
                    ? callbackUrl.substring(callbackUrl.lastIndexOf('/') + 1).toUpperCase()
                    : "BSS1";
            if (callbackUrl.contains("/bss1") || callbackUrl.endsWith("/BSS1")) {
                operator = "BSS1";
            } else if (callbackUrl.contains("/bss2") || callbackUrl.endsWith("/BSS2")) {
                operator = "BSS2";
            }
            activityLog.record("HUB", operator, extractEventType(event), event);
        }

        private static String extractEventType(Object event) {
            if (event instanceof EventNotification notification) {
                return notification.eventType;
            }
            return String.valueOf(event);
        }
    }
}
