import importlib
import os
import pathlib
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pymysql
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVICE_DIRS = {
    "clients": ROOT / "services" / "svc-clients-identite",
    "catalogue": ROOT / "services" / "svc-catalogue-offres",
    "lines": ROOT / "services" / "svc-lignes-services",
    "commands": ROOT / "services" / "svc-commandes-activations",
    "billing": ROOT / "services" / "svc-usage-facturation",
    "audit": ROOT / "services" / "svc-conformite-audit",
}


def _mysql_config(database):
    return {
        "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "cantelcox"),
        "password": os.getenv("MYSQL_PASSWORD", "cantelcox_dev"),
        "database": database,
        "charset": "utf8mb4",
        "autocommit": False,
        "cursorclass": pymysql.cursors.DictCursor,
    }


def _connect(database):
    return pymysql.connect(**_mysql_config(database))


def _mysql_available():
    try:
        conn = _connect("clients_identite")
        conn.close()
        return True
    except pymysql.MySQLError:
        return False


pytestmark = pytest.mark.skipif(
    not _mysql_available(),
    reason="MySQL integration dependency is not running on MYSQL_HOST/MYSQL_PORT",
)


@contextmanager
def _service_import(service_key):
    service_path = str(SERVICE_DIRS[service_key])
    root_path = str(ROOT)
    previous_path = list(sys.path)
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]
    sys.path.insert(0, root_path)
    sys.path.insert(0, service_path)
    try:
        yield importlib.import_module
    finally:
        for name in list(sys.modules):
            if name == "app" or name.startswith("app."):
                del sys.modules[name]
        sys.path[:] = previous_path


def _factory(database):
    return lambda: _connect(database)


def _delete_where(database, sql, params):
    with _connect(database) as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
        conn.commit()


def test_clients_identity_mysql_repositories_persist_customer_and_mfa_boundary():
    suffix = uuid.uuid4().hex
    customer_id = str(uuid.uuid4())
    challenge_id = str(uuid.uuid4())
    email = f"integration-{suffix}@example.test"

    try:
        with _service_import("clients") as module:
            Customer = module("app.domain.model.customer").Customer
            MfaChallenge = module("app.domain.model.mfa_challenge").MfaChallenge
            CustomerRepository = module(
                "app.adapters.outbound.persistence.mysql_customer_repository"
            ).MysqlCustomerRepository
            MfaRepository = module("app.adapters.outbound.persistence.mysql_mfa_repository").MysqlMfaRepository

            customers = CustomerRepository(_factory("clients_identite"))
            mfa = MfaRepository(_factory("clients_identite"))

            customers.create(
                Customer(
                    customer_id=customer_id,
                    email=email,
                    display_name="Integration Test",
                    legal_name="Integration Test",
                    address_line1="123 Rue Test",
                    city="Montreal",
                    province="QC",
                    postal_code="H1A1A1",
                    identity_document_type="driver_license",
                    identity_document_hash=f"hash-{suffix}",
                    customer_type="individual",
                    status="ACTIVE",
                    identity_status="VERIFIED",
                    risk_level="LOW",
                )
            )
            customers.set_password_hash(customer_id, "hashed-password")
            customers.record_failed_login(customer_id)
            customers.record_login_risk(customer_id, "MEDIUM")

            by_email = customers.find_by_email(email)
            assert by_email["customer_id"] == customer_id
            assert by_email["password_hash"] == "hashed-password"
            assert by_email["failed_login_attempts"] == 1
            assert by_email["last_login_risk"] == "MEDIUM"

            mfa.create(
                MfaChallenge(
                    challenge_id=challenge_id,
                    customer_id=customer_id,
                    otp_hash="otp-hash",
                    status="PENDING",
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
                )
            )
            assert mfa.find_by_id(challenge_id)["status"] == "PENDING"
            mfa.mark_verified(challenge_id)
            assert mfa.find_by_id(challenge_id)["status"] == "VERIFIED"
    finally:
        _delete_where("clients_identite", "DELETE FROM mfa_challenges WHERE challenge_id=%s", (challenge_id,))
        _delete_where("clients_identite", "DELETE FROM customers WHERE customer_id=%s", (customer_id,))


