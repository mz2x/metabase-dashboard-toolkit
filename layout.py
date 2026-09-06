"""Auto-layout helper for building dashboards in a standard section pattern
(heading -> KPI row -> heading -> trend row -> heading -> breakdown row -> ...)
— the shape most "real" analytics dashboards converge on, so it's worth a
small helper instead of hand-computing row/col on every card.

Metabase's dashboard grid is 24 columns wide. This class just tracks the
current row and hands back dashcard dicts ready for
client.MetabaseClient.set_dashboard_cards().
"""

GRID_WIDTH = 24


class DashboardLayout:
    def __init__(self):
        self._row = 0
        self._next_id = -1
        self.dashcards = []

    def _take_id(self):
        i = self._next_id
        self._next_id -= 1
        return i

    def heading(self, markdown_text, height=2):
        """A full-width section divider, e.g. layout.heading('## Trends')."""
        self.dashcards.append({
            "id": self._take_id(),
            "card_id": None,
            "row": self._row,
            "col": 0,
            "size_x": GRID_WIDTH,
            "size_y": height,
            "visualization_settings": {
                "text": markdown_text,
                "virtual_card": {
                    "name": None,
                    "display": "text",
                    "dataset_query": {},
                    "visualization_settings": {},
                },
                "dashcard.background": False,
            },
        })
        self._row += height
        return self

    def row(self, cards, height=None):
        """One row of cards placed left-to-right.

        `cards`: list of dicts, each needs `card_id` (from create_card's result).
        Optional per-card `size_x` (defaults to an even split of the 24-wide
        grid), `size_y`, `series`, `visualization_settings`, `parameter_mappings`
        (list built with `filters.variable_mappings`/`dimension_mappings`, needed
        for this card to respond to a dashboard filter set via
        `MetabaseClient.set_dashboard_parameters`).
        `height`: overrides size_y for every card in the row at once.
        """
        n = len(cards)
        if n == 0:
            return self
        default_width = GRID_WIDTH // n
        row_height = height or max((c.get("size_y") for c in cards if c.get("size_y")), default=7)
        col = 0
        for c in cards:
            width = c.get("size_x", default_width)
            self.dashcards.append({
                "id": self._take_id(),
                "card_id": c["card_id"],
                "row": self._row,
                "col": col,
                "size_x": width,
                "size_y": c.get("size_y", row_height),
                "series": c.get("series", []),
                "visualization_settings": c.get("visualization_settings", {}),
                "parameter_mappings": c.get("parameter_mappings", []),
            })
            col += width
        self._row += row_height
        return self
