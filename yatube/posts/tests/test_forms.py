import shutil
import tempfile

from django.contrib.auth import get_user_model
from posts.forms import PostForm
from posts.models import Post, Group
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestAuthor')
        cls.group = Group.objects.create(
            title='Теcтовый заголовок',
            slug='test-slug'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostCreateFormTests.user)
        cache.clear()

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст2',
            'group': PostCreateFormTests.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username':
                            PostCreateFormTests.post.author.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст2',
                group=PostCreateFormTests.group,
                author=PostCreateFormTests.post.author
            ).exists()
        )

    def test_edit_post(self):
        """Редактированный пост сохраняется в БД с post_id."""
        posts_count = Post.objects.count()
        self.assertEqual(PostCreateFormTests.post.group.id, self.post.id)
        form_data = {
            'text': 'Тестовый текст3',
            'group': PostCreateFormTests.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': PostCreateFormTests.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response,
                             reverse('posts:post_detail',
                                     kwargs={'post_id':
                                             PostCreateFormTests.post.pk}))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст3',
                author=PostCreateFormTests.user,
                group=PostCreateFormTests.group
            ).exists()
        )

    def test_image_post(self):
        """Валидная форма создает запись с изображением в Post."""
        posts_count = Post.objects.count()
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
            content_type='image/gif')

        form_data = {
            'text': 'Тестовый текст2',
            'group': PostCreateFormTests.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username':
                            PostCreateFormTests.post.author.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст2',
                group=PostCreateFormTests.group,
                image='posts/small.gif'
            ).exists()
        )
