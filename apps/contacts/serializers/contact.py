from rest_framework import serializers

from apps.contacts.models.contact import Contact, ContactCategory


class ContactCategorySerializer(serializers.ModelSerializer):
    """Serializer for ContactCategory model"""
    
    class Meta:
        model = ContactCategory
        fields = [
            'uuid', 'name', 'name_kg', 'name_en', 'description',
            'is_active', 'sort_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']


class ContactSerializer(serializers.ModelSerializer):
    """Serializer for Contact model"""
    
    class Meta:
        model = Contact
        fields = [
            'uuid', 'category', 'contact_type', 'full_name', 'email', 'phone',
            'subject', 'message', 'company', 'position', 'city',
            'preferred_contact_method', 'status', 'priority',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uuid', 'created_at', 'updated_at']

class ContactCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating Contact instances"""
    
    class Meta:
        model = Contact
        fields = [
            'category', 'contact_type', 'full_name', 'email', 'phone',
            'subject', 'message', 'company', 'position', 'city',
            'preferred_contact_method', 'consent_data_processing', 'consent_marketing'
        ]
    
    def validate_full_name(self, value):
        """Валидация имени"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Имя должно содержать минимум 2 символа")
        return value.strip()
    
    def validate_message(self, value):
        """Валидация сообщения"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Сообщение должно содержать минимум 10 символов")
        return value.strip()
    
    def validate_consent_data_processing(self, value):
        """Согласие на обработку данных обязательно"""
        if not value:
            raise serializers.ValidationError("Необходимо согласие на обработку персональных данных")
        return value


class ContactFormSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для формы обратной связи из дизайна"""
    
    class Meta:
        model = Contact
        fields = ['full_name', 'email', 'message']
    
    def validate_full_name(self, value):
        """Валидация имени"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Имя должно содержать минимум 2 символа")
        return value.strip()
    
    def validate_message(self, value):
        """Валидация сообщения"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Сообщение должно содержать минимум 10 символов")
        return value.strip()
    
    def create(self, validated_data):
        """Создание заявки с автоматическими полями"""
        # Устанавливаем значения по умолчанию
        validated_data.update({
            'contact_type': Contact.ContactType.GENERAL,
            'subject': 'Обращение через форму сайта',
            'consent_data_processing': True,  # Обязательно для формы
            'preferred_contact_method': 'email'
        })
        return super().create(validated_data)


class ContactListSerializer(serializers.ModelSerializer):
    """Serializer for listing Contact instances"""
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    contact_type_display = serializers.CharField(source='get_contact_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = Contact
        fields = [
            'uuid', 'category_name', 'contact_type_display', 'full_name', 'email',
            'subject', 'status_display', 'priority_display', 'created_at'
        ]