from sqlalchemy import Column, Integer, text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase

class Base(AsyncAttrs, DeclarativeBase):
    pass


class VersionadoMixin:
    """Bloqueo optimista (plan §7): el cliente envía la ``version`` que leyó y
    la escritura hace ``UPDATE ... WHERE id = :id AND version = :version``,
    incrementándola. 0 filas actualizadas → 409 "fue modificado por otra persona"."""

    version = Column(Integer, nullable=False, default=1, server_default=text("1"))
