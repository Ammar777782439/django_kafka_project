from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from datetime import timedelta
from .kafka_utils import start_consumer, stop_consumer, get_received_messages, consumer_thread
from .models import MessageAnalytics, KeywordAnalytics, UserActivityAnalytics, MessageLifetimeAnalytics
import json

def index(request):
    """
    Main view for the Kafka application
    Handles both GET and POST requests for sending messages and files to Kafka
    and for starting/stopping the Kafka consumer
    """
    success_message = None
    error_message = None

    if request.method == 'POST':
        # Check if this is a text message submission
        if 'message' in request.POST:
            message = request.POST.get('message')
            if message:
                success, msg = send_text_message(message)
                if success:
                    success_message = msg
                else:
                    error_message = msg
            else:
                error_message = "Message cannot be empty"

        # Check if this is a file submission
        elif 'file' in request.FILES:
            file_obj = request.FILES['file']
            if file_obj:
                success, msg = send_file(file_obj)
                if success:
                    success_message = msg
                else:
                    error_message = msg
            else:
                error_message = "No file selected"

        # Check if this is a consumer control request
        elif 'action' in request.POST:
            action = request.POST.get('action')
            if action == 'start_consumer':
                success, msg = start_consumer()
                if success:
                    success_message = msg
                else:
                    error_message = msg
            elif action == 'stop_consumer':
                success, msg = stop_consumer()
                if success:
                    success_message = msg
                else:
                    error_message = msg

    # Get received messages for display, filtered by event_type if specified
    event_type = request.GET.get('event_type', None)

    # For the main page, we specifically want soft_delete messages
    soft_delete_messages = get_received_messages(event_type='soft_delete')

    # If this is an AJAX request for messages, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('action') == 'get_messages':
        # If event_type is specified in the request, filter messages
        if event_type:
            filtered_messages = get_received_messages(event_type=event_type)
        else:
            filtered_messages = get_received_messages()

        return JsonResponse({
            'messages': filtered_messages
        })

    # If this is an AJAX request for form submission, return JSON response
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        response_data = {
            'success': success_message is not None,
            'message': success_message if success_message else error_message
        }
        return JsonResponse(response_data)

    # For regular requests, render the template
    context = {
        'success_message': success_message,
        'error_message': error_message,
        'soft_delete_messages': soft_delete_messages,
        'consumer_running': consumer_thread is not None and consumer_thread.is_alive() if 'consumer_thread' in globals() else False
    }
    return render(request, 'kafka_app/index.html', context)


def get_messages(request):
    """
    API endpoint to get received messages
    """
    event_type = request.GET.get('event_type', None)

    if event_type:
        messages = get_received_messages(event_type=event_type)
    else:
        messages = get_received_messages()

    return JsonResponse({
        'messages': messages
    })


