class Api:
    def __init__(self, app):
        self.app = app

    def route(self, resource, view, *urls, url_rule_options=None):
        """Create an api view.

        :param Resource resource: a resource class inherited from flask_rest_jsonapi.resource.Resource
        :param str view: the view name
        :param list urls: the urls of the view
        :param dict url_rule_options: additional url rule options. For more info look at Flask.add_url_rule()
        """
        view_func = resource.as_view(view)
        for url in urls:
            self.app.add_url_rule(url, view_func=view_func, **url_rule_options or dict())
