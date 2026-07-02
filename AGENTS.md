This is a personal website built to feel like a little desktop operating system: a beige
gridded "desktop", clickable icons that open draggable **windows**, a bottom **taskbar**, and
multiple "desktops" you navigate between with sliding page transitions. It's intentionally
playful and bespoke — the aesthetic is hand-tuned element by element, so favour taste and
iteration over generic UI patterns.

This doc is an orientation, not a rulebook. It explains how the pieces fit together and the
sharp edges we've already hit, so you can move fast without relearning them painfully. Where
it describes "how we do X", that's the current grain of the codebase — follow it when it
helps, diverge when you have a good reason.

## Development

Dev server in background mode:

```
astro dev --background
```

Manage it with `astro dev stop`, `astro dev status`, `astro dev logs`.

The user keeps the dev server open and watches changes live, so **don't run `npm run build`
just to "validate" routine edits** — it tells you nothing they can't already see, and Astro's
dev overlay surfaces real errors. Build only for genuinely risky, multi-file, or cross-page
changes.

## Stack & big picture

- **Astro + TypeScript**, mostly static. No backend (contact form posts to Netlify).
- **`<ClientRouter />`** (Astro view transitions) gives SPA-style navigation between desktops,
  with a directional slide and a taskbar that stays put.
- Each **"desktop" is a page** (`src/pages/*.astro`) wrapped in a shared `Layout`.
- The desktop surface = scattered **desktop icons** + **windows** + the **taskbar**.

## Project map

```
src/
  layouts/Layout.astro     <html>/<head>, ClientRouter, global.css, renders the Taskbar,
                           and an inline script that tags nav direction (forward/back).
  pages/
    index.astro            The home desktop. Lays out icons + windows, and holds the
                           window-management <script>.
    photography.astro      A second desktop (placeholder for now).
  components/
    Window.astro           The window *chrome*: title bar, close/maximize buttons, drag,
                           maximize logic. Props: title, id, open, persistent, maximizable,
                           width, height.
    DesktopIcon.astro      A desktop icon (box + label). Either opens a window (opens="id")
                           or links to another desktop (href="/x"). Positioned per-icon.
    Taskbar.astro          Fixed bottom bar (Home / Info / Shutdown). Persists across nav.
    About.astro            Contents of the persistent "Welcome" window.
    Beliefs.astro          Contents of "Large beliefs" — collapsible sections, hand-written.
    Contact.astro          Contact form: slide-to-send, AJAX→Netlify, green success state.
    Projects.astro         Projects list (data array + Astro <Image>).
    Info.astro             "How to use the site" window.
  styles/global.css        Theme tokens (:root), reset, the html grid background, the
                           view-transition slide animations, and mobile-only overrides.
  assets/projects/         Project images (imported + optimized via astro:assets).
public/                    Static files served as-is. The Welcome avatar reads /me.jpg here.
```

## How the window system works

A window is just `<Window id="about" title="About me"> …content… </Window>` placed on a page.
Anything with `data-opens="about"` (a desktop icon, a taskbar button, the mail chip in the
About card…) opens it. The page's `<script>` wires this up generically:

- **`[data-opens]` → open/close.** Clicking an opener toggles its window. Re-clicking an open
  window's opener closes it.
- **Single-window rule.** Only one *non-default* window is open at a time; opening another
  closes the current one (it animates collapsing toward the icon that opened it).
- **Persistent windows.** A window with the `persistent` prop (the Welcome window) is exempt
  from that rule — it stays open until you close it with its ✕.
- **Esc** closes the open non-default window.
- **Window chrome** (`Window.astro`) handles dragging by the title bar, the maximize toggle
  (for `maximizable` windows — near-fullscreen, clears the taskbar), and the close button
  (which dispatches a bubbling `windowclose` event the page listens for).
- When a window finishes closing, the page dispatches a `windowclosed` event on it — content
  components use this to reset their state (e.g. Contact resets its form).

To **add a window**: drop a `<Window id="x">` on a page and give something `data-opens="x"`.
To **add a desktop icon**: `<DesktopIcon label="X" opens="x" center={[dx, dy]} />` (or edge
props like `top`/`right`/`bottom`/`left`, or `href="/other-desktop"` to navigate instead).
To **add a desktop**: a new `src/pages/foo.astro` using `<Layout>`, linked from a
`<DesktopIcon href="/foo">`.

## The one pattern you must internalise: re-init on navigation

Because `<ClientRouter />` swaps the page DOM on navigation (instead of a full reload),
**module `<script>`s do not re-run for the new DOM**. So every interactive component binds its
setup to `astro:page-load` (fires on first load *and* after each navigation) and is
**idempotent** — it marks already-wired elements (e.g. `data-wired`) so persisted elements
(the taskbar) aren't bound twice while freshly-rendered ones are. If you add interactivity and
it "works until you navigate away and back", this is why.

## Styling & aesthetic

- **Component-scoped `<style>`** holds each component's own styling. `global.css` holds the
  shared stuff: theme tokens, the reset, the desktop background, page-transition CSS, and
  mobile overrides. There's deliberately no per-page stylesheet — scoped styles cover it.
- **Theme tokens** live in `:root` (`--beige`, `--window-bg`, `--window-border`,
  `--window-bar` olive, `--ink`, `--ink-muted`, `--close-red`, `--taskbar-h`). Reach for these
  before hard-coding colours.
- **The look:** warm beige graph-paper desktop, olive-green chrome, monospace for UI/titles
  and labels, system sans for reading text. Muted, tactile, lightly "engineered". The user has
  strong, specific taste and usually wants to tune visuals together — propose, show, iterate.

## Mobile

A `@media (max-width: 640px)` layer adapts things: scattered icons collapse into a simple grid,
non-default windows open near-fullscreen, the Welcome card shrinks. Note icons position
themselves with *inline* styles, so the mobile grid overrides them with `!important`. Mobile is
only roughly tuned — expect to iterate on a real device.

## Sharp edges we've already hit

- **`classList.remove(token)` writes the class attribute even when the token is absent**, which
  fires `MutationObserver`s — a reset that mutated the watched element from inside its own
  observer caused an infinite microtask loop (a silent, no-error freeze). Prefer events over
  observers; if you must observe, never let the callback mutate what it watches.
- **`[hidden]` is overridden by `display: flex/grid`.** Re-assert `.thing[hidden]{display:none}`
  when hiding a flex/grid container via the `hidden` attribute.
- **Inline styles beat media queries** — hence the `!important` overrides for mobile icons.
- **Chrome autofill** repaints inputs blue; we cover it with a `box-shadow` inset trick.
- **Netlify forms only work once deployed.** Locally the AJAX submit can't reach Netlify, so
  the success/error UI is what you test on localhost; real delivery is post-deploy.
- **`scrollbar-gutter: stable both-edges`** on window bodies keeps centered content from
  shifting when a scrollbar appears/disappears.

## Working style

The user builds this incrementally and visually — small, specific changes, lots of "try this,
now tweak that". They care about feel and detail, dislike over-engineering, and like
understanding the trade-offs. Good collaboration here looks like: make the change, describe
what you did and any honest caveats, offer a sensible option or two, and leave room for their
taste to drive. Be creative — this doc is a map, not a fence.

## Astro docs

Full docs: https://docs.astro.build — handy ones: routing, components, framework components,
content collections, styling, view transitions.

When starting the dev server, use background mode:

```
astro dev --background
```

Manage the background server with `astro dev stop`, `astro dev status`, and `astro dev logs`.

## Documentation

Full documentation: https://docs.astro.build
