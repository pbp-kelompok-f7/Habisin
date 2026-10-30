from django.test import SimpleTestCase, override_settings
from django.urls import reverse


@override_settings(DEBUG=False)
class ProductionNavigationTests(SimpleTestCase):
    def test_account_and_fridge_routes_exist_without_debug(self):
        self.assertEqual(reverse("authentication:login"), "/auth/login/")
        self.assertEqual(reverse("fridge:show_fridge"), "/kulkas/")

    def test_landing_page_renders_account_links_without_debug(self):
        response = self.client.get(reverse("home:show_home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("authentication:login"))
        self.assertContains(response, 'class="lp-nav nav-shell"')
        self.assertContains(response, f'href="{reverse("home:show_home")}" class="lp-link is-active" aria-current="page"')
        self.assertNotContains(response, 'id="main-nav"')
