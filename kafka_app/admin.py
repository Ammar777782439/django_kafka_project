from django.contrib import admin
from .models import KafkaMessage

@admin.register(KafkaMessage)
class KafkaMessageAdmin(admin.ModelAdmin):
    list_display = ('message', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('message',)
    ordering = ('-timestamp',)
