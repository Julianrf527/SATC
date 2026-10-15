// Adaptación de los datos de app-recurso a las formas que espera
// `@features/acto-administrativo` (tipos heredados de sancionatorio). Lógica pura.
import type { Involucrado } from "@shared/types/involucrado";
import type { ActoAdministrativo } from "@shared/types/sancionatorio";
import type { ActoEtapa, VinculoInvolucrado } from "../../types";

/** Acto del nodo → `ActoAdministrativo` de la feature (numerados como texto). */
export function actoParaFeature(acto: ActoEtapa): ActoAdministrativo {
  return {
    id: acto.id,
    numerado: String(acto.numerado),
    fecha_numerado: acto.fecha_numerado,
    documento_acto_administrativo_id: acto.documento_acto_administrativo_id,
    // La feature muestra y edita "Tipo de acto" como AUTO/RES (contrato de
    // infraction): se le pasa la forma del acto, no la clase interna.
    tipo_acto: acto.clase_acto ?? "",
    fecha_creacion: acto.fecha_creacion ?? "",
    etapa_id: acto.etapa_id,
    comunicacion: acto.comunicacion
      ? {
          id: acto.comunicacion.id,
          numerado: String(acto.comunicacion.numerado),
          fecha_numerado: acto.comunicacion.fecha_numerado,
          fecha_envio: acto.comunicacion.fecha_envio,
          fecha_creacion: acto.comunicacion.fecha_creacion ?? "",
          documento_comunicacion_id: acto.comunicacion.documento_comunicacion_id,
        }
      : null,
    notificacion: acto.notificacion
      ? {
          id: acto.notificacion.id,
          fecha_creacion: acto.notificacion.fecha_creacion ?? "",
          involucrados: acto.notificacion.involucrados.map((n) => ({
            id: n.id,
            involucrado_id: n.involucrado_id,
            numerado: String(n.numerado),
            fecha_numerado: n.fecha_numerado,
            fecha_envio_citacion: n.fecha_envio_citacion,
            fecha_constancia_citacion: n.fecha_constancia_citacion,
            notificacion_exitosa: n.notificacion_exitosa,
            documento_notificacion_id: n.documento_notificacion_id,
            documento_citacion_id: n.documento_citacion_id,
            tipo_notificacion_id: n.tipo_notificacion_id,
            fecha_notificacion: n.fecha_notificacion,
            fecha_creacion: n.fecha_creacion ?? "",
          })),
        }
      : null,
  };
}

/**
 * Personas a notificar: solicitantes y terceros intervinientes vinculados
 * (B.3). El `id` es el de app-involved (`involucrado_id`), que es lo que
 * espera POST /actos/notificaciones. Si app-involved no respondió, la
 * persona llega solo con id y se muestra "Persona #id".
 */
export function notificablesDe(vinculos: VinculoInvolucrado[]): Involucrado[] {
  const vistos = new Set<number>();
  const lista: Involucrado[] = [];
  for (const v of vinculos) {
    if (vistos.has(v.involucrado_id)) continue;
    vistos.add(v.involucrado_id);
    const p = v.involucrado ?? { id: v.involucrado_id };
    const tercero = v.tipo_vinculo === "TERCERO_INTERVINIENTE";
    lista.push({
      id: v.involucrado_id,
      numero_documento: Number(p.numero_documento ?? 0),
      digito_verificacion: p.digito_verificacion ?? null,
      tipo_documento: p.tipo_documento ?? "",
      nombre: `${p.nombre ?? `Persona #${v.involucrado_id}`}${tercero ? " (tercero interviniente)" : ""}`,
      celular: p.celular ? Number(p.celular) : null,
      correo: p.correo ?? null,
      direccion: p.direccion ?? null,
    });
  }
  return lista;
}

/** Clave de remontaje: `ActoAdmin` guarda el acto en estado local al montarse. */
export function claveActo(acto: ActoEtapa): string {
  return JSON.stringify([acto.id, acto.numerado, acto.fecha_numerado, acto.documento_acto_administrativo_id, acto.comunicacion, acto.notificacion]);
}

/** Vínculos notificables: los del expediente más los terceros del árbol de etapas. */
export function vinculosNotificables(
  involucrados: VinculoInvolucrado[],
  terceros: Omit<VinculoInvolucrado, "acciones_disponibles">[] | undefined,
): VinculoInvolucrado[] {
  return [...involucrados, ...(terceros ?? [])];
}

/**
 * Regla del área (14/10/2026): SOLO se comunican —y nunca se notifican— el auto
 * que admite y el acto que reconoce a un tercero; todos los demás actos solo
 * se notifican. Misma regla que `ACTOS_SOLO_COMUNICACION` del backend
 * (services/actos.py), que además la valida.
 */
export const ACTOS_SOLO_COMUNICACION: readonly string[] = ["AUTO_ADMITE", "RECONOCE_TERCERO"];

/** ¿El acto (por su clase interna `tipo_acto`) se comunica en vez de notificarse? */
export function seComunica(tipoActo: string): boolean {
  return ACTOS_SOLO_COMUNICACION.includes(tipoActo);
}
