import json
import threading
import time
import base64
import os
import mimetypes
from pathlib import Path
from django.core.files.base import ContentFile
from confluent_kafka import Producer, Consumer, KafkaError
from django.conf import settings
from .models import KafkaMessage

class KafkaProducer:
    """
    فئة للتعامل مع إرسال الرسائل إلى Kafka
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KafkaProducer, cls).__new__(cls)
                cls._instance.producer = Producer(settings.KAFKA_PRODUCER_CONFIG)
        return cls._instance

    def send_message(self, message):
        """
        إرسال رسالة نصية إلى موضوع Kafka
        """
        try:
            # تحويل الرسالة إلى JSON
            message_data = {
                'type': 'text',
                'message': message,
                'timestamp': time.time()
            }

            # إرسال الرسالة إلى Kafka
            self.producer.produce(
                settings.KAFKA_PRODUCER_TOPIC,
                json.dumps(message_data).encode('utf-8'),
                callback=self._delivery_report
            )

            # ضمان إرسال جميع الرسائل
            self.producer.flush()

            return True, "تم إرسال الرسالة بنجاح"
        except Exception as e:
            return False, f"حدث خطأ أثناء إرسال الرسالة: {str(e)}"

    def send_file(self, file, description=''):
        """
        إرسال ملف إلى موضوع Kafka
        """
        try:
            # قراءة الملف وتحويله إلى Base64
            file_content = file.read()
            file_base64 = base64.b64encode(file_content).decode('utf-8')

            # الحصول على معلومات الملف
            file_name = file.name
            file_size = file.size
            file_type = file.content_type or mimetypes.guess_type(file_name)[0] or 'application/octet-stream'

            # تحويل الملف إلى JSON
            message_data = {
                'type': 'file',
                'file_name': file_name,
                'file_size': file_size,
                'file_type': file_type,
                'file_content': file_base64,
                'description': description,
                'timestamp': time.time()
            }

            # إرسال الملف إلى Kafka
            self.producer.produce(
                settings.KAFKA_PRODUCER_TOPIC,
                json.dumps(message_data).encode('utf-8'),
                callback=self._delivery_report
            )

            # ضمان إرسال جميع الرسائل
            self.producer.flush()

            return True, "تم إرسال الملف بنجاح"
        except Exception as e:
            return False, f"حدث خطأ أثناء إرسال الملف: {str(e)}"

    def _delivery_report(self, err, msg):
        """
        تقرير تسليم الرسالة
        """
        if err is not None:
            print(f'فشل تسليم الرسالة: {err}')
        else:
            print(f'تم تسليم الرسالة إلى {msg.topic()} [{msg.partition()}]')


class KafkaConsumer:
    """
    فئة للتعامل مع استقبال الرسائل من Kafka
    """
    _instance = None
    _lock = threading.Lock()
    _running = False
    _consumer_thread = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(KafkaConsumer, cls).__new__(cls)
                # إعداد مستهلك Kafka
                # استخدام إعدادات المستهلك الجديدة
                cls._instance.consumer = Consumer(settings.KAFKA_CONSUMER_CONFIG)
        return cls._instance

    def start_consuming(self):
        """
        بدء استهلاك الرسائل من Kafka
        """
        if self._running:
            return False, "المستهلك يعمل بالفعل"

        try:
            # الاشتراك في موضوع Kafka
            self.consumer.subscribe([settings.KAFKA_CONSUMER_TOPIC])
            print(f'تم الاشتراك في موضوع: {settings.KAFKA_CONSUMER_TOPIC}')

            # بدء مؤشر ترابط لاستهلاك الرسائل
            self._running = True
            self._consumer_thread = threading.Thread(target=self._consume_messages)
            self._consumer_thread.daemon = True
            self._consumer_thread.start()

            return True, "تم بدء استهلاك الرسائل بنجاح"
        except Exception as e:
            self._running = False
            return False, f"حدث خطأ أثناء بدء استهلاك الرسائل: {str(e)}"

    def stop_consuming(self):
        """
        إيقاف استهلاك الرسائل من Kafka
        """
        if not self._running:
            return False, "المستهلك متوقف بالفعل"

        try:
            self._running = False
            if self._consumer_thread:
                self._consumer_thread.join(timeout=5.0)
            self.consumer.close()
            return True, "تم إيقاف استهلاك الرسائل بنجاح"
        except Exception as e:
            return False, f"حدث خطأ أثناء إيقاف استهلاك الرسائل: {str(e)}"

    def _consume_messages(self):
        """
        استهلاك الرسائل من Kafka وحفظها في قاعدة البيانات
        """
        print(f'\n\n*** بدء حلقة استهلاك الرسائل من موضوع: {settings.KAFKA_CONSUMER_TOPIC} ***\n\n')
        while self._running:
            try:
                # قراءة رسالة من Kafka
                print(f'\nمحاولة قراءة رسالة من موضوع: {settings.KAFKA_CONSUMER_TOPIC}\n')
                msg = self.consumer.poll(1.0)

                if msg is None:
                    print('لم يتم استلام أي رسالة')
                    continue
                else:
                    print(f'تم استلام رسالة من موضوع: {msg.topic()}')

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # نهاية القسم - ليس خطأ
                        print(f'نهاية القسم للموضوع: {msg.topic()}, القسم: {msg.partition()}')
                        continue
                    else:
                        print(f'خطأ في استهلاك الرسالة: {msg.error()}')
                        continue

                # معالجة الرسالة المستلمة
                try:
                    # تحويل الرسالة من JSON
                    message_value = msg.value().decode('utf-8')
                    print(f'محتوى الرسالة: {message_value}')
                    message_data = json.loads(message_value)

                    # تحديد نوع الرسالة (نص أو ملف)
                    message_type = message_data.get('type', 'text')

                    if message_type == 'text':
                        # حفظ الرسالة النصية في قاعدة البيانات
                        KafkaMessage.objects.create(
                            message_type='text',
                            message=message_data['message'],
                            source='consumer',  # تم استلامها من السيرفر الجديد
                            topic=settings.KAFKA_CONSUMER_TOPIC  # تخزين اسم الموضوع
                        )
                        print(f'تم استلام رسالة نصية: {message_data["message"]}')

                    elif message_type == 'file':
                        # استخراج معلومات الملف
                        file_name = message_data['file_name']
                        file_size = message_data['file_size']
                        file_type = message_data['file_type']
                        file_content_base64 = message_data['file_content']
                        description = message_data.get('description', '')

                        # تحويل محتوى الملف من Base64 إلى بيانات ثنائية
                        file_content = base64.b64decode(file_content_base64)

                        # إنشاء ملف جديد في قاعدة البيانات
                        kafka_message = KafkaMessage(
                            message_type='file',
                            message=description,
                            file_name=file_name,
                            file_size=file_size,
                            file_type=file_type,
                            source='consumer',  # تم استلامها من السيرفر الجديد
                            topic=settings.KAFKA_CONSUMER_TOPIC  # تخزين اسم الموضوع
                        )

                        # حفظ الملف
                        content_file = ContentFile(file_content, name=file_name)
                        kafka_message.file.save(file_name, content_file, save=False)
                        kafka_message.save()

                        print(f'تم استلام ملف: {file_name} ({file_size} بايت)')

                    else:
                        print(f'نوع رسالة غير معروف: {message_type}')

                except Exception as e:
                    print(f'خطأ في معالجة الرسالة: {str(e)}')

            except Exception as e:
                print(f'خطأ في حلقة الاستهلاك: {str(e)}')
                if not self._running:
                    break
                time.sleep(1)  # انتظار قبل المحاولة مرة أخرى

# تهيئة مستهلك Kafka عند بدء التطبيق
def reset_kafka_consumer():
    """
    إعادة تعيين مستهلك Kafka
    """
    try:
        consumer = KafkaConsumer()
        # إيقاف المستهلك الحالي إذا كان يعمل
        consumer.stop_consuming()
        # إعادة تعيين المتغيرات
        KafkaConsumer._instance = None
        # إنشاء مستهلك جديد
        new_consumer = KafkaConsumer()
        success, message = new_consumer.start_consuming()
        print(f"إعادة تعيين مستهلك Kafka: {message}")
        return success, message
    except Exception as e:
        print(f"خطأ في إعادة تعيين مستهلك Kafka: {str(e)}")
        return False, str(e)

def initialize_kafka_consumer():
    """
    تهيئة مستهلك Kafka عند بدء التطبيق
    """
    try:
        consumer = KafkaConsumer()
        success, message = consumer.start_consuming()
        print(f"تهيئة مستهلك Kafka: {message}")
        return success
    except Exception as e:
        print(f"خطأ في تهيئة مستهلك Kafka: {str(e)}")
        return False
