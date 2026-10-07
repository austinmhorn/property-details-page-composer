# Property Details Page Composer

Builds one searchable Interact Page Composer page containing the Birchstone property portfolio.

## Architecture

```text
Notion Properties database
        ↓
Go fetch/normalization layer
        ↓
data/notion_data_unsorted.csv
        ↓
Python Property models + Jinja renderer
        ↓
one semantic HTML portfolio page
        ↓
Interact Page Composer API
```

All property facts are present in the initial HTML so Interact search can index them. A selector at the top controls which property is visible to the user.

## Setup

Copy `.env.example` to `secrets/.env` and populate the values.

```bash
mkdir -p secrets
cp .env.example secrets/.env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The same `secrets/.env` stores both Interact and Notion configuration.

## Runtime workflow

`start.sh` is the production/portal entrypoint. It calls `oversee_process.py`, which is the true workflow orchestrator.

```text
start.sh
   ↓
oversee_process.py
   ├── go run .
   │      ↓
   │   fetch Notion property data
   │      ↓
   │   data/notion_data_unsorted.csv
   │
   └── scripts/publish_portfolio.py
          ↓
       render portfolio HTML
          ↓
       publish to Interact
```

`start.sh` also writes `last_run.json` with status, timestamps, duration, and `RUN_SOURCE`, matching the runtime pattern used by the other Birchstone data engines.

On the Birchstone Portal VM it prefers the shared Python environment:

```text
/home/birchstonereporting/shared-venvs/data-engines/bin/python
```

For local development, it falls back to the available `python3`.

Running:

```bash
./start.sh
```

now performs the full production workflow and publishes the Property Details page to the Interact page configured by `INTERACT_PAGE_ID`.

## Development workflow

Preview one property while developing the information architecture:

```bash
python3 scripts/preview_property.py "Birchstone Waterleigh"
```

Render the complete portfolio without fetching Notion again:

```bash
python3 scripts/render_portfolio.py
```

Generated HTML is written under `output/` and is intentionally ignored by Git.

Local preview files automatically load the shared development assets from:

- `assets/property-details.css`
- `assets/property-details.js`

`preview_property.py` opens the generated file automatically. To open the full 46-property portfolio after rendering:

```bash
python3 scripts/render_portfolio.py --open
```

The CSS and JavaScript in `assets/` are intentionally written so we can later move them nearly verbatim into Interact Masterpage CSS/JS. They are **not** included in the HTML fragment published through Page Composer.

## Publishing

The production entrypoint publishes automatically:

```bash
./start.sh
```

For a direct/manual publish without running the Go fetch first:

```bash
python3 scripts/publish_portfolio.py --page-id 1234
```

For preview-only work, use `scripts/render_portfolio.py` or `scripts/preview_property.py` instead of `start.sh`.

The destination should be a pure HTML Page Composer page, not a Block Editor page. The publisher refuses to overwrite a Block Editor page.

## Property selector

The generated page contains every property record in the HTML and hides all but the selected record. This keeps the full dataset available to Interact search while giving onsite users one clean property view at a time.

Put this in Interact Masterpage JavaScript:

```javascript
(() => {
  const app = document.querySelector("[data-property-details-app]");
  if (!app) return;

  const selector = app.querySelector("[data-property-selector]");
  const records = [...app.querySelectorAll("[data-property-record]")];
  if (!selector || !records.length) return;

  const showProperty = (key) => {
    records.forEach((record) => {
      record.dataset.propertyActive =
        record.dataset.propertyRecord === key ? "true" : "false";
    });
    localStorage.setItem("birchstone-property-details-selection", key);
  };

  const remembered = localStorage.getItem("birchstone-property-details-selection");
  if (
    remembered &&
    records.some((record) => record.dataset.propertyRecord === remembered)
  ) {
    selector.value = remembered;
  }

  showProperty(selector.value);
  selector.addEventListener("change", () => showProperty(selector.value));
})();
```

Add this baseline rule to Interact Masterpage CSS so only the active property is visible while every property's text remains in the source HTML for indexing:

```css
.property-record[data-property-active="false"] {
  display: none;
}
```

Masterpage CSS can then target the structural classes already emitted by the template:

- `.property-details-app`
- `.property-details-toolbar`
- `.property-details-selector`
- `.property-record`
- `.property-quick-links`
- `.property-section`
- `.property-detail-grid`

The Page Composer HTML fragment intentionally contains no embedded styling or application JavaScript. During local development, the preview wrapper links to the files in `assets/`. When the design is approved, those same assets become the starting point for the Interact Masterpage CSS/JS. Python continues to own only the data and semantic markup.

## Data behavior

- Blank values are omitted.
- URLs, emails, and phone-like values render as usable links.
- Known fields are grouped into onsite-friendly sections.
- Any populated CSV columns not explicitly mapped still appear under **Additional Details**, so new Notion fields do not silently disappear.
- Property records are sorted alphabetically.
- The selector value uses Property Number when available, falling back to a stable name slug.

## Runtime files

These are generated locally and are not committed:

- `data/notion_data_unsorted.csv`
- `json/api_response.json`
- `output/*.html`
- `secrets/.env`

The Go fetcher creates runtime directories automatically and reads Notion credentials from the same `secrets/.env` file used by Python.

## Development branch

The initial application foundation is developed on `feature/property-page-foundation`.
