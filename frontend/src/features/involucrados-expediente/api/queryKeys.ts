// Claves react-query de la feature involucrados-expediente. La lista se indexa
// por la URL de listado (cada servicio tiene la suya).
export const involucradosExpedienteKeys = {
  all: ["involucrados-expediente"] as const,
  list: (listarUrl: string) =>
    [...involucradosExpedienteKeys.all, "list", listarUrl] as const,
};
