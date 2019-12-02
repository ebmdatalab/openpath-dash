from werkzeug.routing import Map, Rule, Submount
from werkzeug.routing import UnicodeConverter, BaseConverter, AnyConverter

import settings


class ListConverter(UnicodeConverter):
    def to_python(self, value):
        value = super(ListConverter, self).to_python(value)
        return value.split("+")

    def to_url(self, value):
        if value:
            if not isinstance(value, str):
                encoded = [super(ListConverter, self).to_url(x) for x in value]
                value = "+".join(encoded)
        return value


class AppConverter(AnyConverter):
    def __init__(self, map):
        super().__init__(map, *settings.PAGES)


class GroupByEntityConverter(BaseConverter):
    regex = r"(?:ccg_id|lab_id|practice_id|lab|test_code|result_category)"


class FilterEntityConverter(BaseConverter):
    regex = r"(?:ccg_id|lab_id)"


url_map = Map(
    [
        Submount(
            "/data",
            [
                Rule("/<app:page_id>", endpoint="index"),
                Rule(
                    "/<app:page_id>/by/<groupby_entity_type:groupby>/showing/ccg_id/<list:ccg_ids_for_practice_filter>/lab_id/<list:lab_ids_for_practice_filter>/numerators/<list:numerators>/denominators/<list:denominators>/filter/<string:result_filter>",
                    endpoint="analysis",
                ),
            ],
        )
    ],
    converters={
        "list": ListConverter,
        "app": AppConverter,
        "groupby_entity_type": GroupByEntityConverter,
        "filter_entity_type": FilterEntityConverter,
    },
)

urls = url_map.bind(
    "hostname"
)  # Required by werkzeug for redirects, although we never use
