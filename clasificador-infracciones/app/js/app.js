import { CATALOGO_ETAPAS } from "./catalogo.js";
import * as pdfjsLib from "../lib/pdf.min.mjs";

pdfjsLib.GlobalWorkerOptions.workerSrc = "lib/pdf.worker.min.mjs";

// ---------- Estado ----------
let pdfBytesOriginal = null; // ArrayBuffer crudo, se copia antes de pasarlo a cada consumidor
let pdfDoc = null; // documento pdf.js (para visualizar)
let numPages = 0;
let paginaActual = 1;
let escala = 1.2;
let nombreArchivoBase = "expediente";

let uidSeq = 1;
function crearFila(nombre) {
  return { uid: uidSeq++, nombre, desde: "", hasta: "" };
}

// etapas[etapaId] = [{ uid, nombre, desde, hasta }, ...]
const etapasState = {};
const etapaColapsada = {};
CATALOGO_ETAPAS.forEach((etapa) => {
  etapasState[etapa.id] = etapa.documentos.map((nombre) => crearFila(nombre));
  etapaColapsada[etapa.id] = true;
});

let filaActivaUid = null;

function buscarFilaPorUid(uid) {
  for (const etapa of CATALOGO_ETAPAS) {
    const fila = etapasState[etapa.id].find((f) => f.uid === uid);
    if (fila) return { etapaId: etapa.id, fila };
  }
  return null;
}

// ---------- Referencias DOM ----------
const inputPdf = document.getElementById("input-pdf");
const btnAbrir = document.getElementById("btn-abrir");
const nombreArchivoSpan = document.getElementById("nombre-archivo");
const btnGenerar = document.getElementById("btn-generar");

const visorContenedor = document.getElementById("visor-contenedor");
const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");
const inputPagina = document.getElementById("input-pagina");
const paginaInfo = document.getElementById("pagina-info");
const btnZoomOut = document.getElementById("btn-zoom-out");
const btnZoomIn = document.getElementById("btn-zoom-in");
const zoomInfo = document.getElementById("zoom-info");

const panelEtapas = document.getElementById("panel-etapas");

