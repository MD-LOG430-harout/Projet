from app.domain.repositories.customer_repository import CustomerRepository


class MysqlCustomerRepository(CustomerRepository):
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory
        self._schema_checked = False

    def ensure_schema(self):
        if self._schema_checked:
            return
        columns = {
            "legal_name": "VARCHAR(180) NOT NULL DEFAULT ''",
            "address_line1": "VARCHAR(255) NOT NULL DEFAULT ''",
            "city": "VARCHAR(120) NOT NULL DEFAULT ''",
            "province": "CHAR(2) NOT NULL DEFAULT ''",
            "postal_code": "VARCHAR(12) NOT NULL DEFAULT ''",
            "identity_document_type": "VARCHAR(40) NOT NULL DEFAULT ''",
            "identity_document_hash": "VARCHAR(255) NOT NULL DEFAULT ''",
            "failed_login_attempts": "INT NOT NULL DEFAULT 0",
            "locked_until": "DATETIME NULL",
            "last_login_risk": "VARCHAR(40) NULL",
        }
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW COLUMNS FROM customers")
                existing_columns = {row["Field"] for row in cursor.fetchall()}
                for column_name, definition in columns.items():
                    if column_name not in existing_columns:
                        cursor.execute(f"ALTER TABLE customers ADD COLUMN {column_name} {definition}")
            conn.commit()
        self._schema_checked = True

    def create(self, customer):
        self.ensure_schema()
        sql = """
            INSERT INTO customers
            (
              customer_id, email, display_name, legal_name, address_line1, city, province,
              postal_code, identity_document_type, identity_document_hash, customer_type,
              status, identity_status, risk_level
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        customer.customer_id,
                        customer.email,
                        customer.display_name,
                        customer.legal_name,
                        customer.address_line1,
                        customer.city,
                        customer.province,
                        customer.postal_code,
                        customer.identity_document_type,
                        customer.identity_document_hash,
                        customer.customer_type,
                        customer.status,
                        customer.identity_status,
                        customer.risk_level,
                    ),
                )
            conn.commit()

    def set_password_hash(self, customer_id, password_hash):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE customers SET password_hash=%s WHERE customer_id=%s",
                    (password_hash, customer_id),
                )
            conn.commit()

    def record_failed_login(self, customer_id, lock_until=None):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                if lock_until:
                    cursor.execute(
                        """
                        UPDATE customers
                        SET failed_login_attempts = failed_login_attempts + 1,
                            locked_until = %s
                        WHERE customer_id = %s
                        """,
                        (lock_until.replace(tzinfo=None), customer_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE customers
                        SET failed_login_attempts = failed_login_attempts + 1
                        WHERE customer_id = %s
                        """,
                        (customer_id,),
                    )
            conn.commit()

    def reset_failed_logins(self, customer_id):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE customers
                    SET failed_login_attempts = 0, locked_until = NULL
                    WHERE customer_id = %s
                    """,
                    (customer_id,),
                )
            conn.commit()

    def record_login_risk(self, customer_id, risk_level):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE customers SET last_login_risk = %s WHERE customer_id = %s",
                    (risk_level, customer_id),
                )
            conn.commit()

    def find_by_email(self, email):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM customers WHERE email=%s", (email,))
                return cursor.fetchone()

    def find_by_id(self, customer_id):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM customers WHERE customer_id=%s", (customer_id,))
                return cursor.fetchone()
