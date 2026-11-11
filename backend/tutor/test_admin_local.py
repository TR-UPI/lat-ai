from django.test import TestCase
from accounts.models import User

class LocalAdminTests(TestCase):
    def test_admin_requires_login_and_login_page_loads(self):
        response=self.client.get('/admin/')
        self.assertEqual(response.status_code,302)
        self.assertTrue(response['Location'].startswith('/admin/login/'))
        self.assertEqual(self.client.get('/admin/login/').status_code,200)

    def test_regular_review_account_cannot_enter_admin(self):
        user=User.objects.create_user('review@example.test','Only-a-test-123!')
        self.client.force_login(user)
        response=self.client.get('/admin/')
        self.assertEqual(response.status_code,302)
        self.assertTrue(response['Location'].startswith('/admin/login/'))

    def test_superuser_can_open_admin_and_course_list(self):
        user=User.objects.create_superuser('admin@example.test','Only-a-test-123!')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/admin/').status_code,200)
        self.assertEqual(self.client.get('/admin/courses/course/').status_code,200)
        self.assertEqual(self.client.get('/admin/progress/exerciseattempt/').status_code,200)
        self.assertEqual(self.client.get('/admin/documents/document/').status_code,404)

    def test_only_admin_static_assets_are_served(self):
        response=self.client.get('/static/admin/css/base.css')
        self.assertEqual(response.status_code,200)
        self.assertIn('text/css',response['Content-Type'])
        self.assertEqual(self.client.get('/static/runtime/django-secret.txt').status_code,404)
        self.assertIn(self.client.get('/static/admin/../../config/ai_local.py').status_code,(400,404))
