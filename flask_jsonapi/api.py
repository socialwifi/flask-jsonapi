import re


class Api:
    def __init__(self, app):
        self.app = app

    def route(self, resource, view, *urls, view_kwargs=None, url_rule_options=None):
        """Create an api view.

        :param Resource resource: a resource class inherited from flask_rest_jsonapi.resource.Resource
        :param str view: the view name
        :param list urls: the urls of the view
        :param dict view_kwargs: kwargs passed to resource constructor
        :param dict url_rule_options: additional url rule options. For more info look at Flask.add_url_rule()
        """
        view_func = resource.as_view(view, **(view_kwargs or {}))
        for url in urls:
            self.app.add_url_rule(url, view_func=view_func, **url_rule_options or dict())

    def repository(self, repository, base_view_name, *urls, url_rule_options=None):
        detail_view = repository.as_detail_view('{}_detail'.format(base_view_name))
        list_view = repository.as_list_view('{}_list'.format(base_view_name))
        for list_url in urls:
            detail_url = re.sub(r'(/?)$', r'/<id>\g<1>', list_url)
            self.app.add_url_rule(list_url, view_func=list_view, **url_rule_options or dict())
            self.app.add_url_rule(detail_url, view_func=detail_view, **url_rule_options or dict())
