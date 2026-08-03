package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.config.OutboxProperties;
import com.cantelcox.portabilityhubsync.domain.OutboxEventEntity;
import com.cantelcox.portabilityhubsync.domain.OutboxEventStatus;
import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.cantelcox.portabilityhubsync.repository.OutboxEventRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.PageRequest;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.List;

@Component
public class OutboxDispatcher {

    private static final Logger log = LoggerFactory.getLogger(OutboxDispatcher.class);

    private final OutboxEventRepository outboxRepository;
    private final WebhookClient webhookClient;
    private final ObjectMapper objectMapper;
    private final OutboxProperties outboxProperties;

    public OutboxDispatcher(OutboxEventRepository outboxRepository,
                            WebhookClient webhookClient,
                            ObjectMapper objectMapper,
                            OutboxProperties outboxProperties) {
        this.outboxRepository = outboxRepository;
        this.webhookClient = webhookClient;
        this.objectMapper = objectMapper;
        this.outboxProperties = outboxProperties;
    }

    @Scheduled(fixedDelayString = "${portabilityhubsync.outbox.poll-interval-ms:1000}")
    public void dispatchScheduled() {
        dispatchPending();
    }

    @Transactional
    public int dispatchPending() {
        List<OutboxEventEntity> pending = outboxRepository.findByStatusOrderByCreatedAtAsc(
                OutboxEventStatus.PENDING,
                PageRequest.of(0, outboxProperties.getBatchSize()));

        int sent = 0;
        for (OutboxEventEntity entry : pending) {
            if (deliverEntry(entry)) {
                sent++;
            }
        }
        return sent;
    }

    private boolean deliverEntry(OutboxEventEntity entry) {
        try {
            EventNotification notification = objectMapper.readValue(entry.getPayload(), EventNotification.class);
            webhookClient.deliver(entry.getCallbackUrl(), notification);
            entry.setStatus(OutboxEventStatus.SENT);
            entry.setSentAt(OffsetDateTime.now());
            entry.setLastError(null);
            log.info("Outbox delivered {} to {} (id={})",
                    entry.getEventType(), entry.getCallbackUrl(), entry.getId());
            return true;
        } catch (Exception ex) {
            entry.setAttempts(entry.getAttempts() + 1);
            entry.setLastError(truncate(ex.getMessage()));
            if (entry.getAttempts() >= outboxProperties.getMaxAttempts()) {
                entry.setStatus(OutboxEventStatus.FAILED);
                log.error("Outbox delivery failed permanently for {} → {} after {} attempts: {}",
                        entry.getEventType(), entry.getCallbackUrl(), entry.getAttempts(), ex.getMessage());
            } else {
                log.warn("Outbox delivery attempt {} failed for {} → {}: {}",
                        entry.getAttempts(), entry.getEventType(), entry.getCallbackUrl(), ex.getMessage());
            }
            return false;
        }
    }

    private static String truncate(String message) {
        if (message == null) {
            return null;
        }
        return message.length() > 500 ? message.substring(0, 500) : message;
    }
}
