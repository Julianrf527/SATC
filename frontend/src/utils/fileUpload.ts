import { apiCall, API_CONFIG } from "./api";

/** Sube un archivo a app-docs y devuelve su file_id. */
export async function uploadFileToDocuments(
  file: File,
  fileName: string,
): Promise<number> {
  const formData = new FormData();
  // app-docs espera el archivo en el campo multipart "archivo"
  formData.append("archivo", file, fileName);

  const uploadRes = await apiCall(API_CONFIG.ENDPOINTS.FILE_UPLOAD, {
    method: "POST",
    body: formData,
  });

  if (!uploadRes.ok) {
    throw new Error(uploadRes.detail || "Error al subir el archivo");
  }

  // El backend puede retornar file_id en raíz o dentro de data según endpoint/proxy.
  const fileId = uploadRes.file_id ?? uploadRes.data?.file_id;

  if (!fileId) {
    throw new Error("No se recibió el ID del archivo subido");
  }

  return fileId;
}

/** Sube archivos en paralelo; los IDs vuelven en el mismo orden de entrada. */
export async function uploadMultipleFiles(
  files: { file: File; fileName: string }[],
): Promise<number[]> {
  const uploadPromises = files.map(({ file, fileName }) =>
    uploadFileToDocuments(file, fileName),
  );

  return Promise.all(uploadPromises);
}

/** Nombre estandarizado `PREFIJO_numerado_YYYYMMDD.ext` (prefijo: NOTIF, CITAC, AUTO, RES…). */
export function generateDocumentFileName(
  prefix: string,
  numerado: string,
  fecha: string,
  extension: string = "pdf",
): string {
  const cleanDate = fecha.replace(/-/g, "");
  return `${prefix}_${numerado}_${cleanDate}.${extension}`;
}

export function validateFile(
  file: File,
  allowedTypes: string[] = ["application/pdf"],
  maxSizeBytes: number = 10 * 1024 * 1024,
): { isValid: boolean; error?: string } {
  if (!allowedTypes.includes(file.type)) {
    return {
      isValid: false,
      error: `Solo se permiten archivos de tipo: ${allowedTypes.join(", ")}`,
    };
  }

  if (file.size > maxSizeBytes) {
    const maxSizeMB = Math.round(maxSizeBytes / (1024 * 1024));
    return {
      isValid: false,
      error: `El archivo no debe superar los ${maxSizeMB}MB`,
    };
  }

  return { isValid: true };
}

export class FileUploadError extends Error {
  public cause?: Error;

  constructor(message: string, cause?: Error) {
    super(message);
    this.name = "FileUploadError";
    this.cause = cause;
  }
}
