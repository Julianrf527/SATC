type Props = { id:number; state?: boolean};

export default function ({ id, state }: Props) {
  return (
    <>
      <button key={id} className={ state ? "btn btn-outline btn-primary" : "btn btn-outline btn-accent" }> {state ? "Agregar" : "Quitar"}</button>
    </>
  );
}
