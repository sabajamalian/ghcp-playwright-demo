---
applyTo: "**/*.html,**/*.css,**/*.js"
description: "Use when creating or modifying UI files (HTML, CSS, JavaScript). Enforces vanilla web stack with Shoelace web components — no frameworks."
---
# UI Development Guidelines

## Vanilla Stack Only

- Use **plain HTML, CSS, and JavaScript** for all UI work.
- **Do not** use any JavaScript frameworks or libraries (no React, Vue, Angular, Svelte, etc.).
- **Do not** use CSS frameworks like Bootstrap or Tailwind.
- **Do not** use build tools, bundlers, or transpilers unless explicitly requested.

## Use Shoelace Web Components

Use [Shoelace](https://shoelace.style/) (`@shoelace-style/shoelace`) for UI components such as buttons, inputs, dialogs, menus, tabs, and other interactive elements.

### CDN Setup

Include Shoelace via CDN in HTML files that need UI components:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/themes/light.css" />
<script type="module" src="https://cdn.jsdelivr.net/npm/@shoelace-style/shoelace@2.20.1/cdn/shoelace-autoloader.js"></script>
```

### Component Usage

- Prefer Shoelace components (`<sl-button>`, `<sl-input>`, `<sl-dialog>`, etc.) over native HTML elements when a richer UI is needed.
- Always use full closing tags — never self-close: `<sl-input></sl-input>`, not `<sl-input />`.
- Listen to Shoelace custom events (prefixed `sl-`) instead of native DOM events on Shoelace components (e.g., `sl-change` instead of `change`).
- Set complex properties (arrays, objects) via JavaScript, not attributes.
- Refer to the Shoelace docs for available components: https://shoelace.style/components/alert

### Prevent Flash of Undefined Custom Elements

Add this CSS to avoid unstyled content before components register:

```css
:not(:defined) {
  visibility: hidden;
}
```
