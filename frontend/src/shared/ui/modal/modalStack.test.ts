import { describe, expect, it } from "vitest";
import { isTopModal, popModal, pushModal } from "./modalStack";

describe("modalStack", () => {
  it("solo el último modal abierto es el superior", () => {
    pushModal("a");
    pushModal("b");
    expect(isTopModal("b")).toBe(true);
    expect(isTopModal("a")).toBe(false);
    popModal("b");
    expect(isTopModal("a")).toBe(true);
    popModal("a");
    expect(isTopModal("a")).toBe(false);
  });
  it("cerrar uno intermedio no rompe la pila", () => {
    pushModal("x");
    pushModal("y");
    popModal("x");
    expect(isTopModal("y")).toBe(true);
    popModal("y");
  });
});
