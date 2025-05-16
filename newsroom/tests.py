from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Story, Category, Tag
from accounts.models import RadioStation, CustomUser
from django.urls import reverse
from django.core.exceptions import ValidationError
import uuid

# Create your tests here.

class StoryTests(TestCase):
    def setUp(self):
        # Create test radio station
        self.radio_station = RadioStation.objects.create(
            name='Test Radio',
            province=RadioStation.Province.GAUTENG
        )
        
        # Create test users
        self.author = get_user_model().objects.create_user(
            email='author@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Author',
            user_type='STAFF',
            staff_role='JOURNALIST'
        )
        self.editor = get_user_model().objects.create_user(
            email='editor@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Editor',
            user_type='STAFF',
            staff_role='EDITOR'
        )
        self.reviewer = get_user_model().objects.create_user(
            email='reviewer@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Reviewer',
            user_type='STAFF',
            staff_role='SUB_EDITOR'
        )
        
        # Create test category
        self.category = Category.objects.create(
            name='Test Category',
            content_type='NEWS_STORIES',
            level=2
        )
        
        # Create test tags
        self.tag1 = Tag.objects.create(name='Test Tag 1')
        self.tag2 = Tag.objects.create(name='Test Tag 2')

    def test_basic_story_creation(self):
        """Test that a story can be created with basic required fields"""
        story = Story.objects.create(
            title='Test Story',
            content='This is a test story content',
            author=self.author,
            category=self.category
        )
        
        self.assertEqual(story.title, 'Test Story')
        self.assertEqual(story.content, 'This is a test story content')
        self.assertEqual(story.author, self.author)
        self.assertEqual(story.category, self.category)
        self.assertEqual(story.status, 'DRAFT')  # Default status
        self.assertEqual(story.language, 'ENGLISH')  # Default language
        self.assertEqual(story.religion_classification, 'GENERAL')  # Default religion

    def test_story_with_all_fields(self):
        """Test story creation with all optional fields"""
        story = Story.objects.create(
            title='Complete Test Story',
            content='This is a complete test story',
            author=self.author,
            category=self.category,
            editor=self.editor,
            reviewer=self.reviewer,
            status='REVIEW',
            religion_classification='CHRISTIAN',
            language='AFRIKAANS',
            is_translation=False
        )
        
        # Add tags
        story.tags.add(self.tag1, self.tag2)
        
        # Verify all fields
        self.assertEqual(story.title, 'Complete Test Story')
        self.assertEqual(story.editor, self.editor)
        self.assertEqual(story.reviewer, self.reviewer)
        self.assertEqual(story.status, 'REVIEW')
        self.assertEqual(story.religion_classification, 'CHRISTIAN')
        self.assertEqual(story.language, 'AFRIKAANS')
        self.assertEqual(story.is_translation, False)
        self.assertEqual(story.tags.count(), 2)
        self.assertIn(self.tag1, story.tags.all())
        self.assertIn(self.tag2, story.tags.all())

    def test_story_slug_generation(self):
        """Test that slugs are automatically generated and unique"""
        # Create first story
        story1 = Story.objects.create(
            title='Test Story',
            content='First story',
            author=self.author,
            category=self.category
        )
        
        # Create second story with same title
        story2 = Story.objects.create(
            title='Test Story',
            content='Second story',
            author=self.author,
            category=self.category
        )
        
        self.assertEqual(story1.slug, 'test-story')
        self.assertEqual(story2.slug, 'test-story-1')

    def test_story_translation(self):
        """Test story translation functionality"""
        # Create original story
        original_story = Story.objects.create(
            title='Original Story',
            content='Original content',
            author=self.author,
            category=self.category,
            language='ENGLISH'
        )
        
        # Create translation
        translation = Story.objects.create(
            title='Translated Story',
            content='Translated content',
            author=self.author,
            category=self.category,
            language='AFRIKAANS',
            translation_of=original_story
        )
        
        self.assertTrue(translation.is_translation)
        self.assertEqual(translation.translation_of, original_story)
        self.assertEqual(original_story.translations.count(), 1)
        self.assertEqual(original_story.translations.first(), translation)

    def test_story_metrics(self):
        """Test story view and download count functionality"""
        story = Story.objects.create(
            title='Metrics Test Story',
            content='Test content',
            author=self.author,
            category=self.category
        )
        
        # Initial counts should be 0
        self.assertEqual(story.view_count, 0)
        self.assertEqual(story.download_count, 0)
        
        # Update counts
        story.view_count = 5
        story.download_count = 2
        story.save()
        
        # Verify updated counts
        updated_story = Story.objects.get(id=story.id)
        self.assertEqual(updated_story.view_count, 5)
        self.assertEqual(updated_story.download_count, 2)

    def test_story_timestamps(self):
        """Test story timestamp functionality"""
        story = Story.objects.create(
            title='Timestamp Test Story',
            content='Test content',
            author=self.author,
            category=self.category
        )
        
        # Check created_at and updated_at
        self.assertIsNotNone(story.created_at)
        self.assertIsNotNone(story.updated_at)
        self.assertIsNone(story.published_at)  # Should be None initially
        
        # Update story and check updated_at changes
        old_updated_at = story.updated_at
        story.title = 'Updated Title'
        story.save()
        
        updated_story = Story.objects.get(id=story.id)
        self.assertGreater(updated_story.updated_at, old_updated_at)

