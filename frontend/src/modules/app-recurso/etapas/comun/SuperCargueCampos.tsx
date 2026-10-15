import type { ReactNode } from "react";
import { OPCIONES_DECISION, OPCIONES_RESULTADO } from "../formularios/actoFinal";
import { OPCIONES_CLASE_ACTO } from "../formularios/comunes";
import { camposConcepto } from "../formularios/conceptoFinal";
import { MAX_RADICADO, type RadicadoForm } from "../formularios/radicado";
import type { SeccionesSuper, SuperCargueForm } from "../formularios/superCargue";
import { CampoFecha, CampoOpciones, CampoPdf, CampoSiNo, CampoTexto } from "./campos/Campos";
import CampoAbogado from "./campos/CampoAbogado";
import CampoTecnico from "./campos/CampoTecnico";
import CamposConcepto from "./campos/CamposConcepto";

type Props = {
  s: SeccionesSuper;
  form: SuperCargueForm;
  cambiar: (c: Partial<SuperCargueForm>) => void;
  /** La fila ya existe: los datos son opcionales (solo se actualiza lo enviado). */
  existe: boolean;
  /** Documentos ya cargados, para "Ver actual". */
  actuales: Partial<Record<"radicado" | "oficio" | "fijacion" | "constancia" | "concepto" | "respuesta", number | null>>;
};

function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="border border-base-300 rounded-lg p-3 space-y-3">
      <h4 className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">{titulo}</h4>
      {children}
    </section>
  );
}

function CamposRadicado({
  valor,
  onChange,
  documento,
  requerido,
  actualId,
}: {
  valor: RadicadoForm;
  onChange: (r: RadicadoForm) => void;
  documento: string;
  requerido: boolean;
  actualId?: number | null;
}) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CampoTexto
          etiqueta="Radicado"
          valor={valor.radicado}
          onChange={(radicado) => onChange({ ...valor, radicado })}
          maxLength={MAX_RADICADO}
          requerido={requerido}
        />
        <CampoFecha
          etiqueta="Fecha de radicado"
          valor={valor.fecha_radicado}
          onChange={(fecha_radicado) => onChange({ ...valor, fecha_radicado })}
          requerido={requerido}
        />
      </div>
      <CampoPdf
        etiqueta={`${documento} (PDF)`}
        archivo={valor.archivo}
        onChange={(archivo) => onChange({ ...valor, archivo })}
        requerido={requerido}
        actualId={actualId}
      />
    </>
  );
}

