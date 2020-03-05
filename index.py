#!/usr/bin/env python
import os
import settings


def setup_app_and_layout():
    from app import app
    from layout import layout
    from data import get_test_list
    from data import get_org_list

    app.layout = layout(
        get_test_list(),
        get_org_list("ccg_id"),
        get_org_list("lab_id"),
        get_org_list("practice_id"),
    )
    return app


def setup_callbacks():
    import apps.base

    import apps.analyse
    import apps.heatmap
    import apps.datatable
    import apps.measure

    import stateful_routing


app = setup_app_and_layout()
setup_callbacks()

if __name__ == "__main__":
    # You can't set up callbacks until the layout has been registered
    port = int(os.environ.get("PORT", 8050))
    debug = settings.DEBUG
    app.run_server(port=port, debug=debug)
