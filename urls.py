from werkzeug.routing import Map, Rule, Submount
from werkzeug.routing import UnicodeConverter, BaseConverter


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


class RangeConverter(UnicodeConverter):
    def to_python(self, value):
        return [float(v) for v in value.split("-")]

    def to_url(self, value):
        return f"{value[0]}-{value[1]}"


class AppConverter(BaseConverter):
    regex = r"(?:deciles|heatmap|counts|measures)"


class EntityConverter(BaseConverter):
    regex = r"(?:ccg_id|practice|lab|test_code|result_category)"


url_map = Map(
    [
        Submount(
            "/data",
            [
                Rule("/<app:page_id>", endpoint="index"),
                Rule(
                    "/<app:page_id>/by/<entity_type:groupby>/showing/<entity_type:practice_filter_entity>/<list:entity_ids_for_practice_filter>/numerators/<list:numerators>/denominators/<list:denominators>/filter/<string:result_filter>/range-filter/<range:calc_value_range_filter>",
                    endpoint="analysis",
                ),
            ],
        )
    ],
    converters={
        "list": ListConverter,
        "app": AppConverter,
        "entity_type": EntityConverter,
        "range": RangeConverter,
    },
)

urls = url_map.bind(
    "hostname"
)  # Required by werkzeug for redirects, although we never use
