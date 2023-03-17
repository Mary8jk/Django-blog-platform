from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from ..models import Group, Post
from http import HTTPStatus
from django.core.cache import cache


User = get_user_model()


class GroupURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='user')
        cls.user2 = User.objects.create_user(username='user2')
        cls.user_client = Client()
        cls.user_client.force_login(cls.user2)
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            author=cls.user2,
            text='Тестовый текст',
            group=cls.group,
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_home_url_exists_at_desired_location(self):
        """Страница / доступна любому пользователю."""
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_group_list_url_exists_at_desired_location(self):
        """Страница group/<test-slug>/ доступна любому пользователю."""
        response = self.guest_client.get('/group/test-slug/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_profile_url_exists_at_desired_location(self):
        """Страница profile/<str:username>/ доступна любому пользователю."""
        response = self.guest_client.get('/profile/user/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_detail_url_exists_at_desired_location(self):
        """Страница posts/<int:post_id>/ доступна любому пользователю."""
        response = self.guest_client.get('/posts/1/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unexisting_page_url_exists_at_desired_location(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_create_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /create/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/create/'
        )

    def test_post_edit_url_redirect_anonymous_on_admin_login(self):
        """Страница по адресу /post/1/edit/ перенаправит анонимного
        пользователя на страницу логина.
        """
        response = self.guest_client.get('/posts/1/edit/', follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/posts/1/edit/'
        )

    def test_post_edit_url_redirect_location_authorized(self):
        """Страница по адресу /post/1/edit/ оставит авторизованного
        пользователя на этой же странице.
        """
        response = self.authorized_client.get('/posts/1/edit/', follow=True)
        self.assertRedirects(
            response, '/posts/1/'
        )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            (f'/group/{self.group.slug}/'): 'posts/group_list.html',
            (f'/profile/{self.user.username}/'): 'posts/profile.html',
            (f'/posts/{self.post.id}/'): 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            (f'/posts/{self.post.id}/edit/'): 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.user_client.get(url)
                self.assertTemplateUsed(response, template)
