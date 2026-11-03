// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
	// The site's public address: used for the og:image link, canonical links and the sitemap.
	site: 'https://simchaorgel.net',
	// Builds /sitemap-index.xml (linked from public/robots.txt) listing every page.
	integrations: [sitemap()],
});
