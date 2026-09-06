"""Minimal Metabase API client.

Pure standard library — no `pip install` needed. Reads credentials from
`.env` in this same folder (METABASE_URL, METABASE_API_KEY).
"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_DATABASE_ID = 0             # your Metabase database id
DEFAULT_COLLECTION_ID = 0           # your default collection id


def _load_env():
    env_path = Path(__file__).parent / ".env"
    env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


_ENV = _load_env()
METABASE_URL = os.environ.get("METABASE_URL") or _ENV.get("METABASE_URL")
METABASE_API_KEY = os.environ.get("METABASE_API_KEY") or _ENV.get("METABASE_API_KEY")


class MetabaseError(RuntimeError):
    pass


class MetabaseClient:
    def __init__(self, base_url=None, api_key=None):
        self.base_url = (base_url or METABASE_URL or "").rstrip("/")
        self.api_key = api_key or METABASE_API_KEY
        if not self.base_url or not self.api_key:
            raise MetabaseError(
                "Missing METABASE_URL / METABASE_API_KEY — put them in metabase/.env"
            )

    def _request(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("x-api-key", self.api_key)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            raise MetabaseError(f"{method} {path} -> HTTP {e.code}: {detail}") from None

    # ---------- read ----------

    def list_databases(self):
        return self._request("GET", "/api/database")["data"]

    def list_collections(self):
        return self._request("GET", "/api/collection")

    def find_collection_id(self, name):
        for c in self.list_collections():
            if c.get("name") == name:
                return c["id"]
        raise MetabaseError(f"No collection named {name!r}")

    def run_query(self, sql, database_id=DEFAULT_DATABASE_ID):
        """Dry-run a native SQL query — nothing is saved. Returns (columns, rows)."""
        result = self._request("POST", "/api/dataset", {
            "database": database_id,
            "type": "native",
            "native": {"query": sql},
        })
        data = result.get("data", {})
        cols = [c["display_name"] for c in data.get("cols", [])]
        rows = data.get("rows", [])
        return cols, rows

    def find_table_id(self, name):
        for t in self._request("GET", "/api/table"):
            if t.get("name") == name:
                return t["id"]
        raise MetabaseError(f"No table named {name!r}")

    def create_collection(self, name, parent_id=DEFAULT_COLLECTION_ID):
        """Sub-folder inside a collection — e.g. one per dashboard, so a
        dashboard's cards don't clutter the parent collection's flat list
        (matches the existing "360" sub-folder convention)."""
        return self._request("POST", "/api/collection", {"name": name, "parent_id": parent_id})

    def find_field_id(self, table_name, field_name):
        """Look up a column's Metabase field_id — needed to wire a Field Filter
        (dimension-type) template tag to a real column."""
        table_id = self.find_table_id(table_name)
        meta = self._request("GET", f"/api/table/{table_id}/query_metadata")
        for f in meta.get("fields", []):
            if f.get("name") == field_name:
                return f["id"]
        raise MetabaseError(f"No field {field_name!r} on table {table_name!r}")

    # ---------- write ----------

    def create_card(self, name, sql, display="table", visualization_settings=None,
                     description=None, collection_id=DEFAULT_COLLECTION_ID,
                     database_id=DEFAULT_DATABASE_ID, template_tags=None,
                     card_type="question"):
        """`template_tags`: dict of Metabase template-tag defs, needed when `sql`
        references `{{variable}}` placeholders — see `filters.date_tag` /
        `filters.dimension_tag` to build them.
        `card_type`: "question" (default) or "model" (Metabase Model — a
        saved query other questions can build on top of, v0.48+ API)."""
        native = {"query": sql}
        if template_tags:
            native["template-tags"] = template_tags
        body = {
            "name": name,
            "type": card_type,
            "dataset_query": {
                "type": "native",
                "native": native,
                "database": database_id,
            },
            "display": display,
            "visualization_settings": visualization_settings or {},
            "collection_id": collection_id,
        }
        if description:
            body["description"] = description
        return self._request("POST", "/api/card", body)

    def create_dashboard(self, name, description=None, collection_id=DEFAULT_COLLECTION_ID):
        body = {"name": name, "collection_id": collection_id}
        if description:
            body["description"] = description
        return self._request("POST", "/api/dashboard", body)

    def set_dashboard_parameters(self, dashboard_id, parameters):
        """Define dashboard-level filter widgets — see `filters.date_parameter` /
        `filters.field_filter_parameter` to build them. Each card that should
        respond to a parameter needs a matching `parameter_mappings` entry,
        wired via `layout.DashboardLayout.row(..., parameter_mappings=...)`."""
        return self._request("PUT", f"/api/dashboard/{dashboard_id}",
                              {"parameters": parameters})

    def set_dashboard_cards(self, dashboard_id, dashcards, tabs=None):
        """Full replace of a dashboard's cards/layout.

        `dashcards` is a list of raw Metabase dashcard dicts — build them with
        `layout.DashboardLayout` rather than by hand. If the dashboard has
        tabs (`GET .../dashboard/:id` returns a non-empty `tabs` list), you
        MUST pass `tabs` too (each dashcard then needs a `dashboard_tab_id`
        matching one of them) — omitting it 500s with a dashboard-tab foreign
        key error on multi-tab dashboards.
        """
        body = {"cards": dashcards}
        if tabs is not None:
            body["tabs"] = tabs
        return self._request("PUT", f"/api/dashboard/{dashboard_id}/cards", body)

    def update_card(self, card_id, sql=None, display=None, visualization_settings=None,
                     description=None, template_tags=None, database_id=DEFAULT_DATABASE_ID):
        """Partial update of an existing card in place (dashboards keep pointing
        at the same card_id/dashcard, no re-layout needed)."""
        body = {}
        if sql is not None:
            native = {"query": sql}
            if template_tags:
                native["template-tags"] = template_tags
            body["dataset_query"] = {"type": "native", "native": native, "database": database_id}
        if display is not None:
            body["display"] = display
        if visualization_settings is not None:
            body["visualization_settings"] = visualization_settings
        if description is not None:
            body["description"] = description
        return self._request("PUT", f"/api/card/{card_id}", body)

    def archive_card(self, card_id):
        return self._request("PUT", f"/api/card/{card_id}", {"archived": True})

    def archive_dashboard(self, dashboard_id):
        return self._request("PUT", f"/api/dashboard/{dashboard_id}", {"archived": True})

    def move_card(self, card_id, collection_id):
        return self._request("PUT", f"/api/card/{card_id}", {"collection_id": collection_id})

    def move_dashboard(self, dashboard_id, collection_id):
        return self._request("PUT", f"/api/dashboard/{dashboard_id}", {"collection_id": collection_id})

    def dashboard_url(self, dashboard_id, slug="dashboard"):
        return f"{self.base_url}/dashboard/{dashboard_id}-{slug}"
