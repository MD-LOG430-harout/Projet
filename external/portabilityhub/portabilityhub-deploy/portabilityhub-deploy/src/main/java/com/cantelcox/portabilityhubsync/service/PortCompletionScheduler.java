package com.cantelcox.portabilityhubsync.service;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
public class PortCompletionScheduler {

    private static final Logger log = LoggerFactory.getLogger(PortCompletionScheduler.class);

    private final PortabilityHubService hubService;

    public PortCompletionScheduler(PortabilityHubService hubService) {
        this.hubService = hubService;
    }

    @Scheduled(fixedDelayString = "${portabilityhubsync.port-completion.poll-interval-ms:60000}")
    public void completeDuePorts() {
        int completed = hubService.completeDuePorts();
        if (completed > 0) {
            log.info("Completed {} due portability order(s)", completed);
        }
    }
}
