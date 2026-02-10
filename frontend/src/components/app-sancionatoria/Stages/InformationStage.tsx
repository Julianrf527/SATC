import type { File, Town, Resource } from "../../../types";
import BasicDataFile from "./Information/BasicDataFile";
import InvolvedFile from "./Information/InvolvedFile";
import Alerts from "./Information/Alerts";

type Props = {
  file: File | null;
  towns?: Town[];
  resources?: Resource[];
  onFileUpdate?: (updatedFile: File) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
};

export default function InformationStage({
  file,
  towns = [],
  resources = [],
  onFileUpdate,
  setToast,
  isEditable = true,
}: Props) {
  if (!file) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
            <svg
              className="w-8 h-8 text-base-content/40"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-base-content/70 mb-2">
            Sin expediente seleccionado
          </h3>
          <p className="text-base-content/50">
            Selecciona un expediente para ver su información
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="w-full">
        <BasicDataFile
          file={file}
          towns={towns}
          resources={resources}
          onFileUpdate={onFileUpdate}
          setToast={setToast}
          isEditable={isEditable}
        />
      </div>

      <div className="w-full">
        <InvolvedFile
          file={file}
          onFileUpdate={onFileUpdate}
          setToast={setToast}
          isEditable={isEditable}
        />
      </div>

      {/* Alertas solo visibles en modo editable */}
      {isEditable && (
        <div className="w-full">
          <Alerts radicado={file.radicado} setToast={setToast} />
        </div>
      )}
    </div>
  );
}
