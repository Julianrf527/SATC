"""Validaciones de negocio del plan §6 (V4–V13) y del orden del flujo §4.

Una función por regla. Todas reciben la foto ``Estado`` (``services/etapas.py``)
y devuelven ``None`` si la regla se cumple o el **motivo** (texto para el
usuario) si no. Las rutas las convierten en error con ``etapas.exigir`` (400;
super gestión las omite, §2.1) y ``etapas_lectura`` las usa para calcular
``habilitada`` / ``motivos_bloqueo`` / ``acciones_disponibles``: una sola
definición de cada regla.

V1 (permiso de gestión) → ``core.acceso.requiere_gestion``; V2 (encargado) →
``etapas.exigir_encargado`` y la asignación atómica; V3 (técnico) →
``etapas.crear_concepto`` / ``cargar_concepto_final``; V14 → servicio de
involucrados (A); V15 → ``etapas.enlazar_hijo`` + ``unique``; V16 → ``unique``
de ``expediente_id`` (``integridad_a_409``).
"""
from __future__ import annotations

from typing import Optional

from db.models import TipoDecision

Motivo = Optional[str]


def primera(*motivos: Motivo) -> Motivo:
    for m in motivos:
        if m:
            return m
    return None


# ═══════════════════════════════════════════════════════════════ §6

def v4_auto_admite(e) -> Motivo:
    """V4: ninguna etapa sin auto admite (firmado y numerado: plan §4-Etapa 1
    "sin auto admite no puede existir ninguna etapa siguiente")."""
    if e.admite is None or not e.admite.acto_admin_id:
        return "Primero debe existir el auto que admite firmado y numerado (V4)"
    return None


def v5_concepto_etapa2(e) -> Motivo:
    """V5: el concepto de la etapa 2 nace al cargar el auto admite con técnico y
    fecha de visita."""
    if e.concepto2 is not None:
        return None
    return v4_auto_admite(e) or (
        "El concepto técnico nace al cargar el auto admite firmado con técnico y fecha de visita (V5)"
    )


def v6_requerimiento(e) -> Motivo:
    """V6: requerimiento de la etapa 3 solo si existe el concepto de la etapa 2
    (con fecha de concepto, plan §4-Etapa 3)."""
    if e.concepto2 is None or e.concepto2.fecha_aceptacion is None:
        return primera(v4_auto_admite(e), "Primero debe estar cargado el concepto técnico de la etapa 2 (V6)")
    return v4_auto_admite(e)


def v7_decision(e) -> Motivo:
    """V7: decisión solo si existe la constancia de fijación de la Alcaldía (y
    el auto admite, plan §4-Etapa 4). No requiere concepto técnico."""
    motivo = v4_auto_admite(e)
    if motivo:
        return motivo
    if not e.admite.doc_constancia_fijacion_aviso_id:
        return "Primero debe cargarse la constancia de fijación de la Alcaldía (V7)"
    return None


def v8_requiere_memorias(decision: TipoDecision, requiere_memorias: Optional[bool]) -> Motivo:
    """V8: ``requiere_memorias = true`` solo si la decisión es OTORGADA."""
    if requiere_memorias and decision != TipoDecision.OTORGADA:
        return "Solo una decisión OTORGADA puede requerir memorias de cálculo (V8)"
    return None


def _decision_otorgada(e) -> bool:
    return e.decision is not None and e.decision.decision == TipoDecision.OTORGADA


def v9_memorias(e) -> Motivo:
    """V9: memorias de cálculo solo si la decisión OTORGADA exige planos."""
    if not _decision_otorgada(e) or not e.decision.requiere_memorias:
        return "Las memorias de cálculo solo aplican si la decisión es OTORGADA y requiere planos (V9)"
    return None


def v10_obras(e) -> Motivo:
    """V10: recibo de obras solo si la decisión es OTORGADA; si requiere
    memorias, además deben estar aprobadas (acto que aprueba)."""
    if not _decision_otorgada(e):
        return "El recibo de obras solo aplica si la decisión es OTORGADA (V10)"
    if e.decision.requiere_memorias and (e.memorias is None or not e.memorias.acto_admin_id):
        return "Primero deben estar aprobadas las memorias de cálculo (V10)"
    return None


def v11_requerimiento_memorias(e) -> Motivo:
    """V11: requerimiento de memorias solo si el concepto dice ``cumple = false``."""
    concepto = e.concepto("memorias")
    if concepto is None or concepto.doc_concepto_tecnico_id is None or concepto.cumple is not False:
        return "El requerimiento de memorias solo procede si el concepto técnico dice que NO cumple (V11)"
    return None


def v11_requerimiento_obras(e) -> Motivo:
    """V11: requerimiento de obras solo si el concepto dice ``cumple = false``."""
    concepto = e.concepto("obras")
    if concepto is None or concepto.doc_concepto_tecnico_id is None or concepto.cumple is not False:
        return "El requerimiento de obras solo procede si el concepto técnico dice que NO cumple (V11)"
    return None


