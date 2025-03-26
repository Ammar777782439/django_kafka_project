from django.apps import AppConfig


class KafkaAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "kafka_app"

    def ready(self):
        """
        تهيئة مستهلك Kafka عند بدء التطبيق
        """
        # تجنب تشغيل المستهلك في وضع التطوير عند تشغيل الخادم مرتين
        import sys
        if 'runserver' not in sys.argv:
            return

        # تجنب تشغيل المستهلك في وضع التطوير عند تشغيل الخادم مرتين
        if 'autoreload' in sys.modules:
            import threading
            if threading.current_thread() is not threading.main_thread():
                return

        # تهيئة مستهلك Kafka
        from .kafka_utils import initialize_kafka_consumer
        initialize_kafka_consumer()
