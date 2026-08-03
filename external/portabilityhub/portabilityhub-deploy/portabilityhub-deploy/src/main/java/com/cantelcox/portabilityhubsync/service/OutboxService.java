package com.cantelcox.portabilityhubsync.service;

import com.cantelcox.portabilityhubsync.domain.HubEntity;
import com.cantelcox.portabilityhubsync.domain.OutboxEventEntity;
import com.cantelcox.portabilityhubsync.domain.OutboxEventStatus;
import com.cantelcox.portabilityhubsync.event.EventNotification;
import com.cantelcox.portabilityhubsync.repository.HubRepository;
import com.cantelcox.portabilityhubsync.repository.OutboxEventRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.OffsetDateTime;
import java.util.UUID;

@Service
public class OutboxService {

    private static final Logger log = LoggerFactory.getLogger(OutboxService.class);

    private final HubRepository hubRepository;
    private final OutboxEventRepository outboxRepository;
    private final ObjectMapper objectMapper;

    public OutboxService(HubRepository hubRepository,
                         OutboxEventRepository outboxRepository,
                         ObjectMapper objectMapper) {
        this.hubRepository = hubRepository;
        this.outboxRepository = outboxRepository;
        this.objectMapper = objectMapper;
    }

    @Transactional
    public void enqueue(String eventType, EventNotification notification) {
        String payload = toJson(notification);
        int enqueued = 0;

        for (HubEntity hub : hubRepository.findAll()) {
            if (WebhookService.matchesQuery(hub.getQuery(), eventType)) {
                OutboxEventEntity entry = new OutboxEventEntity();
                entry.setId(UUID.randomUUID());
                entry.setCreatedAt(OffsetDateTime.now());
                entry.setCallbackUrl(hub.getCallback());
                entry.setEventType(eventType);
                entry.setCorrelationId(notification.correlationId);
                entry.setPayload(payload);
                entry.setStatus(OutboxEventStatus.PENDING);
                entry.setAttempts(0);
                outboxRepository.save(entry);
                enqueued++;
            }
        }

        log.debug("Enqueued {} outbox webhook(s) for eventType={} correlationId={}",
                enqueued, eventType, notification.correlationId);
    }

    private String toJson(EventNotification notification) {
        try {
            return objectMapper.writeValueAsString(notification);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Failed to serialize outbox event", e);
        }
    }
}
