from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.donors.models import (
    F2FCoordinator, 
    F2FRegion, 
    F2FCoordinatorRegionAssignment, 
    F2FLocation
)

User = get_user_model()


class F2FRegionSerializer(serializers.ModelSerializer):
    """Сериализатор для F2F регионов"""
    
    coordinators_count = serializers.SerializerMethodField()
    locations_count = serializers.SerializerMethodField()
    
    class Meta:
        model = F2FRegion
        fields = [
            'id', 'name', 'code', 'description', 'is_active',
            'latitude', 'longitude', 'coordinators_count', 'locations_count',
            'created_at', 'updated_at'
        ]
    
    def get_coordinators_count(self, obj):
        """Количество координаторов в регионе"""
        return obj.f2fcoordinatorregionassignment_set.filter(
            coordinator__status=F2FCoordinator.Status.ACTIVE
        ).count()
    
    def get_locations_count(self, obj):
        """Количество активных локаций в регионе"""
        return obj.f2flocation_set.filter(status=F2FLocation.Status.ACTIVE).count()


class F2FLocationSerializer(serializers.ModelSerializer):
    """Сериализатор для F2F локаций"""
    
    region = F2FRegionSerializer(read_only=True)
    region_uuid = serializers.UUIDField(write_only=True)
    working_days_list = serializers.ListField(
        child=serializers.IntegerField(),
        source='get_working_days_list',
        read_only=True
    )
    registrations_count = serializers.SerializerMethodField()
    
    class Meta:
        model = F2FLocation
        fields = [
            'uuid', 'name', 'location_type', 'region', 'region_uuid',
            'address', 'latitude', 'longitude', 'status',
            'working_hours_start', 'working_hours_end', 'working_days', 'working_days_list',
            'foot_traffic_level', 'contact_person', 'contact_phone',
            'notes', 'registrations_count', 'is_active',
            'created_at', 'updated_at'
        ]
    
    def get_registrations_count(self, obj):
        """Количество регистраций в локации"""
        return obj.registrations.count()


class F2FCoordinatorRegionAssignmentSerializer(serializers.ModelSerializer):
    """Сериализатор для назначений координатора на регионы"""
    
    region = F2FRegionSerializer(read_only=True)
    
    class Meta:
        model = F2FCoordinatorRegionAssignment
        fields = [
            'id', 'region', 'assigned_date', 'is_primary', 'created_at'
        ]


class F2FCoordinatorListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка координаторов (краткая информация)"""
    
    supervisor_name = serializers.CharField(source='supervisor.full_name', read_only=True)
    regions = F2FCoordinatorRegionAssignmentSerializer(
        source='f2fcoordinatorregionassignment_set',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = F2FCoordinator
        fields = [
            'uuid', 'employee_id', 'full_name', 'phone', 'email',
            'status', 'experience_level', 'hire_date', 'supervisor_name',
            'monthly_target', 'current_month_registrations', 'total_registrations',
            'success_rate', 'target_completion_rate', 'regions',
            'last_sync', 'is_active', 'created_at'
        ]


class F2FCoordinatorDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о координаторе"""
    
    supervisor = F2FCoordinatorListSerializer(read_only=True)
    subordinates = F2FCoordinatorListSerializer(many=True, read_only=True)
    regions = F2FCoordinatorRegionAssignmentSerializer(
        source='f2fcoordinatorregionassignment_set',
        many=True,
        read_only=True
    )
    
    # Статистика
    recent_registrations = serializers.SerializerMethodField()
    monthly_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = F2FCoordinator
        fields = [
            'uuid', 'employee_id', 'full_name', 'phone', 'email', 'birth_date',
            'status', 'experience_level', 'hire_date', 'termination_date',
            'supervisor', 'subordinates', 'regions',
            'monthly_target', 'current_month_registrations', 'total_registrations',
            'success_rate', 'target_completion_rate',
            'device_id', 'last_sync', 'offline_mode_enabled',
            'recent_registrations', 'monthly_stats',
            'is_active', 'created_at', 'updated_at'
        ]
    
    def get_recent_registrations(self, obj):
        """Последние регистрации координатора"""
        from apps.donors.serializers.f2f_registration import F2FRegistrationListSerializer
        recent = obj.registrations.order_by('-registered_at')[:5]
        return F2FRegistrationListSerializer(recent, many=True).data
    
    def get_monthly_stats(self, obj):
        """Статистика за текущий месяц"""
        from django.db.models import Count, Q
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        stats = obj.registrations.filter(registered_at__gte=month_start).aggregate(
            total=Count('id'),
            confirmed=Count('id', filter=Q(status='confirmed')),
            pending=Count('id', filter=Q(status='pending')),
            rejected=Count('id', filter=Q(status='rejected'))
        )
        
        return {
            'total_registrations': stats['total'],
            'confirmed_registrations': stats['confirmed'],
            'pending_registrations': stats['pending'],
            'rejected_registrations': stats['rejected'],
            'target_progress': obj.target_completion_rate,
            'days_in_month': now.day,
            'days_remaining': (month_start.replace(month=month_start.month+1) - now).days
        }


