import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from ..models import Group, Post, Comment, Follow
from django.urls import reverse
from . import constants
from django.core.cache import cache


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Author')
        cls.user = User.objects.create_user(username='User')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            pk='1',
            author=cls.user_author,
            text='Тестовый текст',
            group=cls.group
        )
        cls.image = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='image.gif',
            content=cls.image,
            content_type='image/gif')
        cls.post_image = Post.objects.create(
            author=cls.user_author,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.user_author)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': 'test-slug'}): (
                'posts/group_list.html'),
            reverse('posts:profile', kwargs={'username': 'User'}): (
                'posts/profile.html'),
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}): (
                'posts/post_detail.html'),
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}): (
                'posts/create_post.html'),
            reverse('posts:post_create'): 'posts/create_post.html'}

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_author.get(
            reverse('post:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertEqual(response.context['post'].text, 'Тестовый текст')
        self.assertEqual(response.context['post'].author, self.post.author)
        self.assertEqual(response.context['post'].group, self.post.group)

    def test_add_comment_for_authorized_user(self):
        """После проверки формы добавляется комментарий авторизованного
        пользователя."""
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый коммент',
        }
        response = self.authorized_author.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id': self.post.pk}))
        self.assertEqual(Comment.objects.count(), comment_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='Тестовый коммент',
            ).exists()
        )

    def test_not_add_comment_for_guest(self):
        """Комментарии недоступны для неавторизованных
        пользователей."""
        form_data = {
            'text': 'Тестовый коммент',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, ('/auth/login/?next=/posts/'
                                        f'{self.post.pk}/comment/'))

    def test_post_images_correct_context(self):
        """Проверка передачи изображения в контекст."""
        response_index = self.authorized_author.get(
            reverse('post:index'))
        response_profile = self.authorized_author.get(
            reverse('post:profile', kwargs={'username':
                                            PostPagesTests.post_image.author}))
        response_group = self.authorized_author.get(
            reverse('post:group_list',
                    kwargs={'slug':
                            PostPagesTests.post_image.group.slug}))
        response_delail = self.authorized_author.get(
            reverse('post:post_detail',
                    kwargs={'post_id':
                            PostPagesTests.post_image.pk}))
        last_post = Post.objects.latest('pub_date')
        context_index_image = (response_index.context[
            'page_obj'][constants.SECTION].image.name)
        context_profile_image = (response_profile.context[
            'page_obj'][constants.SECTION].image.name)
        context_group_image = (response_group.context[
            'page_obj'][constants.SECTION].image.name)
        context_delail_image = (response_delail.context[
            'post'].image.name)
        self.assertEqual(last_post.image.name, context_index_image)
        self.assertEqual(last_post.image.name, context_profile_image)
        self.assertEqual(last_post.image.name, context_group_image)
        self.assertEqual(last_post.image.name, context_delail_image)

    def test_post_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_author.get(
            reverse('post:group_list', kwargs={'slug': 'test-slug'}))
        first_object = response.context['page_obj'][constants.SECTION]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(post_author_0, self.post.author)
        self.assertEqual(post_group_0, self.post.group)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_author.get(
            reverse('post:index'))
        first_object = response.context['page_obj'][constants.SECTION]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(post_author_0, self.post.author)
        self.assertEqual(post_group_0, self.post.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_author.get(
            reverse('post:profile', kwargs={'username': 'Author'}))
        first_object = response.context['page_obj'][constants.SECTION]
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        self.assertEqual(post_text_0, 'Тестовый текст')
        self.assertEqual(post_author_0, self.post.author)
        self.assertEqual(post_group_0, self.post.group)

    def test_check_post_in_group(self):
        """"Проверка поста на попадание в другую группу"""
        group2 = Group.objects.create(
            title='Тестовая новая группа2',
            slug='!')
        self.assertNotEqual(self.post.group, group2)

    def test_check_post_in_pages(self):
        """"Проверка поста на попадание в group_list, index, profile"""
        user2 = User.objects.create_user(username='author2')
        group2 = Group.objects.create(
            title='title test2',
            slug='test-slig2'
        )
        post2 = Post.objects.create(
            author=user2,
            text='text post2',
            group=group2
        )
        client2 = Client()
        client2.force_login(user2)
        response_1 = client2.get(reverse('post:group_list',
                                         kwargs={'slug': group2.slug}))
        response_2 = client2.get(reverse('post:index'))
        response_3 = client2.get(reverse('posts:profile',
                                         kwargs={'username': 'author2'}))
        self.assertIn(post2, response_1.context['page_obj'])
        self.assertIn(post2, response_2.context['page_obj'])
        self.assertIn(post2, response_3.context['page_obj'])

    def test_comment_in_post_detail(self):
        """Проверка отображения комментария в post_detail."""
        response = self.guest_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertIn('comments', response.context)

    def test_cache_index(self):
        """Проверка кэша на главной странице."""
        response = self.authorized_author.get(reverse('posts:index'))
        countent_1 = response.content
        Post.objects.create(
            text='Тестовый текст для кэша',
            author=self.user_author
        )
        response_creat_post = self.authorized_author.get(
            reverse('posts:index')
        )
        self.assertEqual(countent_1, response_creat_post.content)
        cache.clear()
        new_response = self.authorized_author.get(
            reverse('posts:index')
        )
        new_countent_posts = new_response.content
        self.assertNotEqual(
            countent_1, new_countent_posts
        )

    def test_unexisting_page_castom(self):
        """Запрос к несуществующей странице вернет кастомный шаблон 404."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertTemplateUsed(response, 'core/404.html')


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.authorized_author = Client()
        cls.author = User.objects.create_user(username='Author')
        cls.user = User.objects.create_user(username='User')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            pk=constants.ANY
        )
        for num in range(0, 12):
            Post.objects.create(text=f'{num}Пост пагинация',
                                author=cls.user,
                                group=cls.group
                                )
        cache.clear()

    def test_first_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']),
                         constants.TEN_POSTS)

    def test_second_page_contains_three_records(self):
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         constants.THREE_POSTS)

    def test_first1_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': 'test-slug'}))
        self.assertEqual(len(response.context['page_obj']),
                         constants.TEN_POSTS)

    def test_second1_page_contains_three_records(self):
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug':
                                                   'test-slug'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         constants.THREE_POSTS)

    def test_first2_page_contains_ten_records(self):
        response = self.client.get(reverse('posts:profile',
                                           kwargs={'username': 'User'}))
        self.assertEqual(len(response.context['page_obj']),
                         constants.TEN_POSTS)

    def test_second2_page_contains_three_records(self):
        response = self.client.get(reverse('posts:profile',
                                           kwargs={'username':
                                                   'User'}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']),
                         constants.THREE_POSTS)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_follower = User.objects.create_user(username='user1')
        cls.user_following = User.objects.create_user(username='user2')
        cls.user_notfollower = User.objects.create_user(username='user3')
        cls.post = Post.objects.create(
            author=cls.user_following,
            text='Тестовый текст для подписок',
        )

    def setUp(self):
        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.client_auth_notfollower = Client()
        self.client_auth_follower.force_login(self.user_follower)
        self.client_auth_following.force_login(self.user_following)
        self.client_auth_notfollower.force_login(self.user_notfollower)
        cache.clear()

    def test_profile_follow(self):
        """"Авторизованный пользователь может
        подписываться на других пользователей."""
        self.client_auth_follower.get(
            f'/profile/{self.user_following.username}/follow/')
        count = Follow.objects.all().count()
        self.assertEqual(count, 1)

    def test_profile_unfollow(self):
        """"Авторизованный пользователь может
        удалять из подписок других пользователей."""
        self.client_auth_follower.get(
            f'/profile/{self.user_following.username}/unfollow/')
        count = Follow.objects.all().count()
        self.assertEqual(count, 0)

    def test_post_follow(self):
        """"Пост автора передается в ленту
        подписчика."""
        self.new_post_following = Post.objects.create(
            text='Тестовый текст follow',
            author=self.user_following,
        )
        Follow.objects.create(
            author=self.user_following,
            user=self.user_follower
        )
        response = self.client_auth_follower.get(reverse('posts:follow_index'))
        self.assertIn(self.new_post_following, response.context['page_obj'])

    def test_post_not_follower(self):
        """"Пост автора не передается в ленту
        не подписчика."""
        self.new_post_following2 = Post.objects.create(
            text='Тестовый текст follow2',
            author=self.user_following,
        )
        response = self.client_auth_notfollower.get(reverse(
            'posts:follow_index'))
        self.assertNotIn(self.new_post_following2,
                         response.context['page_obj'])
