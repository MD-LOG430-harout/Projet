class MysqlOfferRepository:
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
                    CREATE TABLE IF NOT EXISTS offers (
                      offer_id VARCHAR(80) PRIMARY KEY,
                      name VARCHAR(160) NOT NULL,
                      monthly_price DECIMAL(10,2) NOT NULL,
                      data_gb INT NOT NULL,
                      status VARCHAR(40) NOT NULL,
                      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                      KEY idx_offers_status (status)
                    )
                    """
                )
                cursor.execute(
                    """
                    INSERT INTO offers (offer_id, name, monthly_price, data_gb, status)
                    VALUES
                      ('forfait-5g-20gb', 'CanTelcoX 5G 20 Go', 45.00, 20, 'ACTIVE'),
                      ('forfait-5g-50gb', 'CanTelcoX 5G 50 Go', 65.00, 50, 'ACTIVE'),
                      ('forfait-sme-100gb', 'CanTelcoX PME 100 Go', 95.00, 100, 'ACTIVE'),
                      ('forfait-retired-10gb', 'Ancien forfait 10 Go', 35.00, 10, 'INACTIVE')
                    ON DUPLICATE KEY UPDATE
                      name = VALUES(name),
                      monthly_price = VALUES(monthly_price),
                      data_gb = VALUES(data_gb),
                      status = VALUES(status)
                    """
                )
            conn.commit()
        self._schema_checked = True

    def find_by_id(self, offer_id):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM offers WHERE offer_id=%s", (offer_id,))
                return cursor.fetchone()

    def list_active(self):
        self.ensure_schema()
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM offers WHERE status='ACTIVE' ORDER BY monthly_price, offer_id")
                return cursor.fetchall()