/** Secciones del cargue directo de super gestión según el nodo (ver `seccionesSuper`). */
export default function SuperCargueCampos({ s, form, cambiar, existe, actuales }: Props) {
  return (
    <>
      {s.encargado && (
        <Seccion titulo="Abogado encargado">
          <CampoAbogado
            valor={form.encargado_acto_id}
            onChange={(encargado_acto_id) => cambiar({ encargado_acto_id })}
            existe={existe}
          />
        </Seccion>
      )}

      {s.radicado && (
        <Seccion titulo={s.radicado}>
          <CamposRadicado
            valor={form.radicado}
            onChange={(radicado) => cambiar({ radicado })}
            documento={s.radicado}
            requerido={!existe}
            actualId={actuales.radicado}
          />
        </Seccion>
      )}

      {s.concepto && (
        <Seccion titulo="Concepto técnico">
          <CampoTecnico
            valor={form.tecnico_encargado_id}
            onChange={(tecnico_encargado_id) => cambiar({ tecnico_encargado_id })}
            requerido={!existe}
          />
          <CampoPdf
            etiqueta="Concepto firmado (PDF)"
            archivo={form.concepto.archivo}
            onChange={(archivo) => cambiar({ concepto: { ...form.concepto, archivo } })}
            actualId={actuales.concepto}
          />
          <CamposConcepto
            form={form.concepto}
            onChange={(c) => cambiar({ concepto: { ...form.concepto, ...c } })}
            campos={{ obligatorios: [], opcionales: camposConcepto(s.concepto).obligatorios.concat(camposConcepto(s.concepto).opcionales) }}
          />
        </Seccion>
      )}

      {s.acto && (
        <Seccion titulo="Acto administrativo firmado">
          {!s.actoObligatorio && (
            <p className="text-xs text-base-content/60">Opcional. Si lo carga, se cierra el proceso de revisión abierto.</p>
          )}
          <CampoPdf
            etiqueta="Acto (PDF)"
            archivo={form.acto.archivo}
            onChange={(archivo) => cambiar({ acto: { ...form.acto, archivo } })}
            requerido={s.actoObligatorio}
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CampoOpciones
              etiqueta="Tipo de acto"
              valor={form.acto.clase_acto}
              opciones={OPCIONES_CLASE_ACTO}
              onChange={(clase_acto) => cambiar({ acto: { ...form.acto, clase_acto } })}
              requerido={s.actoObligatorio}
            />
            <CampoTexto
              etiqueta="Numerado"
              valor={form.acto.numerado}
              onChange={(v) => cambiar({ acto: { ...form.acto, numerado: v.replace(/\D/g, "").slice(0, 4) } })}
              inputMode="numeric"
              placeholder="0012"
              requerido={s.actoObligatorio}
            />
          </div>
          <CampoFecha
            etiqueta="Fecha de numerado"
            valor={form.acto.fecha_numerado}
            onChange={(fecha_numerado) => cambiar({ acto: { ...form.acto, fecha_numerado } })}
            requerido={s.actoObligatorio}
          />
        </Seccion>
      )}

      {s.tecnicoVisita && (
        <Seccion titulo="Técnico y visita (nace el concepto de la etapa 2)">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CampoTecnico valor={form.tecnico_id} onChange={(tecnico_id) => cambiar({ tecnico_id })} />
            <CampoFecha
              etiqueta="Fecha de visita técnica"
              valor={form.fecha_visita_tecnica}
              onChange={(fecha_visita_tecnica) => cambiar({ fecha_visita_tecnica })}
              permitirFutura
            />
          </div>
        </Seccion>
      )}

      {s.docsAdmite && (
        <Seccion titulo="Documentos del auto">
          <CampoPdf etiqueta="Oficio a la Alcaldía" archivo={form.oficio} onChange={(oficio) => cambiar({ oficio })} actualId={actuales.oficio} />
          <CampoPdf
            etiqueta="Fijación del aviso"
            archivo={form.fijacion}
            onChange={(fijacion) => cambiar({ fijacion })}
            actualId={actuales.fijacion}
          />
          <CampoPdf
            etiqueta="Constancia de fijación de la Alcaldía"
            archivo={form.constancia}
            onChange={(constancia) => cambiar({ constancia })}
            actualId={actuales.constancia}
          />
        </Seccion>
      )}

      {s.respuesta && (
        <Seccion titulo="Respuesta del usuario (opcional)">
          <CamposRadicado
            valor={form.respuesta}
            onChange={(respuesta) => cambiar({ respuesta })}
            documento="Oficio de respuesta"
            requerido={false}
            actualId={actuales.respuesta}
          />
        </Seccion>
      )}

      {s.decision && (
        <Seccion titulo="Decisión">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <CampoOpciones
              etiqueta="Decisión"
              valor={form.decision}
              opciones={OPCIONES_DECISION}
              onChange={(decision) => cambiar({ decision })}
            />
            {form.decision === "OTORGADA" && (
              <CampoSiNo
                etiqueta="¿Exige memorias de cálculo?"
                valor={form.requiere_memorias}
                onChange={(requiere_memorias) => cambiar({ requiere_memorias })}
              />
            )}
            <CampoFecha
              etiqueta="Fecha de ejecutoria"
              valor={form.fecha_ejecutoria}
              onChange={(fecha_ejecutoria) => cambiar({ fecha_ejecutoria })}
            />
          </div>
        </Seccion>
      )}

      {s.resultado && (
        <Seccion titulo="Resultado del recurso">
          <CampoOpciones
            etiqueta="Resultado"
            valor={form.resultado}
            opciones={OPCIONES_RESULTADO}
            onChange={(resultado) => cambiar({ resultado })}
          />
        </Seccion>
      )}
    </>
  );
}
