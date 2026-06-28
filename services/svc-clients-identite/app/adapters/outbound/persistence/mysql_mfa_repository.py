from app.domain.repositories.mfa_repository import MfaRepository


class MysqlMfaRepository(MfaRepository):
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def create(self, challenge):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO mfa_challenges
                    (challenge_id, customer_id, otp_hash, status, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        challenge.challenge_id,
                        challenge.customer_id,
                        challenge.otp_hash,
                        challenge.status,
                        challenge.expires_at.replace(tzinfo=None),
                    ),
                )
            conn.commit()

    def find_by_id(self, challenge_id):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM mfa_challenges WHERE challenge_id=%s", (challenge_id,))
                return cursor.fetchone()

    def mark_verified(self, challenge_id):
        with self.connection_factory() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE mfa_challenges SET status='VERIFIED', verified_at=UTC_TIMESTAMP() WHERE challenge_id=%s",
                    (challenge_id,),
                )
            conn.commit()