def analytics_dashboard(request):
    """
    View for the analytics dashboard
    """
    # Get time period from request or default to daily
    period = request.GET.get('period', MessageAnalytics.PERIOD_DAILY)

    # Get message type from request or default to all
    message_type = request.GET.get('message_type', MessageAnalytics.TYPE_ALL)

    # Get date range from request or default to last 7 days
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get message analytics for the selected period and type
    message_analytics = MessageAnalytics.objects.filter(
        period=period,
        period_start__gte=start_date,
        period_start__lte=end_date,
        message_type=message_type
    ).order_by('period_start')

    # Get top keywords
    top_keywords = KeywordAnalytics.objects.order_by('-occurrences')[:20]

    # Get most active users (by messages sent)
    most_active_senders = UserActivityAnalytics.objects.order_by('-messages_sent')[:10]

    # Get most active users (by messages received)
    most_active_receivers = UserActivityAnalytics.objects.order_by('-messages_received')[:10]

    # Get total message count by type
    message_counts_by_type = MessageAnalytics.objects.filter(
        period=MessageAnalytics.PERIOD_DAILY,  # Use daily for overall counts
        period_start__gte=start_date,
        period_start__lte=end_date
    ).values('message_type').annotate(
        total_count=Sum('message_count')
    ).order_by('-total_count')

    # Get message lifetime analytics (commented out until migrations are applied)
    # message_lifetime_analytics = MessageLifetimeAnalytics.objects.all().order_by('lifetime_range')
    message_lifetime_analytics = []  # Empty list as a placeholder

    # Prepare data for charts
    labels = [analytics.period_start.strftime('%Y-%m-%d %H:%M') for analytics in message_analytics]
    message_counts = [analytics.message_count for analytics in message_analytics]
    sender_counts = [analytics.unique_senders for analytics in message_analytics]
    receiver_counts = [analytics.unique_receivers for analytics in message_analytics]

    # Prepare keyword data for chart
    keyword_labels = [keyword.keyword for keyword in top_keywords]
    keyword_counts = [keyword.occurrences for keyword in top_keywords]

    # Prepare message lifetime data for chart (commented out until migrations are applied)
    # lifetime_labels = [lifetime.get_lifetime_range_display() for lifetime in message_lifetime_analytics]
    # lifetime_counts = [lifetime.message_count for lifetime in message_lifetime_analytics]
    lifetime_labels = []  # Empty list as a placeholder
    lifetime_counts = []  # Empty list as a placeholder

    context = {
        'period': period,
        'message_type': message_type,
        'days': days,
        'message_analytics': message_analytics,
        'top_keywords': top_keywords,
        'most_active_senders': most_active_senders,
        'most_active_receivers': most_active_receivers,
        'message_counts_by_type': message_counts_by_type,
        'message_lifetime_analytics': message_lifetime_analytics,
        'chart_data': {
            'labels': labels,
            'message_counts': message_counts,
            'sender_counts': sender_counts,
            'receiver_counts': receiver_counts,
            'keyword_labels': keyword_labels,
            'keyword_counts': keyword_counts,
            'lifetime_labels': lifetime_labels,
            'lifetime_counts': lifetime_counts,
        },
        'periods': MessageAnalytics.PERIOD_CHOICES,
        'message_types': MessageAnalytics.TYPE_CHOICES,
    }

    return render(request, 'kafka_app/analytics_dashboard.html', context)


def analytics_api(request):
    """
    API endpoint for analytics data
    """
    # Get time period from request or default to daily
    period = request.GET.get('period', MessageAnalytics.PERIOD_DAILY)

    # Get message type from request or default to all
    message_type = request.GET.get('message_type', MessageAnalytics.TYPE_ALL)

    # Get date range from request or default to last 7 days
    days = int(request.GET.get('days', 7))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    # Get data type from request
    data_type = request.GET.get('data_type', 'message_counts')

    if data_type == 'message_counts':
        # Get message analytics for the selected period and type
        analytics = MessageAnalytics.objects.filter(
            period=period,
            period_start__gte=start_date,
            period_start__lte=end_date,
            message_type=message_type
        ).order_by('period_start')

        data = {
            'labels': [a.period_start.strftime('%Y-%m-%d %H:%M') for a in analytics],
            'datasets': [{
                'label': 'Message Count',
                'data': [a.message_count for a in analytics],
                'borderColor': 'rgba(75, 192, 192, 1)',
                'backgroundColor': 'rgba(75, 192, 192, 0.2)',
            }]
        }

    elif data_type == 'user_activity':
        # Get top users by messages sent
        users = UserActivityAnalytics.objects.order_by('-messages_sent')[:10]

        data = {
            'labels': [user.username for user in users],
            'datasets': [{
                'label': 'Messages Sent',
                'data': [user.messages_sent for user in users],
                'backgroundColor': 'rgba(54, 162, 235, 0.2)',
                'borderColor': 'rgba(54, 162, 235, 1)',
            }, {
                'label': 'Messages Received',
                'data': [user.messages_received for user in users],
                'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                'borderColor': 'rgba(255, 99, 132, 1)',
            }]
        }

    elif data_type == 'keywords':
        # Get top keywords
        keywords = KeywordAnalytics.objects.order_by('-occurrences')[:20]

        data = {
            'labels': [keyword.keyword for keyword in keywords],
            'datasets': [{
                'label': 'Occurrences',
                'data': [keyword.occurrences for keyword in keywords],
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)',
                    'rgba(255, 206, 86, 0.2)',
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(153, 102, 255, 0.2)',
                    'rgba(255, 159, 64, 0.2)'
                ],
                'borderColor': [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)'
                ],
            }]
        }

    else:
        return JsonResponse({'error': 'Invalid data type'}, status=400)

    return JsonResponse(data)
