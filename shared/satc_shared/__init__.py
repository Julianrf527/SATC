"""Paquete compartido de los microservicios SATC.

- ``satc_shared.auth``: generación/verificación del service JWT (x-service-token).
- ``satc_shared.clients``: clientes HTTP async tipados para llamadas entre servicios.
- ``satc_shared.review_process``: helper genérico de proceso de revisión de documentos.

Regla: este paquete NO conoce flujos concretos (informe técnico, documentos
genéricos...). Cada app extiende lo genérico en su propio código.
"""

__version__ = "0.1.0"
