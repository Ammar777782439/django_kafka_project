"""
URL configuration for django_kafka_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from kafka_app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("send/", views.send_message, name="send_message"),
    path("send-file/", views.send_file, name="send_file"),
    path("refresh/", views.refresh_messages, name="refresh_messages"),
    path("start-consumer/", views.start_consumer, name="start_consumer"),
    path("stop-consumer/", views.stop_consumer, name="stop_consumer"),
    path("reset-consumer/", views.reset_consumer, name="reset_consumer"),
]

# إضافة مسارات الوسائط في وضع التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
