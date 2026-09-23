# Ledger — Frontend

React + Vite SPA for the finance platform. Talks to the Flask API in `../backend_api`.

## What's actually been verified vs. not

**Verified in this sandbox (no internet access here, so real limits on what I could check):**
- Every `.jsx`/`.js` file passes real TypeScript syntax validation (`tsc --noEmit`), confirmed to have teeth by deliberately breaking a file and seeing it get caught, then restoring and reconfirming clean.
- `package.json` is valid JSON.
- The Flask API this frontend calls is fully tested end-to-end (see `../backend_api/README.md` or the main README).

**NOT verified — this sandbox has no npm registry access, so I could not run `npm install` or `npm run build`:**
- Whether the actual component tree renders correctly in a real browser.
- Whether `liquid-glass-react`'s actual exported API matches exactly what I assumed from its README (props: `cornerRadius`, `blurAmount`, `saturation`, `aberrationIntensity`, `elasticity`).
- CSS layout/visual correctness — I wrote it carefully but never saw it rendered.

**First thing to do on your machine:**
```bash
cd frontend
npm install
npm run dev
```
If `npm run dev` throws an error, paste the exact message back to me — I can fix it immediately, same as we did with the earlier pip/pandas issues. Don't assume a build error means the whole approach is wrong; it more likely means one specific import or prop name needs a small correction.

## Running it

1. Start the backend first (separate terminal): see `../backend_api/README.md`.
2. `npm install`
3. `npm run dev` — opens on `http://localhost:5173`
4. The frontend calls the API at `http://127.0.0.1:5000` (hardcoded in `src/api/client.js` — change it there if your backend runs elsewhere).

## Design decisions worth knowing

- **Glass effect** uses `liquid-glass-react` (npm), the React-ready equivalent of the WebGL/SVG-displacement libraries you linked — chosen over hand-wiring the raw imperative APIs because a pre-built component is far less likely to contain a mistake I can't catch without a real build.
- **`GlassPanel.jsx`** wraps it with an error boundary that falls back to a plain `backdrop-filter` blur card if the glass effect throws (e.g. an unsupported browser) — the page degrades, it doesn't break.
- **Glass is only used on nav and summary cards** — never wrapped around the transaction table or any chart, per your call on where the effect should appear.
- **No pill-shaped anything** — every `cornerRadius` in the codebase is a rounded rectangle (16-22px), never a full/999px pill, despite one of your linked libraries' primary showcase being pill buttons.
- **Privacy/Terms pages** describe what this app *actually* does (in-memory session, no cloud storage, one clearly-scoped exception for the optional Anthropic API call) — not generic boilerplate. Still flagged as unreviewed by a lawyer.
