/**
 * Red de seguridad contra extensiones o traductores que modifican el DOM que
 * maneja React (Google Translate envuelve textos en <font>; otras extensiones
 * insertan o mueven nodos). Cuando React intenta quitar o insertar junto a un
 * nodo que ya no es hijo del padre esperado, el navegador lanza NotFoundError
 * y se cae toda la pantalla. Aquí se ignora esa operación inválida en lugar
 * de lanzar el error (workaround conocido: facebook/react#11538).
 */
export function instalarParcheDomExterno(): void {
  if (typeof Node !== "function" || !Node.prototype) return;

  const removeChildOriginal = Node.prototype.removeChild;
  Node.prototype.removeChild = function <T extends Node>(this: Node, hijo: T): T {
    if (hijo.parentNode !== this) {
      console.warn("DOM modificado externamente: removeChild omitido", hijo, this);
      return hijo;
    }
    return removeChildOriginal.call(this, hijo) as T;
  };

  const insertBeforeOriginal = Node.prototype.insertBefore;
  Node.prototype.insertBefore = function <T extends Node>(
    this: Node,
    nuevo: T,
    referencia: Node | null,
  ): T {
    if (referencia && referencia.parentNode !== this) {
      console.warn("DOM modificado externamente: insertBefore sin referencia válida", referencia, this);
      return insertBeforeOriginal.call(this, nuevo, null) as T;
    }
    return insertBeforeOriginal.call(this, nuevo, referencia) as T;
  };
}
