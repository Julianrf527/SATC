import pytest
from jose import jwt

from satc_shared.auth import (
    ServiceTokenConfigError,
    ServiceTokenInvalid,
    ServiceTokenMissing,
    expected_callers_from_env,
    generate_service_jwt,
    identify_caller,
    service_headers,
)


def test_claims_y_algoritmo():
    token = generate_service_jwt("docs-service", "s3cret")
    assert jwt.get_unverified_header(token)["alg"] == "HS256"
    payload = jwt.decode(token, "s3cret", algorithms=["HS256"])
    assert payload["service"] == "docs-service"
    assert payload["exp"] - payload["iat"] == 300


def test_identify_caller():
    callers = {"sanctioning-service": "a", "infraction-service": "b"}
    assert identify_caller(generate_service_jwt("infraction-service", "b"), callers) == "infraction-service"
    # firma válida pero identidad falseada
    with pytest.raises(ServiceTokenInvalid):
        identify_caller(generate_service_jwt("sanctioning-service", "b"), callers)
    with pytest.raises(ServiceTokenInvalid):
        identify_caller(generate_service_jwt("infraction-service", "otro"), callers)
    with pytest.raises(ServiceTokenMissing):
        identify_caller(None, callers)
    with pytest.raises(ServiceTokenConfigError):
        identify_caller("x", {})


def test_token_expirado():
    from datetime import timedelta

    token = generate_service_jwt("docs-service", "a", ttl=timedelta(seconds=-1))
    with pytest.raises(ServiceTokenInvalid):
        identify_caller(token, {"docs-service": "a"})


def test_expected_callers_from_env():
    env = {"SANCTIONING_SERVICE_SECRET": "a", "INFRACTION_SERVICE_SECRET": ""}
    assert expected_callers_from_env(["sanctioning-service", "infraction-service"], env) == {
        "sanctioning-service": "a"
    }
    with pytest.raises(KeyError):
        expected_callers_from_env(["desconocido"], env)


def test_service_headers_sin_secreto():
    with pytest.raises(ServiceTokenConfigError):
        service_headers("docs-service", None)
    assert "x-service-token" in service_headers("docs-service", "a")
