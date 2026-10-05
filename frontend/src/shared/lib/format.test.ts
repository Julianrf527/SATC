import { describe, expect, it } from "vitest";
import { formatDate, formatDateTime, formatFileSize, parseDate } from "./format";

describe("parseDate", () => {
  it("interpreta fechas sin hora en hora local (sin corrimiento UTC)", () => {
    const d = parseDate("2026-01-05")!;
    expect([d.getFullYear(), d.getMonth(), d.getDate()]).toEqual([2026, 0, 5]);
  });
  it("devuelve null para vacíos e inválidos", () => {
    expect(parseDate(null)).toBeNull();
    expect(parseDate("")).toBeNull();
    expect(parseDate("no-es-fecha")).toBeNull();
  });
});

describe("formatDate", () => {
  it("formato corto dd/mm/aaaa (igual al split manual y a es-ES 2-digit)", () => {
    expect(formatDate("2026-01-05")).toBe("05/01/2026");
    expect(formatDate("2026-12-31T10:20:00")).toBe("31/12/2026");
    expect(formatDate("2026-1-5")).toBe("05/01/2026");
    const legacy = new Date("2026-03-09T08:00:00").toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
    expect(formatDate("2026-03-09T08:00:00")).toBe(legacy);
  });
  it("formato largo '5 de enero de 2026'", () => {
    expect(formatDate("2026-01-05", { style: "long" })).toBe("5 de enero de 2026");
    expect(formatDate("2025-09-30", { style: "long" })).toBe("30 de septiembre de 2025");
  });
  it("usa fallback para vacíos", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined, { fallback: "No registrada" })).toBe("No registrada");
  });
});

describe("formatDateTime", () => {
  it("coincide con toLocaleString es-CO usado en las tablas de auditoría", () => {
    const iso = "2026-01-05T14:30:15";
    const opts = { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" } as const;
    expect(formatDateTime(iso)).toBe(new Date(iso).toLocaleString("es-CO", opts));
    expect(formatDateTime(iso, { seconds: true })).toBe(
      new Date(iso).toLocaleString("es-CO", { ...opts, second: "2-digit" }),
    );
  });
  it("fallback", () => {
    expect(formatDateTime("", { fallback: "-" })).toBe("-");
  });
});

describe("formatFileSize", () => {
  it("misma salida que la versión de DocumentoDetalleModal", () => {
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(5 * 1024 * 1024)).toBe("5.0 MB");
  });
  it("GB y valores inválidos", () => {
    expect(formatFileSize(2 * 1024 ** 3)).toBe("2.0 GB");
    expect(formatFileSize(null)).toBe("—");
    expect(formatFileSize(-1)).toBe("—");
  });
});
