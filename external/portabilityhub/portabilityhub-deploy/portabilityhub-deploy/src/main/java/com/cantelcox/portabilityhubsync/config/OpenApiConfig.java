package com.cantelcox.portabilityhubsync.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI portabilityHubOpenAPI() {
        return new OpenAPI().info(new Info()
                .title("Hub de Portabilité — REST Prototype")
                .version("1.2")
                .description("Contrat normatif : docs/openapi/portability-hub.openapi.yaml")
                .license(new License().name("Apache 2.0")));
    }
}
