package com.cantelcox.portabilityhubgateway;

import com.cantelcox.portabilityhubgateway.config.GatewayProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(GatewayProperties.class)
public class PortabilityHubGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(PortabilityHubGatewayApplication.class, args);
    }
}
