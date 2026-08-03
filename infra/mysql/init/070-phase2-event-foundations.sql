-- Phase 2 event persistence foundations. The script is additive and idempotent.

USE commandes_activations;

CREATE TABLE IF NOT EXISTS outbox_events (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  event_id CHAR(36) NOT NULL,
  aggregate_id VARCHAR(120) NOT NULL,
  aggregate_type VARCHAR(80) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  event_version INT UNSIGNED NOT NULL,
  payload JSON NOT NULL,
  occurred_at DATETIME(6) NOT NULL,
  status ENUM('PENDING', 'PUBLISHING', 'PUBLISHED') NOT NULL DEFAULT 'PENDING',
  attempt_count INT UNSIGNED NOT NULL DEFAULT 0,
  next_attempt_at DATETIME(6) NOT NULL,
  published_at DATETIME(6) NULL,
  last_error TEXT NULL,
  lock_token CHAR(36) NULL,
  locked_until DATETIME(6) NULL,
  UNIQUE KEY uq_outbox_event_id (event_id),
  KEY idx_outbox_pending (status, next_attempt_at, occurred_at, id),
  KEY idx_outbox_aggregate (aggregate_id, occurred_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS processed_events (
  event_id CHAR(36) NOT NULL PRIMARY KEY,
  event_type VARCHAR(100) NOT NULL,
  processed_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  KEY idx_processed_type_time (event_type, processed_at)
);

USE usage_facturation;

CREATE TABLE IF NOT EXISTS outbox_events LIKE commandes_activations.outbox_events;
CREATE TABLE IF NOT EXISTS processed_events LIKE commandes_activations.processed_events;

USE lignes_services;

CREATE TABLE IF NOT EXISTS outbox_events LIKE commandes_activations.outbox_events;
CREATE TABLE IF NOT EXISTS processed_events LIKE commandes_activations.processed_events;

USE conformite_audit;

CREATE TABLE IF NOT EXISTS processed_events LIKE commandes_activations.processed_events;
