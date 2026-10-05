// Pila global de modales abiertos: con modales anidados (p. ej. detalle de
// documento -> subir versión), Esc y la trampa de foco solo aplican al de arriba.
const stack: string[] = [];

export function pushModal(id: string): void {
  stack.push(id);
}

export function popModal(id: string): void {
  const i = stack.lastIndexOf(id);
  if (i !== -1) stack.splice(i, 1);
}

export function isTopModal(id: string): boolean {
  return stack[stack.length - 1] === id;
}
