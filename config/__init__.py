# Инициализация поддержки кыргызского языка
import django.conf.locale
from django.conf.locale import LANG_INFO

# Добавляем поддержку кыргызского языка
LANG_INFO['kg'] = {
    'bidi': False,
    'code': 'kg',
    'name': 'Кыргызча',
    'name_local': 'Кыргызча',
}