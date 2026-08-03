import json

from services.shared.outbox import MysqlOutboxRepository


class MysqlActivationRepository:
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
                      current_operator VARCHAR(80) NULL,
                      failure_reason VARCHAR(255) NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      UNIQUE KEY uq_activations_idempotency_key (idempotency_key),
                      KEY idx_activations_customer (customer_id),
                      KEY idx_activations_offer (offer_id),
                      KEY idx_activations_line (line_id),
                      KEY idx_activations_status (status)
                    )
                    """
                )
                cursor.execute(
                    """
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
                      KEY idx_orders_customer_status (customer_id, status),
                      KEY idx_orders_status (status)
                    )
                    """
                )
                self._ensure_column(cursor, "orders", "orchestration_status", "VARCHAR(60) NOT NULL DEFAULT 'READY_FOR_ACTIVATION'")
                self._ensure_column(cursor, "orders", "confirmation_status", "VARCHAR(60) NOT NULL DEFAULT 'SIMULATED_SENT'")
                self._ensure_column(cursor, "orders", "current_operator", "VARCHAR(80) NULL")
                self._ensure_index(cursor, "activations", "idx_activations_offer", "offer_id")
                self._ensure_index(cursor, "activations", "idx_activations_line", "line_id")
                self._ensure_index(cursor, "orders", "idx_orders_customer_status", "customer_id, status")
            conn.commit()
        self._schema_checked = True

    def _ensure_column(self, cursor, table_name, column_name, definition):
        cursor.execute(
            """
            SELECT COUNT(*) AS column_count
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND COLUMN_NAME = %s
            """,
            (table_name, column_name),
        )
        row = cursor.fetchone()
        exists = row["column_count"] if isinstance(row, dict) else row[0]
        if not exists:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def _ensure_index(self, cursor, table_name, index_name, columns):
        cursor.execute(
            """
            SELECT COUNT(*) AS index_count
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = %s
              AND INDEX_NAME = %s
            """,
            (table_name, index_name),
        )
        row = cursor.fetchone()
        exists = row["index_count"] if isinstance(row, dict) else row[0]
        if not exists:
            cursor.execute(f"ALTER TABLE {table_name} ADD INDEX {index_name} ({columns})")

    def create(self, activation):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO activations
                    (activation_id, idempotency_key, request_hash, customer_id, offer_id,
                     line_id, status, response_body, http_status, failure_reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        activation.activation_id,
                        activation.idempotency_key,
                        activation.request_hash,
                        activation.customer_id,
                        activation.offer_id,
                        activation.line_id,
                        activation.status,
                        json.dumps(activation.response_body),
                        activation.http_status,
                        activation.failure_reason,
                    ),
                )
            conn.commit()

    def find_by_idempotency_key(self, idempotency_key):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM activations WHERE idempotency_key=%s", (idempotency_key,))
                return cursor.fetchone()

    def create_order(self, order):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders
                    (order_id, customer_id, offer_id, order_type, status, orchestration_status, confirmation_status, total_amount, currency,
                    idempotency_key, request_hash, response_body, http_status, saga_id, current_operator, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order.order_id,
                        order.customer_id,
                        order.offer_id,
                        order.order_type,
                        order.status,
                        order.orchestration_status,
                        order.confirmation_status,
                        order.total_amount,
                        order.currency,
                        order.idempotency_key,
                        order.request_hash,
                        json.dumps(order.response_body),
                        order.http_status,
                        order.saga_id,
                        order.current_operator,
                        order.created_at.replace(tzinfo=None),
                    ),
                )
            conn.commit()

    def create_order_with_saga(self, order, saga, event):
        self.ensure_schema()
        with self.connection_factory() as conn:
            try:
                with conn.cursor() as cursor:
                    self._insert_order(cursor, order)
                    cursor.execute(
                        """
                        INSERT INTO saga_state
                          (saga_id, order_id, status, payment_status, line_status,
                           portability_status, last_event_type, last_event_id,
                           deadline_at, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            saga.saga_id,
                            saga.order_id,
                            saga.status,
                            saga.payment_status,
                            saga.line_status,
                            saga.portability_status,
                            saga.last_event_type,
                            saga.last_event_id,
                            saga.deadline_at.replace(tzinfo=None),
                            saga.created_at.replace(tzinfo=None),
                        ),
                    )
                    MysqlOutboxRepository().insert(cursor, event)
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def _insert_order(self, cursor, order):
        cursor.execute(
            """
            INSERT INTO orders
              (order_id, customer_id, offer_id, order_type, status,
               orchestration_status, confirmation_status, total_amount, currency,
               idempotency_key, request_hash, response_body, http_status, saga_id,
               current_operator, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                order.order_id,
                order.customer_id,
                order.offer_id,
                order.order_type,
                order.status,
                order.orchestration_status,
                order.confirmation_status,
                order.total_amount,
                order.currency,
                order.idempotency_key,
                order.request_hash,
                json.dumps(order.response_body),
                order.http_status,
                order.saga_id,
                order.current_operator,
                order.created_at.replace(tzinfo=None),
            ),
        )

    def find_order_by_idempotency_key(self, idempotency_key):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM orders WHERE idempotency_key=%s", (idempotency_key,))
                return cursor.fetchone()

    def find_order_by_id(self, order_id):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM orders WHERE order_id=%s", (order_id,))
                return cursor.fetchone()

    def find_expired_sagas(self, limit=100):
        self.ensure_schema()
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT * FROM saga_state
                    WHERE status='EN_COURS' AND deadline_at <= UTC_TIMESTAMP(6)
                    ORDER BY deadline_at LIMIT {limit}
                    """
                )
                return cursor.fetchall()
