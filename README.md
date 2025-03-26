# مشروع Django مع Kafka

هذا المشروع هو تطبيق Django يعمل كمنتج (Producer) ومستهلك (Consumer) لـ Kafka في نفس الوقت. يستخدم المشروع Kafka في وضع KRaft Mode (بدون Zookeeper).

يدعم المشروع إرسال واستقبال كل من الرسائل النصية والملفات عبر Kafka.

## المتطلبات

- Python 3.8+
- Django 3.2+
- confluent-kafka 1.8.2+
- Kafka Broker يعمل في وضع KRaft Mode على Ubuntu

## التثبيت

1. قم بتثبيت المكتبات المطلوبة:

```bash
pip install -r requirements.txt
```

2. قم بتعديل إعدادات Kafka في ملف `django_kafka_project/settings.py`:

```python
KAFKA_CONFIG = {
    'bootstrap.servers': 'your-ubuntu-ip:9092',  # تغيير هذا إلى عنوان IP الخاص بخادم Ubuntu
    'client.id': 'django-kafka-client',
    'default.topic.config': {
        'acks': 'all'
    }
}
```

3. قم بإنشاء قاعدة البيانات:

```bash
python manage.py migrate
```

4. قم بإنشاء مستخدم مدير:

```bash
python manage.py createsuperuser
```

## تشغيل المشروع

1. قم بتشغيل خادم التطوير:

```bash
python manage.py runserver
```

2. افتح المتصفح على العنوان: http://127.0.0.1:8000/

## إعداد Kafka على Ubuntu (KRaft Mode)

### 1. تثبيت Java

```bash
sudo apt update
sudo apt install openjdk-11-jdk
```

### 2. تنزيل وإعداد Kafka

```bash
wget https://downloads.apache.org/kafka/3.3.1/kafka_2.13-3.3.1.tgz
tar -xzf kafka_2.13-3.3.1.tgz
cd kafka_2.13-3.3.1
```

### 3. إعداد Kafka في وضع KRaft

1. قم بإنشاء معرف عقدة Kafka:

```bash
KAFKA_CLUSTER_ID=$(bin/kafka-storage.sh random-uuid)
```

2. قم بتهيئة التخزين:

```bash
bin/kafka-storage.sh format -t $KAFKA_CLUSTER_ID -c config/kraft/server.properties
```

3. قم بتعديل ملف `config/kraft/server.properties` للسماح بالاتصال من Windows:

```
# تعديل عنوان الاستماع ليسمح بالاتصال من أي عنوان IP
listeners=PLAINTEXT://0.0.0.0:9092
advertised.listeners=PLAINTEXT://YOUR_UBUNTU_IP:9092
```

استبدل `YOUR_UBUNTU_IP` بعنوان IP الخاص بخادم Ubuntu.

4. قم بتشغيل Kafka:

```bash
bin/kafka-server-start.sh config/kraft/server.properties
```

### 4. إنشاء موضوع Kafka

```bash
bin/kafka-topics.sh --create --topic django_messages --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

## التحقق من الاتصال بـ Kafka

1. تأكد من أن Kafka يعمل على خادم Ubuntu.
2. تأكد من أن جدار الحماية يسمح بالاتصال على المنفذ 9092.
3. تأكد من تعديل إعدادات Kafka في ملف `django_kafka_project/settings.py` لتشير إلى عنوان IP الصحيح لخادم Ubuntu.
4. قم بتشغيل المشروع واختبار إرسال واستقبال الرسائل.

## استخدام التطبيق

1. الصفحة الرئيسية تحتوي على نموذجين:
   - نموذج لإدخال الرسائل النصية وإرسالها إلى Kafka.
   - نموذج لرفع الملفات وإرسالها إلى Kafka.
2. يمكنك بدء وإيقاف مستهلك Kafka من خلال الأزرار الموجودة في الصفحة.
3. الرسائل والملفات المستلمة من Kafka يتم عرضها في جدول ويتم تحديثها تلقائياً كل 5 ثوانٍ.
4. يمكنك تحميل الملفات المستلمة من خلال النقر على اسم الملف في الجدول.

## ملاحظات

- يتم تشغيل مستهلك Kafka تلقائيًا عند بدء التطبيق.
- يمكنك إيقاف وإعادة تشغيل المستهلك من خلال الأزرار الموجودة في الصفحة.
- يتم تخزين الرسائل والملفات المستلمة في قاعدة البيانات ويمكن عرضها في لوحة الإدارة.
- يتم تخزين الملفات المرفوعة في مجلد `media/kafka_files/` ويمكن الوصول إليها من خلال الروابط في الجدول.
- الحد الأقصى لحجم الملف المرفوع هو 10 ميجابايت.
