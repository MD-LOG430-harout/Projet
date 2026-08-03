-- Increment 5: original internal event identifiers for append-only Kafka audit.
USE conformite_audit;

DELIMITER //
CREATE PROCEDURE add_audit_column_if_missing(IN name_value VARCHAR(64), IN definition_value VARCHAR(500))
BEGIN
  IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema=DATABASE() AND table_name='audit_events' AND column_name=name_value) THEN
    SET @audit_alter=definition_value;
    PREPARE audit_alter_statement FROM @audit_alter;
    EXECUTE audit_alter_statement;
    DEALLOCATE PREPARE audit_alter_statement;
  END IF;
END//
DELIMITER ;

CALL add_audit_column_if_missing('event_id', 'ALTER TABLE audit_events ADD COLUMN event_id CHAR(36) NULL AFTER audit_event_id');
CALL add_audit_column_if_missing('occurred_at', 'ALTER TABLE audit_events ADD COLUMN occurred_at DATETIME(6) NULL AFTER event_type');
CALL add_audit_column_if_missing('aggregate_id', 'ALTER TABLE audit_events ADD COLUMN aggregate_id VARCHAR(120) NULL AFTER occurred_at');
CALL add_audit_column_if_missing('correlation_id', 'ALTER TABLE audit_events ADD COLUMN correlation_id VARCHAR(120) NULL AFTER aggregate_id');
CALL add_audit_column_if_missing('causation_id', 'ALTER TABLE audit_events ADD COLUMN causation_id CHAR(36) NULL AFTER correlation_id');
CALL add_audit_column_if_missing('saga_id', 'ALTER TABLE audit_events ADD COLUMN saga_id CHAR(36) NULL AFTER causation_id');
DROP PROCEDURE add_audit_column_if_missing;

SET @has_event_id_index=(SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema=DATABASE() AND table_name='audit_events' AND index_name='uq_audit_event_id');
SET @add_event_id_index=IF(@has_event_id_index=0,'CREATE UNIQUE INDEX uq_audit_event_id ON audit_events(event_id)','SELECT 1');
PREPARE audit_event_index_statement FROM @add_event_id_index;
EXECUTE audit_event_index_statement;
DEALLOCATE PREPARE audit_event_index_statement;
