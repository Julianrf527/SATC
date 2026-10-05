export type Municipio = {
  id: number;
  nombre: string;
  veredas: ModeloGenerico[];
};

export type ModeloGenerico = {
  id: number;
  nombre: string;
};