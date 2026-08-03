-- Increment 1: additive order-saga entry persistence for existing MySQL schemas.
USE commandes_activations;

DELIMITER //
CREATE PROCEDURE add_increment1_column_if_missing(
  IN column_name_value VARCHAR(64),
  IN alter_statement_value VARCHAR(500)
)
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'orders'
      AND column_name = column_name_value
  ) THEN
    SET @increment1_alter = alter_statement_value;
    PREPARE increment1_alter_statement FROM @increment1_alter;
    EXECUTE increment1_alter_statement;
    DEALLOCATE PREPARE increment1_alter_statement;
  END IF;
END//
DELIMITER ;

CALL add_increment1_column_if_missing('saga_id', 'ALTER TABLE orders ADD COLUMN saga_id CHAR(36) NULL AFTER http_status');
CALL add_increment1_column_if_missing('line_id', 'ALTER TABLE orders ADD COLUMN line_id CHAR(36) NULL AFTER saga_id');
CALL add_increment1_column_if_missing('terminal_event_id', 'ALTER TABLE orders ADD COLUMN terminal_event_id CHAR(36) NULL AFTER line_id');
CALL add_increment1_column_if_missing('terminal_reason', 'ALTER TABLE orders ADD COLUMN terminal_reason VARCHAR(100) NULL AFTER terminal_event_id');
DROP PROCEDURE add_increment1_column_if_missing;

UPDATE orders
SET saga_id = UUID()
WHERE saga_id IS NULL;

ALTER TABLE orders
  MODIFY saga_id CHAR(36) NOT NULL;

SET @has_saga_index = (
  SELECT COUNT(*) FROM information_schema.statistics
  WHERE table_schema = DATABASE() AND table_name = 'orders' AND index_name = 'uq_orders_saga_id'
);
SET @create_saga_index = IF(
  @has_saga_index = 0,
  'CREATE UNIQUE INDEX uq_orders_saga_id ON orders (saga_id)',
  'SELECT 1'
);
PREPARE create_saga_index_statement FROM @create_saga_index;
EXECUTE create_saga_index_statement;
DEALLOCATE PREPARE create_saga_index_statement;

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
