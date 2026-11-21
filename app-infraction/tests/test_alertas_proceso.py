"""Alertas del proceso (visita, acoger concepto, seguimiento, actos de medida
y de cierre) y aviso de la fecha de programación de la visita.

Reglas: services/alertas.py (docstring). Las unitarias arman ``_Datos`` a
mano; las de integración pasan por la carga en bloque contra la BD.
"""
from datetime import date, datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from sqlalchemy import select

from db.models.acto_administrativo import ActoAdministrativo
from db.models.documento_proceso import DocumentoProceso, DocumentoProcesoVersion
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.informe_tecnico import InformeTecnico
from db.models.notificacion import Notificacion
from db.models.oficio_remite import OficioRemite
from db.models.solicitud_informacion import SolicitudInformacion
from db.migrations import _rellenar_fecha_asignacion
from services.alertas import (
    _Datos,
    _calcular,
    advertencia_programacion,
    calcular_alertas_expedientes,
    fecha_limite_habiles,
    limite_programacion,
)

HOY = date(2026, 6, 10)  # miércoles
BOG = ZoneInfo("America/Bogota")


def _informe(id=1, profesional=None, programada=None, asignacion=None, aceptado=None):
    return SimpleNamespace(id=id, profesional_asignado_id=profesional, fecha_programacion_visita=programada,
                           fecha_asignacion=asignacion, fecha_aceptacion_informe=aceptado,
                           fecha_creacion=datetime(2026, 5, 1, tzinfo=BOG))


def _concepto(id=10, tipo="AUTO_REQUERIMIENTO", acto=None, termino=None, dias=None):
    return SimpleNamespace(id=id, tipo_acogida_concepto=tipo, acto_administrativo_id=acto,
                           fecha_termino_calculada=termino, dias_termino=dias)


def _respuesta(fecha=date(2026, 5, 4), medida=False):
    return SimpleNamespace(fecha_creacion=fecha, fecha_radicado=fecha, requiere_medida_preventiva=medida)


def _datos(**kw):
    kw.setdefault("respuesta", _respuesta())
    return _Datos(fecha_creacion=date(2026, 4, 1), tiene_respuesta=kw["respuesta"] is not None, **kw)


def _claves(alertas):
    return set(alertas)


class TestVisita:
    def test_sin_asignar_cuenta_desde_la_respuesta(self):
        a = _calcular(_datos(informes={"VISITA": _informe()}), HOY)
        assert _claves(a) == {"visita_asignar"}
        assert a["visita_asignar"]["fecha_inicio"] == "2026-05-04"
        assert a["visita_asignar"]["fecha_limite"] == fecha_limite_habiles(date(2026, 5, 4), 30).isoformat()

    def test_sin_informe_tambien_pide_asignar(self):
        assert _claves(_calcular(_datos(), HOY)) == {"visita_asignar"}

    def test_tecnico_sin_fecha_sigue_sin_asignar(self):
        a = _calcular(_datos(informes={"VISITA": _informe(profesional=5)}), HOY)
        assert _claves(a) == {"visita_asignar"}

    def test_asignada_pide_primera_version_desde_la_asignacion(self):
        inf = _informe(profesional=5, programada=date(2026, 6, 20), asignacion=date(2026, 6, 1))
        a = _calcular(_datos(informes={"VISITA": inf}), HOY)
        assert _claves(a) == {"visita_primera_version"}
        assert a["visita_primera_version"]["fecha_inicio"] == "2026-06-01"
        assert a["visita_primera_version"]["plazo_legal"] == "30 días hábiles desde la asignación de la visita"

    def test_con_primera_version_pide_aprobacion(self):
        inf = _informe(profesional=5, programada=date(2026, 6, 20), asignacion=date(2026, 6, 1))
        d = _datos(informes={"VISITA": inf}, primeras_versiones={("informe_tecnico", 1): date(2026, 6, 5)})
        a = _calcular(d, HOY)
        assert _claves(a) == {"visita_aprobacion"}
        assert a["visita_aprobacion"]["fecha_limite"] == fecha_limite_habiles(date(2026, 6, 5), 20).isoformat()

    def test_aceptado_no_tiene_alertas_de_visita(self):
        inf = _informe(profesional=5, programada=date(2026, 6, 1), aceptado=date(2026, 6, 8))
        a = _calcular(_datos(informes={"VISITA": inf}), HOY)
        # Aceptado y sin concepto: ahora corre "proyectar acto".
        assert _claves(a) == {"concepto_acto_proyectar"}


