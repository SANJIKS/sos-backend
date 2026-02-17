from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import DigitalCampaign, CampaignMetric

User = get_user_model()


class CampaignMetricSerializer(serializers.ModelSerializer):
    """Сериализатор для метрик кампаний"""
    
    class Meta:
        model = CampaignMetric
        fields = [
            'id', 'metric_type', 'name', 'value', 'unit',
            'date_recorded', 'notes', 'created_at'
        ]


class DigitalCampaignListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка цифровых кампаний"""
    progress_percentage = serializers.ReadOnlyField()
    budget_utilization = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    
    class Meta:
        model = DigitalCampaign
        fields = [
            'uuid', 'title', 'slug', 'short_description',
            'campaign_type', 'status', 'impact_level',
            'start_date', 'end_date', 'progress_percentage',
            'budget_planned', 'budget_spent', 'budget_utilization',
            'website_visits', 'social_media_reach', 'engagement_rate',
            'conversion_rate', 'is_featured', 'is_public',
            'is_active', 'created_by_name', 'created_at'
        ]


class DigitalCampaignSerializer(serializers.ModelSerializer):
    """Полный сериализатор для цифровых кампаний"""
    progress_percentage = serializers.ReadOnlyField()
    budget_utilization = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    metrics = CampaignMetricSerializer(many=True, read_only=True)
    related_donation_campaigns = serializers.StringRelatedField(many=True, read_only=True)
    related_programs = serializers.StringRelatedField(many=True, read_only=True)
    
    class Meta:
        model = DigitalCampaign
        fields = [
            'uuid', 'title', 'slug', 'description', 'short_description',
            'campaign_type', 'status', 'impact_level',
            'start_date', 'end_date', 'planned_duration_days',
            'goal_description', 'target_audience', 'expected_impact',
            'budget_planned', 'budget_spent', 'budget_utilization',
            'main_image', 'banner_image', 'video_url',
            'website_visits', 'social_media_reach', 'engagement_rate',
            'conversion_rate', 'actual_impact', 'lessons_learned',
            'success_factors', 'challenges_faced',
            'related_donation_campaigns', 'related_programs',
            'is_featured', 'is_public', 'order',
            'progress_percentage', 'is_active',
            'created_by_name', 'metrics', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Создание кампании с привязкой к текущему пользователю"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


class DigitalCampaignStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики цифровых кампаний"""
    total_campaigns = serializers.IntegerField()
    active_campaigns = serializers.IntegerField()
    completed_campaigns = serializers.IntegerField()
    total_budget_planned = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_budget_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_website_visits = serializers.IntegerField()
    total_social_media_reach = serializers.IntegerField()
    average_engagement_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    campaigns_by_type = serializers.DictField()
    campaigns_by_status = serializers.DictField()
    campaigns_by_impact_level = serializers.DictField()
    top_performing_campaigns = DigitalCampaignListSerializer(many=True)
    recent_campaigns = DigitalCampaignListSerializer(many=True)


class CampaignMetricCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания метрик кампаний"""
    
    class Meta:
        model = CampaignMetric
        fields = [
            'metric_type', 'name', 'value', 'unit',
            'date_recorded', 'notes'
        ]

    def create(self, validated_data):
        """Создание метрики с привязкой к кампании"""
        campaign_id = self.context.get('campaign_id')
        if campaign_id:
            validated_data['campaign_id'] = campaign_id
        return super().create(validated_data)

