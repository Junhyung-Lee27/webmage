from collections import OrderedDict
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework import status
from ..models import MandaMain, MandaSub, MandaContent
from ..serializers.manda_serializer import *
from django.urls import reverse
import json

class MandaMainCreateTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('create')

    def test_manda_main_create(self):
        data = {
            'user': self.user.id,
            'success': True,
            'main_title': 'Test Main Title'
        }

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(MandaMain.objects.filter(user=self.user, main_title='Test Main Title').exists())
        created_object = MandaMain.objects.get(user=self.user, main_title='Test Main Title')
        expected_data = MandaMainSerializer(created_object).data
        self.assertEqual(response.data['main'], expected_data)

    def test_manda_main_create_with_sub_and_content(self):
        data = {
            'user': self.user.id,
            'success': True,
            'main_title': 'Test Main Title'
        }

        response = self.client.post(self.url, data, format='json')

        # MandaMain 객체가 정상적으로 생성되었는지 확인
        self.assertTrue(MandaMain.objects.filter(user=self.user, main_title='Test Main Title').exists())

        # MandaSub 객체가 8개 생성되었는지 확인
        main_instance = MandaMain.objects.get(user=self.user, main_title='Test Main Title')
        self.assertEqual(MandaSub.objects.filter(main_id=main_instance).count(), 8)

        # MandaContent 객체가 64개 생성되었는지 확인 (8 * 8)
        sub_instances = MandaSub.objects.filter(main_id=main_instance)
        total_content_count = 0
        for sub_instance in sub_instances:
            total_content_count += MandaContent.objects.filter(sub_id=sub_instance).count()
        self.assertEqual(total_content_count, 64)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unauthenticated_user(self):
        self.client.logout()
        data = {'title': 'Test Title'}
        
        response = self.client.post(self.url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manda_main_title_too_long(self):
        self.client.login(username='testuser', password='testpassword')
        long_title = 'a' * 101
        data = {'title': long_title}

        response = self.client.post(self.url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('main_title', response.data)

    def test_invalid_manda_main_title(self):
        self.client.login(username='testuser', password='testpassword')

        response = self.client.post(self.url, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('main_title', response.data)

class MandaMainSerializerTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('create')

    def test_main_title_length_validation(self):
        too_long_title = 'a' * 31
        empty_title = ''
        too_long_data = {
            'user': self.user.id,
            'success': True,
            'main_title': too_long_title
        }
        empty_data = {
            'user': self.user.id,
            'success': True,
            'main_title': empty_title
        }

        serializer1 = MandaMainSerializer(data=too_long_data)
        serializer2 = MandaMainSerializer(data=empty_data)

        self.assertFalse(serializer1.is_valid())
        self.assertFalse(serializer2.is_valid())
        self.assertIn('title은 30자 이하여야 합니다.', serializer1.errors['main_title'][0])
        self.assertIn('This field may not be blank.', serializer2.errors['main_title'][0])

class UpdateMandaSubsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.manda_main = MandaMain.objects.create(user=self.user, success=True, main_title='Main Title')
        self.manda_subs = MandaSub.objects.filter(main_id=self.manda_main)
        self.url = reverse('edit_sub')

    def test_update_manda_subs(self):
        updated_values = [
            {"id": self.manda_subs[0].id, "sub_title": "New Sub 1", "success": False},
            {"id": self.manda_subs[2].id, "sub_title": "New Sub 3", "success": False},
            {"id": self.manda_subs[4].id, "sub_title": "New Sub 5", "success": False},
            {"id": self.manda_subs[6].id, "sub_title": "New Sub 7", "success": False},
        ]
        data = {"subs": updated_values}

        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['sub_title'], "New Sub 1")
        self.assertEqual(response.data[1]['sub_title'], "New Sub 3")
        self.assertEqual(response.data[2]['sub_title'], "New Sub 5")
        self.assertEqual(response.data[3]['sub_title'], "New Sub 7")

        # 업데이트된 MandaSub 객체들을 다시 불러와서 값 검증
        updated_subs = [MandaSub.objects.get(id=sub_data["id"]) for sub_data in updated_values]
        for updated_sub, sub_data in zip(updated_subs, updated_values):
            self.assertEqual(updated_sub.sub_title, sub_data["sub_title"])

        # 다른 MandaSub 객체들의 값은 변경되지 않았는지 검증
        for i in range(len(self.manda_subs)):
            if i not in [0, 2, 4, 6]:
                self.assertEqual(self.manda_subs[i].sub_title, None)

    def test_long_sub_title(self):
        long_sub_title_data = {
            'subs': [
                {'id': 1, 'sub_title': 'a' * 51},
            ]
        }

        response = self.client.post(self.url, data=json.dumps(long_sub_title_data), content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('세부 목표는 50글자 이하여야 합니다.', response.data[0]['sub_title'])

    def test_nonexistent_sub_id(self):
        nonexistent_sub_data = {
            'subs': [
                {'id': 999, 'sub_title': 'Valid Value', 'success': False},
            ]
        }

        response = self.client.post(self.url, data=json.dumps(nonexistent_sub_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('MandaSub with ID 999 does not exist for the current user.', response.data)

class MandaMainDeleteTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client = APIClient()
        self.client.login(username='testuser', password='testpassword')
        self.manda_main = MandaMain.objects.create(user=self.user, success=True, main_title='Test MandaMain')
        self.url = reverse('delete_manda', args=[self.manda_main.id])

    def test_manda_main_delete(self):
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MandaMain.objects.filter(id=self.manda_main.id).exists())

    def test_manda_main_delete_unauthorized(self):
        unauthorized_user = User.objects.create_user(username='unauthorized', password='unauthorizedpassword')
        self.client.login(username='unauthorized', password='unauthorizedpassword')

        response = self.client.delete(self.url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(MandaMain.objects.filter(id=self.manda_main.id).exists())

class MandaMainViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.manda_main = MandaMain.objects.create(user=self.user, success=False, main_title='Test Main Title')
        self.url = reverse('mandamain', args=[self.manda_main.id])

    def test_manda_main_list_view(self):
        response = self.client.get(self.url)
        
        expected_data = {
            'main': {
                'id': self.manda_main.id,
                'user': self.user.id,
                'success': False,
                'main_title': 'Test Main Title'
            },
            'subs': [],
            'contents': []
        }

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['main'], expected_data['main'])
        self.assertEqual(len(response.data['subs']), 8)
        self.assertEqual(len(response.data['contents']), 64)

class MandaMainListViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        MandaMain.objects.create(user=self.user, success=False, main_title='Test Main Title 1')
        MandaMain.objects.create(user=self.user, success=True, main_title='Test Main Title 2')
        self.url = reverse('usermanda')

    def test_manda_main_list_view(self):
        response = self.client.get(self.url)

        expected_data = MandaMainSerializer(MandaMain.objects.all(), many=True).data

        self.assertEqual(response.data, expected_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class OthersMandaMainListTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')

        self.other_user = User.objects.create_user(username='otheruser', password='otherpassword')
        self.other_manda_main = MandaMain.objects.create(user=self.other_user, success=False, main_title='Other Main')
        self.other_manda_main = MandaMain.objects.create(user=self.other_user, success=False, main_title='Other Main2')

        self.url = reverse('others')

    def test_others_manda_main_list(self):
        response = self.client.get(self.url) 

        user_id = self.other_user.id
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(user_id, response.data)
        self.assertIsInstance(response.data[user_id], list)
        self.assertEqual(len(response.data[user_id]), 2) 
        manda_main_entry = response.data[user_id][0]
        self.assertIn('id', manda_main_entry)
        self.assertIn('success', manda_main_entry)
        self.assertIn('main_title', manda_main_entry)
        self.assertIn('subs', manda_main_entry)
        self.assertIsInstance(manda_main_entry['subs'], list)
        self.assertEqual(len(manda_main_entry['subs']), 8)  
        manda_sub_entry = manda_main_entry['subs'][0]
        self.assertIn('id', manda_sub_entry)
        self.assertIn('success', manda_sub_entry)
        self.assertIn('sub_title', manda_sub_entry)

class UpdateMandaContentsTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.manda_main = MandaMain.objects.create(user=self.user, success=False, main_title='Main Title')
        self.manda_subs = MandaSub.objects.filter(main_id=self.manda_main)
        self.manda_contents = MandaContent.objects.filter(sub_id__in=self.manda_subs)
        self.url = reverse('edit_content')

    def test_update_manda_contents(self):
        updated_values = [
            {"id": self.manda_contents[0].id, "content": "New Content 1", "success_count": 0},
            {"id": self.manda_contents[12].id, "content": "New Content 13", "success_count": 0},
            {"id": self.manda_contents[24].id, "content": "New Content 25", "success_count": 0},
            {"id": self.manda_contents[36].id, "content": "New Content 37", "success_count": 0},
        ]
        data = {"contents": updated_values}

        response = self.client.post(self.url, data=json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['content'], "New Content 1")
        self.assertEqual(response.data[1]['content'], "New Content 13")
        self.assertEqual(response.data[2]['content'], "New Content 25")
        self.assertEqual(response.data[3]['content'], "New Content 37")

        # 업데이트된 MandaContent 객체들을 다시 불러와서 값 검증
        updated_contents = [MandaContent.objects.get(id=content_data["id"]) for content_data in updated_values]
        for updated_content, content_data in zip(updated_contents, updated_values):
            self.assertEqual(updated_content.content, content_data["content"])

        # 다른 MandaContent 객체들의 값은 변경되지 않았는지 검증
        for i in range(len(self.manda_contents)):
            if i not in [0, 12, 24, 36]:
                self.assertEqual(self.manda_contents[i].content, None)

    def test_long_content(self):
        long_content_data = {
            'contents': [
                {'id': 1, 'content': 'a' * 51, "success_count": 0},
            ]
        }

        response = self.client.post(self.url, data=json.dumps(long_content_data), content_type='application/json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('내용은 50글자 이하여야 합니다.', response.data[0]['content'])

    def test_nonexistent_content_id(self):
        nonexistent_content = {
            'contents': [
                {'id': 999, 'content': 'Valid Value', "success_count": 0},
            ]
        }

        response = self.client.post(self.url, data=json.dumps(nonexistent_content), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('MandaContent with ID 999 does not exist for the current user.', response.data)

class UpdateMandaMainTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.manda_main = MandaMain.objects.create(user=self.user, main_title='Original Title')
        self.url = reverse('edit_main')

    def test_update_manda_main(self):
        manda_main = MandaMain.objects.create(user=self.user, main_title='Original Title')
        data = {
            'user': self.user.id,
            'id': manda_main.id,
            'main_title': 'Updated Title',
            "success": False
        }

        response = self.client.patch(self.url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['main_title'], 'Updated Title')
        manda_main.refresh_from_db()
        self.assertEqual(manda_main.main_title, 'Updated Title')

    def test_update_manda_main_invalid_id(self):
        data = {
            'user': self.user.id,
            'id': 9999,
            'main_title': 'Updated Title'
        }

        response = self.client.patch(self.url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, "MandaMain with ID 9999 does not exist for the current user.")

    def test_update_manda_main_missing_id(self):
        data = {
            'user': self.user.id,
            'main_title': 'Updated Title'
        }

        response = self.client.patch(self.url, json.dumps(data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_manda_main_invalid_data(self):
        invalid_data = {
            'user': self.user.id,
            'id': self.manda_main.pk,
            'main_title': '',
        }

        response = self.client.patch(self.url, json.dumps(invalid_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.manda_main.refresh_from_db()
        self.assertNotEqual(self.manda_main.main_title, invalid_data['main_title'])

    def test_update_manda_main_too_long_title(self):
        invalid_data = {
            'user': self.user.id,
            'id': self.manda_main.pk,
            'main_title': 'a' * 51,
        }

        response = self.client.patch(self.url, json.dumps(invalid_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.manda_main.refresh_from_db()
        self.assertIn('main_title', response.data)
