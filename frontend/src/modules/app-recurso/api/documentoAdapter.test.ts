import { describe, expect, it } from "vitest";
// Se importa el archivo de endpoints directo: `@shared/lib/api` carga el
// cliente HTTP, que usa `window` (no existe en el entorno node de los tests).
import { RECURSO_ENDPOINTS } from "@shared/lib/api/endpoints/recurso";
import { recursoKeys } from "./queryKeys";
import { formRevision, formVersion } from "./revisionForms";

describe("rutas del adapter de revisión", () => {
  it("apuntan a /recurso/revision-documentos", () => {
    expect(RECURSO_ENDPOINTS.RECURSO_REVISION_DESCARGA_VERSION(7, 12)).toBe(
      "/recurso/revision-documentos/7/versiones/12/descarga",
    );
    expect(RECURSO_ENDPOINTS.RECURSO_REVISION_ADJUNTO(7, 5)).toBe("/recurso/revision-documentos/7/revisiones/5/adjunto");
    expect(RECURSO_ENDPOINTS.RECURSO_VINCULO_DELETE(15, 2)).toBe("/recurso/involucrados/vinculos/15?version=2");
  });

  it("la clave del proceso cuelga de Mis informes (se invalida con la lista)", () => {
    expect(recursoKeys.proceso(7)).toEqual(["app-recurso", "mis-documentos", "proceso", 7]);
    expect(recursoKeys.proceso(7).slice(0, 2)).toEqual(recursoKeys.misDocumentos());
  });
});

describe("formularios multipart", () => {
  it("revisión: omite comentario vacío y adjunto nulo", () => {
    const f = formRevision({ accion: "aprobado", comentario: "  ", adjunto: null });
    expect(f.get("accion")).toBe("aprobado");
    expect(f.has("comentario")).toBe(false);
    expect(f.has("adjunto")).toBe(false);
  });

  it("revisión: devolver con comentario y adjunto", () => {
    const adjunto = new File(["x"], "obs.pdf", { type: "application/pdf" });
    const f = formRevision({ accion: "devuelto", comentario: " Corregir ", adjunto });
    expect(f.get("comentario")).toBe("Corregir");
    expect((f.get("adjunto") as File).name).toBe("obs.pdf");
  });

  it("versión: archivo obligatorio y comentario opcional", () => {
    const archivo = new File(["x"], "auto.docx");
    const f = formVersion({ archivo, comentario: "v2" });
    expect((f.get("archivo") as File).name).toBe("auto.docx");
    expect(f.get("comentario")).toBe("v2");
  });
});