def test_catalogue_mysql_repository_reads_seeded_active_offers_boundary():
    with _service_import("catalogue") as module:
        OfferRepository = module("app.adapters.outbound.persistence.mysql_offer_repository").MysqlOfferRepository
        offers = OfferRepository(_factory("catalogue_offres"))

        offer = offers.find_by_id("forfait-5g-20gb")
        active = offers.list_active()

        assert offer["offer_id"] == "forfait-5g-20gb"
        assert offer["status"] == "ACTIVE"
        assert all(row["status"] == "ACTIVE" for row in active)


def test_lines_mysql_repository_persists_line_state_and_uniqueness_boundary():
    suffix = uuid.uuid4().hex[:12]
    line_id = str(uuid.uuid4())
    duplicate_line_id = str(uuid.uuid4())
    msisdn = f"1438{int(suffix[:8], 16) % 1_000_000_000:09d}"

    try:
        with _service_import("lines") as module:
            Line = module("app.domain.model.line").Line
            LineRepository = module("app.adapters.outbound.persistence.mysql_line_repository").MysqlLineRepository
            lines = LineRepository(_factory("lignes_services"))

            lines.create(
                Line(
                    line_id=line_id,
                    customer_id=str(uuid.uuid4()),
                    offer_id="forfait-5g-20gb",
                    msisdn=msisdn,
                    sim_type="ESIM",
                    sim_identifier=f"EID-{suffix}",
                    imsi=f"20893{int(suffix[:10], 16) % 10_000_000_000:010d}",
                    supi=f"imsi-20893{int(suffix[:10], 16) % 10_000_000_000:010d}",
                    status="PENDING",
                    hlr_status="PENDING",
                    number_mode="NEW",
                )
            )

            assert lines.find_by_id(line_id)["msisdn"] == msisdn
            assert lines.find_by_msisdn(msisdn)["line_id"] == line_id
            lines.mark_active(line_id)
            assert lines.find_by_id(line_id)["status"] == "ACTIVE"
            lines.mark_failed(line_id, "adapter failure")
            failed = lines.find_by_id(line_id)
            assert failed["status"] == "FAILED"
            assert failed["hlr_status"] == "FAILED"

            with pytest.raises(pymysql.err.IntegrityError):
                lines.create(
                    Line(
                        line_id=duplicate_line_id,
                        customer_id=str(uuid.uuid4()),
                        offer_id="forfait-5g-20gb",
                        msisdn=msisdn,
                        sim_type="SIM",
                        sim_identifier=f"ICCID-{suffix}",
                        imsi=f"20893{(int(suffix[:10], 16) + 1) % 10_000_000_000:010d}",
                        supi=f"imsi-20893{(int(suffix[:10], 16) + 1) % 10_000_000_000:010d}",
                        status="PENDING",
                        hlr_status="PENDING",
                    )
                )
    finally:
        _delete_where(
            "lignes_services",
            "DELETE FROM service_lines WHERE line_id IN (%s, %s)",
            (line_id, duplicate_line_id),
        )


def test_commandes_activations_mysql_repository_enforces_idempotency_boundary():
    activation_id = str(uuid.uuid4())
    order_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    activation_key = f"it-act-{uuid.uuid4()}"
    order_key = f"it-order-{uuid.uuid4()}"

    try:
        with _service_import("commands") as module:
            Activation = module("app.domain.model.activation").Activation
            Order = module("app.domain.model.order").Order
            Repository = module(
                "app.adapters.outbound.persistence.mysql_activation_repository"
            ).MysqlActivationRepository
            repo = Repository(_factory("commandes_activations"))

            activation = Activation(
                activation_id=activation_id,
                idempotency_key=activation_key,
                request_hash="a" * 64,
                customer_id=customer_id,
                offer_id="forfait-5g-20gb",
                line_id=str(uuid.uuid4()),
                status="ACTIVE",
                response_body={"activationId": activation_id, "status": "ACTIVE"},
                http_status=201,
            )
            repo.create(activation)
            stored_activation = repo.find_by_idempotency_key(activation_key)
            assert stored_activation["activation_id"] == activation_id

            with pytest.raises(pymysql.err.IntegrityError):
                repo.create(activation)

            order = Order(
                order_id=order_id,
                customer_id=customer_id,
                offer_id="forfait-5g-20gb",
                order_type="MOBILE_PLAN_SUBSCRIPTION",
                status="ACCEPTED",
                orchestration_status="READY_FOR_ACTIVATION",
                confirmation_status="SIMULATED_SENT",
                total_amount=49.99,
                currency="CAD",
                idempotency_key=order_key,
                request_hash="b" * 64,
                response_body={"orderId": order_id, "status": "ACCEPTED"},
                saga_id=str(uuid.uuid4()),
            )
            repo.create_order(order)
            stored_order = repo.find_order_by_idempotency_key(order_key)
            assert stored_order["order_id"] == order_id

            with pytest.raises(pymysql.err.IntegrityError):
                repo.create_order(order)
    finally:
        _delete_where("commandes_activations", "DELETE FROM activations WHERE activation_id=%s", (activation_id,))
        _delete_where("commandes_activations", "DELETE FROM orders WHERE order_id=%s", (order_id,))


