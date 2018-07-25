from flask_jsonapi import api


class TestGettingDetailURL:
    def test_url_ends_with_slash_detail_url_ends_with_slash(self):
        list_url = '/car/'
        detail_url = api.Api.get_detail_url(list_url)
        assert detail_url == '/car/<id>/'

    def test_url_does_not_ends_with_slash_detail_url_does_not_ends_with_slash(self):
        list_url = '/car'
        detail_url = api.Api.get_detail_url(list_url)
        assert detail_url == '/car/<id>'
