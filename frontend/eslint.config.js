// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { globalIgnores } from 'eslint/config'

// ─────────────────────────────────────────────────────────────────────────────
// Fronteras de capas (ver ARCHITECTURE.md)
//
//   app      → todo
//   modules  → features (solo su index), shared
//   features → shared            (nunca otra feature, modules ni app)
//   shared   → nada de arriba
//
// Dos mecanismos con `no-restricted-imports`:
//  1. Alias prohibidos por capa (@app, @features, @modules).
//  2. Imports relativos que se salen del "slice" (src/<capa>/<slice>/): entre
//     slices siempre se usa alias, así la regla 1 los ve. Se generan bloques
//     por profundidad porque el número de "../" que escapa depende de ella.
// ─────────────────────────────────────────────────────────────────────────────

const MSG_SLICE =
  'Import relativo que sale de su slice. Entre slices usa el alias (@shared/..., @features/<nombre>, @modules/...) y respeta las capas (ver ARCHITECTURE.md).'

const LAYER_BANS = {
  shared: [
    {
      group: ['@app', '@app/**', '@features', '@features/**', '@modules', '@modules/**'],
      message: 'shared no puede depender de app, features ni modules.',
    },
  ],
  features: [
    {
      group: ['@app', '@app/**', '@modules', '@modules/**'],
      message: 'Una feature solo puede depender de shared (no de app ni de modules).',
    },
    {
      group: ['@features', '@features/**'],
      message: 'Una feature no importa otras features. Dentro de la misma feature usa rutas relativas; si dos features comparten algo, va a shared.',
    },
  ],
  modules: [
    { group: ['@app', '@app/**'], message: 'modules no puede depender de app.' },
    {
      group: ['@features/*/**'],
      message: 'Importa la feature por su API pública: "@features/<nombre>" (index.ts), no archivos internos.',
    },
    {
      group: ['@modules', '@modules/**'],
      message: 'Un módulo no importa otro módulo. Si algo se comparte, muévelo a features/ (o shared/ si no tiene dominio).',
    },
  ],
  app: [
    {
      group: ['@features/*/**'],
      message: 'Importa la feature por su API pública: "@features/<nombre>" (index.ts).',
    },
  ],
}

const MAX_DEPTH = 6
const layerBoundaryConfigs = []
for (const layer of ['shared', 'features', 'modules']) {
  // depth = nº de carpetas bajo src/<capa>/ (incluye la del slice)
  for (let depth = 1; depth <= MAX_DEPTH; depth++) {
    layerBoundaryConfigs.push({
      files: [`src/${layer}/${'*/'.repeat(depth)}*.{ts,tsx}`],
      rules: {
        'no-restricted-imports': [
          'error',
          {
            patterns: [
              ...LAYER_BANS[layer],
              { regex: `^(\\.\\./){${depth},}`, message: MSG_SLICE },
            ],
          },
        ],
      },
    })
  }
}
layerBoundaryConfigs.push({
  files: ['src/app/**/*.{ts,tsx}'],
  rules: { 'no-restricted-imports': ['error', { patterns: LAYER_BANS.app }] },
})

// features/proceso-revision es un motor genérico: no puede conocer flujos
// concretos. Lo específico de cada flujo entra por props/slots/adapters.
const MSG_FLUJO =
  'features/proceso-revision no puede referenciar flujos concretos (informe_tecnico, origen...). Recibe lo específico por props/slots/adapters desde el módulo.'
const procesoRevisionConfig = {
  files: ['src/features/proceso-revision/**/*.{ts,tsx}'],
  rules: {
    'no-restricted-syntax': [
      'error',
      { selector: 'Literal[value=/informe_tecnico|origen/i]', message: MSG_FLUJO },
      { selector: 'TemplateElement[value.raw=/informe_tecnico|origen/i]', message: MSG_FLUJO },
      { selector: 'Identifier[name=/^origen$|informe_?tecnico/i]', message: MSG_FLUJO },
    ],
  },
}

export default tseslint.config([
  globalIgnores(['dist', 'storybook-static']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs['recommended-latest'],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  ...layerBoundaryConfigs,
  procesoRevisionConfig,
], storybook.configs["flat/recommended"]);
