import type { DatosRevision, DatosVersion } from "@features/proceso-revision";

/** FormData de POST /revisiones (`accion`, `comentario`, `adjunto`). */
export function formRevision({ accion, comentario, adjunto }: DatosRevision): FormData {
  const form = new FormData();
  form.append("accion", accion);
  if (comentario.trim()) form.append("comentario", comentario.trim());
  if (adjunto) form.append("adjunto", adjunto);
  return form;
}

/** FormData de POST /versiones (`archivo`, `comentario`). */
export function formVersion({ archivo, comentario }: DatosVersion): FormData {
  const form = new FormData();
  form.append("archivo", archivo);
  if (comentario.trim()) form.append("comentario", comentario.trim());
  return form;
}
