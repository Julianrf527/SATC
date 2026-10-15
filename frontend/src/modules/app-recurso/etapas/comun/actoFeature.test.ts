import { describe, expect, it } from "vitest";
import type { ActoEtapa, VinculoInvolucrado } from "../../types";
import { documentosPermitidos } from "../auto-admite/documentosAdmite";
import { actoParaFeature, claveActo, notificablesDe, seComunica } from "./actoFeature";

const acto: ActoEtapa = {
  id: 4,
  tipo_acto: "AUTO_ADMITE",
  clase_acto: "AUTO",
  numerado: 12,
  fecha_numerado: "2026-04-01",
  documento_acto_administrativo_id: 345,
  fecha_creacion: null,
  etapa_tipo: "acto_admite",
  etapa_id: 2,
  comunicacion: null,
  notificacion: {
    id: 4,
    fecha_creacion: null,
    involucrados: [
      {
        id: 9,
        involucrado_id: 501,
        numerado: 45,
        fecha_numerado: "2026-04-02",
        fecha_envio_citacion: "2026-04-03",
        fecha_constancia_citacion: null,
        documento_citacion_id: 347,
        notificacion_exitosa: false,
        tipo_notificacion_id: null,
        documento_notificacion_id: null,
        fecha_notificacion: null,
        fecha_creacion: null,
      },
    ],
  },
  notificado: false,
  acciones_disponibles: ["editar_acto"],
};

const vinculo = (id: number, involucradoId: number, tipo: VinculoInvolucrado["tipo_vinculo"], nombre?: string) =>
  ({
    id,
    expediente_id: 7,
    involucrado_id: involucradoId,
    tipo_vinculo: tipo,
    representante_id: null,
    acto_admin_id: null,
    fecha_vinculacion: "",
    version: 1,
    involucrado: nombre ? { id: involucradoId, nombre, tipo_documento: "CC", numero_documento: 123 } : { id: involucradoId },
    representante: null,
    requiere_representante: false,
  }) as VinculoInvolucrado;

describe("actoParaFeature", () => {
  it("numerados como texto y fechas nulas como cadena vacía", () => {
    const a = actoParaFeature(acto);
    expect(a.numerado).toBe("12");
    expect(a.fecha_creacion).toBe("");
    expect(a.notificacion?.involucrados[0].numerado).toBe("45");
    expect(a.comunicacion).toBeNull();
  });
  it("muestra AUTO/RES (forma del acto), no la clase interna de la etapa", () => {
    expect(actoParaFeature(acto).tipo_acto).toBe("AUTO");
    expect(actoParaFeature({ ...acto, clase_acto: "RES" }).tipo_acto).toBe("RES");
    expect(actoParaFeature({ ...acto, clase_acto: null }).tipo_acto).toBe("");
  });
  it("la clave cambia si cambian las notificaciones", () => {
    const otra = { ...acto, notificacion: { ...acto.notificacion!, involucrados: [] } };
    expect(claveActo(acto)).not.toBe(claveActo(otra));
  });
});

describe("notificablesDe", () => {
  it("usa el id de app-involved, sin duplicados, y marca terceros", () => {
    const lista = notificablesDe([
      vinculo(1, 501, "SOLICITANTE", "Ana"),
      vinculo(2, 502, "TERCERO_INTERVINIENTE"),
      vinculo(2, 502, "TERCERO_INTERVINIENTE"),
    ]);
    expect(lista.map((p) => p.id)).toEqual([501, 502]);
    expect(lista[0].nombre).toBe("Ana");
    expect(lista[1].nombre).toBe("Persona #502 (tercero interviniente)");
  });
});

describe("documentos del auto que admite", () => {
  it("solo los que el backend permite cargar", () => {
    const puede = (a: string) => a === "cargar_constancia_fijacion";
    expect(documentosPermitidos(puede)).toEqual(["doc_constancia_fijacion_aviso_id"]);
  });
});

describe("seComunica (regla del área 14/10/2026)", () => {
  it("solo el auto que admite y el acto que reconoce al tercero se comunican", () => {
    expect(seComunica("AUTO_ADMITE")).toBe(true);
    expect(seComunica("RECONOCE_TERCERO")).toBe(true);
    for (const tipo of ["REQUERIMIENTO", "DECISION", "RECURSO", "APRUEBA_MEMORIAS", "APRUEBA_OBRAS"]) {
      expect(seComunica(tipo)).toBe(false);
    }
  });

  it("pasa la fecha de registro de la comunicación a la feature", () => {
    const conCom: ActoEtapa = {
      ...acto,
      comunicacion: {
        id: 1,
        acto_administrativo_id: 4,
        numerado: 3,
        fecha_numerado: "2026-04-02",
        fecha_envio: "2026-04-03",
        documento_comunicacion_id: 9,
        fecha_creacion: "2026-10-14T09:00:00-05:00",
      },
    };
    expect(actoParaFeature(conCom).comunicacion?.fecha_creacion).toBe("2026-10-14T09:00:00-05:00");
  });
});
