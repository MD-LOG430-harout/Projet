USE usage_facturation;

CREATE TABLE IF NOT EXISTS invoices (
  invoice_id CHAR(36) PRIMARY KEY,
  customer_id CHAR(36) NOT NULL,
  billing_period VARCHAR(20) NOT NULL,
  amount_due DECIMAL(10,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  status VARCHAR(20) NOT NULL,
  due_date DATE NOT NULL,
  created_at DATETIME NOT NULL,
  paid_at DATETIME NULL,
  KEY idx_invoices_customer (customer_id),
  KEY idx_invoices_status (status)
);

CREATE TABLE IF NOT EXISTS payments (
  payment_id CHAR(36) PRIMARY KEY,
  invoice_id CHAR(36) NOT NULL,
  customer_id CHAR(36) NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  request_hash CHAR(64) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  payment_method VARCHAR(40) NOT NULL,
  status VARCHAR(20) NOT NULL,
  response_body JSON NOT NULL,
  http_status INT NOT NULL,
  failure_reason VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_payments_idempotency_key (idempotency_key),
  UNIQUE KEY uq_successful_payment_per_invoice (invoice_id, status),
  KEY idx_payments_invoice (invoice_id),
  KEY idx_payments_customer (customer_id)
);
