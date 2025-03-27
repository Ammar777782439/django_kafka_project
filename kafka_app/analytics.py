import re
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import F
from .models import MessageAnalytics, KeywordAnalytics, UserActivityAnalytics, MessageLifetimeAnalytics

logger = logging.getLogger(__name__)

class MessageAnalyzer:
    """
    Class for analyzing messages and updating analytics data
    """
    # Common Arabic stop words to exclude from keyword analysis
    STOP_WORDS = {
        'في', 'من', 'إلى', 'على', 'أن', 'عن', 'مع', 'هذا', 'هذه', 'ذلك', 'تلك',
        'هو', 'هي', 'هم', 'هن', 'أنا', 'أنت', 'أنتم', 'نحن', 'كان', 'كانت', 'كانوا',
        'يكون', 'تكون', 'أو', 'ثم', 'لكن', 'و', 'ف', 'ب', 'ل', 'لل', 'ال', 'ما',
        'لا', 'إن', 'إذا', 'حتى', 'عندما', 'كما', 'بعد', 'قبل', 'منذ', 'خلال',
        'بين', 'فوق', 'تحت', 'عند', 'كل', 'بعض', 'غير', 'مثل', 'أكثر', 'أقل',
        'جدا', 'فقط', 'أيضا', 'هنا', 'هناك', 'الذي', 'التي', 'الذين', 'اللواتي',
        'أي', 'كيف', 'متى', 'لماذا', 'ماذا', 'من', 'أين', 'نعم', 'لا'
    }

    # Minimum word length for keyword analysis
    MIN_WORD_LENGTH = 3

    # Maximum keywords to track
    MAX_KEYWORDS = 1000

    @staticmethod
    def get_period_start(dt, period):
        """
        Get the start of the period containing the given datetime

        Args:
            dt (datetime): The datetime to get the period start for
            period (str): The period type ('hourly', 'daily', 'weekly', 'monthly')

        Returns:
            datetime: The start of the period
        """
        if period == MessageAnalytics.PERIOD_HOURLY:
            return dt.replace(minute=0, second=0, microsecond=0)
        elif period == MessageAnalytics.PERIOD_DAILY:
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == MessageAnalytics.PERIOD_WEEKLY:
            # Start of the week (Monday)
            return (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == MessageAnalytics.PERIOD_MONTHLY:
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Invalid period: {period}")

    @classmethod
    def extract_keywords(cls, text):
        """
        Extract keywords from text

        Args:
            text (str): The text to extract keywords from

        Returns:
            list: List of keywords
        """
        if not text:
            return []

        # Convert to lowercase and remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())

        # Split into words
        words = text.split()

        # Filter out stop words and short words
        keywords = [
            word for word in words
            if word not in cls.STOP_WORDS and len(word) >= cls.MIN_WORD_LENGTH
        ]

        return keywords

    @classmethod
    def update_message_analytics(cls, message_data):
        """
        Update message analytics based on a message

        Args:
            message_data (dict): The message data with the following structure:
            {
                'event_type': event_type,
                'message_id': instance.id,
                'sender': instance.sender.username,
                'receiver': instance.receiver.username,
                'content': instance.content,
                'timestamp': instance.timestamp.isoformat(),
                'deleted_at': instance.deleted_at.isoformat() if instance.deleted_at else None
            }

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Extract message data
            event_type = message_data.get('event_type', 'unknown')
            message_id = message_data.get('message_id', 0)
            sender = message_data.get('sender', '')
            receiver = message_data.get('receiver', '')
            content = message_data.get('content', '')
            timestamp_str = message_data.get('timestamp', '')
            deleted_at_str = message_data.get('deleted_at', None)

            # Parse timestamp
            if timestamp_str:
                try:
                    # Try to parse ISO format timestamp
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    # If that fails, use current time
                    timestamp = timezone.now()
            else:
                timestamp = timezone.now()

            # Log the message details for debugging
            logger.info(f"Processing message: ID={message_id}, Type={event_type}, Sender={sender}, Receiver={receiver}")

            # Update message count analytics for all periods
            for period in [MessageAnalytics.PERIOD_HOURLY, MessageAnalytics.PERIOD_DAILY,
                          MessageAnalytics.PERIOD_WEEKLY, MessageAnalytics.PERIOD_MONTHLY]:

                period_start = cls.get_period_start(timestamp, period)

                # Update for specific message type
                cls._update_analytics_record(period, period_start, event_type, sender, receiver)

                # Update for all message types
                cls._update_analytics_record(period, period_start, MessageAnalytics.TYPE_ALL, sender, receiver)

            # Update keyword analytics
            if content:
                keywords = cls.extract_keywords(content)
                for keyword in keywords:
                    cls._update_keyword_analytics(keyword)

            # Update user activity analytics
            if sender:
                cls._update_user_sent_analytics(sender)

            if receiver:
                cls._update_user_received_analytics(receiver)

            # Update message lifetime analytics for soft_delete messages (commented out until migrations are applied)
            # if event_type == 'soft_delete' and deleted_at_str and timestamp_str:
            #     try:
            #         # Parse deleted_at timestamp
            #         deleted_at = datetime.fromisoformat(deleted_at_str.replace('Z', '+00:00'))
            #
            #         # Calculate message lifetime in minutes
            #         lifetime_minutes = (deleted_at - timestamp).total_seconds() / 60
            #
            #         # Update message lifetime analytics
            #         cls._update_message_lifetime_analytics(lifetime_minutes)
            #
            #         logger.info(f"Message lifetime: {lifetime_minutes:.2f} minutes")
            #     except Exception as e:
            #         logger.error(f"Error calculating message lifetime: {e}")

            # For now, just log the message lifetime if available
            if event_type == 'soft_delete' and deleted_at_str and timestamp_str:
                try:
                    # Parse deleted_at timestamp
                    deleted_at = datetime.fromisoformat(deleted_at_str.replace('Z', '+00:00'))

                    # Calculate message lifetime in minutes
                    lifetime_minutes = (deleted_at - timestamp).total_seconds() / 60

                    logger.info(f"Message lifetime: {lifetime_minutes:.2f} minutes")
                except Exception as e:
                    logger.error(f"Error calculating message lifetime: {e}")

            return True

        except Exception as e:
            logger.error(f"Error updating message analytics: {e}")
            return False

    @staticmethod
    def _update_analytics_record(period, period_start, message_type, sender, receiver):
        """
        Update or create an analytics record

        Args:
            period (str): The period type
            period_start (datetime): The start of the period
            message_type (str): The message type
            sender (str): The message sender
            receiver (str): The message receiver
        """
        # Get or create analytics record
        analytics, created = MessageAnalytics.objects.get_or_create(
            period=period,
            period_start=period_start,
            message_type=message_type,
            defaults={
                'message_count': 0,
                'unique_senders': 0,
                'unique_receivers': 0
            }
        )

        # Update message count
        analytics.message_count += 1

        # Check if we need to update unique senders/receivers
        if created:
            # For a new record, initialize with the current sender/receiver
            if sender:
                analytics.unique_senders = 1
            if receiver:
                analytics.unique_receivers = 1
        else:
            # For existing records, we'd need to check if this sender/receiver is new
            # This is a simplified approach - in a real system, you'd use a more efficient method
            # like maintaining sets of unique users in a separate table or using Redis sets
            pass

        analytics.save()

    @staticmethod
    def _update_keyword_analytics(keyword):
        """
        Update keyword analytics

        Args:
            keyword (str): The keyword to update
        """
        # Get or create keyword record
        keyword_obj, created = KeywordAnalytics.objects.get_or_create(
            keyword=keyword,
            defaults={
                'occurrences': 0,
                'last_seen': timezone.now()
            }
        )

        # Update occurrences and last seen
        keyword_obj.occurrences += 1
        keyword_obj.last_seen = timezone.now()
        keyword_obj.save()

        # Limit the number of keywords we track
        # Delete the least occurring keywords if we exceed the limit
        count = KeywordAnalytics.objects.count()
        if count > MessageAnalyzer.MAX_KEYWORDS:
            # Get the IDs of the least occurring keywords
            to_delete = KeywordAnalytics.objects.order_by('occurrences')[:count - MessageAnalyzer.MAX_KEYWORDS]
            KeywordAnalytics.objects.filter(id__in=[k.id for k in to_delete]).delete()

    @staticmethod
    def _update_user_sent_analytics(username):
        """
        Update user sent message analytics

        Args:
            username (str): The username to update
        """
        # Get or create user activity record
        user_activity, created = UserActivityAnalytics.objects.get_or_create(
            username=username,
            defaults={
                'messages_sent': 0,
                'messages_received': 0,
                'last_activity': timezone.now()
            }
        )

        # Update messages sent and last activity
        user_activity.messages_sent += 1
        user_activity.last_activity = timezone.now()
        user_activity.save()

    @staticmethod
    def _update_user_received_analytics(username):
        """
        Update user received message analytics

        Args:
            username (str): The username to update
        """
        # Get or create user activity record
        user_activity, created = UserActivityAnalytics.objects.get_or_create(
            username=username,
            defaults={
                'messages_sent': 0,
                'messages_received': 0,
                'last_activity': timezone.now()
            }
        )

        # Update messages received and last activity
        user_activity.messages_received += 1
        user_activity.last_activity = timezone.now()
        user_activity.save()

    @classmethod
    def _update_message_lifetime_analytics(cls, lifetime_minutes):
        """
        Update message lifetime analytics

        Args:
            lifetime_minutes (float): The message lifetime in minutes
        """
        # Determine the lifetime range
        lifetime_range = cls._get_lifetime_range(lifetime_minutes)

        # Get or create lifetime analytics record
        lifetime_analytics, created = MessageLifetimeAnalytics.objects.get_or_create(
            lifetime_range=lifetime_range,
            defaults={
                'message_count': 0
            }
        )

        # Update message count
        lifetime_analytics.message_count += 1
        lifetime_analytics.save()

    @staticmethod
    def _get_lifetime_range(minutes):
        """
        Get the lifetime range for a given number of minutes

        Args:
            minutes (float): The number of minutes

        Returns:
            str: The lifetime range
        """
        if minutes < 1:
            return '0-1'
        elif minutes < 5:
            return '1-5'
        elif minutes < 15:
            return '5-15'
        elif minutes < 30:
            return '15-30'
        elif minutes < 60:
            return '30-60'
        elif minutes < 180:
            return '60-180'
        elif minutes < 360:
            return '180-360'
        elif minutes < 720:
            return '360-720'
        elif minutes < 1440:
            return '720-1440'
        else:
            return '1440+'
