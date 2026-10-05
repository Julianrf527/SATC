import { useId, useState } from "react";
import { Pencil } from "lucide-react";
import { Modal } from "@shared/ui";
import { getErrorMessage } from "@shared/lib/api";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { ActualizarUsuarioPayload, RolResumen, UsuarioFila } from "../types";

type Props = {
  user: UsuarioFila | null;
  rolList: RolResumen[];
  onClose: () => void;
  /** Debe rechazar si no se pudo guardar: el modal queda abierto con el error. */
  onSave: (id: number, data: ActualizarUsuarioPayload) => Promise<void>;
};

export default function EditUserModal({ user, rolList, onClose, onSave }: Props) {
  const formId = useId();
  const [isSubmitting, setIsSubmitting] = useState(false);

  return (
    <Modal
      isOpen={!!user}
      onClose={onClose}
      title="Editar Usuario"
      subtitle="Modifica los datos, rol o estado del usuario"
      icon={<Pencil size={18} />}
      size="xl"
      closeOnEsc={!isSubmitting}
      closeOnBackdrop={!isSubmitting}
      footer={
        <>
          <button type="button" onClick={onClose} className="btn btn-ghost btn-sm" disabled={isSubmitting}>
            Cancelar
          </button>
          <button
            type="submit"
            form={formId}
            className="btn btn-success btn-sm text-white gap-2 min-w-[150px]"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="loading loading-spinner loading-xs" />
                Guardando...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                Guardar Cambios
              </>
            )}
          </button>
        </>
      }
    >
      {user && (
        // key: al cambiar de usuario el formulario se reinicia con sus datos.
        <EditUserForm
          key={user.id}
          formId={formId}
          user={user}
          rolList={rolList}
          isSubmitting={isSubmitting}
          setIsSubmitting={setIsSubmitting}
          onSave={onSave}
          onClose={onClose}
        />
      )}
    </Modal>
  );
}

type FormProps = {
  formId: string;
  user: UsuarioFila;
  rolList: RolResumen[];
  isSubmitting: boolean;
  setIsSubmitting: (v: boolean) => void;
  onSave: Props["onSave"];
  onClose: () => void;
};

