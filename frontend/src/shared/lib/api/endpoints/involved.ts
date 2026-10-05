// Endpoints del servicio app-involved (/involveds).
// Strings fijos o funciones que construyen la ruta; se concatenan a BASE_URL en apiCall.
export const INVOLVED_ENDPOINTS = {
  // involved route
  INVOLVED: (involved_id: number) => `/involveds/involved/${involved_id}`,
  INVOLVED_SEARCH: (tipo: string, numero: string, dv?: string) =>
    `/involveds/involved/search/${tipo}/${numero}${dv ? `?dv=${dv}` : ""}`,
  INVOLVED_CREATE: "/involveds/involved/new",
  INVOLVED_UPDATE: (involved_id: number) =>
    `/involveds/involved/${involved_id}`,
  INVOLVED_MANAGE: "/involveds/involved/manage",
  INVOLVED_LOG: "/involveds/involved/log",
};
