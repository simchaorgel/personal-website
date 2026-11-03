// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	// The site's public address, used to build absolute URLs (the og:image link needs one).
	// Netlify sets URL to the site's main address during its builds.
	site: process.env.URL,
});
