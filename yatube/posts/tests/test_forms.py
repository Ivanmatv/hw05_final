import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from http import HTTPStatus

from posts.models import Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivan')
        cls.user_noauthor = User.objects.create_user(username='Igor')
        cls.small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded,
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client = Client()
        # Авторизуем пользователя
        self.authorized_client.force_login(self.user)
        # Создаём третий клиент
        self.authorized_client_noauthor = Client()
        # Авторизуем не автора постов
        self.authorized_client_noauthor.force_login(self.user_noauthor)

    def test_create_post(self):
        post_create = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': self.uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        created_post = Post.objects.latest('pk')

        # self.assertRedirects(response, reverse(
        #     'posts:profile', kwargs={'username': created_post.author})
        # )
        self.assertEqual(Post.objects.count(), post_create + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(created_post.author, self.post.author)
        self.assertEqual(created_post.text, form_data['text'])
        self.assertEqual(created_post.group_id, form_data['group'])
        self.assertTrue(
            Post.objects.filter(
                image='posts/small.gif'
            ).exists()
        )

    def test_guest_create_post(self):
        post_create = Post.objects.count()
        form_data = {
            'text': 'Текст от гостя',
            'group': self.group.id,
            'image': self.uploaded,
        }

        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), post_create)

    def test_post_edit_form(self):
        group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2'
        )
        post_create = Post.objects.count()
        form_data = {
            'text': 'Пост изменён',
            'group': group_2.id,
            'image': self.uploaded,
        }
        response = self.authorized_client.post(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        edited_post = Post.objects.latest('pk')

        # self.assertRedirects(response, reverse(
        #     'posts:post_detail', kwargs={'post_id': self.post.id})
        # )
        self.assertEqual(Post.objects.count(), post_create)
        self.assertEqual(edited_post.author, self.post.author)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group_id, form_data['group'])
        self.assertTrue(
            Post.objects.filter(
                image='posts/small.gif'
            ).exists()
        )

    def test_guest_post_edit(self):
        group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2'
        )

        form_data = {
            'text': 'Текст от анонима',
            'group': group_2.id,
            'image': self.uploaded,
        }

        self.guest_client.post(
            reverse('posts:post_edit', kwargs={"post_id": self.post.pk}),
            data=form_data,
            follow=True
        )
        edited_post = Post.objects.latest('pk')

        self.assertEqual(self.post.author, edited_post.author)
        self.assertEqual(self.post.text, edited_post.text)
        self.assertEqual(self.post.group, edited_post.group)

    def test_authorized_client_noauthor_post_edit(self):
        group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2'
        )
        form_data = {
            'text': 'Текст от не автора',
            'group': group_2.id,
            'image': self.uploaded,
        }

        self.authorized_client_noauthor.post(
            reverse(
                'posts:post_edit', kwargs={"post_id": self.post.pk}
            ),
            data=form_data,
            follow=True
        )
        edited_post = Post.objects.latest('pk')

        self.assertEqual(self.post.author, edited_post.author)
        self.assertEqual(self.post.text, edited_post.text)
        self.assertEqual(self.post.group, edited_post.group)
