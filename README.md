# Simcha O

Personal site, built with [Astro](https://astro.build) and hosted on Netlify.

## Running

```sh
npm install
npm run dev       # http://localhost:4321
npm run build     # outputs to dist/
npm run preview   # serve the build locally
```

## Content

- **Projects**: `src/content/projects.yaml` (icons and screenshots in `src/assets/projects/`)
- **Pics**: drop images into `src/assets/pics/`
- **Tweets**: drop screenshots into `src/assets/favorites/tweets/`
- **Colours**: CSS variables at the top of `src/layouts/BaseLayout.astro` (in dev, a colour panel in the bottom-right lets you tweak them live)

The contact form uses Netlify Forms, so it only works on the deployed site.
