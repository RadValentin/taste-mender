from django.test import SimpleTestCase


class PublicEndpointTests(SimpleTestCase):
    def test_robots_txt_returns_plain_text_with_sitemap_url(self):
        response = self.client.get("/robots.txt")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"].split(";", 1)[0], "text/plain")
        self.assertContains(response, "Sitemap: https://taste-mender.com/sitemap.xml")

    def test_sitemap_xml_returns_expected_public_locations(self):
        response = self.client.get("/sitemap.xml")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Type"].split(";", 1)[0], "application/xml")
        self.assertContains(response, "<loc>http://testserver/</loc>")
        self.assertContains(response, "<loc>http://testserver/search</loc>")

    def test_unknown_frontend_url_returns_not_found(self):
        response = self.client.get("/does-not-exist")

        self.assertEqual(response.status_code, 404)