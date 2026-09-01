const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const http = require("http");
const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");

const APP_DIR = path.join(__dirname, "app");

function sanitizarNombreArchivo(txt) {
  const limpio = String(txt || "").replace(/[\\/:*?"<>|]/g, "-").trim().slice(0, 150);
  return limpio || "documento";
}

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".pdf": "application/pdf",
};

function servidorEstatico(req, res) {
  let ruta = decodeURIComponent(req.url.split("?")[0]);
  if (ruta === "/") ruta = "/index.html";

  const rutaAbsoluta = path.normalize(path.join(APP_DIR, ruta));
  // Evita salir de APP_DIR (path traversal)
  if (!rutaAbsoluta.startsWith(APP_DIR)) {
    res.writeHead(403);
    res.end("Prohibido");
    return;
  }

  fs.readFile(rutaAbsoluta, (err, data) => {
    if (err) {
      res.writeHead(404);
      res.end("No encontrado");
      return;
    }
    const ext = path.extname(rutaAbsoluta);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
}

function iniciarServidor() {
  return new Promise((resolve) => {
    const server = http.createServer(servidorEstatico);
    // Puerto 0 = el sistema operativo asigna uno libre
    server.listen(0, "127.0.0.1", () => {
      resolve(server.address().port);
    });
  });
}

async function crearVentana() {
  const puerto = await iniciarServidor();

  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  win.loadURL(`http://127.0.0.1:${puerto}/`);
}

ipcMain.handle("elegir-carpeta", async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  const result = await dialog.showOpenDialog(win, {
    title: "Selecciona la carpeta donde guardar los PDFs (ej. Escritorio)",
    properties: ["openDirectory", "createDirectory"],
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
});

ipcMain.handle("guardar-expediente", async (_event, payload) => {
  const { carpetaBase, expedienteNombre, archivos } = payload;
  const carpetaExpediente = path.join(
    carpetaBase,
    sanitizarNombreArchivo(expedienteNombre),
  );
  await fsp.mkdir(carpetaExpediente, { recursive: true });

  let generados = 0;
  for (const archivo of archivos) {
    const carpetaEtapa = path.join(
      carpetaExpediente,
      sanitizarNombreArchivo(archivo.etapaLabel),
    );
    await fsp.mkdir(carpetaEtapa, { recursive: true });
    const rutaArchivo = path.join(
      carpetaEtapa,
      sanitizarNombreArchivo(archivo.nombreArchivo),
    );
    await fsp.writeFile(rutaArchivo, Buffer.from(archivo.bytes));
    generados++;
  }

  return { generados, carpetaFinal: carpetaExpediente };
});

app.whenReady().then(crearVentana);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) crearVentana();
});
