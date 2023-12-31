from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
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

class RegistrationAPITest(APITestCase):
    def test_user_registration(self):
        url = reverse('signup')
        data = {'username': 'testuser', 'password': 'testpassword'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_invalid_user_registration(self):
        url = reverse('signup')
        data = {'username': '', 'password': 'testpassword'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class UpdateUserAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client.login(username='testuser', password='testpassword')
        self.update_url = reverse('edit')

    def test_user_edit_with_password_change(self):
        new_password = 'newpassword123'
        response = self.client.patch(self.update_url, {'password': new_password}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        updated_user = User.objects.get(id=self.user.id)
        self.assertTrue(updated_user.check_password(new_password))

    def test_user_edit_without_password_change(self):
        response = self.client.patch(self.update_url, {'username': 'newusername'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        unchanged_user = User.objects.get(id=self.user.id)
        self.assertTrue(unchanged_user.check_password('testpassword'))

    def test_invalid_user_edit(self):
        data = {'username': '', 'email': '', 'password': 'testpassword'}
        response = self.client.patch(self.update_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ResetPasswordAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.reset_password_url = reverse('reset_password')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )

    def test_reset_password_valid_email(self):
        response = self.client.post(self.reset_password_url, {'email': self.user_data['email']}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Temporary password has been sent to your email address.')

    def test_reset_password_invalid_email(self):
        response = self.client.post(self.reset_password_url, {'email': 'nonexistent@example.com'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'User with this email address does not exist.')

class DeleteUserAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        self.user = User.objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.login_url = reverse('login')
        self.delete_url = reverse('delete_user')

    def test_check_existence_of_deleted_user(self):
        # 로그인
        response_login = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response_login.status_code, status.HTTP_200_OK)

        # 회원탈퇴
        response_delete = self.client.delete(self.delete_url, format='json')
        self.assertEqual(response_delete.status_code, status.HTTP_200_OK)

        # 탈퇴 성공 메시지 확인
        response_data = response_delete.content.decode('utf-8')
        expected_response_data = '{"message":"User deleted successfully."}'
        self.assertJSONEqual(response_data, expected_response_data)

        # 탈퇴한 계정 로그인시 실패 확인
        response_login_after_delete = self.client.post(self.login_url, self.user_data, format='json')
        self.assertEqual(response_login_after_delete.status_code, status.HTTP_400_BAD_REQUEST)
