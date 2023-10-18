from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth.models import User

class LoginAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('login')
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )

    def test_login_valid_user(self):
        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_login_invalid_user(self):
        invalid_data = {
            'username': 'nottestuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields(self):
        incomplete_data = {
            'username': 'testuser',
        }
        response = self.client.post(self.login_url, incomplete_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        
        response = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_invalid_password(self):
        invalid_password_data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, invalid_password_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_http_method(self):
        response = self.client.get(self.login_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

class LogoutAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.logout_url = reverse('logout')
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')

    def test_user_logout(self):
        response = self.client.post(self.logout_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