class TestConcepto:
    def _base(self, **kw):
        inf = _informe(profesional=5, programada=date(2026, 5, 20), aceptado=date(2026, 6, 1))
        return _datos(informes={"VISITA": inf}, **kw)

    def test_auto_requerimiento_proyectar_desde_la_version_firmada(self):
        a = _calcular(self._base(concepto=_concepto()), HOY)
        assert _claves(a) == {"concepto_acto_proyectar"}
        alerta = a["concepto_acto_proyectar"]
        assert alerta["fecha_inicio"] == "2026-06-01"
        assert alerta["fecha_limite"] == fecha_limite_habiles(date(2026, 6, 1), 17).isoformat()
        assert "auto de requerimiento" in alerta["accion_requerida"]

    def test_primera_version_del_auto_pide_aprobacion(self):
        d = self._base(concepto=_concepto(), primeras_versiones={("etapa_concepto", 10): date(2026, 6, 3)})
        a = _calcular(d, HOY)
        assert _claves(a) == {"concepto_acto_aprobacion"}
        assert a["concepto_acto_aprobacion"]["fecha_limite"] == fecha_limite_habiles(date(2026, 6, 3), 25).isoformat()

    def test_acto_creado_cierra_las_dos(self):
        d = self._base(concepto=_concepto(acto=99), primeras_versiones={("etapa_concepto", 10): date(2026, 6, 3)})
        assert "concepto_acto_aprobacion" not in _calcular(d, HOY)
        assert "concepto_acto_proyectar" not in _calcular(self._base(concepto=_concepto(acto=99)), HOY)

    def test_solicitud_sin_respuesta_frena_el_acto(self):
        sol = SimpleNamespace(fecha_radicado="2026-06-02", fecha_radicado_respuesta=None)
        a = _calcular(self._base(concepto=_concepto(), solicitudes={10: sol}), HOY)
        assert _claves(a) == {"concepto_solicitud"}
        assert a["concepto_solicitud"]["fecha_limite"] == fecha_limite_habiles(date(2026, 6, 2), 10).isoformat()

    def test_con_respuesta_el_acto_cuenta_desde_ella(self):
        sol = SimpleNamespace(fecha_radicado="2026-06-02", fecha_radicado_respuesta="2026-06-05")
        a = _calcular(self._base(concepto=_concepto(), solicitudes={10: sol}), HOY)
        assert _claves(a) == {"concepto_acto_proyectar"}
        assert a["concepto_acto_proyectar"]["fecha_inicio"] == "2026-06-05"
        assert "solicitud de información" in a["concepto_acto_proyectar"]["plazo_legal"]

    def test_oficio_sin_acto_en_concepto_ni_en_cierre_sin_oficio(self):
        assert _calcular(self._base(concepto=_concepto(tipo="OFICIO")), HOY) == {}

    def test_resolucion_archivo_alerta_va_al_acto_de_cierre(self):
        a = _calcular(self._base(concepto=_concepto(tipo="RESOLUCION_ARCHIVO")), HOY)
        assert _claves(a) == {"cierre_acto_proyectar"}
        assert a["cierre_acto_proyectar"]["fecha_inicio"] == "2026-06-01"
        assert a["cierre_acto_proyectar"]["etapa"] == "Cierre"


