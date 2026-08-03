-- Increments 3 and 4: additive line saga and portability correlation state.
USE commandes_activations;

SET @has_current_operator = (
  SELECT COUNT(*) FROM information_schema.columns
  WHERE table_schema=DATABASE() AND table_name='orders' AND column_name='current_operator'
);
SET @add_current_operator = IF(
  @has_current_operator=0,
  'ALTER TABLE orders ADD COLUMN current_operator VARCHAR(80) NULL AFTER terminal_reason',
  'SELECT 1'
);
PREPARE add_current_operator_statement FROM @add_current_operator;
EXECUTE add_current_operator_statement;
DEALLOCATE PREPARE add_current_operator_statement;

USE lignes_services;

CREATE TABLE IF NOT EXISTS line_saga_state (
  line_id CHAR(36) PRIMARY KEY,
  order_id CHAR(36) NOT NULL,
  saga_id CHAR(36) NOT NULL,
  customer_id CHAR(36) NOT NULL,
  offer_id VARCHAR(80) NOT NULL,
  number_mode ENUM('NEW','PORT_IN') NOT NULL,
  current_operator VARCHAR(80) NULL,
  status ENUM('RESERVED','PROVISIONING','PORTABILITY_PENDING','ACTIVE','FAILED','RELEASED') NOT NULL,
  source_event_id CHAR(36) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_line_saga_order (order_id),
  UNIQUE KEY uq_line_saga_saga (saga_id),
  KEY idx_line_saga_status (status, updated_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS portability_correlations (
  portability_id CHAR(36) PRIMARY KEY,
  hub_order_id VARCHAR(120) NULL,
  id_ligne CHAR(36) NOT NULL,
  id_commande CHAR(36) NOT NULL,
  saga_id CHAR(36) NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  msisdn VARCHAR(32) NOT NULL,
  current_operator VARCHAR(80) NOT NULL,
  trace_id_initial CHAR(32) NOT NULL,
  status ENUM('INITIATING','pending_out_validation','approved','rejected','port_completed','cancelled','TIMED_OUT','FAILED') NOT NULL,
  deadline_at DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_portability_hub_order (hub_order_id),
  UNIQUE KEY uq_portability_idempotency (idempotency_key),
  UNIQUE KEY uq_portability_line (id_ligne),
  KEY idx_portability_deadline (status, deadline_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS portability_webhook_events (
  event_id VARCHAR(160) PRIMARY KEY,
  hub_order_id VARCHAR(120) NOT NULL,
  hub_status VARCHAR(40) NOT NULL,
  processed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_portability_hub_status (hub_order_id, hub_status)
) ENGINE=InnoDB;
