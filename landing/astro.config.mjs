import react from '@astrojs/react'
import tailwind from '@astrojs/tailwind'
import { defineConfig } from 'astro/config'

// https://astro.build/config
export default defineConfig({
  // Fixed port so the URL doesn’t silently change when 4321 is taken (common “page won’t open” confusion).
  server: {
    port: 4788,
    strictPort: true,
  },
  integrations: [
    react(),
    tailwind({
      applyBaseStyles: false,
    }),
  ],
})