class TestCierre:
    def _aceptado(self, **kw):
        inf = _informe(profesional=5, programada=date(2026, 5, 20), aceptado=date(2026, 5, 25))
        return _datos(informes={"VISITA": inf}, **kw)

    def test_oficio_cuenta_desde_la_remision(self):
        oficio = SimpleNamespace(fecha_remitido="2026-06-03", archivo_remite_id=7)
        a = _calcular(self._aceptado(concepto=_concepto(tipo="OFICIO"), oficios={10: oficio}), HOY)
        assert _claves(a) == {"cierre_acto_proyectar"}
        assert a["cierre_acto_proyectar"]["fecha_inicio"] == "2026-06-03"

    def test_oficio_sin_documento_no_habilita(self):
        oficio = SimpleNamespace(fecha_remitido="2026-06-03", archivo_remite_id=None)
        assert _calcular(self._aceptado(concepto=_concepto(tipo="OFICIO"), oficios={10: oficio}), HOY) == {}

    def test_auto_de_seguimiento_cuenta_desde_la_primera_notificacion_exitosa(self):
        seg = _informe(id=2, profesional=5, programada=date(2026, 5, 27), aceptado=date(2026, 5, 28))
        cs = _concepto(id=20, acto=30)
        d = _datos(concepto=_concepto(acto=9, termino=date(2026, 5, 20), dias=10),
                   informes={"VISITA": _informe(aceptado=date(2026, 5, 1), profesional=5,
                                                programada=date(2026, 4, 20)),
                             "SEGUIMIENTO": seg},
                   concepto_seguimiento=cs, primera_exitosa={30: date(2026, 6, 4)})
        a = _calcular(d, HOY)
        assert a["cierre_acto_proyectar"]["fecha_inicio"] == "2026-06-04"
        assert "notificación exitosa" in a["cierre_acto_proyectar"]["plazo_legal"]

    def test_acto_de_cierre_en_revision_y_listo(self):
        d = self._aceptado(concepto=_concepto(tipo="RESOLUCION_ARCHIVO"),
                           cierre=SimpleNamespace(id=50, acto_administrativo_id=None),
                           primeras_versiones={("etapa_cierre", 50): date(2026, 6, 2)})
        assert _claves(_calcular(d, HOY)) == {"cierre_acto_aprobacion"}
        d.cierre = SimpleNamespace(id=50, acto_administrativo_id=77)
        assert _calcular(d, HOY) == {}


class TestSeguimiento:
    def _base(self, termino, **kw):
        inf = _informe(profesional=5, programada=date(2026, 4, 20), aceptado=date(2026, 5, 1))
        return _datos(informes={"VISITA": inf, **kw.pop("informes", {})},
                      concepto=_concepto(acto=9, termino=termino, dias=10), **kw)

    def test_termino_en_curso_no_pide_asignar(self):
        a = _calcular(self._base(date(2026, 6, 15)), HOY)
        assert "seguimiento_asignar" not in a
        assert "concepto_termino" in a

    def test_termino_vencido_pide_asignar_desde_el_vencimiento(self):
        a = _calcular(self._base(date(2026, 6, 5)), HOY)
        assert a["seguimiento_asignar"]["fecha_inicio"] == "2026-06-05"
        assert a["seguimiento_asignar"]["etapa"] == "Seguimiento"

    def test_seguimiento_asignado_y_concepto_seguimiento(self):
        seg = _informe(id=2, profesional=5, programada=date(2026, 6, 1), asignacion=date(2026, 5, 29))
        a = _calcular(self._base(date(2026, 5, 20), informes={"SEGUIMIENTO": seg}), HOY)
        assert "seguimiento_primera_version" in a
        seg.fecha_aceptacion_informe = date(2026, 6, 8)
        a = _calcular(self._base(date(2026, 5, 20), informes={"SEGUIMIENTO": seg}), HOY)
        assert "seguimiento_primera_version" not in a
        assert a["concepto_seguimiento_acto_proyectar"]["fecha_inicio"] == "2026-06-08"
        assert a["concepto_seguimiento_acto_proyectar"]["etapa"] == "Concepto seguimiento"


class TestMedida:
    def test_medida_preventiva_desde_la_respuesta(self):
        a = _calcular(_datos(respuesta=_respuesta(date(2026, 6, 1), medida=True)), HOY)
        assert a["medida_acto_proyectar"]["fecha_inicio"] == "2026-06-01"
        assert a["medida_acto_proyectar"]["etapa"] == "Respuesta"

    def test_medida_con_version_y_con_acto(self):
        medida = SimpleNamespace(id=3, acto_administrativo_id=None)
        d = _datos(respuesta=_respuesta(date(2026, 6, 1), medida=True), medida=medida,
                   primeras_versiones={("medida_preventiva", 3): date(2026, 6, 3)})
        assert "medida_acto_aprobacion" in _calcular(d, HOY)
        medida.acto_administrativo_id = 8
        assert not {"medida_acto_proyectar", "medida_acto_aprobacion"} & _claves(_calcular(d, HOY))

    def test_sin_medida_no_alerta(self):
        assert "medida_acto_proyectar" not in _calcular(_datos(), HOY)


