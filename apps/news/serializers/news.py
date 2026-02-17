from rest_framework import serializers
from django.utils import timezone
from apps.news.models import News, NewsCategory, NewsTag
from apps.news.models.news import NewsImage
from apps.partners.mixins import BuildFullUrlToImage
from apps.common.serializers.localization import LocalizedSerializerMixin, LocalizedCharField, LocalizedTextField


class NewsImageSerializer(serializers.ModelSerializer, BuildFullUrlToImage):
    """Сериализатор для изображений новости"""
    image = serializers.SerializerMethodField()

    class Meta:
        model = NewsImage
        fields = ['image', 'caption', 'is_main']

    def get_image(self, obj):
        return self.get_full_url_to_image(obj.image)

class NewsTagSerializer(serializers.ModelSerializer, LocalizedSerializerMixin):
    """Сериализатор для тегов новостей"""
    name = LocalizedCharField(field_name='name')
    
    class Meta:
        model = NewsTag
        fields = ['uuid', 'name', 'slug', 'color', 'is_active', 'created_at']
        read_only_fields = ['uuid', 'slug', 'created_at']


class NewsCategorySerializer(serializers.ModelSerializer, LocalizedSerializerMixin):
    """Сериализатор для категорий новостей"""
    name = LocalizedCharField(field_name='name')
    description = LocalizedTextField(field_name='description')
    
    # news_count = serializers.SerializerMethodField()
    
    class Meta:
        model = NewsCategory
        fields = [
            'uuid', 'name', 'slug', 'description', 'color', 'icon', 'is_active', 
            'sort_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'slug', 'created_at', 'updated_at']
    
    # def get_news_count(self, obj):
    #     """Количество новостей в категории"""
    #     return obj.news.filter(status=News.Status.PUBLISHED).count()


class NewsListSerializer(serializers.ModelSerializer, BuildFullUrlToImage, LocalizedSerializerMixin):
    """Сериализатор для списка новостей (краткая информация)"""
    title = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    category = NewsCategorySerializer(read_only=True)
    tags = NewsTagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    reading_time = serializers.SerializerMethodField()
    images = NewsImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'uuid', 'title', 'slug', 'excerpt', 'images', 'video_url', 'category', 'tags',
            'author_name', 'status', 'published_at',
            'is_featured', 'is_pinned', 'views_count',
            'reading_time', 'created_at', 'updated_at'
        ]
    
    def get_title(self, obj):
        """Получить локализованный заголовок"""
        return self.get_localized_field(obj, 'title')
    
    def get_excerpt(self, obj):
        """Получить локализованное краткое описание"""
        return self.get_localized_field(obj, 'excerpt')
    
    def get_reading_time(self, obj):
        """Примерное время чтения (слов в минуту)"""
        content = self.get_localized_field(obj, 'content')
        if content:
            word_count = len(content.split())
            return max(1, word_count // 200)  # 200 слов в минуту
        return 1



class NewsDetailSerializer(serializers.ModelSerializer, BuildFullUrlToImage, LocalizedSerializerMixin):
    """Сериализатор для детальной информации о новости"""
    title = LocalizedCharField(field_name='title')
    content = LocalizedTextField(field_name='content')
    excerpt = LocalizedTextField(field_name='excerpt')
    category = NewsCategorySerializer(read_only=True)
    tags = NewsTagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    reading_time = serializers.SerializerMethodField()
    related_news = serializers.SerializerMethodField()
    images = NewsImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'uuid', 'title', 'slug', 'content', 'excerpt',
            'images',
            'video_url', 'category', 'tags',
            'author_name', 'status', 'published_at',
            'is_featured', 'is_pinned', 'views_count',
            'meta_title', 'meta_description', 'meta_keywords',
            'social_title', 'social_description', 'social_image',
            'reading_time', 'related_news', 'created_at', 'updated_at'
        ]
    
    def get_reading_time(self, obj):
        """Примерное время чтения"""
        content = self.get_localized_field(obj, 'content')
        if content:
            word_count = len(content.split())
            return max(1, word_count // 200)
        return 1
    
    def get_related_news(self, obj):
        """Похожие новости"""
        related = News.objects.filter(
            status=News.Status.PUBLISHED,
            category=obj.category
        ).exclude(uuid=obj.uuid)[:3]
        
        return NewsListSerializer(related, many=True, context=self.context).data


class NewsSerializer(serializers.ModelSerializer, BuildFullUrlToImage, LocalizedSerializerMixin):
    """Основной сериализатор для создания/редактирования новостей"""
    title = LocalizedCharField(field_name='title')
    content = LocalizedTextField(field_name='content')
    excerpt = LocalizedTextField(field_name='excerpt')
    
    category_uuid = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    tag_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    # Read-only поля для отображения
    category = NewsCategorySerializer(read_only=True)
    tags = NewsTagSerializer(many=True, read_only=True)
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    images = NewsImageSerializer(many=True, read_only=True)
    
    class Meta:
        model = News
        fields = [
            'uuid', 'title', 'slug', 'content', 'excerpt', 'video_url',
            'images', 'category_uuid', 'category', 'tag_uuids', 'tags',
            'author_name', 'status', 'published_at',
            'is_featured', 'is_pinned', 'content_type',
            'meta_title', 'meta_description', 'meta_keywords',
            'social_title', 'social_description', 'social_image',
            'views_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'author_name', 'views_count', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # Извлекаем связанные данные
        category_uuid = validated_data.pop('category_uuid', None)
        tag_uuids = validated_data.pop('tag_uuids', [])
        
        # Устанавливаем автора
        validated_data['author'] = self.context['request'].user
        
        # Создаем новость
        news = News.objects.create(**validated_data)
        
        # Устанавливаем категорию
        if category_uuid:
            try:
                category = NewsCategory.objects.get(uuid=category_uuid)
                news.category = category
            except NewsCategory.DoesNotExist:
                pass
        
        # Устанавливаем теги
        if tag_uuids:
            tags = NewsTag.objects.filter(uuid__in=tag_uuids)
            news.tags.set(tags)
        
        news.save()
        return news
    
    def update(self, instance, validated_data):
        # Извлекаем связанные данные
        category_uuid = validated_data.pop('category_uuid', None)
        tag_uuids = validated_data.pop('tag_uuids', None)
        
        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Обновляем категорию
        if category_uuid is not None:
            if category_uuid:
                try:
                    category = NewsCategory.objects.get(uuid=category_uuid)
                    instance.category = category
                except NewsCategory.DoesNotExist:
                    pass
            else:
                instance.category = None
        
        # Обновляем теги
        if tag_uuids is not None:
            tags = NewsTag.objects.filter(uuid__in=tag_uuids)
            instance.tags.set(tags)
        
        instance.save()
        return instance
    
    def validate_published_at(self, value):
        """Валидация даты публикации"""
        if value and value > timezone.now():
            pass
        return value


class NewsStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики новостей"""
    
    total_news = serializers.IntegerField()
    published_news = serializers.IntegerField()
    draft_news = serializers.IntegerField()
    featured_news = serializers.IntegerField()
    total_views = serializers.IntegerField()
    categories_count = serializers.IntegerField()
    tags_count = serializers.IntegerField()
    news_by_category = serializers.DictField()
    popular_tags = serializers.ListField(child=serializers.DictField())
    recent_news = NewsListSerializer(many=True)