import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Category, SavedRecipe, default_category

MEAL = {
    "idMeal": "52772",
    "strMeal": "teriyaki chicken casserole",
    "strMealThumb": "https://www.themealdb.com/images/media/meals/wvpsxx1468256321.jpg",
    "strIngredient1": "soy sauce",
    "strIngredient2": "water",
    "strIngredient3": "",
}


class BookmarksTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("budi", password="test123")
        self.other = User.objects.create_user("sari", password="test123")
        self.client.force_login(self.user)

    def post(self, name, *args, body=None):
        return self.client.post(
            reverse(f"bookmarks:{name}", args=args), json.dumps(body or {}), content_type="application/json"
        )


class PageTests(BookmarksTestCase):
    def test_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("bookmarks:show_bookmarks"))
        self.assertEqual(response.status_code, 302)

    def test_page_creates_default_category(self):
        response = self.client.get(reverse("bookmarks:show_bookmarks"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Category.objects.filter(user=self.user, is_default=True, name="Favourites").exists())
        self.assertEqual(response.context["selected_category"].is_default, True)

    def test_page_shows_selected_category_recipes(self):
        category = Category.objects.create(user=self.user, name="Sarapan")
        SavedRecipe.objects.create(category=category, recipe_id=1, name="Corba", image="https://x.test/a.jpg", ingredients=["Lentils"])
        response = self.client.get(reverse("bookmarks:show_bookmarks"), {"category": category.id})
        self.assertEqual(response.context["selected_category"], category)
        self.assertEqual(response.context["recipes"][0]["ingredient_count"], 1)

    def test_other_users_category_falls_back_to_default(self):
        foreign = Category.objects.create(user=self.other, name="Rahasia")
        response = self.client.get(reverse("bookmarks:show_bookmarks"), {"category": foreign.id})
        self.assertTrue(response.context["selected_category"].is_default)


class CategoryApiTests(BookmarksTestCase):
    def test_create(self):
        response = self.post("category_create", body={"name": "  Sarapan "})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["category"]["name"], "Sarapan")

    def test_create_rejects_empty_and_duplicate_names(self):
        Category.objects.create(user=self.user, name="Sarapan")
        self.assertIn("name", self.post("category_create", body={"name": " "}).json()["errors"])
        response = self.post("category_create", body={"name": "sarapan"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.json()["errors"])

    def test_same_name_allowed_for_different_users(self):
        Category.objects.create(user=self.other, name="Sarapan")
        self.assertEqual(self.post("category_create", body={"name": "Sarapan"}).status_code, 201)

    def test_rename(self):
        category = Category.objects.create(user=self.user, name="Sarapan")
        self.assertEqual(self.post("category_rename", category.id, body={"name": "Pagi"}).status_code, 200)
        category.refresh_from_db()
        self.assertEqual(category.name, "Pagi")

    def test_rename_to_own_name_with_different_case(self):
        category = Category.objects.create(user=self.user, name="Sarapan")
        self.assertEqual(self.post("category_rename", category.id, body={"name": "SARAPAN"}).status_code, 200)

    def test_default_category_cannot_be_renamed_or_deleted(self):
        category = default_category(self.user)
        self.assertEqual(self.post("category_rename", category.id, body={"name": "Lain"}).status_code, 400)
        self.assertEqual(self.post("category_delete", category.id).status_code, 400)
        self.assertTrue(Category.objects.filter(pk=category.id).exists())

    def test_delete(self):
        category = Category.objects.create(user=self.user, name="Sarapan")
        SavedRecipe.objects.create(category=category, recipe_id=1, name="Corba", image="https://x.test/a.jpg")
        response = self.post("category_delete", category.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect_category"], default_category(self.user).id)
        self.assertFalse(SavedRecipe.objects.exists())

    def test_cannot_touch_other_users_categories(self):
        foreign = Category.objects.create(user=self.other, name="Rahasia")
        self.assertEqual(self.post("category_rename", foreign.id, body={"name": "x"}).status_code, 404)
        self.assertEqual(self.post("category_delete", foreign.id).status_code, 404)
        self.assertEqual(self.post("category_recipe_delete", foreign.id, 1).status_code, 404)

    def test_remove_recipe_from_category(self):
        category = Category.objects.create(user=self.user, name="Sarapan")
        SavedRecipe.objects.create(category=category, recipe_id=1, name="Corba", image="https://x.test/a.jpg")
        SavedRecipe.objects.create(category=category, recipe_id=2, name="Sushi", image="https://x.test/b.jpg")
        response = self.post("category_recipe_delete", category.id, 1)
        self.assertEqual(response.json()["recipe_count"], 1)
        self.assertFalse(SavedRecipe.objects.filter(recipe_id=1).exists())

    def test_api_requires_login(self):
        self.client.logout()
        self.assertEqual(self.post("category_create", body={"name": "x"}).status_code, 401)
        self.assertEqual(self.client.get(reverse("bookmarks:recipe_categories", args=[1])).status_code, 401)


@patch("bookmarks.views._lookup_meal", return_value=MEAL)
class RecipeSaveTests(BookmarksTestCase):
    def test_categories_list_marks_selected(self, lookup):
        favourites = default_category(self.user)
        breakfast = Category.objects.create(user=self.user, name="Sarapan")
        SavedRecipe.objects.create(category=breakfast, recipe_id=52772, name="x", image="https://x.test/a.jpg")
        data = self.client.get(reverse("bookmarks:recipe_categories", args=[52772])).json()
        selected = {c["id"]: c["selected"] for c in data["categories"]}
        self.assertEqual(selected, {favourites.id: False, breakfast.id: True})

    def test_save_syncs_categories(self, lookup):
        favourites = default_category(self.user)
        breakfast = Category.objects.create(user=self.user, name="Sarapan")

        response = self.post("recipe_save", 52772, body={"category_ids": [favourites.id, breakfast.id]})
        self.assertEqual(response.json(), {"bookmarked": True})
        saved = SavedRecipe.objects.get(category=favourites)
        self.assertEqual(saved.name, "Teriyaki Chicken Casserole")
        self.assertEqual(saved.ingredients, ["Soy Sauce", "Water"])

        self.post("recipe_save", 52772, body={"category_ids": [breakfast.id]})
        self.assertEqual(list(SavedRecipe.objects.values_list("category_id", flat=True)), [breakfast.id])
        self.assertEqual(lookup.call_count, 1)

        response = self.post("recipe_save", 52772, body={"category_ids": []})
        self.assertEqual(response.json(), {"bookmarked": False})
        self.assertFalse(SavedRecipe.objects.exists())

    def test_save_ignores_other_users_categories(self, lookup):
        foreign = Category.objects.create(user=self.other, name="Rahasia")
        response = self.post("recipe_save", 52772, body={"category_ids": [foreign.id]})
        self.assertEqual(response.json(), {"bookmarked": False})
        self.assertFalse(SavedRecipe.objects.exists())

    def test_save_rejects_invalid_body(self, lookup):
        self.assertEqual(self.post("recipe_save", 52772, body={"category_ids": "1"}).status_code, 400)

    def test_save_unknown_recipe(self, lookup):
        lookup.return_value = None
        response = self.post("recipe_save", 1, body={"category_ids": [default_category(self.user).id]})
        self.assertEqual(response.status_code, 404)


class RecipeSearchTests(BookmarksTestCase):
    def setUp(self):
        super().setUp()
        self.category = Category.objects.create(user=self.user, name="Sarapan")
        SavedRecipe.objects.create(category=self.category, recipe_id=1, name="Chicken Curry", image="https://x.test/a.jpg", ingredients=["Chicken", "Rice"])
        SavedRecipe.objects.create(category=self.category, recipe_id=2, name="Corba", image="https://x.test/b.jpg", ingredients=["Lentils", "Onion"])

    def search(self, category_id=None, **params):
        return self.client.get(reverse("bookmarks:category_recipes", args=[category_id or self.category.id]), params)

    def ids(self, response):
        return [r["id"] for r in response.json()["recipes"]]

    def test_search_by_name_and_ingredient(self):
        self.assertEqual(self.ids(self.search(q="curry")), [1])
        self.assertEqual(self.ids(self.search(q="ONION")), [2])

    def test_empty_query_returns_everything(self):
        response = self.search(q="  ")
        self.assertEqual(response.json()["count"], 2)

    def test_no_results(self):
        self.assertEqual(self.search(q="sushi").json()["count"], 0)

    def test_pagination(self):
        for i in range(3, 11):
            SavedRecipe.objects.create(category=self.category, recipe_id=i, name=f"Resep {i}", image="https://x.test/c.jpg")
        data = self.search(page=2).json()
        self.assertEqual((data["num_pages"], data["page"], len(data["recipes"])), (2, 2, 2))

    def test_page_renders_pagination_meta(self):
        response = self.client.get(reverse("bookmarks:show_bookmarks"), {"category": self.category.id})
        self.assertEqual(response.context["num_pages"], 1)
        self.assertContains(response, 'id="recipe-card-template"')

    def test_other_users_category(self):
        foreign = Category.objects.create(user=self.other, name="Rahasia")
        self.assertEqual(self.search(foreign.id).status_code, 404)

    def test_requires_login(self):
        self.client.logout()
        self.assertEqual(self.search().status_code, 401)


@patch("discovery.views._lookup_meal", return_value=MEAL)
class RecipeDetailBookmarkTests(BookmarksTestCase):
    def detail(self):
        return self.client.get(reverse("discovery:show_recipe_detail", args=[52772]))

    def test_detail_shows_bookmark_button_and_dialog(self, lookup):
        response = self.detail()
        self.assertContains(response, 'data-bookmark="52772"')
        self.assertContains(response, 'id="bookmark-dialog"')
        self.assertContains(response, "bookmark_dialog.js")
        self.assertFalse(response.context["recipe"]["bookmarked"])

    def test_detail_marks_saved_recipe(self, lookup):
        SavedRecipe.objects.create(category=default_category(self.user), recipe_id=52772, name="x", image="https://x.test/a.jpg")
        response = self.detail()
        self.assertTrue(response.context["recipe"]["bookmarked"])
        self.assertContains(response, 'aria-pressed="true"')

    def test_detail_logged_out_links_to_login(self, lookup):
        self.client.logout()
        response = self.detail()
        self.assertNotContains(response, 'id="bookmark-dialog"')
        self.assertNotContains(response, "data-bookmark=")
        self.assertContains(response, reverse("authentication:login") + "?next=")