class TestSemaforoHabiles:
    def test_cuenta_dias_habiles(self):
        a = _calcular(_datos(respuesta=None), date(2026, 4, 6))  # creado miércoles 1-abr
        s = a["respuesta_plazo"]["semaforo"]
        # 1-abr → 6-abr: jue 2 y vie 3 son festivos (Semana Santa); lun 6 sí cuenta.
        assert s["dias_totales"] == 15
        assert s["dias_transcurridos"] == 1


class TestAdvertenciaProgramacion:
    def test_dentro_del_plazo(self):
        assert advertencia_programacion(limite_programacion(HOY), HOY) is None
        assert advertencia_programacion(None, HOY) is None

    def test_fuera_del_plazo(self):
        limite = limite_programacion(HOY)
        msg = advertencia_programacion(date.fromordinal(limite.toordinal() + 1), HOY)
        assert msg.startswith("Fecha fuera del plazo")
        assert limite.strftime("%d/%m/%Y") in msg


# ───────────────────────────────────────────────────────────── integración

async def _proceso(db, exp_id, etapa_tipo, ref_id, tipo, fecha_version=None):
    p = DocumentoProceso(nombre="p", estado="en_revision", creador_id=1, expediente_id=exp_id,
                         tipo_documento=tipo, etapa_tipo=etapa_tipo, etapa_ref_id=ref_id,
                         fecha_creacion=datetime(2026, 5, 2, 9, tzinfo=BOG))
    db.add(p)
    await db.flush()
    if fecha_version:
        db.add(DocumentoProcesoVersion(proceso_id=p.id, numero_version=1, archivo_url="x", archivo_nombre="x.pdf",
                                       usuario_subida_id=1, fecha_subida=fecha_version))
        await db.flush()
    return p


class TestCargaEnBloque:
    async def test_carga_versiones_solicitud_oficio_y_cierre(self, db_session, make_expediente):
        db = db_session
        # 1) Visita aceptada + auto de requerimiento con primera versión (hora UTC del día siguiente).
        e1 = await make_expediente()
        db.add(EtapaRespuesta(expediente_id=e1.id, fecha_radicado=date(2026, 5, 4), fecha_creacion=date(2026, 5, 4)))
        inf = InformeTecnico(expediente_id=e1.id, tipo_informe="VISITA", profesional_asignado_id=5,
                             fecha_programacion_visita=date(2026, 5, 10), fecha_aceptacion_informe=date(2026, 6, 1))
        c1 = EtapaAcogerConcepto(expediente_id=e1.id, tipo_acogida_concepto="AUTO_REQUERIMIENTO")
        db.add_all([inf, c1])
        await db.flush()
        await _proceso(db, e1.id, "etapa_concepto", c1.id, "ACTO_CONCEPTO",
                       datetime(2026, 6, 3, 22, 30, tzinfo=BOG))
        # 2) Concepto OFICIO con oficio y cierre con versión.
        e2 = await make_expediente()
        db.add(EtapaRespuesta(expediente_id=e2.id, fecha_radicado=date(2026, 5, 4), fecha_creacion=date(2026, 5, 4)))
        db.add(InformeTecnico(expediente_id=e2.id, tipo_informe="VISITA", profesional_asignado_id=5,
                              fecha_programacion_visita=date(2026, 5, 10), fecha_aceptacion_informe=date(2026, 5, 20)))
        c2 = EtapaAcogerConcepto(expediente_id=e2.id, tipo_acogida_concepto="OFICIO")
        db.add(c2)
        await db.flush()
        db.add(OficioRemite(etapa_acoger_concepto_id=c2.id, radicado="R1", fecha_remitido="2026-06-02",
                            archivo_remite_id=4))
        cierre = EtapaCierre(expediente_id=e2.id)
        db.add(cierre)
        await db.flush()
        await _proceso(db, e2.id, "etapa_cierre", cierre.id, "ACTO_CIERRE", datetime(2026, 6, 4, 10, tzinfo=BOG))
        # 3) Solicitud de información pendiente.
        e3 = await make_expediente()
        db.add(EtapaRespuesta(expediente_id=e3.id, fecha_radicado=date(2026, 5, 4), fecha_creacion=date(2026, 5, 4)))
        db.add(InformeTecnico(expediente_id=e3.id, tipo_informe="VISITA", profesional_asignado_id=5,
                              fecha_programacion_visita=date(2026, 5, 10), fecha_aceptacion_informe=date(2026, 5, 20)))
        c3 = EtapaAcogerConcepto(expediente_id=e3.id, tipo_acogida_concepto="AUTO_REQUERIMIENTO")
        db.add(c3)
        await db.flush()
        db.add(SolicitudInformacion(etapa_acoger_concepto_id=c3.id, radicado="S1", fecha_radicado="2026-06-02",
                                    archivo_solicitud_id=1))
        # 4) Archivado: sin alertas aunque le falte la respuesta.
        e4 = await make_expediente(archivado=True)
        await db.commit()

        res = await calcular_alertas_expedientes([e1.id, e2.id, e3.id, e4.id], db, HOY)

        assert set(res[e1.id]) == {"concepto_acto_aprobacion"}
        assert res[e1.id]["concepto_acto_aprobacion"]["fecha_inicio"] == "2026-06-03"  # día en Bogotá
        assert set(res[e2.id]) == {"cierre_acto_aprobacion"}
        assert res[e2.id]["cierre_acto_aprobacion"]["fecha_inicio"] == "2026-06-04"
        assert set(res[e3.id]) == {"concepto_solicitud"}
        assert e4.id not in res

    async def test_primera_notificacion_exitosa_habilita_el_cierre(self, db_session, make_expediente):
        db = db_session
        e = await make_expediente()
        db.add(EtapaRespuesta(expediente_id=e.id, fecha_radicado=date(2026, 4, 1), fecha_creacion=date(2026, 4, 1)))
        for tipo, aceptado in (("VISITA", date(2026, 4, 20)), ("SEGUIMIENTO", date(2026, 5, 25))):
            db.add(InformeTecnico(expediente_id=e.id, tipo_informe=tipo, profesional_asignado_id=5,
                                  fecha_programacion_visita=date(2026, 4, 10), fecha_aceptacion_informe=aceptado))
        a1, a2 = ActoAdministrativo(tipo_acto="auto"), ActoAdministrativo(tipo_acto="auto")
        db.add_all([a1, a2])
        await db.flush()
        db.add(EtapaAcogerConcepto(expediente_id=e.id, tipo_acogida_concepto="AUTO_REQUERIMIENTO",
                                   acto_administrativo_id=a1.id))
        db.add(EtapaAcogerConcepto(expediente_id=e.id, instancia="SEGUIMIENTO",
                                   tipo_acogida_concepto="AUTO_REQUERIMIENTO", acto_administrativo_id=a2.id))
        db.add(Notificacion(acto_administrativo_id=a2.id, involucrado_id=1, notificacion_exitosa=True,
                            fecha_notificacion=datetime(2026, 6, 4, 15, tzinfo=BOG)))
        await db.commit()

        res = (await calcular_alertas_expedientes([e.id], db, HOY))[e.id]

        assert res["cierre_acto_proyectar"]["fecha_inicio"] == "2026-06-04"