def test_usage_facturation_mysql_repository_enforces_payment_exactly_once_boundary():
    customer_id = str(uuid.uuid4())
    invoice_id = str(uuid.uuid4())
    payment_id = str(uuid.uuid4())
    second_payment_id = str(uuid.uuid4())
    payment_key = f"it-pay-{uuid.uuid4()}"

    try:
        with _connect("usage_facturation") as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO invoices
                    (invoice_id, customer_id, billing_period, amount_due, currency, status, due_date, created_at)
                    VALUES (%s, %s, '2026-06', 49.99, 'CAD', 'OPEN', '2026-07-15', %s)
                    """,
                    (invoice_id, customer_id, datetime.now(timezone.utc).replace(tzinfo=None)),
                )
            conn.commit()

        with _service_import("billing") as module:
            Payment = module("app.domain.model.payment").Payment
            Repository = module(
                "app.adapters.outbound.persistence.mysql_usage_billing_repository"
            ).MysqlUsageBillingRepository
            repo = Repository(_factory("usage_facturation"))

            payment = Payment(
                payment_id=payment_id,
                invoice_id=invoice_id,
                customer_id=customer_id,
                idempotency_key=payment_key,
                request_hash="c" * 64,
                amount=49.99,
                currency="CAD",
                payment_method="SIMULATED_CARD",
                status="ACCEPTED",
                response_body={"paymentId": payment_id, "status": "ACCEPTED"},
                http_status=201,
            )
            repo.create_payment_and_mark_invoice_paid(payment)

            assert repo.find_payment_by_idempotency_key(payment_key)["payment_id"] == payment_id
            assert repo.get_invoice(invoice_id)["status"] == "PAID"

            with pytest.raises(pymysql.err.IntegrityError):
                repo.create_payment_and_mark_invoice_paid(
                    Payment(
                        payment_id=second_payment_id,
                        invoice_id=invoice_id,
                        customer_id=customer_id,
                        idempotency_key=f"it-pay-{uuid.uuid4()}",
                        request_hash="d" * 64,
                        amount=49.99,
                        currency="CAD",
                        payment_method="SIMULATED_CARD",
                        status="ACCEPTED",
                        response_body={"paymentId": second_payment_id, "status": "ACCEPTED"},
                        http_status=201,
                    )
                )
    finally:
        _delete_where("usage_facturation", "DELETE FROM payments WHERE invoice_id=%s", (invoice_id,))
        _delete_where("usage_facturation", "DELETE FROM invoices WHERE invoice_id=%s", (invoice_id,))


def test_conformite_audit_mysql_repository_is_append_only_boundary():
    audit_event_id = str(uuid.uuid4())
    trace_id = f"it-trace-{uuid.uuid4()}"

    with _service_import("audit") as module:
        AuditEvent = module("app.domain.model.audit_event").AuditEvent
        Repository = module("app.adapters.outbound.persistence.mysql_audit_repository").MysqlAuditRepository
        repo = Repository(_factory("conformite_audit"))

        repo.append(
            AuditEvent(
                audit_event_id=audit_event_id,
                event_type="INTEGRATION_TEST",
                actor_id="pytest",
                customer_id=str(uuid.uuid4()),
                resource_id="resource",
                trace_id=trace_id,
                source_service="integration-tests",
                result="SUCCESS",
                metadata={"boundary": "audit"},
            )
        )

        events = repo.list_by_trace_id(trace_id)
        assert len(events) == 1
        assert events[0]["auditEventId"] == audit_event_id

    with pytest.raises(pymysql.MySQLError):
        _delete_where("conformite_audit", "DELETE FROM audit_events WHERE audit_event_id=%s", (audit_event_id,))
