package com.cantelcox.portabilityhubsync.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** Registered TMF Hub subscription that receives event callbacks. */
@Entity
@Table(name = "hub")
public class HubEntity {

    @Id
    @Column(nullable = false, updatable = false, length = 64)
    private String id;

    @Column(nullable = false, length = 2048)
    private String callback;

    @Column(length = 512)
    private String query;

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }

    public String getCallback() { return callback; }
    public void setCallback(String callback) { this.callback = callback; }

    public String getQuery() { return query; }
    public void setQuery(String query) { this.query = query; }
}
