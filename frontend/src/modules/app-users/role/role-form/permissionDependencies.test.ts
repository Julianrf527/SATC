import { describe, expect, it } from "vitest";
import {
  agregarPermiso,
  alternarCategoria,
  estaBloqueado,
  incumplimientos,
  quitarConDependientes,
  requisitosFaltantes,
  type PermisoDependiente,
} from "./permissionDependencies";
import { permissionLabel } from "./permissionCategories";

// Reglas tal como las manda el backend en `requiere`; C es una cadena de prueba.
const catalogo: PermisoDependiente[] = [
  { id: 1, nombre: "infraccion_consultar", requiere: [] },
  { id: 2, nombre: "infraccion_alertas", requiere: ["infraccion_consultar"] },
  { id: 3, nombre: "infraccion_asignar", requiere: ["infraccion_consultar"] },
  { id: 4, nombre: "infraccion_gestionar" },
  { id: 5, nombre: "infraccion_super_gestion", requiere: ["infraccion_gestionar"] },
  { id: 6, nombre: "prueba_a", requiere: [] },
  { id: 7, nombre: "prueba_b", requiere: ["prueba_a"] },
  { id: 8, nombre: "prueba_c", requiere: ["prueba_b"] },
  { id: 9, nombre: "recurso_sig", requiere: ["recurso_consultar"] }, // requerido fuera del catálogo del usuario
];

describe("bloqueo por dependencias", () => {
  it("un dependiente está bloqueado hasta marcar su requerido", () => {
    const alertas = catalogo[1];
    expect(estaBloqueado(alertas, [], catalogo)).toBe(true);
    expect(requisitosFaltantes(alertas, [], catalogo)).toEqual(["infraccion_consultar"]);
    expect(estaBloqueado(alertas, [1], catalogo)).toBe(false);
  });

  it("un permiso sin requeridos nunca está bloqueado", () => {
    expect(estaBloqueado(catalogo[0], [], catalogo)).toBe(false);
    expect(estaBloqueado(catalogo[3], [], catalogo)).toBe(false);
  });

  it("marcado pero sin requerido (rol viejo) no queda bloqueado para poder desmarcarlo", () => {
    expect(estaBloqueado(catalogo[1], [2], catalogo)).toBe(false);
    expect(requisitosFaltantes(catalogo[1], [2], catalogo)).toEqual(["infraccion_consultar"]);
  });

  it("requerido que el usuario no tiene en su catálogo deja el permiso bloqueado", () => {
    expect(estaBloqueado(catalogo[8], [1, 2, 3], catalogo)).toBe(true);
  });

  it("agregarPermiso no marca un bloqueado y sí uno desbloqueado", () => {
    expect(agregarPermiso([], 2, catalogo)).toEqual([]);
    expect(agregarPermiso([1], 2, catalogo)).toEqual([1, 2]);
    expect(agregarPermiso([1, 2], 2, catalogo)).toEqual([1, 2]);
  });
});

describe("cascada al desmarcar", () => {
  it("quita los dependientes directos", () => {
    const r = quitarConDependientes([1, 2, 3, 4], [1], catalogo);
    expect(r.seleccion).toEqual([4]);
    expect(r.quitados.sort()).toEqual([2, 3]);
  });

  it("es transitiva si las dependencias encadenan", () => {
    const r = quitarConDependientes([6, 7, 8], [6], catalogo);
    expect(r.seleccion).toEqual([]);
    expect(r.quitados).toEqual([7, 8]);
  });

  it("quitar un dependiente no toca su requerido", () => {
    const r = quitarConDependientes([1, 2], [2], catalogo);
    expect(r.seleccion).toEqual([1]);
    expect(r.quitados).toEqual([]);
  });

  it("no quita incumplimientos ajenos a lo desmarcado", () => {
    // Rol viejo: tiene alertas sin consultar; desmarcar gestionar no las toca.
    const r = quitarConDependientes([2, 4], [4], catalogo);
    expect(r.seleccion).toEqual([2]);
    expect(r.quitados).toEqual([]);
  });
});

describe("Todos de una categoría", () => {
  const infraccion = [1, 2, 3, 4, 5];

  it("marca en orden requeridos y dependientes", () => {
    const r = alternarCategoria([], infraccion, catalogo);
    expect(r.seleccion.sort()).toEqual([1, 2, 3, 4, 5]);
  });

  it("con todo marcado desmarca la categoría", () => {
    const r = alternarCategoria([1, 2, 3, 4, 5], infraccion, catalogo);
    expect(r.seleccion).toEqual([]);
  });

  it("deja sin marcar los que exigen algo de otra categoría", () => {
    const r = alternarCategoria([], [7, 9], catalogo);
    expect(r.seleccion).toEqual([]);
    const r2 = alternarCategoria([6], [7, 8], catalogo);
    expect(r2.seleccion.sort()).toEqual([6, 7, 8]);
  });

  it("desmarcar una categoría quita en cascada dependientes de otras", () => {
    const r = alternarCategoria([6, 7, 8], [6], catalogo);
    expect(r.seleccion).toEqual([]);
    expect(r.quitados).toEqual([7, 8]);
  });
});

describe("incumplimientos", () => {
  it("lista los marcados sin sus requeridos", () => {
    expect(incumplimientos([2, 5, 1], catalogo)).toEqual([
      { permiso: catalogo[4], faltan: ["infraccion_gestionar"] },
    ]);
    expect(incumplimientos([1, 2, 4, 5], catalogo)).toEqual([]);
  });
});

describe("permissionLabel", () => {
  it("usa la acción y la categoría", () => {
    expect(permissionLabel("infraccion_consultar")).toBe("Consultar (Infracciones)");
    expect(permissionLabel("recurso_lider_juridico")).toBe("Lider Juridico (Concesiones de aguas)");
  });
});
