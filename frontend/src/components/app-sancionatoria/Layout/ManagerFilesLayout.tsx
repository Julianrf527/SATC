import { useEffect, useState, useMemo, useCallback } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import TableFiles from "../Table/TableFiles";

type File = {
  radicado: string;
  nombre_expediente: string;
  fecha_creacion: string;
  encargado_id: number | null;
  encargado_nombre?: string;
};

type User = {
  id: number;
  name: string;
};

interface FilesResponse {
  ok: boolean;
  data: File[];
  usuarios_disponibles: User[];
  page: number;
  limit: number;
  totalCount: number;
}

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ManagerFiles({ setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);

  const [files, setFiles] = useState<File[]>([]);
  const [usuariosDisponibles, setUsuariosDisponibles] = useState<User[]>([]);
  const [radicadoFilter, setRadicadoFilter] = useState<string>("");
  const [expedienteFilter, setExpedienteFilter] = useState<string>("");
  const [fechaFilter, setFechaFilter] = useState<string>("");
  const [encargadoFilter, setEncargadoFilter] = useState<string>("");
  const [estadoFilter, setEstadoFilter] = useState<string>("all");

  // Cargar expedientes
  useEffect(() => {
    async function loadFiles() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.append("page", String(page));
        params.append("limit", String(rowsPerPage));

        if (radicadoFilter.trim()) {
          params.append("radicado", radicadoFilter.trim());
        }
        if (expedienteFilter.trim()) {
          params.append("nombre_expediente", expedienteFilter.trim());
        }
        if (fechaFilter.trim()) {
          params.append("fecha_creacion", fechaFilter.trim());
        }

        const resFiles = await apiCall(
          `${API_CONFIG.ENDPOINTS.FILES}?${params.toString()}`,
          { method: "GET" }
        );
        const filesData = resFiles as FilesResponse;

        if (filesData.ok) {
          console.log(resFiles);
          setFiles(filesData.data || []);
          setUsuariosDisponibles(filesData.usuarios_disponibles || []);
          setTotalPages(
            filesData.totalCount > 0
              ? Math.ceil(filesData.totalCount / rowsPerPage)
              : 1
          );
        } else {
          setToast({
            id: Date.now(),
            message: "Error en la respuesta del servidor",
            type: "error",
          });
        }
      } catch (e) {
        console.error(e);
        setToast({
          id: Date.now(),
          message: "Error al cargar los datos",
          type: "error",
        });
      } finally {
        setLoading(false);
      }
    }

    loadFiles();
  }, [page, radicadoFilter, expedienteFilter, fechaFilter, setToast]);

  // Crear lista de encargados que tienen expedientes asignados (para el filtro)
  const encargadosConExpedientes = useMemo(() => {
    const encargadosMap = new Map<number, User>();

    files.forEach((f) => {
      if (f.encargado_id && f.encargado_nombre) {
        if (!encargadosMap.has(f.encargado_id)) {
          encargadosMap.set(f.encargado_id, {
            id: f.encargado_id,
            name: f.encargado_nombre,
          });
        }
      }
    });

    return Array.from(encargadosMap.values());
  }, [files]);

  // Filtrado en el cliente
  const filteredFiles = useMemo(() => {
    return files.filter((f) => {
      // Filtro por encargado (nombre o cédula)
      const matchesEncargado = (() => {
        if (!encargadoFilter.trim()) return true;
        if (f.encargado_id === null) return false;

        const searchTerm = encargadoFilter.toLowerCase().trim();

        const matchesName = f.encargado_nombre
          ? f.encargado_nombre.toLowerCase().includes(searchTerm)
          : false;
        const matchesId = String(f.encargado_id).includes(searchTerm);

        return matchesName || matchesId;
      })();

      // Filtro por estado
      const estado = f.encargado_id ? "asignado" : "sin_asignar";
      const matchesEstado =
        estadoFilter === "all" ? true : estadoFilter === estado;

      return matchesEncargado && matchesEstado;
    });
  }, [files, encargadoFilter, estadoFilter]);

  // Actualizar encargado
  const updateEncargado = useCallback(
    async (radicado: string, encargado_id: number | null): Promise<void> => {
      try {
        const normalizedId = encargado_id == null ? 0 : encargado_id;

        // Buscar el nombre del nuevo encargado desde la lista de usuarios disponibles
        const nuevoEncargado = usuariosDisponibles.find(
          (u) => u.id === encargado_id
        );

        const res = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_UPDATE_ENCARGADO(radicado, normalizedId),
          {
            method: "PATCH",
          }
        );

        if (res.ok) {
          setFiles((prevFiles) =>
            prevFiles.map((f) =>
              f.radicado === radicado
                ? {
                    ...f,
                    encargado_id: encargado_id,
                    encargado_nombre: nuevoEncargado?.name || undefined,
                  }
                : f
            )
          );
          await apiCall(API_CONFIG.ENDPOINTS.NOTIFICATION_LINKED(radicado), {
            method: "DELETE",
          });

          await apiCall(API_CONFIG.ENDPOINTS.NOTIFICATION_CREATE, {
            method: "POST",
            body: JSON.stringify({
              mensaje:
                "Se le ha asignado el expediente con radicado " + radicado,
              id_vinculada: radicado,
              tipo: "expediente",
              usuario_id: encargado_id,
            }),
          });

          setToast({
            id: Date.now(),
            message: "Encargado actualizado correctamente",
            type: "success",
          });
        } else {
          setToast({
            id: Date.now(),
            message: "No se pudo actualizar el encargado",
            type: "error",
          });
        }
      } catch (e) {
        console.error(e);
        setToast({
          id: Date.now(),
          message: "No se pudo actualizar el encargado",
          type: "error",
        });
      }
    },
    [usuariosDisponibles, setToast]
  );

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-6xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Gestionar Expedientes"
                body="Filtra y asigna encargados."
              />
              <TableFiles
                titles={[
                  "Radicado",
                  "Expediente",
                  "Fecha",
                  "Encargado",
                  "Estado",
                ]}
                data={filteredFiles}
                encargados={usuariosDisponibles}
                page={page}
                totalPages={totalPages}
                loading={loading}
                onPageChange={setPage}
                onChangeEncargado={updateEncargado}
                radicadoFilter={radicadoFilter}
                expedienteFilter={expedienteFilter}
                fechaFilter={fechaFilter}
                encargadoFilter={encargadoFilter}
                estadoFilter={estadoFilter}
                encargadosConExpedientes={encargadosConExpedientes}
                onRadicadoFilterChange={setRadicadoFilter}
                onExpedienteFilterChange={setExpedienteFilter}
                onFechaFilterChange={setFechaFilter}
                onEncargadoFilterChange={setEncargadoFilter}
                onEstadoFilterChange={setEstadoFilter}
              />
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
