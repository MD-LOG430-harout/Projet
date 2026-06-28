import json


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
                      failure_reason VARCHAR(255) NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      UNIQUE KEY uq_activations_idempotency_key (idempotency_key),
                      KEY idx_activations_customer (customer_id),
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
                    )
                    """
                )
            conn.commit()
        self._schema_checked = True

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
                    (order_id, customer_id, offer_id, order_type, status, total_amount, currency,
                     idempotency_key, request_hash, response_body, http_status, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        order.order_id,
                        order.customer_id,
                        order.offer_id,
                        order.order_type,
                        order.status,
                        order.total_amount,
                        order.currency,
                        order.idempotency_key,
                        order.request_hash,
                        json.dumps(order.response_body),
                        order.http_status,
                        order.created_at.replace(tzinfo=None),
                    ),
                )
            conn.commit()

    def find_order_by_idempotency_key(self, idempotency_key):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM orders WHERE idempotency_key=%s", (idempotency_key,))
                return cursor.fetchone()
