"""
Сервис для генерации PDF квитанций пожертвований
"""
import os
import logging
from io import BytesIO
from datetime import datetime
from django.conf import settings
from django.utils.translation import gettext as _
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

logger = logging.getLogger(__name__)


class ReceiptGeneratorService:
    """Сервис для генерации PDF квитанций"""
    
    # Шрифты для кириллицы
    CYRILLIC_FONT_NAME = 'DejaVuSans'
    CYRILLIC_FONT_BOLD_NAME = 'DejaVuSans-Bold'
    
    def __init__(self):
        self._register_cyrillic_fonts()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _register_cyrillic_fonts(self):
        """Регистрирует шрифты с поддержкой кириллицы"""
        # Список возможных путей к шрифтам DejaVu Sans
        font_paths = [
            # Linux пути
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/TTF/DejaVuSans.ttf',
            '/usr/share/fonts/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
            # macOS пути
            '/Library/Fonts/Arial Unicode.ttf',
            '/System/Library/Fonts/Helvetica.ttc',
            # Windows пути (если используется)
            'C:/Windows/Fonts/arial.ttf',
            'C:/Windows/Fonts/calibri.ttf',
        ]
        
        # Пытаемся найти и зарегистрировать шрифт
        font_registered = False
        bold_font_registered = False
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    # Регистрируем обычный шрифт
                    if not font_registered:
                        try:
                            pdfmetrics.registerFont(TTFont(self.CYRILLIC_FONT_NAME, font_path))
                            font_registered = True
                            logger.info(f"Зарегистрирован шрифт для кириллицы: {font_path}")
                        except Exception as e:
                            logger.warning(f"Ошибка регистрации шрифта {font_path}: {e}")
                            continue
                    
                    # Пытаемся найти bold версию
                    if font_registered and not bold_font_registered:
                        bold_path = font_path.replace('Sans.ttf', 'Sans-Bold.ttf').replace(
                            'Regular.ttf', 'Bold.ttf'
                        ).replace('arial.ttf', 'arialbd.ttf')
                        
                        if os.path.exists(bold_path):
                            try:
                                pdfmetrics.registerFont(TTFont(self.CYRILLIC_FONT_BOLD_NAME, bold_path))
                                bold_font_registered = True
                                registerFontFamily(
                                    self.CYRILLIC_FONT_NAME,
                                    normal=self.CYRILLIC_FONT_NAME,
                                    bold=self.CYRILLIC_FONT_BOLD_NAME,
                                    italic=self.CYRILLIC_FONT_NAME,
                                    boldItalic=self.CYRILLIC_FONT_BOLD_NAME
                                )
                                logger.info(f"Зарегистрирован жирный шрифт для кириллицы: {bold_path}")
                                break
                            except Exception:
                                pass
                    
                    if font_registered:
                        break
                except Exception as e:
                    logger.warning(f"Ошибка при обработке шрифта {font_path}: {e}")
                    continue
        
        # Если не нашли системный шрифт, используем встроенный подход
        # Для этого используем стандартные шрифты, но с правильной кодировкой
        if not font_registered:
            # Fallback: используем Helvetica, но будем кодировать Unicode правильно
            # В ReportLab 3.x+ есть лучшая поддержка Unicode
            self.CYRILLIC_FONT_NAME = 'Helvetica'
            self.CYRILLIC_FONT_BOLD_NAME = 'Helvetica-Bold'
            logger.warning("Используются стандартные шрифты (может не поддерживать кириллицу)")
    
    def _setup_custom_styles(self):
        """Настройка кастомных стилей для PDF"""
        # Стиль для заголовка
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#00A0DC'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=self.CYRILLIC_FONT_BOLD_NAME
        ))
        
        # Стиль для подзаголовка
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=self.CYRILLIC_FONT_NAME
        ))
        
        # Стиль для обычного текста
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=6,
            fontName=self.CYRILLIC_FONT_NAME
        ))
        
        # Стиль для успешного статуса
        self.styles.add(ParagraphStyle(
            name='SuccessStatus',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#28a745'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=self.CYRILLIC_FONT_BOLD_NAME
        ))
        
        # Стиль для неуспешного статуса
        self.styles.add(ParagraphStyle(
            name='FailedStatus',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#dc3545'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName=self.CYRILLIC_FONT_BOLD_NAME
        ))
    
    def generate_receipt(self, donation):
        """
        Генерирует PDF квитанцию для пожертвования
        
        Args:
            donation: Объект пожертвования (Donation)
            
        Returns:
            BytesIO: PDF файл в виде BytesIO объекта
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm
        )
        
        # Создаем содержимое документа
        story = []
        
        # Добавляем заголовок организации
        story.append(Paragraph(
            _('SOS Детские деревни Кыргызстана'),
            self.styles['CustomTitle']
        ))
        story.append(Spacer(1, 5*mm))
        
        # Добавляем тип документа
        story.append(Paragraph(
            _('КВИТАНЦИЯ О ПОЖЕРТВОВАНИИ'),
            self.styles['CustomSubtitle']
        ))
        story.append(Spacer(1, 10*mm))
        
        # Добавляем статус платежа
        status_style = self._get_status_style(donation.status)
        status_text = self._get_status_text(donation.status)
        story.append(Paragraph(status_text, status_style))
        story.append(Spacer(1, 8*mm))
        
        # Создаем таблицу с основной информацией
        # Убеждаемся, что все значения - строки с правильной кодировкой
        data = [
            [str(_('Код пожертвования:')), str(donation.donation_code)],
            [str(_('Дата и время:')), str(self._format_datetime(donation.created_at))],
            [str(_('Тип:')), str(donation.get_donation_type_display())],
            [str(_('Сумма:')), f"{donation.amount} {donation.currency}"],
            [str(_('Статус:')), str(donation.get_status_display())],
            ['', ''],
            [str(_('Донор:')), str(donation.donor_full_name)],
            [str(_('Email:')), str(donation.donor_email)],
            [str(_('Телефон:')), str(donation.donor_phone)],
        ]
        
        # Добавляем информацию о подписке если это рекуррентный платеж
        if donation.is_recurring:
            data.append(['', ''])
            data.append([str(_('Тип подписки:')), str(donation.get_donation_type_display())])
            if donation.subscription_status:
                data.append([
                    str(_('Статус подписки:')), 
                    str(donation.get_subscription_status_display())
                ])
            if donation.next_payment_date:
                data.append([
                    str(_('Следующий платеж:')), 
                    str(self._format_datetime(donation.next_payment_date))
                ])
        
        # Добавляем кампанию если есть
        if donation.campaign:
            data.append(['', ''])
            data.append([str(_('Кампания:')), str(donation.campaign.name)])
        
        # Преобразуем строки в Paragraph для правильного отображения кириллицы
        formatted_data = []
        for row in data:
            formatted_row = []
            for i, cell in enumerate(row):
                if cell:  # Если ячейка не пустая
                    # Первая колонка - жирный, остальные - обычный
                    if i == 0:
                        formatted_cell = Paragraph(
                            str(cell), 
                            ParagraphStyle(
                                'TableLabel',
                                parent=self.styles['Normal'],
                                fontName=self.CYRILLIC_FONT_BOLD_NAME,
                                fontSize=10,
                                textColor=colors.HexColor('#333333'),
                                leading=12
                            )
                        )
                    else:
                        formatted_cell = Paragraph(
                            str(cell),
                            ParagraphStyle(
                                'TableValue',
                                parent=self.styles['Normal'],
                                fontName=self.CYRILLIC_FONT_NAME,
                                fontSize=10,
                                textColor=colors.black,
                                leading=12
                            )
                        )
                else:
                    formatted_cell = ''
                formatted_row.append(formatted_cell)
            formatted_data.append(formatted_row)
        
        # Создаем таблицу
        table = Table(formatted_data, colWidths=[70*mm, 90*mm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.CYRILLIC_FONT_NAME),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F8F9FA')),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 15*mm))
        
        # Добавляем комментарий донора если есть
        if donation.donor_comment:
            story.append(Paragraph(
                f"<b>{_('Комментарий:')}</b>",
                self.styles['CustomBody']
            ))
            story.append(Paragraph(
                donation.donor_comment,
                self.styles['CustomBody']
            ))
            story.append(Spacer(1, 10*mm))
        
        # Добавляем благодарность
        if donation.status == 'completed':
            story.append(Paragraph(
                _('Спасибо за вашу поддержку!'),
                self.styles['CustomSubtitle']
            ))
            story.append(Paragraph(
                _('Ваше пожертвование помогает детям обрести семью и лучшее будущее.'),
                self.styles['CustomBody']
            ))
        
        # Добавляем контактную информацию
        story.append(Spacer(1, 15*mm))
        story.append(Paragraph(
            '<b>' + _('Контактная информация:') + '</b>',
            self.styles['CustomBody']
        ))
        story.append(Paragraph(
            _('Email: info@sos-kg.org'),
            self.styles['CustomBody']
        ))
        story.append(Paragraph(
            _('Телефон: +996 (312) 90-00-00'),
            self.styles['CustomBody']
        ))
        story.append(Paragraph(
            _('Адрес: г. Бишкек, ул. Примерная, 123'),
            self.styles['CustomBody']
        ))
        
        # Генерируем PDF
        doc.build(story)
        
        # Возвращаем буфер в начало
        buffer.seek(0)
        return buffer
    
    def _get_status_style(self, status):
        """Возвращает стиль в зависимости от статуса"""
        if status in ['completed', 'processing']:
            return self.styles['SuccessStatus']
        elif status in ['failed', 'cancelled', 'refunded']:
            return self.styles['FailedStatus']
        else:
            return self.styles['CustomSubtitle']
    
    def _get_status_text(self, status):
        """Возвращает текст статуса"""
        status_texts = {
            'completed': '✓ ' + _('ПЛАТЕЖ УСПЕШНО ЗАВЕРШЕН'),
            'processing': '⏳ ' + _('ПЛАТЕЖ В ОБРАБОТКЕ'),
            'failed': '✗ ' + _('ПЛАТЕЖ НЕ ВЫПОЛНЕН'),
            'cancelled': '✗ ' + _('ПЛАТЕЖ ОТМЕНЕН'),
            'refunded': '↩ ' + _('ПЛАТЕЖ ВОЗВРАЩЕН'),
            'pending': '⏰ ' + _('ОЖИДАЕТ ОПЛАТЫ'),
        }
        return status_texts.get(status, _('НЕИЗВЕСТНЫЙ СТАТУС'))
    
    def _format_datetime(self, dt):
        """Форматирует дату и время"""
        if not dt:
            return _('Не указано')
        return dt.strftime('%d.%m.%Y - %H:%M')
    
    def get_receipt_filename(self, donation):
        """
        Генерирует имя файла для квитанции
        
        Args:
            donation: Объект пожертвования
            
        Returns:
            str: Имя файла
        """
        date_str = donation.created_at.strftime('%Y%m%d')
        return f'receipt_{donation.donation_code}_{date_str}.pdf'

