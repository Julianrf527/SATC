import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { sesionService } from "./sesionService";
import { toastService } from "./toastService";

describe("sesionService.cerrada (401)", () => {
  const location = { pathname: "/recurso/manage", href: "" };
  const toast = vi.fn();

  beforeEach(() => {
    location.pathname = "/recurso/manage";
    location.href = "";
    vi.stubGlobal("window", { location });
    toastService.setHandler(toast);
    toast.mockClear();
  });
  afterEach(() => {
    sesionService.setHandler(null);
    vi.unstubAllGlobals();
  });

  it("con el handler de la app: avisa y navega sin recargar", () => {
    const irAlLogin = vi.fn(() => {
      location.pathname = "/login";
    });
    sesionService.setHandler(irAlLogin);
    sesionService.cerrada("expiró");
    expect(toast).toHaveBeenCalledWith(expect.objectContaining({ message: "expiró", type: "error" }));
    expect(irAlLogin).toHaveBeenCalledTimes(1);
    expect(location.href).toBe("");
    // Otras peticiones que fallan después ya están en el login: ni toast ni navegación.
    sesionService.cerrada("expiró");
    expect(toast).toHaveBeenCalledTimes(1);
    expect(irAlLogin).toHaveBeenCalledTimes(1);
  });

  it("en el login no hace nada (credenciales malas)", () => {
    location.pathname = "/login";
    const irAlLogin = vi.fn();
    sesionService.setHandler(irAlLogin);
    sesionService.cerrada("expiró");
    expect(toast).not.toHaveBeenCalled();
    expect(irAlLogin).not.toHaveBeenCalled();
  });

  it("sin handler registrado recurre a la recarga completa", () => {
    sesionService.cerrada("expiró");
    expect(location.href).toBe("/login");
  });
});
