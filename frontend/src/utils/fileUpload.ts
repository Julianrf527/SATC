import { apiCall, API_CONFIG } from "./api";

/**
 * Upload a single file to the app-docs service
 * @param file - The file to upload
 * @param fileName - The name to give the file
 * @returns Promise<number> - The file ID from app-docs
 */
export async function uploadFileToDocuments(
  file: File,
  fileName: string,
): Promise<number> {
  const formData = new FormData();
  formData.append("file", file, fileName);

  const uploadRes = await apiCall(API_CONFIG.ENDPOINTS.FILE_UPLOAD, {
    method: "POST",
    body: formData,
  });

  if (!uploadRes.ok) {
    throw new Error(uploadRes.detail || "Error al subir el archivo");
  }

  if (!uploadRes.data?.file_id) {
    throw new Error("No se recibió el ID del archivo subido");
  }

  return uploadRes.data.file_id;
}

/**
 * Upload multiple files in parallel to the app-docs service
 * @param files - Array of files with their desired names
 * @returns Promise<number[]> - Array of file IDs in same order as input
 */
export async function uploadMultipleFiles(
  files: { file: File; fileName: string }[],
): Promise<number[]> {
  const uploadPromises = files.map(({ file, fileName }) =>
    uploadFileToDocuments(file, fileName),
  );

  return Promise.all(uploadPromises);
}

/**
 * Generate a standardized document filename
 * @param prefix - Document type prefix (e.g., 'NOTIF', 'CITAC', 'AUTO', 'RES')
 * @param numerado - Document number
 * @param fecha - Date in YYYY-MM-DD format
 * @param extension - File extension (default: 'pdf')
 * @returns Formatted filename
 */
export function generateDocumentFileName(
  prefix: string,
  numerado: string,
  fecha: string,
  extension: string = "pdf",
): string {
  const cleanDate = fecha.replace(/-/g, "");
  return `${prefix}_${numerado}_${cleanDate}.${extension}`;
}

/**
 * Validate a file before upload
 * @param file - The file to validate
 * @param allowedTypes - Array of allowed MIME types (default: ['application/pdf'])
 * @param maxSizeBytes - Maximum file size in bytes (default: 10MB)
 * @returns Validation result with error message if invalid
 */
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

/**
 * File upload error types for better error handling
 */
export class FileUploadError extends Error {
  public cause?: Error;

  constructor(
    message: string,
    cause?: Error,
  ) {
    super(message);
    this.name = "FileUploadError";
    this.cause = cause;
  }
}
