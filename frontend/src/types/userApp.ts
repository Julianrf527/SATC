export type Permiso = {
  id: number;
  nombre: string;
  menu_path: string;
};

export type Rol = {
    id: number;
    nombre: string;
    permisos: number[];
};
