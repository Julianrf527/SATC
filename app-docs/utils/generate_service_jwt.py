from datetime import datetime
from datetime import datetime, timedelta
from jose import jwt


def generate_service_jwt(service_name: str, secret_key: str) -> str:
    payload = {
        "service": service_name,
        "exp": datetime.utcnow() + timedelta(minutes=5),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

