package com.cantelcox.portabilityhubsync.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;

@Entity
@Table(name = "portability_order", indexes = {
        @Index(name = "idx_po_state", columnList = "state")
})
public class PortabilityOrderEntity {

    @Id
    @Column(nullable = false, updatable = false, length = 64)
    private String id;

    @Enumerated(EnumType.STRING)
    @Column(name = "state", length = 32, nullable = false)
    private PortabilityOrderStatus status;

    @Column(name = "creation_date")
    private OffsetDateTime creationDate;

    @Column(name = "last_update")
    private OffsetDateTime lastUpdate;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "payload", nullable = false)
    private String payload;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public PortabilityOrderStatus getStatus() { return status; }
    public void setStatus(PortabilityOrderStatus status) { this.status = status; }

    public OffsetDateTime getCreationDate() { return creationDate; }
    public void setCreationDate(OffsetDateTime creationDate) { this.creationDate = creationDate; }

    public OffsetDateTime getLastUpdate() { return lastUpdate; }
    public void setLastUpdate(OffsetDateTime lastUpdate) { this.lastUpdate = lastUpdate; }

    public String getPayload() { return payload; }
    public void setPayload(String payload) { this.payload = payload; }
}
