from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from django.urls import reverse


class PublicRecipeTests(SimpleTestCase):
    """These requests must work without touching any database, even for guests."""

    def setUp(self):
        self.url = reverse("meals_planner:public_recipes")
        key = "meals_planner:public_recipes:v1"
        cache.delete(key)
        self.addCleanup(cache.delete, key)

    @patch("meals_planner.api.preview_recipes")
    def test_catalogue_shares_only_public_fields_and_reuses_feed(self, preview):
        preview.return_value = [{
            "id": "53254", "name": "Ezme", "image": "https://example.org/ezme.jpg",
            "ingredients": ["Tomato", "Onion", "tomato"],
        }]
        response = self.client.get(self.url, HTTP_ORIGIN="http://localhost:5460")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertEqual(response.json(), {"recipes": [{
            "id": "mealdb:53254", "name": "Ezme", "image_url": "https://example.org/ezme.jpg",
            "ingredients": ["Tomato", "Onion"],
        }]})
        self.assertEqual(self.client.get(self.url).json(), response.json())
        preview.assert_called_once_with()

    @patch("meals_planner.api.preview_recipes", return_value=[])
    def test_upstream_outage_still_serves_a_public_snapshot(self, preview):
        recipes = self.client.get(self.url).json()["recipes"]
        self.assertGreater(len(recipes), 0)
        self.assertEqual(len({item["id"] for item in recipes}), len(recipes))
        self.assertTrue(all(item["ingredients"] and item["name"] for item in recipes))

    @patch("meals_planner.api.preview_recipes")
    def test_mutations_are_rejected(self, preview):
        for method in ("post", "put", "patch", "delete"):
            with self.subTest(method=method):
                self.assertEqual(getattr(self.client, method)(self.url).status_code, 405)
        preview.assert_not_called()
