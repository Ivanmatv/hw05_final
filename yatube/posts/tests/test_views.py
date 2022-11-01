import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django import forms
from django.core.paginator import Page
from django.core.cache import cache
from http import HTTPStatus

from posts.models import Group, Post, User, Comment, Follow

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Ivan')
        cls.new_author = User.objects.create_user(username='Igor')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаём гостя
        self.guest_client = Client()
        # Создаём клиента
        self.authorized_client = Client()
        # Авторизуем клиента
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': 'Ivan'}):
            'posts/profile.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
            'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_page_show_correct_context(self):
        """Проверка контекста главной страницы"""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)
        self.assertIsInstance(response.context['page_obj'], Page)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_group_posts_page_show_correct_context(self):
        """Проверка контекста группы"""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': 'test-slug'})
        )
        self.assertIn('group', response.context)
        self.assertIsInstance(response.context['group'], Group)
        self.assertEqual(response.context['group'], self.group)
        self.assertIn('page_obj', response.context)
        self.assertIsInstance(response.context['page_obj'], Page)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_profile_page_show_correct_context(self):
        """Проверка контекста автора"""
        response = self.authorized_client.get(
            reverse(
                'posts:profile', kwargs={'username': 'Ivan'}
            )
        )
        self.assertIn('author', response.context)
        self.assertEqual(response.context['author'], self.user)
        self.assertIn('page_obj', response.context)
        self.assertIsInstance(response.context['page_obj'], Page)
        self.assertEqual(len(response.context['page_obj']), 1)
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_post_detail_page_show_correct_context(self):
        """Проверка контекста поста"""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.assertIn('post', response.context)
        self.assertEqual(
            response.context['post'], PostPagesTests.post
        )

    def test_post_edit_show_correct_context(self):
        """Проверка редактирования контекста поста"""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context(self):
        """Проверка создания контекста нового поста"""
        response = self.authorized_client.get(
            reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_add_comment_show_correct_context(self):
        """Проверка добавления комментария"""
        post = Post.objects.first()
        comment = Comment.objects.create(
            text='Новый комментарий',
            post=post,
            author=self.user,
        )
        response = self.guest_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': post.id})
        )
        comment_response = response.context['comments'].first()
        self.assertIn('comments', response.context)
        self.assertEqual(comment_response.text, comment.text)
        self.assertEqual(comment_response.author, comment.author)

    def test_cache_index(self):
        """Проверка хранения и очищения кэша для index."""
        cache.clear()
        response_1 = self.authorized_client.get(reverse('posts:index'))
        cache_check = response_1.content
        post = Post.objects.get(id=1)
        post.delete()
        response_2 = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(response_2.content, cache_check)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(response_3.content, cache_check)

    def test_paginator(self):
        RANGE: int = 11
        RANGE_FIRST_PG: int = 10
        RANGE_SECOND_PG: int = 2
        for post in range(RANGE):
            post = Post.objects.create(
                text=f'Тестовый текст {post}',
                author=self.user,
                group=self.group,
            )
        posturls_posts_page = [('', RANGE_FIRST_PG),
                               ('?page=2', RANGE_SECOND_PG)]
        templates = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for postsurls, posts in posturls_posts_page:
            for page in templates:
                with self.subTest(page=page):
                    response = self.authorized_client.get(page + postsurls)
                    self.assertEqual(len(response.context['page_obj']), posts)

    def test_page_not_found(self):
        response = self.client.get('/nonexist-page/')
        self.assertTemplateUsed(response, 'core/404.html')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_follow(self):
        """Проверка подписки на автора """
        follower_count = Follow.objects.count()
        self.authorized_client.get(reverse(
            'posts:profile_follow',
            kwargs={'username': self.new_author}))
        follow_obj = Follow.objects.first()
        self.assertEqual(Follow.objects.count(), follower_count + 1)
        self.assertEqual(follow_obj.author, self.new_author)
        self.assertEqual(follow_obj.user, self.user)

    def test_unfollow(self):
        """Проверка отписки на автора """
        self.authorized_client.get(reverse(
            'posts:profile_unfollow',
            kwargs={'username': self.new_author}))
        self.assertEqual(Follow.objects.count(), 0)

    def test_following_users_corect_content(self):
        """Новая запись автора появляется в ленте подписчика
        и не появляется в ленте тех, кто не подписан
        """
        another_user = User.objects.create_user(username='Fedya')
        another_client = Client()
        another_client.force_login(another_user)
        Follow.objects.create(
            user=self.user,
            author=self.new_author
        )
        post = Post.objects.create(
            text='Пост подписки',
            author=self.new_author,
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response.context['page_obj'][0], post)
        response_another = another_client.get(reverse('posts:follow_index'))
        self.assertNotIn(post, response_another.context['page_obj'])
