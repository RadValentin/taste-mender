from django.urls import reverse
from rest_framework.test import APITestCase
from recommend_api.tests.factories import GenreDortmundFactory, GenreRosamericaFactory


class GenreAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.dortmund = ["rock", "pop", "metal"]
        cls.rosamerica = ["pop", "roc", "rhy"]
        for index, label in enumerate(cls.dortmund):
            GenreDortmundFactory(code=index, label=label)
        for index, label in enumerate(cls.rosamerica):
            GenreRosamericaFactory(code=index, label=label)

    def test_get(self):
        url = reverse("api:genre-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertCountEqual(resp.data["genre_dortmund"], self.dortmund)
        self.assertCountEqual(resp.data["genre_rosamerica"], self.rosamerica)
