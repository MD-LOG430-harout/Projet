USE conformite_audit;

CREATE TABLE IF NOT EXISTS audit_events (
  audit_event_id CHAR(36) PRIMARY KEY,
  event_type VARCHAR(120) NOT NULL,
  actor_id VARCHAR(80) NULL,
  customer_id VARCHAR(80) NULL,
  resource_id VARCHAR(120) NULL,
  trace_id VARCHAR(120) NULL,
  source_service VARCHAR(120) NOT NULL,
  result VARCHAR(40) NOT NULL,
  metadata JSON NOT NULL,
  created_at DATETIME NOT NULL,
  inserted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY idx_audit_customer_created (customer_id, created_at),
  KEY idx_audit_trace (trace_id),
  KEY idx_audit_event_type (event_type)
);

DELIMITER //
CREATE TRIGGER audit_events_no_update
BEFORE UPDATE ON audit_events
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events is append-only';
END//

CREATE TRIGGER audit_events_no_delete
BEFORE DELETE ON audit_events
FOR EACH ROW
BEGIN
  SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'audit_events is append-only';
END//
DELIMITER ;

