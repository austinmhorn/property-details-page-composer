# Property Details Page Composer

Builds one searchable Interact Page Composer page containing the Birchstone property portfolio.

## Architecture

The Property Details Page Composer is a presentation/publishing layer. It does not fetch the Notion Properties database itself.

```text
Notion Properties database
        ↓
Property Data Engine
        ├── notion_data.csv
        └── property_fields.json
                ↓
Property Details Page Composer
        ↓
Python Property models + Jinja renderer
        ↓
one semantic HTML portfolio page
        ↓
Interact Page Composer API
```

The Property Data Engine is the canonical owner of property extraction and the property field registry. The composer consumes the generated CSV plus the small presentation metadata artifact.

All property facts intended for Interact are present in the initial HTML so Interact search can index them. A selector at the top controls which property is visible to the user.

## Setup

Create `secrets/.env` and populate the Interact values used by the publisher.

```bash
mkdir -p secrets
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Expected Interact settings include:

```text
INTERACT_API_DOMAIN
INTERACT_TENANT_GUID
INTERACT_API_KEY
INTERACT_API_SECRET
INTERACT_PERSON_ID
INTERACT_PAGE_ID
```

The Property Data Engine location can optionally be overridden with:

```text
PROPERTY_DATA_ENGINE_DIR=/path/to/Property-Data-Engine
```

When that value is not set, the composer checks the standard Birchstone VM location and the local macOS development location.

## Runtime workflow

`start.sh` is the production/portal entrypoint. It calls `scripts/oversee_process.py`, which is the workflow orchestrator.

```text
start.sh
   ↓
scripts/oversee_process.py
   ├── run Property Data Engine
   │      ↓
   │   notion_data.csv
   │   property_fields.json
   │      ↓
   │   copy both artifacts into data/
   │
   └── scripts/publish_portfolio.py
          ↓
       render portfolio HTML
          ↓
       publish to Interact
```

`start.sh` also writes `last_run.json` with status, timestamps, duration, and `RUN_SOURCE`.

On the Birchstone Portal VM it prefers the shared Python environment:

```text
/home/birchstonereporting/shared-venvs/data-engines/bin/python
```

For local development, it falls back to the available `python3`.

Running:

```bash
./start.sh
```

refreshes Property Data Engine, copies the current artifacts, renders the portfolio, and publishes the Property Details page to the Interact page configured by `INTERACT_PAGE_ID`.

## Property field registry

New property fields are registered in Property Data Engine, not in this repository.

Property Data Engine generates `property_fields.json` with downstream presentation metadata such as:

```json
{
  "key": "program_type",
  "csv_header": "Program Type",
  "notion_type": "select",
  "display_in_interact": true,
  "interact_category": "Systems & Programs",
  "interact_label": "Program Type"
}
```

The composer reads that metadata dynamically:

- `display_in_interact: true` places the CSV field in the specified Interact section.
- `display_in_interact: false` keeps the PDE/Google Sheet field out of Interact.
- `interact_label` controls the displayed label.
- `interact_order` can control ordering among registry-managed fields.
- No template or Python change is required for an ordinary new registry field.

The existing curated core-field section mappings remain in the composer for the original property dataset.

## Development workflow

Refresh PDE artifacts without publishing to Interact:

```bash
python3 scripts/refresh_property_data.py
```

Preview one property:

```bash
python3 scripts/preview_property.py "Birchstone Waterleigh"
```

Render the complete portfolio from the copied PDE artifacts:

```bash
python3 scripts/render_portfolio.py
```

To open the full portfolio after rendering:

```bash
python3 scripts/render_portfolio.py --open
```

Generated HTML is written under `output/` and is intentionally ignored by Git.

Local preview files load the shared development assets from:

- `assets/property-details.css`
- `assets/property-details.js`

The CSS and JavaScript in `assets/` are not embedded in the HTML fragment published through Page Composer.

## Portal page workflows

The Birchstone Data Console exposes four operator actions for Property Details:

- **Render** runs `scripts/render_workflow.py`, which refreshes Property Data Engine artifacts and creates both a browser preview and a publishable HTML fragment without touching Interact.
- **View Render** serves the latest `output/portfolio_details.html` preview through the Portal.
- **Publish** runs `scripts/publish_portfolio.py --existing`, which publishes the saved `output/portfolio_details.fragment.html` without refreshing or rendering again.
- **Render & Publish** runs the production `start.sh` workflow end-to-end.

The saved publish fragment exists so a reviewed render can be published later without silently generating different HTML at publish time.

## Publishing

The production entrypoint publishes automatically:

```bash
./start.sh
```

For a direct/manual publish using the already-copied PDE artifacts:

```bash
python3 scripts/publish_portfolio.py --page-id 1234
```

The destination must be a pure HTML Page Composer page. The publisher refuses to overwrite a Block Editor page.

## Property selector

The generated page contains every included property record in the HTML and hides all but the selected record. This keeps the full dataset available to Interact search while giving onsite users one clean property view at a time.

The Page Composer HTML fragment intentionally contains no embedded styling or application JavaScript. Interact Masterpage CSS/JS owns the presentation and selector behavior.

## Data behavior

- Property Data Engine is the canonical source of property data.
- Blank values are omitted.
- URLs, emails, and phone-like values render as usable links.
- Known core fields are grouped into onsite-friendly sections.
- Registry-managed fields obey Property Data Engine's Interact metadata.
- Registry fields marked not to display in Interact are suppressed.
- Unmanaged populated CSV columns still fall back to **Additional Details**.
- Property records beginning with `x_` or `z_`, plus Corporate Office, are excluded.
- Property records are sorted alphabetically.
- The selector uses Property Number when available, falling back to a stable name slug.

## Runtime files

These are generated locally and are not committed:

- `data/notion_data.csv`
- `data/property_fields.json`
- `output/*.html`
- `last_run.json`
- `secrets/.env`

## Development branch

The PDE-consumer and registry-driven Interact work is developed on `feature/property-field-manager`.
