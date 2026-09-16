import hashlib
import hmac
import time

from wirebox.verify_webhook import verify_webhook


def test_verify_webhook_valid_standard_headers():
    secret = "whsec_test_secret_key_123"
    payload = b'{"event_type": "message.received", "id": "evt_123"}'
    req_id = "req_01J8DEF999XYZ888"
    now = str(int(time.time()))

    signed_data = f"{req_id}.{now}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()

    headers = {
        "X-Wirebox-Signature": f"sha256={digest}",
        "X-Wirebox-Request-ID": req_id,
        "X-Wirebox-Timestamp": now,
    }

    assert verify_webhook(payload=payload, headers=headers, secret=secret) is True


def test_verify_webhook_valid_string_payload_and_raw_hex():
    secret = "whsec_test_secret_key_123"
    payload_str = '{"event_type": "message.received", "id": "evt_456"}'
    req_id = "req_01J8DEF999XYZ888"
    now = str(int(time.time()))

    signed_data = f"{req_id}.{now}.{payload_str}".encode()
    digest = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()

    headers = {
        "x-wirebox-signature": digest,  # no sha256= prefix
        "x-wirebox-request-id": req_id,
        "x-wirebox-timestamp": now,
    }

    assert verify_webhook(payload=payload_str, headers=headers, secret=secret) is True


def test_verify_webhook_compound_header():
    secret = "whsec_test_secret_key_123"
    payload = '{"ping": "pong"}'
    now = str(int(time.time()))

    signed_data = f"{now}.{payload}".encode()
    digest = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()

    headers = {
        "x-wirebox-signature": f"t={now},v1={digest}",
    }

    assert verify_webhook(payload=payload, headers=headers, secret=secret) is True


def test_verify_webhook_tampered_payload():
    secret = "whsec_test_secret_key_123"
    payload = b'{"amount": 100}'
    tampered = b'{"amount": 9999}'
    req_id = "req_123"
    now = str(int(time.time()))

    signed_data = f"{req_id}.{now}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()

    headers = {
        "x-wirebox-signature": f"sha256={digest}",
        "x-wirebox-request-id": req_id,
        "x-wirebox-timestamp": now,
    }

    assert verify_webhook(payload=tampered, headers=headers, secret=secret) is False


def test_verify_webhook_wrong_secret():
    secret = "whsec_test_secret_key_123"
    wrong_secret = "whsec_another_secret_456"
    payload = b'{"test": true}'
    req_id = "req_123"
    now = str(int(time.time()))

    signed_data = f"{req_id}.{now}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()

    headers = {
        "x-wirebox-signature": f"sha256={digest}",
        "x-wirebox-request-id": req_id,
        "x-wirebox-timestamp": now,
    }

    assert verify_webhook(payload=payload, headers=headers, secret=wrong_secret) is False


def test_verify_webhook_expired_timestamp():
    secret = "whsec_test_secret_key_123"
    payload = b'{"test": true}'
    req_id = "req_123"
    expired = str(int(time.time()) - 600)  # 10 minutes ago

    signed_data = f"{req_id}.{expired}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed_data, hashlib.sha256).hexdigest()

    headers = {
        "x-wirebox-signature": f"sha256={digest}",
        "x-wirebox-request-id": req_id,
        "x-wirebox-timestamp": expired,
    }

    # Fails with default 300s tolerance
    assert verify_webhook(payload=payload, headers=headers, secret=secret) is False
    # Passes if tolerance_seconds=0 disables check
    assert (
        verify_webhook(payload=payload, headers=headers, secret=secret, tolerance_seconds=0) is True
    )


def test_verify_webhook_missing_data():
    assert verify_webhook(payload=b"", headers={}, secret="") is False
    assert verify_webhook(payload=b"test", headers={}, secret="whsec_123") is False
