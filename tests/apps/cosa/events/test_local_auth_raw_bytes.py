import hashlib
import hmac

from apps.cosa.events.local_auth import LocalServiceAuth

SECRET = "x" * 40


def test_sign_matches_manual_hmac_over_raw_bytes():
    raw = '{"eventType":"thread.updated","note":"Xin chào — cần hỗ trợ"}'.encode("utf-8")
    auth = LocalServiceAuth(SECRET)
    expected = hmac.new(SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    assert auth.sign(raw) == expected


def test_verify_roundtrip_true_and_tamper_false():
    raw = b'{"a":1,"b":{"c":[2,3]}}'
    auth = LocalServiceAuth(SECRET)
    sig = auth.sign(raw)
    assert auth.verify(sig, raw) is True
    assert auth.verify(sig, raw + b" ") is False
    assert auth.verify("", raw) is False


def test_verify_false_when_secret_missing():
    raw = b"{}"
    assert LocalServiceAuth("").verify("deadbeef", raw) is False
