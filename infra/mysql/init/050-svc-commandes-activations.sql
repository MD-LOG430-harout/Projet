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
  KEY idx_activations_status (status)
);

CREATE TABLE IF NOT EXISTS orders (
  order_id CHAR(36) PRIMARY KEY,
  customer_id CHAR(36) NOT NULL,
  offer_id VARCHAR(80) NOT NULL,
  order_type VARCHAR(60) NOT NULL,
  status VARCHAR(40) NOT NULL,
  orchestration_status VARCHAR(60) NOT NULL DEFAULT 'READY_FOR_ACTIVATION',
  confirmation_status VARCHAR(60) NOT NULL DEFAULT 'SIMULATED_SENT',
  total_amount DECIMAL(10,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  request_hash CHAR(64) NOT NULL,
  response_body JSON NOT NULL,
  http_status INT NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_orders_idempotency_key (idempotency_key),
  KEY idx_orders_customer (customer_id),
  KEY idx_orders_offer (offer_id),
  KEY idx_orders_status (status)
);