class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Test Category",
            content_type=Category.TYPE_CHOICES[0][0],
            level=Category.LEVEL_CHOICES[0][0]
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, "Test Category")
        self.assertEqual(self.category.content_type, Category.TYPE_CHOICES[0][0])
        self.assertEqual(self.category.level, Category.LEVEL_CHOICES[0][0])
        self.assertTrue(self.category.is_active)

    def test_category_str(self):
        self.assertEqual(str(self.category), "Test Category")

    def test_category_hierarchy(self):
        child = Category.objects.create(
            name="Child Category",
            content_type=Category.TYPE_CHOICES[0][0],
            level=Category.LEVEL_CHOICES[1][0],
            parent=self.category
        )
        self.assertEqual(child.parent, self.category)
        self.assertEqual(self.category.children.first(), child)

class StoryModelTest(TestCase):
    def setUp(self):
        self.station = RadioStation.objects.create(
            name="Test Radio",
            province=RadioStation.Province.GAUTENG,
            city="Johannesburg",
            address="123 Test St",
            contact_number="+27123456789",
            email="test@radio.com"
        )
        self.author = CustomUser.objects.create_user(
            email="author@test.com",
            password="testpass123",
            user_type=CustomUser.UserType.STAFF,
            staff_role=CustomUser.StaffRole.JOURNALIST
        )
        self.category = Category.objects.create(
            name="Test Category",
            content_type=Category.TYPE_CHOICES[0][0],
            level=Category.LEVEL_CHOICES[0][0]
        )
        self.story = Story.objects.create(
            title="Test Story",
            content="Test content",
            category=self.category,
            author=self.author,
            status=Story.STATUS_CHOICES[0][0]
        )

    def test_story_creation(self):
        self.assertEqual(self.story.title, "Test Story")
        self.assertEqual(self.story.content, "Test content")
        self.assertEqual(self.story.category, self.category)
        self.assertEqual(self.story.author, self.author)
        self.assertEqual(self.story.status, Story.STATUS_CHOICES[0][0])
        self.assertEqual(self.story.view_count, 0)

    def test_story_str(self):
        self.assertEqual(str(self.story), "Test Story")

    def test_story_publish(self):
        self.story.publish(self.author)
        self.assertEqual(self.story.status, 'PUBLISHED')
        self.assertIsNotNone(self.story.published_at)

    def test_story_permissions(self):
        # Test author permissions
        self.assertTrue(self.story.can_be_edited_by(self.author))
        
        # Create another user
        other_user = CustomUser.objects.create_user(
            email="other@test.com",
            password="testpass123",
            user_type=CustomUser.UserType.STAFF,
            staff_role=CustomUser.StaffRole.JOURNALIST
        )
        self.assertFalse(self.story.can_be_edited_by(other_user))

