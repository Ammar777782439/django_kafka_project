from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.conf import settings as django_settings
from .forms import MessageForm, FileForm
from .models import KafkaMessage
from .kafka_utils import KafkaProducer, KafkaConsumer, reset_kafka_consumer

def index(request):
    """
    عرض الصفحة الرئيسية مع نموذج إرسال الرسائل والملفات وقائمة الرسائل المستلمة
    """
    # جلب آخر 10 رسائل مستلمة
    kafka_messages = KafkaMessage.objects.all()[:10]

    # إنشاء نموذج إرسال الرسائل والملفات
    message_form = MessageForm()
    file_form = FileForm()

    context = {
        'message_form': message_form,
        'file_form': file_form,
        'kafka_messages': kafka_messages,
        'settings': django_settings,
    }

    return render(request, 'kafka_app/index.html', context)

@require_http_methods(["POST"])
def send_message(request):
    """
    إرسال رسالة نصية إلى Kafka
    """
    form = MessageForm(request.POST)

    if form.is_valid():
        # الحصول على الرسالة من النموذج
        message = form.cleaned_data['message']

        # إرسال الرسالة إلى Kafka
        producer = KafkaProducer()
        success, message_result = producer.send_message(message)

        if success:
            messages.success(request, message_result)
        else:
            messages.error(request, message_result)
    else:
        # إذا كان النموذج غير صالح
        messages.error(request, 'الرجاء تصحيح الأخطاء في النموذج')

    return redirect('index')

@require_http_methods(["POST"])
def send_file(request):
    """
    إرسال ملف إلى Kafka
    """
    form = FileForm(request.POST, request.FILES)

    if form.is_valid():
        # الحصول على الملف والوصف من النموذج
        file = request.FILES['file']
        description = form.cleaned_data.get('description', '')

        # إرسال الملف إلى Kafka
        producer = KafkaProducer()
        success, message_result = producer.send_file(file, description)

        if success:
            messages.success(request, message_result)
        else:
            messages.error(request, message_result)
    else:
        # إذا كان النموذج غير صالح
        error_message = 'الرجاء تصحيح الأخطاء في النموذج'
        if 'file' in form.errors:
            error_message = form.errors['file'][0]
        messages.error(request, error_message)

    return redirect('index')

def refresh_messages(request):
    """
    تحديث قائمة الرسائل والملفات المستلمة
    """
    # جلب آخر 10 رسائل مستلمة
    kafka_messages = KafkaMessage.objects.all()[:10]

    return render(request, 'kafka_app/messages_list.html', {'kafka_messages': kafka_messages})

def start_consumer(request):
    """
    بدء مستهلك Kafka
    """
    consumer = KafkaConsumer()
    success, message_result = consumer.start_consuming()

    if success:
        messages.success(request, message_result)
    else:
        messages.error(request, message_result)

    return redirect('index')

def stop_consumer(request):
    """
    إيقاف مستهلك Kafka
    """
    consumer = KafkaConsumer()
    success, message_result = consumer.stop_consuming()

    if success:
        messages.success(request, message_result)
    else:
        messages.error(request, message_result)

    return redirect('index')

def reset_consumer(request):
    """
    إعادة تعيين مستهلك Kafka
    """
    success, message_result = reset_kafka_consumer()

    if success:
        messages.success(request, message_result)
    else:
        messages.error(request, message_result)

    return redirect('index')
