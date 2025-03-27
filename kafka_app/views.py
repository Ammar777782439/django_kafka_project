from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from .kafka_utils import send_text_message, send_file, start_consumer, stop_consumer, get_received_messages, consumer_thread
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