class AudioClipModelTest(TestCase):
    def setUp(self):
        self.station = RadioStation.objects.create(
            name="Test Radio",
            province=RadioStation.Province.GAUTENG,
            city="Johannesburg",
            address="123 Test St",
            contact_number="+27123456789",
            email="test@radio.com"
        )
        self.author = CustomUser.objects.create_user(
            email="author@test.com",
            password="testpass123",
            user_type=CustomUser.UserType.STAFF,
            staff_role=CustomUser.StaffRole.JOURNALIST
        )
        self.category = Category.objects.create(
            name="Test Category",
            content_type=Category.TYPE_CHOICES[0][0],
            level=Category.LEVEL_CHOICES[0][0]
        )
        self.story = Story.objects.create(
            title="Test Story",
            content="Test content",
            category=self.category,
            author=self.author,
            status=Story.STATUS_CHOICES[0][0]
        )

    def test_audio_clip_creation(self):
        clip = AudioClip.objects.create(
            title="Test Clip",
            description="Test description",
            story=self.story,
            uploaded_by=self.author
        )
        self.assertEqual(clip.title, "Test Clip")
        self.assertEqual(clip.story, self.story)
        self.assertEqual(clip.uploaded_by, self.author)

class TaskModelTest(TestCase):
    def setUp(self):
        self.station = RadioStation.objects.create(
            name="Test Radio",
            province=RadioStation.Province.GAUTENG,
            city="Johannesburg",
            address="123 Test St",
            contact_number="+27123456789",
            email="test@radio.com"
        )
        self.author = CustomUser.objects.create_user(
            email="author@test.com",
            password="testpass123",
            user_type=CustomUser.UserType.STAFF,
            staff_role=CustomUser.StaffRole.JOURNALIST
        )
        self.assignee = CustomUser.objects.create_user(
            email="assignee@test.com",
            password="testpass123",
            user_type=CustomUser.UserType.STAFF,
            staff_role=CustomUser.StaffRole.JOURNALIST
        )
        self.category = Category.objects.create(
            name="Test Category",
            content_type=Category.TYPE_CHOICES[0][0],
            level=Category.LEVEL_CHOICES[0][0]
        )
        self.story = Story.objects.create(
            title="Test Story",
            content="Test content",
            category=self.category,
            author=self.author,
            status=Story.STATUS_CHOICES[0][0]
        )

    def test_task_creation(self):
        task = Task.objects.create(
            title="Test Task",
            description="Test description",
            task_type=Task.TYPE_CHOICES[0][0],
            priority=Task.PRIORITY_CHOICES[0][0],
            assigned_by=self.author,
            assigned_to=self.assignee,
            related_story=self.story
        )
        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.assigned_by, self.author)
        self.assertEqual(task.assigned_to, self.assignee)
        self.assertEqual(task.related_story, self.story)
        self.assertEqual(task.status, Task.STATUS_CHOICES[0][0])

    def test_task_completion(self):
        task = Task.objects.create(
            title="Test Task",
            description="Test description",
            task_type=Task.TYPE_CHOICES[0][0],
            priority=Task.PRIORITY_CHOICES[0][0],
            assigned_by=self.author,
            assigned_to=self.assignee,
            related_story=self.story
        )
        task.complete()
        self.assertEqual(task.status, 'COMPLETED')
        self.assertIsNotNone(task.completed_at)

class NewsroomViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.station = RadioStation.objects.create(
            name="Test Radio",
            province=RadioStation.Province.GAUTENG,
            city="Johannesburg",
            address="123 Test St",
            contact_number="+27123456789",
            email="test@radio.com"
        )
        self.author = CustomUser.objects.create_user(
            email="author@test.com",
            password="testpass123",
            user_type=CustomUser.UserType.STAFF,
            staff_role=CustomUser.StaffRole.JOURNALIST
        )
        self.category = Category.objects.create(
            name="Test Category",
            content_type=Category.TYPE_CHOICES[0][0],
            level=Category.LEVEL_CHOICES[0][0]
        )
        self.story = Story.objects.create(
            title="Test Story",
            content="Test content",
            category=self.category,
            author=self.author,
            status=Story.STATUS_CHOICES[0][0]
        )

    def test_story_list_view(self):
        self.client.login(email='author@test.com', password='testpass123')
        response = self.client.get(reverse('newsroom:story_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Story")

    def test_story_detail_view(self):
        self.client.login(email='author@test.com', password='testpass123')
        response = self.client.get(reverse('newsroom:story_detail', args=[self.story.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Story")

    def test_story_create_view(self):
        self.client.login(email='author@test.com', password='testpass123')
        response = self.client.post(reverse('newsroom:story_create'), {
            'title': 'New Story',
            'content': 'New content',
            'category': self.category.id,
            'status': Story.STATUS_CHOICES[0][0]
        })
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        self.assertTrue(Story.objects.filter(title='New Story').exists())
