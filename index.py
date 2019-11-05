#!/usr/bin/env python
import os


def setup_app_and_layout():
    from app import app
    from layout import layout
    from data import get_test_list
    from data import get_ccg_list
    from data import get_measures

    app.layout = layout(get_test_list(), get_ccg_list(), get_measures())
    return app


def setup_callbacks():
    import apps.base
    import apps.deciles
    import apps.heatmap
    import apps.test_counts

    import stateful_routing


app = setup_app_and_layout()
setup_callbacks()

if __name__ == "__main__":
    # You can't set up callbacks until the layout has been registered
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DEBUG", "").strip().lower() == "true"
    app.run_server(port=port, debug=debug)
