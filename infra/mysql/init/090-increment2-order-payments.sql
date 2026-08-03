-- Increment 2: order-saga payment authorization, separate from UC-06 capture.
USE usage_facturation;

CREATE TABLE IF NOT EXISTS order_saga_payments (
  payment_id CHAR(36) PRIMARY KEY,
  order_id CHAR(36) NOT NULL,
  saga_id CHAR(36) NOT NULL,
  amount DECIMAL(10,2) NOT NULL,
  currency CHAR(3) NOT NULL,
  status ENUM('EN_ATTENTE','AUTORISE','REFUSE','REMBOURSE') NOT NULL,
  authorization_id VARCHAR(120) NULL,
  refund_id VARCHAR(120) NULL,
  authorization_event_id CHAR(36) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_order_saga_payment_order (order_id),
  UNIQUE KEY uq_order_saga_payment_saga (saga_id),
  KEY idx_order_saga_payment_status (status, updated_at)
) ENGINE=InnoDB;
