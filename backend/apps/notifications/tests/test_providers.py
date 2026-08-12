from apps.notifications.providers import MockWebhookProvider, sign_payload


def test_sign_payload_is_deterministic_hmac_sha256():
    signature_a = sign_payload(payload_bytes=b'{"a":1}', secret="s3cret")
    signature_b = sign_payload(payload_bytes=b'{"a":1}', secret="s3cret")

    assert signature_a == signature_b
    assert len(signature_a) == 64  # hex-encoded sha256 digest


def test_sign_payload_changes_with_the_secret():
    signature_a = sign_payload(payload_bytes=b'{"a":1}', secret="secret-one")
    signature_b = sign_payload(payload_bytes=b'{"a":1}', secret="secret-two")

    assert signature_a != signature_b


def test_mock_provider_never_touches_the_network_and_always_succeeds():
    status_code = MockWebhookProvider().deliver(
        url="https://example.com/hook", payload={"x": 1}, secret="s3cret"
    )

    assert status_code == 200
