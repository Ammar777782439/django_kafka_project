# Generated by Django 5.0 on 2025-03-26 23:32

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("kafka_app", "0002_kafkamessage_file_kafkamessage_file_name_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="kafkamessage",
            name="source",
            field=models.CharField(
                choices=[("producer", "السيرفر الأول"), ("consumer", "السيرفر الجديد")],
                default="consumer",
                max_length=10,
                verbose_name="مصدر الرسالة",
            ),
        ),
    ]
