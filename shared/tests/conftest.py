"""Modelos concretos de prueba (como los definiría una app) sobre SQLite async."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from satc_shared.review_process import (
    AsignacionRevisorMixin,
    AuditoriaRevisionMixin,
    ProcesoRevisionMixin,
    ReviewModels,
    RevisionMixin,
    VersionRevisionMixin,
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Proceso(ProcesoRevisionMixin, Base):
    __tablename__ = "test_procesos"


class Version(VersionRevisionMixin, Base):
    __tablename__ = "test_versiones"
    __proceso_tabla__ = "test_procesos"


class Revision(RevisionMixin, Base):
    __tablename__ = "test_revisiones"
    __proceso_tabla__ = "test_procesos"


class Auditoria(AuditoriaRevisionMixin, Base):
    __tablename__ = "test_auditoria"
    __proceso_tabla__ = "test_procesos"


class Asignacion(AsignacionRevisorMixin, Base):
    __tablename__ = "test_asignaciones"
    __proceso_tabla__ = "test_procesos"


MODELS = ReviewModels(
    proceso=Proceso, version=Version, revision=Revision, auditoria=Auditoria, asignacion=Asignacion
)


class FakeTracker:
    def __init__(self, ok: bool = True, falla: bool = False):
        self.incrementos: list[list[int]] = []
        self.decrementos: list[list[int]] = []
        self.ok = ok
        self.falla = falla

    async def increment_usage(self, file_ids):
        if self.falla:
            raise RuntimeError("app-docs caído")
        self.incrementos.append(list(file_ids))
        return {"ok": self.ok}

    async def decrement_usage(self, file_ids):
        self.decrementos.append(list(file_ids))
        return {"ok": True}


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(
        "sqlite+aiosqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def tracker():
    return FakeTracker()
