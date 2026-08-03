USE commandes_activations;

CREATE TABLE IF NOT EXISTS activations (
  activation_id CHAR(36) PRIMARY KEY,
  idempotency_key VARCHAR(160) NOT NULL,
  request_hash CHAR(64) NOT NULL,
  customer_id CHAR(36) NOT NULL,
  offer_id VARCHAR(80) NOT NULL,
  line_id CHAR(36) NULL,
  status VARCHAR(40) NOT NULL,
  response_body JSON NOT NULL,
  http_status INT NOT NULL,
  failure_reason VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_activations_idempotency_key (idempotency_key),
  KEY idx_activations_customer (customer_id),
  KEY idx_activations_offer (offer_id),
  KEY idx_activations_line (line_id),
  KEY idx_activations_status (status)
);

CREATE TABLE IF NOT EXISTS orders (
  order_id CHAR(36) PRIMARY KEY,
  customer_id CHAR(36) NOT NULL,
  offer_id VARCHAR(80) NOT NULL,
  order_type VARCHAR(60) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'EN_COURS',
  orchestration_status VARCHAR(60) NOT NULL DEFAULT 'EN_COURS',
  confirmation_status VARCHAR(60) NOT NULL DEFAULT 'PENDING',
  total_amount DECIMAL(10,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  request_hash CHAR(64) NOT NULL,
  response_body JSON NOT NULL,
  http_status INT NOT NULL,
  saga_id CHAR(36) NOT NULL,
  line_id CHAR(36) NULL,
  terminal_event_id CHAR(36) NULL,
  terminal_reason VARCHAR(100) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_orders_idempotency_key (idempotency_key),
  UNIQUE KEY uq_orders_saga_id (saga_id),
  KEY idx_orders_customer (customer_id),
  KEY idx_orders_offer (offer_id),
  KEY idx_orders_customer_status (customer_id, status),
  KEY idx_orders_status (status)
);

CREATE TABLE IF NOT EXISTS saga_state (
  saga_id CHAR(36) PRIMARY KEY,
  order_id CHAR(36) NOT NULL,
  status VARCHAR(40) NOT NULL DEFAULT 'EN_COURS',
  payment_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
  line_status VARCHAR(40) NOT NULL DEFAULT 'PENDING',
  portability_status VARCHAR(40) NOT NULL DEFAULT 'NOT_REQUIRED',
  last_event_type VARCHAR(100) NOT NULL,
  last_event_id CHAR(36) NULL,
  deadline_at DATETIME(6) NOT NULL,
  completed_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL,
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_saga_state_order (order_id),
  KEY idx_saga_state_deadline (status, deadline_at),
  CONSTRAINT fk_saga_state_order FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB;