def v12_aprueba_memorias(e) -> Motivo:
    """V12: acto que aprueba memorias solo si el ÚLTIMO concepto (subsanación
    si existe, si no el de memorias) dice ``cumple = true``.
    TODO(negocio): si el concepto de la subsanación tampoco cumple, el modelo
    no admite otro ciclo (el plan "asume que cumple")."""
    if e.memorias is None:
        return "Primero debe registrarse el radicado de los planos"
    concepto = e.ultimo_concepto_memorias()
    if concepto is None or concepto.doc_concepto_tecnico_id is None or concepto.cumple is not True:
        return "El acto que aprueba las memorias solo procede si el último concepto técnico dice que cumple (V12)"
    return None


def v12_aprueba_obras(e) -> Motivo:
    """V12: acto que aprueba obras solo si el último concepto dice ``cumple = true``.
    TODO(negocio): el plan dice que el acto puede "exigir corregir o demoler" la
    obra, pero V12 lo limita a cuando cumple; se aplica V12."""
    if e.obras is None:
        return "Primero debe registrarse el informe del usuario"
    concepto = e.ultimo_concepto_obras()
    if concepto is None or concepto.doc_concepto_tecnico_id is None or concepto.cumple is not True:
        return "El acto que aprueba las obras solo procede si el último concepto técnico dice que cumple (V12)"
    return None


def v13_recurso(e) -> Motivo:
    """V13: recurso de reposición solo si la decisión está notificada
    (``services.actos.acto_notificado``, regla provisional de B)."""
    if e.decision is None or not e.decision.acto_admin_id:
        return "Primero debe existir la decisión firmada y numerada"
    if not e.decision_notificada:
        return "El recurso de reposición solo procede si la decisión está notificada (V13)"
    return None


# ═════════════════════════════════════════════ orden del flujo (§4)

def flujo_documentos_admite(e) -> Motivo:
    """Oficio a la Alcaldía / fijación del aviso / constancia: después del auto
    firmado (plan §4-Etapa 1 pasos 6–7)."""
    return v4_auto_admite(e)


def flujo_respuesta_requerimiento(e) -> Motivo:
    """Etapa 3 paso 4: el usuario responde al requerimiento ya expedido."""
    if e.req3 is None or not e.req3.acto_admin_id:
        return "Primero debe existir el requerimiento firmado y numerado"
    return None


def flujo_concepto_adicional(e) -> Motivo:
    """Concepto adicional: solo si hay respuesta del usuario que reevaluar."""
    motivo = flujo_respuesta_requerimiento(e)
    if motivo:
        return motivo
    if not e.req3.doc_oficio_entrada_id:
        return "Primero debe registrarse la respuesta del usuario al requerimiento"
    return None


def flujo_ejecutoria(e) -> Motivo:
    if e.decision is None or not e.decision.acto_admin_id:
        return "Primero debe existir la decisión firmada y numerada"
    return None


def flujo_concepto_memorias(e) -> Motivo:
    return None if e.memorias is not None else "Primero debe registrarse el radicado de los planos"


def flujo_subsanacion(e) -> Motivo:
    """Etapa 5 paso 4: la subsanación responde al requerimiento de memorias."""
    req = e.requerimiento("memorias")
    if req is None or not req.acto_admin_id:
        return "Primero debe existir el requerimiento de memorias firmado y numerado"
    return None


def flujo_concepto_subsanacion(e) -> Motivo:
    return None if e.subsanacion is not None else "Primero debe registrarse la subsanación (planos ajustados)"


def flujo_concepto_obras(e) -> Motivo:
    return None if e.obras is not None else "Primero debe registrarse el informe del usuario"


def flujo_nuevo_informe(e) -> Motivo:
    """Etapa 6 paso 3: nuevo informe tras el requerimiento de obras."""
    req = e.requerimiento("obras")
    if req is None or not req.acto_admin_id:
        return "Primero debe existir el requerimiento de obras firmado y numerado"
    return None


def flujo_concepto_obras_segundo(e) -> Motivo:
    return None if e.nuevo_informe_obras is not None else "Primero debe registrarse el nuevo informe del usuario"


# Condición para crear cada concepto (slug → regla). Etapa 2 nace con el auto.
CONDICION_CONCEPTO = {
    "etapa2": v5_concepto_etapa2,
    "adicional": flujo_concepto_adicional,
    "memorias": flujo_concepto_memorias,
    "subsanacion": flujo_concepto_subsanacion,
    "obras": flujo_concepto_obras,
    "obras_segundo": flujo_concepto_obras_segundo,
}

# Condición para asignarse cada requerimiento (ámbito → regla).
CONDICION_REQUERIMIENTO = {
    "etapa3": v6_requerimiento,
    "memorias": v11_requerimiento_memorias,
    "obras": v11_requerimiento_obras,
}
