# Opt-in related onsite team in Property Details

The existing Property Manager field remains authoritative. A separately
generated PDE sidecar `property_onsite_team.json` adds other **active, onsite**
associates to the **Property Team** section. The presentation groups all
people with the same title into one row and alphabetizes their preferred names.

The PDE artifact must have `version: 1`, `properties` keyed by verified
Notion DB.Properties page ID, and entries with `property_name` and
`associates: [{page_id, title, name}]`. The Composer joins by the
PDE-verified property name, as it already does for related fees. It excludes
the Property Manager role again as a safety guard.

The feature is **disabled unless `COMPOSER_ONSITE_TEAM_ENABLED=1`**.
When enabled, the Composer requires the artifact in the configured
`PROPERTY_DATA_ENGINE_DIR`, copies it during Render, validates schema and
duplicate property names, and fails the render if the artifact is missing.
When disabled, it never reads the roster artifact.

## Safe rollout

1. Merge and update the PDE and Composer checkouts on the VM with rollback
   SHAs and worktrees preserved.
2. Run PDE's `onsite_roster.py` independently and review record counts,
   warnings, Property Manager exclusion, and title/name values.
3. Verify the normal Composer regression suite still passes with the
   feature disabled.
4. In a controlled environment with the artifact present, set
   `COMPOSER_ONSITE_TEAM_ENABLED=1` and render a preview. Confirm grouped
   job titles and alphabetic associates, especially where no onsite
   associates exist, without publishing.
5. Only after acceptance, enable the PDE's separate
   `PDE_ONSITE_ROSTER_ENABLED=1` schedule step and Composer's consumer gate.
   Ensure the PDE extraction finishes before scheduled render/publish.
6. Publish to Interact page 2186 only after explicitly reviewing the
   rendered preview.

The existing property CSV, registry field display orders, Google Sheets,
fees manifest and automation semantics remain unchanged. Secrets stay in
their configured environment / config files; do not print credentials.
