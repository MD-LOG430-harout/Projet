class MysqlLineRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory
        self._schema_checked = False

    def ensure_schema(self):
        if self._schema_checked:
            return
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS service_lines (
                      line_id CHAR(36) PRIMARY KEY,
                      customer_id CHAR(36) NOT NULL,
                      offer_id VARCHAR(80) NOT NULL,
                      msisdn VARCHAR(32) NOT NULL,
                      sim_type VARCHAR(10) NOT NULL,
                      sim_identifier VARCHAR(80) NOT NULL,
                      imsi VARCHAR(32) NOT NULL,
                      supi VARCHAR(48) NOT NULL,
                      status VARCHAR(40) NOT NULL,
                      hlr_status VARCHAR(40) NOT NULL,
                      failure_reason VARCHAR(255) NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      UNIQUE KEY uq_lines_msisdn (msisdn),
                      UNIQUE KEY uq_lines_sim_identifier (sim_identifier),
                      UNIQUE KEY uq_lines_imsi (imsi),
                      KEY idx_lines_customer (customer_id),
                      KEY idx_lines_status (status)
                    )
                    """
                )
            conn.commit()
        self._schema_checked = True

    def create(self, line):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO service_lines
                    (line_id, customer_id, offer_id, msisdn, sim_type, sim_identifier,
                     imsi, supi, status, hlr_status, failure_reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        line.line_id,
                        line.customer_id,
                        line.offer_id,
                        line.msisdn,
                        line.sim_type,
                        line.sim_identifier,
                        line.imsi,
                        line.supi,
                        line.status,
                        line.hlr_status,
                        line.failure_reason,
                    ),
                )
            conn.commit()

    def find_by_id(self, line_id):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM service_lines WHERE line_id=%s", (line_id,))
                return cursor.fetchone()

    def find_by_msisdn(self, msisdn):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM service_lines WHERE msisdn=%s", (msisdn,))
                return cursor.fetchone()

    def mark_active(self, line_id):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE service_lines SET status='ACTIVE', hlr_status='PROVISIONED', failure_reason=NULL WHERE line_id=%s",
                    (line_id,),
                )
            conn.commit()

    def mark_failed(self, line_id, reason):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE service_lines SET status='FAILED', hlr_status='FAILED', failure_reason=%s WHERE line_id=%s",
                    (reason[:255], line_id),
                )
            conn.commit()