class TestMigracionFechaAsignacion:
    async def test_rellena_con_el_primer_proceso_o_la_creacion(self, db_session, make_expediente):
        db = db_session
        e = await make_expediente()
        con_proceso = InformeTecnico(expediente_id=e.id, tipo_informe="VISITA", profesional_asignado_id=5,
                                     fecha_programacion_visita=date(2026, 5, 10),
                                     fecha_creacion=datetime(2026, 4, 1, 9, tzinfo=BOG))
        sin_proceso = InformeTecnico(expediente_id=e.id, tipo_informe="SEGUIMIENTO", profesional_asignado_id=5,
                                     fecha_programacion_visita=date(2026, 5, 10),
                                     fecha_creacion=datetime(2026, 4, 3, 22, tzinfo=BOG))
        sin_asignar = InformeTecnico(expediente_id=e.id, tipo_informe="VISITA")
        db.add_all([con_proceso, sin_proceso, sin_asignar])
        await db.flush()
        await _proceso(db, e.id, "informe_tecnico", con_proceso.id, "INFORME_VISITA")
        exp_id, ids = e.id, (con_proceso.id, sin_proceso.id, sin_asignar.id)

        await _rellenar_fecha_asignacion(await db.connection())
        db.expire_all()

        fechas = dict((await db.execute(
            select(InformeTecnico.id, InformeTecnico.fecha_asignacion).where(InformeTecnico.expediente_id == exp_id)
        )).all())
        assert fechas[ids[0]] == date(2026, 5, 2)
        assert fechas[ids[1]] == date(2026, 4, 3)  # 22:00 en Bogotá (día siguiente en UTC)
        assert fechas[ids[2]] is None
