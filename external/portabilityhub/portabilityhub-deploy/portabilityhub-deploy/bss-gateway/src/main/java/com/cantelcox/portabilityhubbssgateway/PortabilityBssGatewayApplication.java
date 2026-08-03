package com.cantelcox.portabilityhubbssgateway;

import com.cantelcox.portabilityhubbssgateway.config.BssGatewayProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

@SpringBootApplication
@EnableConfigurationProperties(BssGatewayProperties.class)
public class PortabilityBssGatewayApplication {

    public static void main(String[] args) {
        SpringApplication.run(PortabilityBssGatewayApplication.class, args);
    }
}
