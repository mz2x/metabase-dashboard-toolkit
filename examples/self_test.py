"""End-to-end sanity check for the metabase/ toolkit: read access, resolving
your default collection, write access (card + dashboard + layout), then
archives everything it created so nothing test-related is left behind.

Run: python3 examples/self_test.py   (from inside the metabase/ folder)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client import MetabaseClient, DEFAULT_COLLECTION_ID  # noqa: E402
from layout import DashboardLayout  # noqa: E402

# Name of the collection DEFAULT_COLLECTION_ID (in client.py) should point
# at — swap this for your own collection's name.
DEFAULT_COLLECTION_NAME = "Your Collection Name"


def main():
    mb = MetabaseClient()

    print("1. Connecting + listing databases...")
    dbs = mb.list_databases()
    print(f"   OK — {len(dbs)} database(s): {[d['name'] for d in dbs]}")

    print(f"2. Resolving '{DEFAULT_COLLECTION_NAME}' collection...")
    collection_id = mb.find_collection_id(DEFAULT_COLLECTION_NAME)
    assert collection_id == DEFAULT_COLLECTION_ID, (
        f"Collection id changed! Found {collection_id}, "
        f"client.py has {DEFAULT_COLLECTION_ID} hardcoded — update it."
    )
    print(f"   OK — id {collection_id}")

    print("3. Dry-run SQL query (no save)...")
    cols, rows = mb.run_query("SELECT 1 AS ok")
    print(f"   OK — columns={cols} rows={rows}")

    print("4. Creating a throwaway card...")
    card = mb.create_card(
        name="[self_test] delete me",
        sql="SELECT 1 AS ok",
        display="scalar",
        description="Created by examples/self_test.py — safe to ignore/delete.",
    )
    card_id = card["id"]
    print(f"   OK — card id {card_id}")

    print("5. Creating a throwaway dashboard + laying out the card...")
    dash = mb.create_dashboard(name="[self_test] delete me")
    dash_id = dash["id"]
    layout = DashboardLayout()
    layout.heading("## self_test").row([{"card_id": card_id, "size_y": 3}], height=3)
    mb.set_dashboard_cards(dash_id, layout.dashcards)
    print(f"   OK — dashboard id {dash_id}, url {mb.dashboard_url(dash_id, 'self-test')}")

    print("6. Cleaning up (archiving the test card + dashboard)...")
    mb.archive_dashboard(dash_id)
    mb.archive_card(card_id)
    print("   OK — archived")

    print("\nAll checks passed. Read + write + layout pipeline works end to end.")


if __name__ == "__main__":
    main()
