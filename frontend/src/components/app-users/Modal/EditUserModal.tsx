import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { getErrorMessage } from "../../../utils/api";
import CustomSelect from "../../Common/Form/CustomSelect";

type Rol = { id: number; nombre: string };

type User = {
  id: number;
  document: number;
  primer_nombre: string;
  segundo_nombre: string | null;
  primer_apellido: string;
  segundo_apellido: string | null;
  email: string;
  rol_id: number;
  state: boolean;
};

type SaveData = {
  document: number;
  first_name: string;
  middle_name: string;
  lastname: string;
  second_lastname: string;
  email: string;
  rol_id: number;
  activo: boolean;
};

type Props = {
  user: User | null;
  rolList: Rol[];
  onClose: () => void;
  onSave: (id: number, data: SaveData) => Promise<void>;
};

export default function EditUserModal({ user, rolList, onClose, onSave }: Props) {
  const [documentNumber, setDocumentNumber] = useState("");
  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [secondLastName, setSecondLastName] = useState("");
  const [email, setEmail] = useState("");
  const [rolId, setRolId] = useState(0);
  const [activo, setActivo] = useState(true);
  const [theme, setTheme] = useState("emerald");
  const [errorGeneral, setErrorGeneral] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  useEffect(() => {
    const update = () =>
      setTheme(document.querySelector("[data-theme]")?.getAttribute("data-theme") || "emerald");
    update();
    const observer = new MutationObserver(update);
    const node = document.querySelector("[data-theme]");
    if (node) observer.observe(node, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (user) {
      setDocumentNumber(String(user.document));
      setFirstName(user.primer_nombre);
      setMiddleName(user.segundo_nombre ?? "");
      setLastName(user.primer_apellido);
      setSecondLastName(user.segundo_apellido ?? "");
      setEmail(user.email);
      setRolId(user.rol_id);
      setActivo(user.state);
      setErrors({});
      setErrorGeneral("");
      setIsSubmitting(false);
    }
  }, [user]);

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
    if (!user || !validate()) return;

    setIsSubmitting(true);
    try {
      const payload: SaveData = {
        document: parseInt(documentNumber.trim(), 10),
        first_name: firstName.trim(),
        middle_name: middleName.trim(),
        lastname: lastName.trim(),
        second_lastname: secondLastName.trim(),
        email: email.trim().toLowerCase(),
        rol_id: rolId,
        activo,
      };
      await onSave(user.id, payload);
      handleClose();
    } catch (err) {
      setErrorGeneral(getErrorMessage(err, "Error al actualizar el usuario"));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setErrors({});
    setErrorGeneral("");
    setIsSubmitting(false);
    onClose();
  };

  if (!user) return null;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm p-3 sm:p-4"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-2xl w-full max-w-[560px] shadow-2xl border border-base-300 overflow-hidden max-h-[92vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-success/10 border-b border-base-300 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/15 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content leading-tight">Editar Usuario</h3>
              <p className="text-xs text-base-content/60">Modifica los datos, rol o estado del usuario</p>
            </div>
          </div>
          <button onClick={handleClose} className="btn btn-ghost btn-sm btn-circle text-base-content/70">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5 space-y-4 overflow-y-auto">
          {errorGeneral && (
            <div className="alert alert-error py-2 text-sm">
              <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              {errorGeneral}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Documento */}
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium text-base-content/60">Número de documento *</span>
              <input
                type="text"
                value={documentNumber}
                onChange={(e) => setDocumentNumber(e.target.value.replace(/\D/g, ""))}
                className={`input input-bordered w-full font-mono ${errors.document ? "input-error" : ""}`}
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
                  className={`input input-bordered w-full ${errors.firstName ? "input-error" : ""}`}
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
                  className={`input input-bordered w-full ${errors.middleName ? "input-error" : ""}`}
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
                  className={`input input-bordered w-full ${errors.lastName ? "input-error" : ""}`}
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
                  className={`input input-bordered w-full ${errors.secondLastName ? "input-error" : ""}`}
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
                className={`input input-bordered w-full ${errors.email ? "input-error" : ""}`}
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

            {/* Botones */}
            <div className="flex justify-end gap-3 pt-3 border-t border-base-300">
              <button type="button" onClick={handleClose} className="btn btn-ghost btn-sm" disabled={isSubmitting}>
                Cancelar
              </button>
              <button type="submit" className="btn btn-success btn-sm text-white gap-2 min-w-[150px]" disabled={isSubmitting}>
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
            </div>
          </form>
        </div>
      </div>
    </div>,
    document.body,
  );
}
