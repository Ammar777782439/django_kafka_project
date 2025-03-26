import os
from django.db import models
from django.utils import timezone
from django.conf import settings

def get_file_upload_path(instance, filename):
    # إنشاء مسار ديناميكي للملفات المرفوعة
    return os.path.join('kafka_files', f"{timezone.now().strftime('%Y%m%d_%H%M%S')}_{filename}")

class KafkaMessage(models.Model):
    """
    نموذج لتخزين الرسائل والملفات المستلمة من Kafka
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'رسالة نصية'),
        ('file', 'ملف'),
    ]

    SOURCE_CHOICES = [
        ('producer', 'السيرفر الأول'),
        ('consumer', 'السيرفر الجديد'),
    ]

    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default='text', verbose_name='نوع الرسالة')
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='consumer', verbose_name='مصدر الرسالة')
    topic = models.CharField(max_length=100, blank=True, null=True, verbose_name='الموضوع')
    message = models.TextField(verbose_name='الرسالة', blank=True, null=True)
    file = models.FileField(upload_to=get_file_upload_path, blank=True, null=True, verbose_name='الملف')
    file_name = models.CharField(max_length=255, blank=True, null=True, verbose_name='اسم الملف')
    file_size = models.IntegerField(blank=True, null=True, verbose_name='حجم الملف (بايت)')
    file_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='نوع الملف')
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='وقت الاستلام')

    class Meta:
        verbose_name = 'رسالة Kafka'
        verbose_name_plural = 'رسائل Kafka'
        ordering = ['-timestamp']

    def __str__(self):
        if self.message_type == 'text':
            return f"نص: {self.message[:50]}... ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
        else:
            return f"ملف: {self.file_name} ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"

    def get_file_url(self):
        """الحصول على رابط الملف إذا كان موجوداً"""
        if self.file:
            return self.file.url
        return None

    def get_file_size_display(self):
        """عرض حجم الملف بطريقة مناسبة"""
        if not self.file_size:
            return ""

        # تحويل حجم الملف إلى وحدات مناسبة (KB, MB, GB)
        size = self.file_size
        for unit in ['بايت', 'كيلوبايت', 'ميجابايت', 'جيجابايت']:
            if size < 1024.0 or unit == 'جيجابايت':
                break
            size /= 1024.0
        return f"{size:.2f} {unit}"
