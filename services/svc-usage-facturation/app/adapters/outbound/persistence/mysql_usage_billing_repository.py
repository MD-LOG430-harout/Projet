import json
from datetime import date, datetime, timezone


class MysqlUsageBillingRepository:
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
                    )
                    """
                )
                cursor.execute(
                    """
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
                    )
                    """
                )
            conn.commit()
        self._schema_checked = True

    def list_invoices_by_customer(self, customer_id):
        self.ensure_schema()
        self.ensure_demo_invoice_for_customer(customer_id)
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM invoices WHERE customer_id=%s ORDER BY created_at DESC", (customer_id,))
                return cursor.fetchall()

    def get_invoice(self, invoice_id):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM invoices WHERE invoice_id=%s", (invoice_id,))
                return cursor.fetchone()

    def ensure_demo_invoice_for_customer(self, customer_id):
        self.ensure_schema()
        invoice_id = f"inv-{customer_id[:32]}"[:36]
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT invoice_id FROM invoices WHERE invoice_id=%s", (invoice_id,))
                if cursor.fetchone():
                    return
                cursor.execute(
                    """
                    INSERT INTO invoices
                    (invoice_id, customer_id, billing_period, amount_due, currency, status, due_date, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        invoice_id,
                        customer_id,
                        "2026-06",
                        49.99,
                        "CAD",
                        "OPEN",
                        date(2026, 7, 15),
                        datetime.now(timezone.utc).replace(tzinfo=None),
                    ),
                )
            conn.commit()

    def find_payment_by_idempotency_key(self, key):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM payments WHERE idempotency_key=%s", (key,))
                return cursor.fetchone()

    def create_payment_and_mark_invoice_paid(self, payment):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO payments
                    (payment_id, invoice_id, customer_id, idempotency_key, request_hash, amount,
                     currency, payment_method, status, response_body, http_status, failure_reason)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        payment.payment_id,
                        payment.invoice_id,
                        payment.customer_id,
                        payment.idempotency_key,
                        payment.request_hash,
                        payment.amount,
                        payment.currency,
                        payment.payment_method,
                        payment.status,
                        json.dumps(payment.response_body),
                        payment.http_status,
                        payment.failure_reason,
                    ),
                )
                cursor.execute(
                    "UPDATE invoices SET status='PAID', paid_at=%s WHERE invoice_id=%s AND status='OPEN'",
                    (datetime.now(timezone.utc).replace(tzinfo=None), payment.invoice_id),
                )
            conn.commit()
