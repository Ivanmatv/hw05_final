import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from http import HTTPStatus

from posts.models import Group, Post, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivan')
        cls.user_noauthor = User.objects.create_user(username='Igor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            text='Текст комментария',
            post=cls.post,
            author=cls.user_noauthor,
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
        """Авторизованный пользователь создаёт пост"""
        post_create = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        created_post = Post.objects.latest('pk')

        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': created_post.author})
        )
        self.assertEqual(Post.objects.count(), post_create + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(created_post.author, self.post.author)
        self.assertEqual(created_post.text, form_data['text'])
        self.assertEqual(created_post.group_id, form_data['group'])
        self.assertEqual(
            created_post.image.name, 'posts/' + form_data['image'].name
        )

    def test_guest_create_post(self):
        """Гость создаёт пост"""
        post_create = Post.objects.count()
        form_data = {
            'text': 'Текст от гостя',
            'group': self.group.id,
        }

        self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), post_create)

    def test_post_edit_form(self):
        """Авторизованный пользователь редактирует пост"""
        group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2'
        )
        post_create = Post.objects.count()
        form_data = {
            'text': 'Пост изменён',
            'group': group_2.id,
        }
        response = self.authorized_client.post(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        edited_post = Post.objects.latest('pk')

        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Post.objects.count(), post_create)
        self.assertEqual(edited_post.author, self.post.author)
        self.assertEqual(edited_post.text, form_data['text'])
        self.assertEqual(edited_post.group_id, form_data['group'])

    def test_guest_post_edit(self):
        """Гость редактирует пост"""
        group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2'
        )

        form_data = {
            'text': 'Текст от анонима',
            'group': group_2.id,
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
        """Авторизованный пользователь, но не автор поста редактирует пост"""
        group_2 = Group.objects.create(
            title='Тестовая группа 2',
            slug='test-slug2',
            description='Тестовое описание 2'
        )
        form_data = {
            'text': 'Текст от не автора',
            'group': group_2.id,
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

    def test_add_comment_authorized_client(self):
        """Комментирует авторизованный пользователь"""
        comment_create = Comment.objects.count()
        form_data = {
            'text': 'Текст комментария',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        created_comment = Comment.objects.latest('pk')
        self.assertEqual(Comment.objects.count(), comment_create + 1)
        self.assertRedirects(response, reverse(
            'posts:post_detail',
            kwargs={'post_id': self.post.id}
        )
        )
        self.assertEqual(created_comment.text, form_data['text'])
        self.assertEqual(created_comment.author, self.post.author)
        self.assertEqual(created_comment.post, self.post)

    def test_add_comment_guest_client(self):
        """Комментирует гость"""
        comment_create = Comment.objects.count()
        form_data = {
            'text': 'Новый комментарий',
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_create)
