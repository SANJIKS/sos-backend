from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.donors.models import (
    F2FRegistration, 
    F2FRegistrationDocument, 
    F2FDailyReport,
    F2FCoordinator,
    F2FLocation,
    Donor
)
from apps.donors.serializers.f2f_coordinator import F2FCoordinatorListSerializer, F2FLocationSerializer

User = get_user_model()


class F2FRegistrationDocumentSerializer(serializers.ModelSerializer):
    """Сериализатор для документов F2F регистрации"""
    
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = F2FRegistrationDocument
        fields = [
            'id', 'document_type', 'file', 'file_url', 'file_name',
            'file_size', 'content_type', 'is_synced', 'created_at'
        ]
    
    def get_file_url(self, obj):
        """Получение URL файла"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None


class F2FRegistrationListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка F2F регистраций (краткая информация)"""
    
    coordinator_name = serializers.CharField(source='coordinator.full_name', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    donation_type_display = serializers.CharField(source='get_donation_type_display', read_only=True)
    
    class Meta:
        model = F2FRegistration
        fields = [
            'uuid', 'registration_number', 'full_name', 'email', 'phone',
            'coordinator_name', 'location_name', 'donation_amount', 'donation_type',
            'donation_type_display', 'status', 'status_display', 'is_synced',
            'registered_at', 'created_at'
        ]


class F2FRegistrationDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детальной информации о F2F регистрации"""
    
    coordinator = F2FCoordinatorListSerializer(read_only=True)
    location = F2FLocationSerializer(read_only=True)
    documents = F2FRegistrationDocumentSerializer(many=True, read_only=True)
    donor_name = serializers.CharField(source='donor.full_name', read_only=True)
    
    class Meta:
        model = F2FRegistration
        fields = [
            'uuid', 'registration_number', 'coordinator', 'location',
            'full_name', 'email', 'phone', 'birth_date', 'gender',
            'preferred_language', 'city', 'address', 'postal_code',
            'donation_amount', 'donation_type', 'payment_method',
            'consent_data_processing', 'consent_marketing', 'consent_newsletter',
            'status', 'donor', 'donor_name', 'user',
            'is_synced', 'sync_attempts', 'last_sync_attempt', 'sync_error',
            'registration_source', 'device_info', 'gps_coordinates',
            'coordinator_notes', 'admin_notes', 'documents',
            'registered_at', 'created_at', 'updated_at'
        ]


class F2FRegistrationSerializer(serializers.ModelSerializer):
    """Основной сериализатор для создания/редактирования F2F регистраций"""
    
    coordinator_uuid = serializers.UUIDField(write_only=True)
    location_uuid = serializers.UUIDField(write_only=True)
    
    # Read-only поля для отображения
    coordinator = F2FCoordinatorListSerializer(read_only=True)
    location = F2FLocationSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = F2FRegistration
        fields = [
            'uuid', 'registration_number', 'coordinator_uuid', 'coordinator',
            'location_uuid', 'location', 'full_name', 'email', 'phone',
            'birth_date', 'gender', 'preferred_language', 'city', 'address', 'postal_code',
            'donation_amount', 'donation_type', 'payment_method',
            'consent_data_processing', 'consent_marketing', 'consent_newsletter',
            'status', 'status_display', 'coordinator_notes', 'admin_notes',
            'registration_source', 'device_info', 'gps_coordinates',
            'registered_at', 'is_pending', 'needs_sync',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'registration_number', 'is_pending', 'needs_sync',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        coordinator_uuid = validated_data.pop('coordinator_uuid')
        location_uuid = validated_data.pop('location_uuid')
        
        # Получаем координатора и локацию
        try:
            coordinator = F2FCoordinator.objects.get(uuid=coordinator_uuid)
            location = F2FLocation.objects.get(uuid=location_uuid)
        except (F2FCoordinator.DoesNotExist, F2FLocation.DoesNotExist):
            raise serializers.ValidationError("Координатор или локация не найдены.")
        
        # Создаем регистрацию
        registration = F2FRegistration.objects.create(
            coordinator=coordinator,
            location=location,
            **validated_data
        )
        
        # Увеличиваем счетчик регистраций координатора
        coordinator.increment_registrations()
        
        return registration
    
    def update(self, instance, validated_data):
        coordinator_uuid = validated_data.pop('coordinator_uuid', None)
        location_uuid = validated_data.pop('location_uuid', None)
        
        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Обновляем координатора
        if coordinator_uuid:
            try:
                coordinator = F2FCoordinator.objects.get(uuid=coordinator_uuid)
                instance.coordinator = coordinator
            except F2FCoordinator.DoesNotExist:
                raise serializers.ValidationError("Координатор не найден.")
        
        # Обновляем локацию
        if location_uuid:
            try:
                location = F2FLocation.objects.get(uuid=location_uuid)
                instance.location = location
            except F2FLocation.DoesNotExist:
                raise serializers.ValidationError("Локация не найдена.")
        
        instance.save()
        return instance
    
    def validate_email(self, value):
        """Валидация email"""
        if self.instance:
            if F2FRegistration.objects.exclude(uuid=self.instance.uuid).filter(email=value).exists():
                raise serializers.ValidationError("Регистрация с таким email уже существует.")
        else:
            if F2FRegistration.objects.filter(email=value).exists():
                raise serializers.ValidationError("Регистрация с таким email уже существует.")
        return value
    
    def validate_donation_amount(self, value):
        """Валидация суммы пожертвования"""
        if value <= 0:
            raise serializers.ValidationError("Сумма пожертвования должна быть больше нуля.")
        return value
    
    def validate_consent_data_processing(self, value):
        """Согласие на обработку данных обязательно"""
        if not value:
            raise serializers.ValidationError("Согласие на обработку данных обязательно.")
        return value


class F2FRegistrationMobileSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для мобильного приложения координаторов"""
    
    coordinator_uuid = serializers.UUIDField(write_only=True)
    location_uuid = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = F2FRegistration
        fields = [
            'uuid', 'coordinator_uuid', 'location_uuid', 'full_name', 'email', 'phone',
            'birth_date', 'gender', 'preferred_language', 'city',
            'donation_amount', 'donation_type', 'payment_method',
            'consent_data_processing', 'consent_marketing', 'consent_newsletter',
            'coordinator_notes', 'device_info', 'gps_coordinates',
            'registered_at', 'registration_number', 'is_synced'
        ]
        read_only_fields = ['uuid', 'registration_number', 'is_synced']
    
    def create(self, validated_data):
        coordinator_uuid = validated_data.pop('coordinator_uuid')
        location_uuid = validated_data.pop('location_uuid')
        
        # Получаем координатора и локацию
        try:
            coordinator = F2FCoordinator.objects.get(uuid=coordinator_uuid)
            location = F2FLocation.objects.get(uuid=location_uuid)
        except (F2FCoordinator.DoesNotExist, F2FLocation.DoesNotExist):
            raise serializers.ValidationError("Координатор или локация не найдены.")
        
        # Устанавливаем время регистрации
        if 'registered_at' not in validated_data:
            validated_data['registered_at'] = timezone.now()
        
        # Создаем регистрацию
        registration = F2FRegistration.objects.create(
            coordinator=coordinator,
            location=location,
            **validated_data
        )
        
        # Увеличиваем счетчик регистраций координатора
        coordinator.increment_registrations()
        
        return registration
    
    def update(self, instance, validated_data):
        coordinator_uuid = validated_data.pop('coordinator_uuid', None)
        location_uuid = validated_data.pop('location_uuid', None)
        
        # Обновляем основные поля
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Обновляем координатора
        if coordinator_uuid:
            try:
                coordinator = F2FCoordinator.objects.get(uuid=coordinator_uuid)
                instance.coordinator = coordinator
            except F2FCoordinator.DoesNotExist:
                raise serializers.ValidationError("Координатор не найден.")
        
        # Обновляем локацию
        if location_uuid:
            try:
                location = F2FLocation.objects.get(uuid=location_uuid)
                instance.location = location
            except F2FLocation.DoesNotExist:
                raise serializers.ValidationError("Локация не найдена.")
        
        instance.save()
        return instance


class F2FDailyReportSerializer(serializers.ModelSerializer):
    """Сериализатор для ежедневных отчетов координаторов"""
    
    coordinator_uuid = serializers.UUIDField(write_only=True)
    location_uuid = serializers.UUIDField(write_only=True)
    
    coordinator = F2FCoordinatorListSerializer(read_only=True)
    location = F2FLocationSerializer(read_only=True)
    
    # Вычисляемые поля
    conversion_rate = serializers.ReadOnlyField()
    working_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = F2FDailyReport
        fields = [
            'id', 'coordinator_uuid', 'coordinator', 'location_uuid', 'location',
            'report_date', 'total_approaches', 'successful_registrations',
            'rejected_approaches', 'start_time', 'end_time', 'break_duration',
            'notes', 'weather_conditions', 'foot_traffic_assessment',
            'conversion_rate', 'working_hours', 'is_synced',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['conversion_rate', 'working_hours', 'is_synced']
    
    def create(self, validated_data):
        coordinator_uuid = validated_data.pop('coordinator_uuid')
        location_uuid = validated_data.pop('location_uuid')
        
        try:
            coordinator = F2FCoordinator.objects.get(uuid=coordinator_uuid)
            location = F2FLocation.objects.get(uuid=location_uuid)
        except (F2FCoordinator.DoesNotExist, F2FLocation.DoesNotExist):
            raise serializers.ValidationError("Координатор или локация не найдены.")
        
        return F2FDailyReport.objects.create(
            coordinator=coordinator,
            location=location,
            **validated_data
        )
    
    def validate(self, data):
        """Валидация отчета"""
        coordinator_uuid = data.get('coordinator_uuid')
        location_uuid = data.get('location_uuid')
        report_date = data.get('report_date')
        
        # Проверяем, что отчет за эту дату еще не создан
        if coordinator_uuid and location_uuid and report_date:
            existing = F2FDailyReport.objects.filter(
                coordinator__uuid=coordinator_uuid,
                location__uuid=location_uuid,
                report_date=report_date
            )
            
            if self.instance:
                existing = existing.exclude(id=self.instance.id)
            
            if existing.exists():
                raise serializers.ValidationError(
                    "Отчет за эту дату уже существует для данного координатора и локации."
                )
        
        # Валидируем время
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Время окончания должно быть позже времени начала.")
        
        # Валидируем статистику
        total_approaches = data.get('total_approaches', 0)
        successful = data.get('successful_registrations', 0)
        rejected = data.get('rejected_approaches', 0)
        
        if successful + rejected > total_approaches:
            raise serializers.ValidationError(
                "Сумма успешных и отклоненных подходов не может превышать общее количество."
            )
        
        return data


class F2FRegistrationStatsSerializer(serializers.Serializer):
    """Сериализатор для статистики F2F регистраций"""
    
    total_registrations = serializers.IntegerField()
    today_registrations = serializers.IntegerField()
    monthly_registrations = serializers.IntegerField()
    pending_registrations = serializers.IntegerField()
    confirmed_registrations = serializers.IntegerField()
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    top_locations = serializers.ListField(child=serializers.DictField())
    top_coordinators = serializers.ListField(child=serializers.DictField())
    registration_trends = serializers.ListField(child=serializers.DictField())
    sync_status = serializers.DictField()