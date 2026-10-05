/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
import { playwright } from '@vitest/browser-playwright';
const dirname = typeof __dirname !== 'undefined' ? __dirname : path.dirname(fileURLToPath(import.meta.url));

// More info at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon
export default defineConfig({
  plugins: [tailwindcss()],
  // Los *.stories.tsx están excluidos de tsconfig.app.json, así que esbuild no
  // hereda "jsx": "react-jsx" y caía al runtime clásico ("React is not defined").
  esbuild: { jsx: 'automatic' },
  // Alias de capas: mantener sincronizado con "paths" de tsconfig.app.json.
  resolve: {
    alias: {
      '@app': path.resolve(dirname, 'src/app'),
      '@shared': path.resolve(dirname, 'src/shared'),
      '@features': path.resolve(dirname, 'src/features'),
      '@modules': path.resolve(dirname, 'src/modules'),
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Sin esto todo cae en un solo bundle de ~630 KB: las librerías cambian
        // poco, así que en trozos aparte se quedan cacheadas entre despliegues.
        manualChunks(id: string) {
          if (!id.includes('node_modules')) return;
          if (id.includes('lucide-react')) return 'icons';
          if (/[\\/]node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/.test(id)) return 'react';
          return 'vendor';
        },
      },
    },
  },
  test: {
    projects: [{
      // Tests unitarios de lógica pura (shared/lib, hooks sin DOM): `npm run test:unit`
      extends: true,
      test: {
        name: 'unit',
        environment: 'node',
        include: ['src/**/*.test.ts']
      }
    }, {
      extends: true,
      plugins: [
      // The plugin will run tests for the stories defined in your Storybook config
      // See options at: https://storybook.js.org/docs/next/writing-tests/integrations/vitest-addon#storybooktest
      storybookTest({
        configDir: path.join(dirname, '.storybook')
      })],
      test: {
        name: 'storybook',
        browser: {
          enabled: true,
          headless: true,
          provider: playwright({}),
          instances: [{
            browser: 'chromium'
          }]
        },
        setupFiles: ['.storybook/vitest.setup.ts']
      }
    }]
  }
});