package com.cantelcox.portabilityhubsync;

import com.cantelcox.portabilityhubsync.config.HubEventProperties;
import com.cantelcox.portabilityhubsync.config.OutboxProperties;
import com.cantelcox.portabilityhubsync.config.SimulatorProperties;
import com.cantelcox.portabilityhubsync.config.WebhookJwtProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
@EnableConfigurationProperties({HubEventProperties.class, OutboxProperties.class, SimulatorProperties.class, WebhookJwtProperties.class})
public class PortabilityHubSyncApplication {

    public static void main(String[] args) {
        SpringApplication.run(PortabilityHubSyncApplication.class, args);
    }
}
