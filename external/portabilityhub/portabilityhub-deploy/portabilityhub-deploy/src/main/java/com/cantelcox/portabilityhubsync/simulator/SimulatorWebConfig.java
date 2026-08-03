package com.cantelcox.portabilityhubsync.simulator;

import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.CacheControl;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
@ConditionalOnProperty(name = "portabilityhubsync.simulator.enabled", havingValue = "true")
public class SimulatorWebConfig implements WebMvcConfigurer {

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        registry.addResourceHandler("/simulator/**")
                .addResourceLocations("classpath:/static/simulator/")
                .setCacheControl(CacheControl.noStore());
    }
}
