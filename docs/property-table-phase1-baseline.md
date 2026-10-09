# Phase 1 — Protected baseline (stable-v2)

This branch adds regression coverage without changing the published HTML, Interact page 2186, or PDE/Field Manager implementation.

## Immutable release references

- Birchstone-Reporting-Portal: `stable-v2` at `36dbc099a2ed1fc9ad6cac436df524804bea22e7`
- Property-Data-Engine: `stable-v2` at `ad04f560769b4e8c3c3bc31bf4f3473a8e059d59`
- property-details-page-composer: `stable-v2` at `64abf518411e805c09ddddace52d4c892f2b1438`
- birchstone-interact-customization: `stable-v2` at `e0d7b81e0bfd209b9b81f72dfc33d74f5309913b`

## Existing data and approval contracts (do not change in Table feature)

1. Field Manager routes in Portal's `routes/property_fields.py` invoke PDE's `scripts/manage_field_registry.py`.
2. Pending changes, locking, Git fetch/merge/pull and tracked state are managed in Portal's `property_field_changes.py`. Never bypass these with a table configuration write.
3. PDE maintains `config/property_fields.json` and emits `notion_data.csv` plus version-1 `property_fields.json` metadata.
4. Composer copies both artifacts, consumes approved metadata, and renders static semantic HTML.
5. Portal Render -> View Render -> Publish uses a saved fragment; publishing that fragment must not silently re-render.
6. Interact page 2186 receives only the HTML fragment. Masterpage CSS/JS live in birchstone-interact-customization. Existing `data-property-*` selectors and `#property=` links remain supported.
7. No `main` merges and no Interact publish until release approval.

## Regression gate implemented in Phase 1

- Composer: `python -m unittest discover -s tests -v`
- Interact customization: `node tests/details-contract.test.cjs` and `node --check property_details/property-details.js`
- Both suites also run in GitHub Actions on feature branch pushes and pull requests.

These are **unit/source contract checks**, not a live end-to-end acceptance test. They deliberately do not create live field-change proposals, approve/merge registry changes, or publish to Interact.

## Phase 2 implementation contract

- UI labels: **Details** and **Table** (not Grid).
- Initial default: Details. Keep all existing `property-record` elements and selector behavior.
- Render the table from the same `Property` models and approved field metadata.
- Client-side switching, searching and sorting; no new Notion or Portal API in the published page.
- Keep `#property=` links valid. Add `view` only compatibly and retain table UI state while switching.
- Use explicit publishable-field eligibility, not an arbitrary full CSV dump.
- New customization JavaScript must feature-detect new markup so current HTML remains functional.
- Add render snapshot/behavior and browser tests before declaring Phase 2 ready.

## Required manual integration checks before production

- Propose -> review -> approve -> merge -> VM sync with existing Field Manager credentials and role guards
- Approved label/category/visibility changes propagate to fresh PDE artifacts and both views
- Conflicting/failed review leaves production registry unchanged
- Published saved fragment matches reviewed preview
- Actual Interact CSS/JS loads and layout works on page 2186

Do not infer these integrations have passed just because the CI source-contract checks pass.
