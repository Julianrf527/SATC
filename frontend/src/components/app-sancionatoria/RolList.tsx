import { useState, useEffect } from "react";
import { apiCall, API_CONFIG } from '../../utils/api';

type Rol = {
  id: number;
  name: string;
};

type Props = {
  rolRef: React.RefObject<HTMLSelectElement | null>;
  setErrorMsg: (message: string) => void;
};

export default function RolList({ rolRef, setErrorMsg }: Props) {
  const [rolList, setRolList] = useState<Rol[]>([]);

  /* Cargar Roles*/
  useEffect(() => {
    async function loadRol() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_LIST, {
          method: "GET",
        });

        if (res.ok) {
          setRolList(res.data);
        } else {
          setErrorMsg(res.detail || "Error Inesperado");
        }
      } catch (error) {
        /* console.log(error); */
      }
    }
    loadRol();
  }, []);

  return (
    <>
      <h3 className="font-semibold text-lg mt-4">Credenciales</h3>
      <label className="block mb-2">Rol</label>
      <select className="select w-full" ref={rolRef}>
        {rolList.map((rol) => (
          <option key={rol.id} value={rol.id}>
            {capitalize(rol.name)}
          </option>
        ))}
      </select>
    </>
  );
}

function capitalize(word: string) {
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
}