// ---------- Toasts ----------
function toast(mensaje, tipo = "info") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast toast-${tipo}`;
  el.textContent = mensaje;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

// ---------- Apertura de PDF ----------
btnAbrir.addEventListener("click", () => inputPdf.click());

inputPdf.addEventListener("change", async (ev) => {
  const file = ev.target.files[0];
  if (!file) return;
  nombreArchivoBase = file.name.replace(/\.pdf$/i, "");
  nombreArchivoSpan.textContent = file.name;

  try {
    pdfBytesOriginal = await file.arrayBuffer();
    const copiaParaVisor = pdfBytesOriginal.slice(0);
    pdfDoc = await pdfjsLib.getDocument({ data: copiaParaVisor }).promise;
    numPages = pdfDoc.numPages;
    paginaActual = 1;

    btnPrev.disabled = false;
    btnNext.disabled = false;
    inputPagina.disabled = false;
    inputPagina.max = numPages;
    btnZoomIn.disabled = false;
    btnZoomOut.disabled = false;
    btnGenerar.disabled = false;

    await renderPagina();
    toast(`Expediente cargado: ${numPages} hojas.`, "success");
  } catch (err) {
    console.error(err);
    toast("No se pudo abrir el PDF. ¿Es un archivo válido?", "error");
  }
});

let canvasVisor = null;
let cargandoBadge = null;
let renderTaskActual = null;
let renderTokenActual = 0;
let cargandoTimeout = null;

function mostrarCargando() {
  cargandoTimeout = setTimeout(() => cargandoBadge.classList.add("visible"), 150);
}
function ocultarCargando() {
  clearTimeout(cargandoTimeout);
  cargandoBadge.classList.remove("visible");
}

// Pide (sin renderizar) las páginas vecinas para que pdf.js las tenga
// parseadas en caché antes de que el usuario navegue hasta ahí.
function precargarVecinas(centro) {
  [centro - 1, centro + 1].forEach((n) => {
    if (n >= 1 && n <= numPages) pdfDoc.getPage(n).catch(() => {});
  });
}

async function renderPagina() {
  if (!pdfDoc) return;

  // Actualiza controles/contador al instante, sin esperar a que la imagen termine de dibujarse
  inputPagina.value = paginaActual;
  paginaInfo.textContent = `/ ${numPages}`;
  zoomInfo.textContent = `${Math.round(escala * 100)}%`;
  btnPrev.disabled = paginaActual <= 1;
  btnNext.disabled = paginaActual >= numPages;

  const miToken = ++renderTokenActual;

  // Si hay un render en curso, se cancela: evita que renders viejos compitan por CPU
  if (renderTaskActual) {
    try {
      renderTaskActual.cancel();
    } catch (e) {
      /* ya terminado o cancelado, se ignora */
    }
  }

  if (!canvasVisor) {
    canvasVisor = document.createElement("canvas");
    cargandoBadge = document.createElement("div");
    cargandoBadge.className = "cargando-badge";
    cargandoBadge.textContent = "Cargando…";
    visorContenedor.innerHTML = "";
    visorContenedor.appendChild(canvasVisor);
    visorContenedor.appendChild(cargandoBadge);
  }
  mostrarCargando();

  const page = await pdfDoc.getPage(paginaActual);
  if (miToken !== renderTokenActual) return; // llegó un pedido más nuevo mientras esperaba

  const viewport = page.getViewport({ scale: escala });
  canvasVisor.width = viewport.width;
  canvasVisor.height = viewport.height;

  const ctx = canvasVisor.getContext("2d");
  const tarea = page.render({ canvasContext: ctx, viewport });
  renderTaskActual = tarea;

  try {
    await tarea.promise;
    precargarVecinas(paginaActual);
  } catch (err) {
    if (err?.name === "RenderingCancelledException") return; // esperado, no es error real
    throw err;
  } finally {
    if (renderTaskActual === tarea) renderTaskActual = null;
    if (miToken === renderTokenActual) ocultarCargando();
  }
}

function irAPagina(valor) {
  const n = parseInt(valor, 10);
  if (!Number.isInteger(n) || n < 1 || n > numPages) {
    inputPagina.value = paginaActual; // revierte si es inválido
    return;
  }
  paginaActual = n;
  renderPagina();
}

inputPagina.addEventListener("change", (e) => irAPagina(e.target.value));
inputPagina.addEventListener("keydown", (e) => {
  if (e.key === "Enter") inputPagina.blur();
});

btnPrev.addEventListener("click", () => {
  if (paginaActual > 1) {
    paginaActual--;
    renderPagina();
  }
});
btnNext.addEventListener("click", () => {
  if (paginaActual < numPages) {
    paginaActual++;
    renderPagina();
  }
});
btnZoomIn.addEventListener("click", () => {
  escala = Math.min(escala + 0.2, 3);
  renderPagina();
});
btnZoomOut.addEventListener("click", () => {
  escala = Math.max(escala - 0.2, 0.4);
  renderPagina();
});

// ---------- Panel de etapas ----------
function renderPanel() {
  panelEtapas.innerHTML = "";

  CATALOGO_ETAPAS.forEach((etapa) => {
    const filas = etapasState[etapa.id];
    const marcadas = filas.filter((f) => filaValida(f)).length;

    const etapaEl = document.createElement("div");
    etapaEl.className = "etapa";
    etapaEl.dataset.etapaId = etapa.id;

    const header = document.createElement("div");
    header.className = "etapa-header";
    header.innerHTML = `
      <h3>${etapa.label}</h3>
      <span>
        <span class="etapa-contador">${marcadas}/${filas.length} marcados</span>
        <span class="etapa-toggle">▾</span>
      </span>
    `;

    const body = document.createElement("div");
    body.className = etapaColapsada[etapa.id] ? "etapa-body colapsado" : "etapa-body";
    header.querySelector(".etapa-toggle").textContent = etapaColapsada[etapa.id]
      ? "▸"
      : "▾";

    header.addEventListener("click", () => {
      etapaColapsada[etapa.id] = !etapaColapsada[etapa.id];
      body.classList.toggle("colapsado", etapaColapsada[etapa.id]);
      header.querySelector(".etapa-toggle").textContent = etapaColapsada[etapa.id]
        ? "▸"
        : "▾";
    });

    filas.forEach((fila) => body.appendChild(renderFila(etapa.id, fila)));

    const btnAgregar = document.createElement("button");
    btnAgregar.className = "btn-agregar";
    btnAgregar.textContent = "+ agregar documento / anexo";
    btnAgregar.addEventListener("click", () => {
      const nuevaFila = crearFila("");
      etapasState[etapa.id].push(nuevaFila);
      body.insertBefore(renderFila(etapa.id, nuevaFila), btnAgregar);
      actualizarContadorEtapa(etapa.id);
    });
    body.appendChild(btnAgregar);

    etapaEl.appendChild(header);
    etapaEl.appendChild(body);
    panelEtapas.appendChild(etapaEl);
  });
}

function actualizarContadorEtapa(etapaId) {
  const filas = etapasState[etapaId];
  const marcadas = filas.filter((f) => filaValida(f)).length;
  const etapaEl = document.querySelector(`.etapa[data-etapa-id="${etapaId}"]`);
  if (!etapaEl) return;
  etapaEl.querySelector(".etapa-contador").textContent = `${marcadas}/${filas.length} marcados`;
}

function filaValida(fila) {
  const desde = parseInt(fila.desde, 10);
  const hasta = parseInt(fila.hasta, 10);
  return (
    Number.isInteger(desde) &&
    Number.isInteger(hasta) &&
    desde >= 1 &&
    hasta >= desde &&
    (!numPages || hasta <= numPages)
  );
}

function filaIncompleta(fila) {
  const tieneDesde = fila.desde !== "" && fila.desde !== null;
  const tieneHasta = fila.hasta !== "" && fila.hasta !== null;
  if (!tieneDesde && !tieneHasta) return false; // vacía, no cuenta
  return !filaValida(fila);
}

function renderFila(etapaId, fila) {
  const wrap = document.createElement("div");
  wrap.className = "doc-fila";
  wrap.dataset.uid = fila.uid;
  if (filaValida(fila)) wrap.classList.add("marcada");
  else if (filaIncompleta(fila)) wrap.classList.add("incompleta");
  if (fila.uid === filaActivaUid) wrap.classList.add("activa");

  wrap.addEventListener("click", (e) => {
    if (e.target.closest("button")) return;
    seleccionarFila(fila.uid);
  });

  const nombreInput = document.createElement("input");
  nombreInput.className = "doc-nombre";
  nombreInput.type = "text";
  nombreInput.placeholder = "Nombre del documento";
  nombreInput.value = fila.nombre;
  nombreInput.addEventListener("input", (e) => {
    fila.nombre = e.target.value;
  });

  const desdeInput = document.createElement("input");
  desdeInput.className = "doc-hoja doc-desde";
  desdeInput.type = "number";
  desdeInput.min = "1";
  desdeInput.placeholder = "Desde";
  desdeInput.value = fila.desde;
  desdeInput.addEventListener("input", (e) => {
    fila.desde = e.target.value;
    actualizarFila(wrap, fila, desdeInput, hastaInput);
  });

  const sep = document.createElement("span");
  sep.className = "doc-sep";
  sep.textContent = "→";

  const hastaInput = document.createElement("input");
  hastaInput.className = "doc-hoja doc-hasta";
  hastaInput.type = "number";
  hastaInput.min = "1";
  hastaInput.placeholder = "Hasta";
  hastaInput.value = fila.hasta;
  hastaInput.addEventListener("input", (e) => {
    fila.hasta = e.target.value;
    actualizarFila(wrap, fila, desdeInput, hastaInput);
  });

  const btnUsarPag = document.createElement("button");
  btnUsarPag.className = "btn-icon";
  btnUsarPag.title = "Usar página actual del visor";
  btnUsarPag.textContent = "📍";
  btnUsarPag.addEventListener("click", () => {
    if (!fila.desde) {
      fila.desde = paginaActual;
      desdeInput.value = paginaActual;
    } else {
      fila.hasta = paginaActual;
      hastaInput.value = paginaActual;
    }
    actualizarFila(wrap, fila, desdeInput, hastaInput);
  });

  const btnBorrar = document.createElement("button");
  btnBorrar.className = "btn-icon btn-borrar";
  btnBorrar.title = "Quitar fila";
  btnBorrar.textContent = "✕";
  btnBorrar.addEventListener("click", () => {
    etapasState[etapaId] = etapasState[etapaId].filter((f) => f.uid !== fila.uid);
    if (filaActivaUid === fila.uid) filaActivaUid = null;
    wrap.remove();
    actualizarContadorEtapa(etapaId);
  });

  wrap.appendChild(nombreInput);
  wrap.appendChild(desdeInput);
  wrap.appendChild(sep);
  wrap.appendChild(hastaInput);
  wrap.appendChild(btnUsarPag);
  wrap.appendChild(btnBorrar);
  return wrap;
}

function actualizarFila(wrap, fila, desdeInput, hastaInput) {
  wrap.classList.remove("marcada", "incompleta");
  if (filaValida(fila)) wrap.classList.add("marcada");
  else if (filaIncompleta(fila)) wrap.classList.add("incompleta");

  const desde = parseInt(fila.desde, 10);
  const hasta = parseInt(fila.hasta, 10);
  const desdeInvalido = fila.desde !== "" && (!Number.isInteger(desde) || desde < 1);
  const hastaInvalido =
    fila.hasta !== "" &&
    (!Number.isInteger(hasta) || hasta < 1 || (Number.isInteger(desde) && hasta < desde));
  desdeInput.classList.toggle("hoja-invalida", desdeInvalido);
  hastaInput.classList.toggle("hoja-invalida", hastaInvalido);

  const etapaId = Object.keys(etapasState).find((id) =>
    etapasState[id].some((f) => f.uid === fila.uid),
  );
  actualizarContadorEtapa(etapaId);
}

renderPanel();

// ---------- Selección de fila + atajos de teclado ----------
function seleccionarFila(uid) {
  filaActivaUid = uid;
  document
    .querySelectorAll(".doc-fila.activa")
    .forEach((el) => el.classList.remove("activa"));
  const nuevo = document.querySelector(`.doc-fila[data-uid="${uid}"]`);
  if (nuevo) nuevo.classList.add("activa");
}

function sincronizarFilaDOM(fila) {
  const wrap = document.querySelector(`.doc-fila[data-uid="${fila.uid}"]`);
  if (!wrap) return;
  const desdeInput = wrap.querySelector(".doc-desde");
  const hastaInput = wrap.querySelector(".doc-hasta");
  desdeInput.value = fila.desde;
  hastaInput.value = fila.hasta;
  actualizarFila(wrap, fila, desdeInput, hastaInput);
}

function avanzarFilaActiva(etapaId, uidActual) {
  const filas = etapasState[etapaId];
  const idx = filas.findIndex((f) => f.uid === uidActual);
  const siguiente = filas[idx + 1];
  if (siguiente) seleccionarFila(siguiente.uid);
}

function marcarConEspacio() {
  if (!pdfDoc) return;
  if (!filaActivaUid) {
    toast("Hace clic en una fila del panel para seleccionarla antes de usar espacio.", "info");
    return;
  }
  const encontrado = buscarFilaPorUid(filaActivaUid);
  if (!encontrado) return;
  const { etapaId, fila } = encontrado;

  let completoHasta = false;
  if (!fila.desde) {
    fila.desde = paginaActual;
  } else if (!fila.hasta) {
    fila.hasta = paginaActual;
    completoHasta = true;
  } else {
    // ya estaba completa: reinicia el rango desde la página actual
    fila.desde = paginaActual;
    fila.hasta = "";
  }

  sincronizarFilaDOM(fila);
  if (completoHasta) avanzarFilaActiva(etapaId, fila.uid);
}

document.addEventListener("keydown", (e) => {
  const activo = document.activeElement;
  const enCampoTexto =
    activo && (activo.tagName === "INPUT" || activo.tagName === "TEXTAREA");

  if (e.code === "ArrowLeft" && !enCampoTexto) {
    e.preventDefault();
    if (!btnPrev.disabled) btnPrev.click();
  } else if (e.code === "ArrowRight" && !enCampoTexto) {
    e.preventDefault();
    if (!btnNext.disabled) btnNext.click();
  } else if (e.code === "Space" && !enCampoTexto) {
    e.preventDefault();
    marcarConEspacio();
  }
});

// ---------- Generación de PDFs ----------
function sanitizarNombre(txt) {
  return txt.replace(/[\\/:*?"<>|]/g, "-").trim().slice(0, 120);
}

btnGenerar.addEventListener("click", async () => {
  if (!pdfBytesOriginal) {
    toast("Primero abre un PDF.", "error");
    return;
  }

  // Recolectar filas incompletas (desde sin hasta, o viceversa)
  const incompletas = [];
  CATALOGO_ETAPAS.forEach((etapa) => {
    etapasState[etapa.id].forEach((fila) => {
      if (filaIncompleta(fila)) {
        incompletas.push(`${etapa.label} — ${fila.nombre || "(sin nombre)"}`);
      }
    });
  });
  if (incompletas.length > 0) {
    toast(
      `Hay ${incompletas.length} fila(s) con "Desde" o "Hasta" sin completar. Corrígelas antes de generar.`,
      "error",
    );
    return;
  }

  const tareas = [];
  CATALOGO_ETAPAS.forEach((etapa) => {
    etapasState[etapa.id].forEach((fila) => {
      if (filaValida(fila)) {
        tareas.push({
          etapaLabel: etapa.label,
          nombre: fila.nombre || "Documento",
          desde: parseInt(fila.desde, 10),
          hasta: parseInt(fila.hasta, 10),
        });
      }
    });
  });

  if (tareas.length === 0) {
    toast("No hay ningún documento marcado con rango de hojas.", "error");
    return;
  }

  const esElectron = !!window.electronAPI;

  let dirHandle = null; // solo modo navegador
  let carpetaBase = null; // solo modo Electron

  if (esElectron) {
    carpetaBase = await window.electronAPI.elegirCarpetaDestino();
    if (!carpetaBase) return; // el usuario canceló el diálogo
  } else if ("showDirectoryPicker" in window) {
    try {
      dirHandle = await window.showDirectoryPicker({
        id: "clasificador-expedientes",
        startIn: "desktop",
      });
    } catch (err) {
      return; // el usuario canceló el picker
    }
  } else {
    toast(
      "Este navegador no soporta guardar directo en Escritorio. Usa Chrome o Edge.",
      "error",
    );
    return;
  }

  btnGenerar.disabled = true;
  btnGenerar.textContent = "Generando...";

  try {
    const PDFDocument = window.PDFLib.PDFDocument;
    const fuente = await PDFDocument.load(pdfBytesOriginal.slice(0));

    // Genera los bytes de cada PDF recortado
    const archivos = [];
    for (const tarea of tareas) {
      const nuevo = await PDFDocument.create();
      const indices = [];
      for (let p = tarea.desde; p <= tarea.hasta; p++) indices.push(p - 1);
      const copiadas = await nuevo.copyPages(fuente, indices);
      copiadas.forEach((pg) => nuevo.addPage(pg));
      const bytes = await nuevo.save();
      const nombreArchivo = sanitizarNombre(
        `${tarea.nombre} (p${tarea.desde}-${tarea.hasta}).pdf`,
      );
      archivos.push({ etapaLabel: tarea.etapaLabel, nombreArchivo, bytes });
    }

    let generados = 0;
    let carpetaFinal = "";

    if (esElectron) {
      const resultado = await window.electronAPI.guardarExpediente({
        carpetaBase,
        expedienteNombre: sanitizarNombre(nombreArchivoBase),
        archivos,
      });
      generados = resultado.generados;
      carpetaFinal = resultado.carpetaFinal;
    } else {
      const expedienteDirHandle = await dirHandle.getDirectoryHandle(
        sanitizarNombre(nombreArchivoBase),
        { create: true },
      );
      for (const archivo of archivos) {
        const etapaDirHandle = await expedienteDirHandle.getDirectoryHandle(
          sanitizarNombre(archivo.etapaLabel),
          { create: true },
        );
        const fileHandle = await etapaDirHandle.getFileHandle(archivo.nombreArchivo, {
          create: true,
        });
        const writable = await fileHandle.createWritable();
        await writable.write(archivo.bytes);
        await writable.close();
        generados++;
      }
      carpetaFinal = sanitizarNombre(nombreArchivoBase);
    }

    toast(`${generados} PDF(s) generado(s) en: ${carpetaFinal}`, "success");
  } catch (err) {
    console.error(err);
    toast("Error generando los PDFs: " + err.message, "error");
  } finally {
    btnGenerar.disabled = false;
    btnGenerar.textContent = "Generar PDFs en Escritorio";
  }
});
