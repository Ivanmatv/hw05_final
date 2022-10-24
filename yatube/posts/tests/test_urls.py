from django.test import TestCase, Client
from django.urls import reverse
from http import HTTPStatus

from posts.models import Group, Post, User


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Ivan')
        cls.user = User.objects.create_user(username='Igor')
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug="test-slug",
            description="Тестовое описание",
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовый пост',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем второй клиент
        self.authorized_client_author = Client()
        # Авторизуем пользователя
        self.authorized_client_author.force_login(self.user_author)
        # Создаём третий клиент
        self.authorized_client = Client()
        # Авторизуем второго пользователя
        self.authorized_client.force_login(self.user)

    # Проверка доступа к общедоступным страницам
    def test_urls_exist_at_desired_locations(self):
        """Страницы доступны по указанным адресам для всех пользователей."""
        url_response_status_code = {
            '': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/Ivan/': HTTPStatus.OK,
            f'/posts/{self.post.pk}/': HTTPStatus.OK,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
        }

        for url, status_code in url_response_status_code.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status_code)

    # Проверяем доступность страниц для авторизованного пользователя
    def test_post_create_url_exists_at_desired_location(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client_author.get(
            reverse('posts:post_create')
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_correct_template(self):
        templates_pages_names = {
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    # Проверяем доступность страницы редактирования автору
    def test_post_edit_url_exists_at_desired_location(self):
        """Страница /posts/<post_id>/edit/ доступна автору публикации."""
        response = self.authorized_client_author.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    # Проверка редиректов для неавторизованного пользователя
    def test_urls_redirect_anonymous_on_login(self):
        """Страница перенаправит анонимного пользователя на страницу логина."""
        url_redirect_to_url = {
            f'{reverse("users:login")}?next={reverse("posts:post_create")}':
            '/create/',
            f'{reverse("users:login")}?next='
            f'{reverse("posts:post_edit", kwargs={"post_id": self.post.pk})}':
            f'/posts/{self.post.pk}/edit/',
        }
        for redirect, url in url_redirect_to_url.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url, follow=True)
                self.assertRedirects(response, redirect)

    # Проверка авторизованного пользователя, но не автора поста
    def test_urls_redirect_another_authorized_client_(self):
        """Страница перенаправит авторизованнного пользователя,"""
        """но не автора поста"""
        response = self.authorized_client.get(
            reverse("posts:post_edit", kwargs={"post_id": self.post.pk})
        )
        self.assertRedirects(response, f'/posts/{self.post.pk}/')

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/Ivan/': 'posts/profile.html',
            f'/posts/{self.post.pk}/': 'posts/post_detail.html',
            f'/posts/{self.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client_author.get(url)
                self.assertTemplateUsed(response, template)