function EditUserForm({ formId, user, rolList, isSubmitting, setIsSubmitting, onSave, onClose }: FormProps) {
  const [documentNumber, setDocumentNumber] = useState(String(user.document));
  const [firstName, setFirstName] = useState(user.primer_nombre);
  const [middleName, setMiddleName] = useState(user.segundo_nombre ?? "");
  const [lastName, setLastName] = useState(user.primer_apellido);
  const [secondLastName, setSecondLastName] = useState(user.segundo_apellido ?? "");
  const [email, setEmail] = useState(user.email);
  const [rolId, setRolId] = useState(user.rol_id);
  const [activo, setActivo] = useState(user.state);
  const [errorGeneral, setErrorGeneral] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateName = (v: string, label: string, required: boolean) => {
    const trimmed = v.trim();
    if (!trimmed) return required ? `${label} es requerido` : "";
    if (trimmed.length > 20) return `Máximo 20 caracteres`;
    if (!/^[A-Za-zÀ-ÿ\s]+$/.test(trimmed)) return "Solo letras y espacios";
    return "";
  };

  const validate = () => {
    const e: Record<string, string> = {};
    const errFirst = validateName(firstName, "Primer nombre", true);
    if (errFirst) e.firstName = errFirst;
    const errLast = validateName(lastName, "Primer apellido", true);
    if (errLast) e.lastName = errLast;
    const errMiddle = validateName(middleName, "Segundo nombre", false);
    if (errMiddle) e.middleName = errMiddle;
    const errSecondLast = validateName(secondLastName, "Segundo apellido", false);
    if (errSecondLast) e.secondLastName = errSecondLast;
    if (!documentNumber.trim() || documentNumber.trim().length < 6 || documentNumber.trim().length > 10)
      e.document = "Entre 6 y 10 dígitos";
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email))
      e.email = "Correo inválido";
    if (!rolId) e.rolId = "Seleccione un rol";
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorGeneral("");
    if (!validate()) return;

    setIsSubmitting(true);
    try {
      await onSave(user.id, {
        document: parseInt(documentNumber.trim(), 10),
        first_name: firstName.trim(),
        middle_name: middleName.trim(),
        lastname: lastName.trim(),
        second_lastname: secondLastName.trim(),
        email: email.trim().toLowerCase(),
        rol_id: rolId,
        activo,
      });
      setIsSubmitting(false);
      onClose();
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, "Error al actualizar el usuario"));
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {errorGeneral && (
        <div className="alert alert-error py-2 text-sm">
          <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          {errorGeneral}
        </div>
      )}

      <form id={formId} onSubmit={handleSubmit} className="space-y-4">
      {/* Documento */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-base-content/60">Número de documento *</span>
        <input
          type="text"
          value={documentNumber}
          onChange={(e) => setDocumentNumber(e.target.value.replace(/\D/g, ""))}
          className={`input w-full font-mono ${errors.document ? "input-error" : ""}`}
          disabled={isSubmitting}
          maxLength={10}
        />
        {errors.document && <span className="text-[11px] text-error">{errors.document}</span>}
      </div>

      {/* Nombres */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Primer nombre *</span>
          <input
            type="text"
            className={`input w-full ${errors.firstName ? "input-error" : ""}`}
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            maxLength={20}
            disabled={isSubmitting}
          />
          {errors.firstName && <span className="text-[11px] text-error">{errors.firstName}</span>}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Segundo nombre</span>
          <input
            type="text"
            className={`input w-full ${errors.middleName ? "input-error" : ""}`}
            value={middleName}
            onChange={(e) => setMiddleName(e.target.value)}
            maxLength={20}
            disabled={isSubmitting}
          />
          {errors.middleName && <span className="text-[11px] text-error">{errors.middleName}</span>}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Primer apellido *</span>
          <input
            type="text"
            className={`input w-full ${errors.lastName ? "input-error" : ""}`}
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            maxLength={20}
            disabled={isSubmitting}
          />
          {errors.lastName && <span className="text-[11px] text-error">{errors.lastName}</span>}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Segundo apellido</span>
          <input
            type="text"
            className={`input w-full ${errors.secondLastName ? "input-error" : ""}`}
            value={secondLastName}
            onChange={(e) => setSecondLastName(e.target.value)}
            maxLength={20}
            disabled={isSubmitting}
          />
          {errors.secondLastName && <span className="text-[11px] text-error">{errors.secondLastName}</span>}
        </div>
      </div>

      {/* Correo */}
      <div className="flex flex-col gap-1">
        <span className="text-xs font-medium text-base-content/60">Correo *</span>
        <input
          type="email"
          className={`input w-full ${errors.email ? "input-error" : ""}`}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={isSubmitting}
        />
        {errors.email && <span className="text-[11px] text-error">{errors.email}</span>}
      </div>

      {/* Rol y Estado */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Rol *</span>
          <CustomSelect
            className="select-sm"
            hidePlaceholderOption
            value={rolId}
            onChange={(v) => setRolId(Number(v))}
            disabled={isSubmitting}
            options={rolList.map((r) => ({ value: r.id, label: r.nombre }))}
          />
          {errors.rolId && <span className="text-[11px] text-error">{errors.rolId}</span>}
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Estado</span>
          <CustomSelect
            className="select-sm"
            hidePlaceholderOption
            value={activo ? "activo" : "inactivo"}
            onChange={(v) => setActivo(v === "activo")}
            disabled={isSubmitting}
            options={[
              { value: "activo", label: "Activo" },
              { value: "inactivo", label: "Inactivo" },
            ]}
          />
        </div>
      </div>
      </form>
    </div>
  );
}
