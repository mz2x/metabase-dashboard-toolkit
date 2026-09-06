"""Helpers for wiring dashboard-level filters (Metabase "parameters") to
native-SQL cards that use `{{variable}}` template tags.

Usage pattern for one filter shared across N cards:
    start_id, end_id, streak_id = str(uuid4()), str(uuid4()), str(uuid4())

    # 1. each card's SQL declares {{start_date}}/{{end_date}}/{{streak_name}}
    #    and gets matching template-tags at creation:
    card = mb.create_card(..., sql=sql, template_tags={
        "start_date": date_tag("start_date", "Start Date"),
        "end_date": date_tag("end_date", "End Date"),
        "streak_name": dimension_tag("streak_name", "Streak Type", field_id),
    })

    # 2. the dashboard declares the visible filter widgets once:
    mb.set_dashboard_parameters(dash_id, [
        date_parameter(start_id, "Start Date", "start_date"),
        date_parameter(end_id, "End Date", "end_date"),
        field_filter_parameter(streak_id, "Streak Type", "streak_name"),
    ])

    # 3. each dashcard maps dashboard parameter -> its own template tag:
    layout.row([{"card_id": card["id"],
                  "parameter_mappings": variable_mappings(card["id"], {
                      start_id: "start_date", end_id: "end_date",
                  }) + dimension_mappings(card["id"], {streak_id: "streak_name"})}])
"""
import uuid


def _id():
    return str(uuid.uuid4())


# ---------- template tags (go on the card's dataset_query.native.template-tags) ----------

def date_tag(name, display_name):
    """Plain date input, bound via SQL variable substitution (`{{name}}`)."""
    return {"id": _id(), "name": name, "display-name": display_name, "type": "date"}


def text_tag(name, display_name):
    return {"id": _id(), "name": name, "display-name": display_name, "type": "text"}


def dimension_tag(name, display_name, field_id, widget_type="string/="):
    """Field Filter — binds to a real column (`field_id` from
    `MetabaseClient.find_field_id`), used as `[[AND {{name}}]]` in SQL."""
    return {
        "id": _id(),
        "name": name,
        "display-name": display_name,
        "type": "dimension",
        "dimension": ["field", field_id, None],
        "widget-type": widget_type,
        "default": None,
    }


# ---------- dashboard parameters (go on set_dashboard_parameters) ----------

def date_parameter(parameter_id, name, slug):
    return {"id": parameter_id, "name": name, "slug": slug, "type": "date/single"}


def field_filter_parameter(parameter_id, name, slug, param_type="string/="):
    return {"id": parameter_id, "name": name, "slug": slug, "type": param_type}


# ---------- per-dashcard parameter_mappings ----------

def variable_mappings(card_id, parameter_id_to_tag_name):
    """For plain (date/text) template tags — target is `variable`."""
    return [
        {"parameter_id": pid, "card_id": card_id,
         "target": ["variable", ["template-tag", tag_name]]}
        for pid, tag_name in parameter_id_to_tag_name.items()
    ]


def dimension_mappings(card_id, parameter_id_to_tag_name):
    """For Field Filter (dimension) template tags — target is `dimension`."""
    return [
        {"parameter_id": pid, "card_id": card_id,
         "target": ["dimension", ["template-tag", tag_name]]}
        for pid, tag_name in parameter_id_to_tag_name.items()
    ]
