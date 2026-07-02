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
  layouts/Layout.astro     The OS "shell": <html>/<head> (incl. the render-blocking boot
                           head-script), ClientRouter, global.css, the Taskbar, the shared
                           Info/Shutdown windows, the shutdown + boot overlays, the
                           nav-direction + boot scripts, AND the generic window-management
                           <script> (so the window system works on every desktop).
  pages/
    index.astro            The home desktop. Lays out icons + its windows (Welcome, About,
                           Beliefs, Contact, Projects, Favourites…).
    photography.astro      A second desktop (placeholder for now).
  components/
    Window.astro           The window *chrome*: title bar, close/maximize, drag, maximize.
                           Props: title, id, open, persistent, maximizable, fullCenter,
                           overlay, width, height.
    DesktopIcon.astro      A desktop icon (box + label, optional `icon` image). Opens a
                           window (opens="id") or links to a desktop (href="/x").
    Taskbar.astro          Fixed bottom bar (Home / Info / Shutdown). Persists across nav.
    Welcome.astro          Contents of the persistent "Welcome" window.
    Beliefs.astro          "Big Ideas" — collapsible sections, hand-written.
    Contact.astro          Contact form: slide-to-send, AJAX→Netlify, green success state.
    Info.astro             "How to use the site" window.
    Shutdown.astro         Shutdown window: confirm → slide-to-confirm; firing it shows the
                           shutdown overlay and sets the boot cookie.
    Projects.astro         Nested-desktop windows (data + per-item detail bodies), built on
    Favourites.astro       IconDesktop/IconDetail. See "Nested-desktop windows".
    IconDesktop.astro      Reusable nested desktop: icon grid + icon-morph + a slot per item.
    IconDetail.astro       Shared detail-panel shell (back/icon/title/links) + a body slot.
    favourites/            Per-screen Favourites bodies (FavTweets/FavBooks/FavEssays), each
                           its own component + scoped styles.
  styles/global.css        Theme tokens (:root, incl. --font-sans), reset, the html grid
                           background, view-transition slides, the shutdown/boot/Aero overlay
                           styles, and mobile overrides.
  assets/projects/, assets/favourites/   Images (imported + optimized via astro:assets).
public/                    Static files served as-is (favicon, /me.jpg, tick.svg…).
```

## How the window system works

A window is just `<Window id="about" title="About me"> …content… </Window>` placed on a page
(or, for shell windows like Info/Shutdown, in the Layout). Anything with `data-opens="about"`
(a desktop icon, a taskbar button, the mail chip in the About card…) opens it. The
**window-management `<script>` in `Layout.astro`** wires this up generically, page-wide:

- **`[data-opens]` → open/close.** Clicking an opener toggles its window. Re-clicking an open
  window's opener closes it.
- **Single-window rule.** Only one *non-default* window is open at a time; opening another
  closes the current one (it animates collapsing toward the icon that opened it).
- **Persistent windows.** A window with the `persistent` prop (the Welcome window) is exempt
  from that rule — it stays open until you close it with its ✕.
- **Centering.** New windows open centered in the space *above* the taskbar; a window with the
  `fullCenter` prop centers in the full viewport instead (Welcome, Info, Shutdown).
- **Overlay windows.** A window with the `overlay` prop (Shutdown) opens *on top of* the current
  window instead of replacing it — the manager tracks a second `overlay` slot alongside `open`.
  It still closes when another (non-overlay) window opens on top, and Esc/Home dismiss it first.
- **Esc** closes the open non-default window.
- **Window chrome** (`Window.astro`) handles dragging by the title bar, the maximize toggle
  (for `maximizable` windows — near-fullscreen, clears the taskbar), and the close button
  (which dispatches a bubbling `windowclose` event the page listens for).
- When a window finishes closing, the page dispatches a `windowclosed` event on it — content
  components use this to reset their state (e.g. Contact resets its form).

To **add a window**: drop a `<Window id="x">` on a page (or in the Layout, if it should open
from the taskbar on every desktop) and give something `data-opens="x"`.
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

## Nested-desktop windows (Projects & Favourites)

Some windows are themselves little desktops: a grid of launcher icons that each **morph** open
into a detail panel. The reusable machinery is two components:

- **`IconDesktop`** — the stage + icon grid + the open/close **icon-morph** (a FLIP where a
  crisp clone of the icon flies between its grid slot and the detail header while the panel
  fades). Takes an `items` array (id, title, optional icon, website/github) for the grid, plus
  a default `<slot>` for the panels. Resets to the grid on `windowclosed`.
- **`IconDetail`** — one panel's shared *shell* (back button, header icon, title, link
  buttons) + a default `<slot>` for the **body**. Optional `dark` prop = black panel + white
  heading (the Tweets screen).

Each consumer (`Projects`, `Favourites`) wires `<IconDesktop items={…}>` with one
`<IconDetail>` per item and **owns each body's markup + scoped styles**. Projects' bodies are
uniform so it maps them; Favourites' screens differ wildly, so each is its own component
(`favourites/Fav*.astro`) wired explicitly. Gotcha: an item's `icon`/`title` is set **twice** —
in the `items` array (drives the grid) and on its `<IconDetail>` (drives the header) — keep them
in sync.

## The shutdown → reload "boot" experience

Pulling the Shutdown window's slider shows a full-screen black overlay (spinner, "Shutting
down…") and sets a `shutdown=1` cookie (5h). On the **next page load**, a **render-blocking
`<script is:inline>` at the top of `<head>`** reads that cookie and sets `data-booting` on
`<html>` *before first paint* — so the black "boot" screen paints on frame one, with no flash of
the real site. The boot script then cycles a list of messages, shows an Aero (Win Vista/7)
"Restart complete!" dialog, and on OK clears the cookie + drops the overlay to reveal the site.

That head script **must** stay `is:inline` and near the top of `<head>` — a bundled/deferred
Astro `<script>` runs after paint and reintroduces the flash. The overlays + Aero styles live in
`global.css`.

## Styling & aesthetic

- **Component-scoped `<style>`** holds each component's own styling. `global.css` holds the
  shared stuff: theme tokens, the reset, the desktop background, page-transition CSS, and
  mobile overrides. There's deliberately no per-page stylesheet — scoped styles cover it.
- **Theme tokens** live in `:root` (`--beige`, `--window-bg`, `--window-border`,
  `--window-bar` olive, `--ink`, `--ink-muted`, `--close-red`, `--taskbar-h`, `--font-sans`).
  Reach for these before hard-coding colours/fonts.
- **The look:** warm beige graph-paper desktop, olive-green chrome, monospace for UI/titles
  and labels, **Hanken Grotesk** (the `--font-sans` token, self-hosted via Fontsource and
  imported in the Layout) for reading text. Muted, tactile, lightly "engineered". The user has
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
  shifting when a scrollbar appears/disappears. (The nested-desktop windows override this to
  `auto` — they scroll internally, so the reserved gutter just read as stray side padding.)
- **Astro hoists named slots out of `.map()`** — `<X slot={`a-${i}`}>` inside a loop loses the
  loop variable (`p is not defined` at build). Pass per-item content via a child *component*'s
  default slot instead (why Favourites uses `IconDetail`, not per-item named slots).
- **Lazy images in `display:none` panels flicker on first reveal.** A detail panel's header
  icon is hidden until opened, so it isn't loaded when the first morph clones it → a one-time
  flicker. Fix: `loading="eager"` on icons that animate in.

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