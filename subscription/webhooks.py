import logging
import json
import datetime
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Subscription, SubscriptionPlan, ProcessedWebhookEvent
from .serializers import SubscriptionSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


def _send_subscription_update(subscription):
    """Send real-time subscription update via WebSocket"""
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            serializer = SubscriptionSerializer(subscription)
            user_group_name = f"user_{subscription.user.id}"
            async_to_sync(channel_layer.group_send)(
                user_group_name,
                {
                    "type": "send_subscription_update",
                    "status_data": serializer.data
                }
            )
            logger.info(f"Sent WebSocket update to user {subscription.user.id}")
    except Exception as e:
        logger.error(f"Error sending WebSocket update: {e}")


def _get_plan_from_product_id(product_id):
    """
    Map RevenueCat product_id to SubscriptionPlan
    """
    try:
        plan = SubscriptionPlan.objects.get(
            revenue_cat_product_id=product_id,
            is_active=True
        )
        return plan
    except SubscriptionPlan.DoesNotExist:
        logger.error(f"No active SubscriptionPlan found for product_id: {product_id}")
        
        # Fallback to free plan
        try:
            free_plan = SubscriptionPlan.objects.get(name='free', is_active=True)
            return free_plan
        except SubscriptionPlan.DoesNotExist:
            logger.critical("No free plan configured! Please create a free plan in admin.")
            return None


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def revenuecat_webhook(request):
    """
    Handle RevenueCat webhook events

    Supported event types:
    - INITIAL_PURCHASE: User subscribes for first time
    - RENEWAL: Subscription renewed
    - PRODUCT_CHANGE: User switched plans
    - CANCELLATION: User canceled (but still active until period end)
    - EXPIRATION: Subscription expired
    - BILLING_ISSUE: Payment failed
    - UNCANCELLATION: User reactivated subscription
    """

    # 🔐 Verify webhook authentication
    auth_header = request.headers.get("Authorization")
    expected_header = settings.REVENUECAT_WEBHOOK_AUTH_HEADER

    if not expected_header:
        logger.error("REVENUECAT_WEBHOOK_AUTH_HEADER not configured in settings.")
        return HttpResponseForbidden("Server Configuration Error")

    if auth_header != expected_header:
        logger.warning(f"Invalid webhook auth header: {auth_header}")
        return HttpResponseForbidden("Invalid Authorization")

    # 📦 Parse webhook payload
    try:
        payload = json.loads(request.body)
        event = payload.get('event', {})
        event_id = event.get('id')
        event_type = event.get('type')
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook: {e}")
        return HttpResponseBadRequest("Invalid JSON")

    if not event_id:
        logger.warning("Webhook received without event_id")
        return HttpResponse(status=200)

    # 🔄 Prevent duplicate processing
    try:
        ProcessedWebhookEvent.objects.create(
            event_id=event_id,
            event_type=event_type,
            app_user_id=event.get('app_user_id'),
            raw_data=payload
        )
    except IntegrityError:
        logger.info(f"Event {event_id} already processed. Skipping.")
        return HttpResponse(status=200)

    # 👤 Find user
    app_user_id = event.get('app_user_id')

    try:
        user_id = int(app_user_id)
        user = User.objects.get(id=user_id)
    except (ValueError, TypeError, User.DoesNotExist):
        logger.error(f"User not found for app_user_id: {app_user_id}")
        return HttpResponse(status=200)

    # 📊 Extract subscription data
    product_id = event.get('product_id')
    expiration_at_ms = event.get('expiration_at_ms')
    purchased_at_ms = event.get('purchased_at_ms')
    store = event.get('store')

    logger.info(
        f"Processing {event_type} for user {user.id} | "
        f"product: {product_id} | store: {store}"
    )

    # 🔍 Get or create subscription
    subscription, created = Subscription.objects.get_or_create(
        user=user,
        defaults={
            'plan': SubscriptionPlan.objects.filter(name='free', is_active=True).first(),
            'status': 'inactive',
            'revenue_cat_id': app_user_id
        }
    )

    # 🎯 Handle different event types
    if event_type in ['INITIAL_PURCHASE', 'RENEWAL', 'UNCANCELLATION', 'PRODUCT_CHANGE']:
        plan = _get_plan_from_product_id(product_id)

        if not plan:
            logger.error(f"Could not determine plan for product_id: {product_id}")
            return HttpResponse(status=200)

        subscription.plan = plan
        subscription.status = 'active'
        subscription.revenue_cat_id = app_user_id

        if purchased_at_ms:
            subscription.started_at = datetime.datetime.fromtimestamp(
                purchased_at_ms / 1000.0,
                tz=datetime.timezone.utc
            )
            subscription.current_period_start = subscription.started_at

        if expiration_at_ms:
            subscription.current_period_end = datetime.datetime.fromtimestamp(
                expiration_at_ms / 1000.0,
                tz=datetime.timezone.utc
            )

        if event_type == 'UNCANCELLATION':
            subscription.canceled_at = None

        subscription.save()

        # ✅ যেকোনো paid plan কিনলে role → coach
        if plan.name != 'free' and user.role != 'coach':
            user.role = 'coach'
            user.save(update_fields=['role'])
            logger.info(f"👑 User {user.id} role updated to coach after purchasing {plan.get_name_display()}")

        logger.info(
            f"✅ User {user.id} subscription activated: "
            f"{plan.get_name_display()} ({plan.billing_period or 'one-time'})"
        )

    elif event_type == 'CANCELLATION':
        # User canceled but subscription remains active until period end
        subscription.status = 'canceled'
        subscription.canceled_at = timezone.now()
        subscription.save()

        logger.info(
            f"⚠️ User {user.id} canceled subscription. "
            f"Active until {subscription.current_period_end}"
        )

    elif event_type == 'EXPIRATION':
        free_plan = SubscriptionPlan.objects.filter(name='free', is_active=True).first()

        if free_plan:
            subscription.plan = free_plan
            subscription.status = 'expired'
            subscription.current_period_end = timezone.now()
            subscription.save()

            # ✅ Subscription expire হলে role → player
            if user.role == 'coach':
                user.role = 'player'
                user.save(update_fields=['role'])
                logger.info(f"🔽 User {user.id} role downgraded to player after expiration")

            logger.info(f"❌ User {user.id} subscription expired. Downgraded to free.")
        else:
            logger.error("No free plan available for downgrade!")

    elif event_type == 'BILLING_ISSUE':
        subscription.status = 'inactive'
        subscription.save()

        logger.warning(
            f"💳 Billing issue for user {user.id}. "
            f"Subscription set to inactive."
        )

    else:
        logger.info(f"Unhandled event type: {event_type}")

    # 📡 Send real-time update to user
    _send_subscription_update(subscription)

    return HttpResponse(status=200)