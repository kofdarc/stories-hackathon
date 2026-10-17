# Stories Coffee Strategy Room

A standalone browser app calibrated to the repository's transaction database. It runs entirely in the browser with a bundled chart library; no API keys or backend are required. Optional Google Fonts fall back to system fonts when offline.

## Run locally

From the repository root:

```sh
python3 -m http.server 8080 --directory simulator/dist --bind 127.0.0.1
```

Open `http://127.0.0.1:8080`. You can also open `simulator/dist/index.html` directly. All scripts and aggregate data are local assets.

## Features

- Eleven assumptions for pricing, traffic, food attachment, Garden product costs, program spending, setup, labor and uncertainty.
- Five illustrative presets, local scenario saving and loading, a downloadable HTML stakeholder brief, and print layout.
- Contribution bridge, 2,000 paired stress trials, cumulative break-even curve, sensitivity grid, and branch contribution comparisons.
- Reproducible random draws and source SHA-256 provenance.

## Model and data

`dist/assets/model.js` is the calculation engine. `dist/assets/calibration.js` contains daily branch aggregates derived from `database/stories.sqlite`, without customer or transaction identifiers. `dist/assets/app.js` handles controls, plots and browser-local state.

The starting data covers January–June 2026: 33,887 orders, $305,925.14 revenue, and $179,430.49 recorded gross profit. This is a historical scenario replay, not a future forecast. The app explains measured inputs, assumptions, resampling and limitations under “Model & evidence.”

Saved scenarios stay in the current browser's local storage. They are not shared between devices or sent to a server. “Export brief” downloads a self-contained report of the selected assumptions and results. Up to 20 named scenarios are kept; saving the same name updates that scenario.

Run the model checks with Node.js:

```sh
node simulator/tests/model.cjs
```

## Hosting

Serve the contents of `dist/` with any static host. The Sites deployment manifest is `.openai/hosting.json`. No install or build command is needed. `d3.min.js` is D3 7.9.0, distributed under its upstream ISC license; its copyright notice is retained in the bundled file.