class F2FCoordinatorSerializer(serializers.ModelSerializer):
    """Основной сериализатор для создания/редактирования координаторов"""
    
    user_uuid = serializers.UUIDField(write_only=True, required=False)
    supervisor_uuid = serializers.UUIDField(write_only=True, required=False, allow_null=True)
    region_uuids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    
    # Read-only поля для отображения
    supervisor = F2FCoordinatorListSerializer(read_only=True)
    regions = F2FCoordinatorRegionAssignmentSerializer(
        source='f2fcoordinatorregionassignment_set',
        many=True,
        read_only=True
    )
    
    class Meta:
        model = F2FCoordinator
        fields = [
            'uuid', 'employee_id', 'full_name', 'phone', 'email', 'birth_date',
            'status', 'experience_level', 'hire_date', 'termination_date',
            'user_uuid', 'supervisor_uuid', 'supervisor', 'region_uuids', 'regions',
            'monthly_target', 'current_month_registrations', 'total_registrations',
            'success_rate', 'device_id', 'offline_mode_enabled',
            'target_completion_rate', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'current_month_registrations', 'total_registrations',
            'success_rate', 'target_completion_rate', 'is_active',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        user_uuid = validated_data.pop('user_uuid', None)
        supervisor_uuid = validated_data.pop('supervisor_uuid', None)
        region_uuids = validated_data.pop('region_uuids', [])
        
        # Создаем координатора
        coordinator = F2FCoordinator.objects.create(**validated_data)
        
        # Связываем с пользователем
        if user_uuid:
            try:
                user = User.objects.get(uuid=user_uuid)
                coordinator.user = user
            except User.DoesNotExist:
                pass
        
        # Устанавливаем супервайзера
        if supervisor_uuid:
            try:
                supervisor = F2FCoordinator.objects.get(uuid=supervisor_uuid)
                coordinator.supervisor = supervisor
            except F2FCoordinator.DoesNotExist:
                pass
        
        coordinator.save()
        
        # Назначаем регионы
        if region_uuids:
            for i, region_uuid in enumerate(region_uuids):
                try:
                    region = F2FRegion.objects.get(id=region_uuid)
                    F2FCoordinatorRegionAssignment.objects.create(
                        coordinator=coordinator,
                        region=region,
                        assigned_date=timezone.now().date(),
                        is_primary=(i == 0)  # Первый регион - основной
                    )
                except F2FRegion.DoesNotExist:
                    pass
        
        return coordinator
    
    def update(self, instance, validated_data):
        user_uuid = validated_data.pop('user_uuid', None)
        supervisor_uuid = validated_data.pop('supervisor_uuid', None)
        region_uuids = validated_data.pop('region_uuids', None)
        
        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Обновляем пользователя
        if user_uuid is not None:
            if user_uuid:
                try:
                    user = User.objects.get(uuid=user_uuid)
                    instance.user = user
                except User.DoesNotExist:
                    pass
            else:
                instance.user = None
        
        # Обновляем супервайзера
        if supervisor_uuid is not None:
            if supervisor_uuid:
                try:
                    supervisor = F2FCoordinator.objects.get(uuid=supervisor_uuid)
                    instance.supervisor = supervisor
                except F2FCoordinator.DoesNotExist:
                    pass
            else:
                instance.supervisor = None
        
        instance.save()
        
        # Обновляем регионы
        if region_uuids is not None:
            # Удаляем старые назначения
            instance.f2fcoordinatorregionassignment_set.all().delete()
            
            # Создаем новые
            for i, region_uuid in enumerate(region_uuids):
                try:
                    region = F2FRegion.objects.get(id=region_uuid)
                    F2FCoordinatorRegionAssignment.objects.create(
                        coordinator=instance,
                        region=region,
                        assigned_date=timezone.now().date(),
                        is_primary=(i == 0)
                    )
                except F2FRegion.DoesNotExist:
                    pass
        
        return instance
    
    def validate_employee_id(self, value):
        """Валидация уникальности ID сотрудника"""
        if self.instance:
            if F2FCoordinator.objects.exclude(pk=self.instance.pk).filter(employee_id=value).exists():
                raise serializers.ValidationError("Координатор с таким ID уже существует.")
        else:
            if F2FCoordinator.objects.filter(employee_id=value).exists():
                raise serializers.ValidationError("Координатор с таким ID уже существует.")
        return value


class F2FCoordinatorStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики F2F координаторов"""
    
    total_coordinators = serializers.IntegerField()
    active_coordinators = serializers.IntegerField()
    total_registrations = serializers.IntegerField()
    monthly_registrations = serializers.IntegerField()
    top_performers = F2FCoordinatorListSerializer(many=True)
    regional_stats = serializers.DictField()
    performance_trends = serializers.ListField(child=serializers.DictField())
    conversion_rates = serializers.DictField()