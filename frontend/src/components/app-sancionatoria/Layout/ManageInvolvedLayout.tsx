import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import TableInvolved from "../Table/TableInvolved";
import EditInvolvedModal from "../Modal/EditInvolvedModal";

type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number;
  correo: string;
};

interface InvolvedResponse {
  ok: boolean;
  data: Involved[];
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

export default function ManageInvolvedLayout({ setToast }: Props) {
  const rowsPerPage = 10;
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);

  const [involved, setInvolved] = useState<Involved[]>([]);
  const [selectedInvolved, setSelectedInvolved] = useState<Involved | null>(
    null
  );

  // Filtros
  const [numeroDocumentoFilter, setNumeroDocumentoFilter] =
    useState<string>("");
  const [tipoDocumentoFilter, setTipoDocumentoFilter] = useState<string>("");
  const [nombreFilter, setNombreFilter] = useState<string>("");
  const [correoFilter, setCorreoFilter] = useState<string>("");

  // Cargar involucrados
  useEffect(() => {
    async function loadInvolved() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.append("page", String(page));
        params.append("limit", String(rowsPerPage));

        if (numeroDocumentoFilter.trim()) {
          params.append("numero_documento", numeroDocumentoFilter.trim());
        }
        if (tipoDocumentoFilter) {
          params.append("tipo_documento", tipoDocumentoFilter);
        }
        if (nombreFilter.trim()) {
          params.append("nombre", nombreFilter.trim());
        }
        if (correoFilter.trim()) {
          params.append("correo", correoFilter.trim());
        }

        const res = await apiCall(
          `${API_CONFIG.ENDPOINTS.INVOLVED_MANAGE}?${params.toString()}`,
          { method: "GET" }
        );
        const data = res as InvolvedResponse;

        if (data.ok) {
          setInvolved(data.data || []);
          setTotalPages(
            data.totalCount > 0 ? Math.ceil(data.totalCount / rowsPerPage) : 1
          );
        } else {
          setToast({
            id: Date.now(),
            message: "Error en la respuesta del servidor",
            type: "error",
          });
        }
      } catch (e) {
        /* console.error(e); */
        setToast({
          id: Date.now(),
          message: "Error al cargar los datos",
          type: "error",
        });
      } finally {
        setLoading(false);
      }
    }

    loadInvolved();
  }, [
    page,
    numeroDocumentoFilter,
    tipoDocumentoFilter,
    nombreFilter,
    correoFilter,
    setToast,
  ]);

  // Editar involucrado
  const handleEdit = (inv: Involved) => {
    setSelectedInvolved(inv);
  };

  const handleSaveEdit = async (
    id: number,
    data: {
      nombre: string;
      celular: string;
      correo: string;
      digito_verificacion: string;
    }
  ) => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_EDIT(id), {
        method: "PUT",
        body: JSON.stringify(data),
      });

      if (res.ok) {
        // Actualizar la lista local
        setInvolved((prev) =>
          prev.map((inv) =>
            inv.id === id
              ? {
                  ...inv,
                  nombre: data.nombre,
                  celular: parseInt(data.celular),
                  correo: data.correo,
                  digito_verificacion: data.digito_verificacion || null,
                }
              : inv
          )
        );

        setToast({
          id: Date.now(),
          message: "Involucrado actualizado correctamente",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.message || "No se pudo actualizar el involucrado",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error(e); */
      setToast({
        id: Date.now(),
        message: "Error al actualizar el involucrado",
        type: "error",
      });
      throw e;
    }
  };

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-7xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Gestionar Involucrados"
                body="Visualiza y edita la información de los involucrados en los expedientes."
              />

              <TableInvolved
                titles={[
                  "Número Documento",
                  "Tipo",
                  "Nombre",
                  "Celular",
                  "Correo",
                  "Acciones",
                ]}
                data={involved}
                page={page}
                totalPages={totalPages}
                loading={loading}
                onPageChange={setPage}
                onEdit={handleEdit}
                numeroDocumentoFilter={numeroDocumentoFilter}
                tipoDocumentoFilter={tipoDocumentoFilter}
                nombreFilter={nombreFilter}
                correoFilter={correoFilter}
                onNumeroDocumentoFilterChange={setNumeroDocumentoFilter}
                onTipoDocumentoFilterChange={setTipoDocumentoFilter}
                onNombreFilterChange={setNombreFilter}
                onCorreoFilterChange={setCorreoFilter}
              />
            </div>
          </div>
        </div>
      </section>

      {/* Modal de edición */}
      <EditInvolvedModal
        involved={selectedInvolved}
        onClose={() => setSelectedInvolved(null)}
        onSave={handleSaveEdit}
      />
    </div>
  );
}
