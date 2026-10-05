"""Service JWT (x-service-token): la implementación vive en el paquete
compartido satc_shared.auth. Este módulo se mantiene para no romper los
imports existentes (`from utils.generate_service_jwt import generate_service_jwt`)."""
from satc_shared.auth import generate_service_jwt

__all__ = ["generate_service_jwt"]
