# metabase-dashboard-toolkit

A small, dependency-free Python toolkit for building Metabase dashboards
through its REST API instead of clicking through the UI (or hand-writing
`curl` calls) every time. Standard library only — no `pip install` needed.

## Why this exists

Building a "real" dashboard by hand in Metabase's UI — cards, dashboard
filters wired to template tags, grid layout — is a lot of repetitive
clicking, and doesn't version well. This toolkit turns that into a Python
script: define the SQL once, describe the layout, run it.

## Files

- **`client.py`** — `MetabaseClient`: every read/write operation used to
  build a dashboard end to end (`run_query`, `create_card`, `update_card`,
  `create_dashboard`, `set_dashboard_cards`, `set_dashboard_parameters`,
  `create_collection`, `move_card`, `move_dashboard`, `find_table_id`,
  `find_field_id`, `archive_card`, `archive_dashboard`, ...). Reads
  credentials from `.env` in this folder automatically.
- **`layout.py`** — `DashboardLayout`: builds the grid layout (headings +
  rows of cards) without hand-computing `row`/`col` on Metabase's 24-column
  grid. `.row()` accepts `parameter_mappings` per card when the dashboard
  has filters.
- **`filters.py`** — dashboard-level filters ("parameters"): `date_tag` /
  `dimension_tag` to declare template tags on a card, `date_parameter` /
  `field_filter_parameter` to declare the dashboard's filter widgets,
  `variable_mappings` / `dimension_mappings` to wire the two together. Full
  worked example in the module docstring.
- **`examples/self_test.py`** — end-to-end sanity check: connects, resolves
  your default collection, runs a dry-run query, creates a real card +
  dashboard, then archives them immediately. Run it after any change to
  `client.py`/`layout.py` to confirm the read/write/layout pipeline still
  works.

## Setup

```
cp .env.example .env
# fill in METABASE_URL and METABASE_API_KEY
```

## Quick usage

```python
from client import MetabaseClient
from layout import DashboardLayout

mb = MetabaseClient()

kpi = mb.create_card(
    name="[Example] Orders Today",
    sql="SELECT COUNT(*) FROM orders WHERE status = 'completed'",
    display="scalar",
    description="Clear description: what it measures, from where, any caveat.",
)

dash = mb.create_dashboard(name="Example Dashboard")

layout = DashboardLayout()
layout.heading("## Example Dashboard\nA short description of the dashboard.")
layout.row([{"card_id": kpi["id"]}], height=3)

mb.set_dashboard_cards(dash["id"], layout.dashcards)
print(mb.dashboard_url(dash["id"], "example-dashboard"))
```

## Patterns worth knowing

- Dashboards with more than one card benefit from a nested-folder
  convention: `<Dashboard Name>` (holds the dashboard itself) →
  `cards for <dashboard name, lowercase>` (holds every underlying card) — so
  the top-level folder always shows exactly two items, no matter how many
  cards the dashboard has underneath.
- If a dashboard has tabs (`GET .../dashboard/:id` returns a non-empty
  `tabs` list), `set_dashboard_cards` **requires** you to pass `tabs` too —
  every dashcard then needs a matching `dashboard_tab_id`. Omitting it 500s
  with a dashboard-tab foreign-key error on multi-tab dashboards.
- A good general layout for a "real" (non-throwaway) dashboard: KPI row →
  trend section → detail/breakdown section → actionable list(s) → a closing
  "Data Quality / Config Audit" card. `layout.py`'s `heading()` +
  `row()` pair map directly onto that shape.
