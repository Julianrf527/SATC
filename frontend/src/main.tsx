import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Tras un deploy, los hashes de los chunks cambian: un import() dinámico
// pendiente de una sesión vieja apunta a un archivo que ya no existe.
// Vite dispara este evento en ese caso; recargamos una sola vez para
// obtener el index.html actualizado en vez de dejar la pestaña en blanco.
const RELOAD_FLAG = 'satc:reloaded-after-chunk-error'
window.addEventListener('vite:preloadError', () => {
  if (sessionStorage.getItem(RELOAD_FLAG)) return
  sessionStorage.setItem(RELOAD_FLAG, '1')
  window.location.reload()
})
// Si la app carga bien tras el reload, limpiamos el flag para que un
// futuro error de chunk (otro deploy) también dispare la recarga.
window.setTimeout(() => sessionStorage.removeItem(RELOAD_FLAG), 5000)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
