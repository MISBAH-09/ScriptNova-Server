import os

import stripe
from stripe._error import SignatureVerificationError, StripeError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ScriptNova.middleware.auth import require_token
from ScriptNova.models import User


PRO_PLAN = 'pro'
FREE_PLAN = 'free'
ACTIVE_SUBSCRIPTION_STATUSES = {'active', 'trialing'}


def _stripe_get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def _stripe_configured():
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')
    return bool(stripe.api_key)


def _frontend_url():
    return os.getenv('FRONTEND_URL', 'http://localhost:3000').rstrip('/')


def _checkout_line_item():
    price_id = os.getenv('STRIPE_PRO_PRICE_ID')
    if price_id and price_id.startswith('price_'):
        return {'price': price_id, 'quantity': 1}

    line_item = {
        'price_data': {
            'currency': os.getenv('STRIPE_PRO_CURRENCY', 'usd'),
            'unit_amount': int(os.getenv('STRIPE_PRO_AMOUNT_CENTS', '1900')),
            'recurring': {'interval': 'month'},
        },
        'quantity': 1,
    }

    if price_id and price_id.startswith('prod_'):
        line_item['price_data']['product'] = price_id
    else:
        line_item['price_data']['product_data'] = {
            'name': os.getenv('STRIPE_PRO_PRODUCT_NAME', 'ScriptNova Pro')
        }

    return line_item


def _sync_user_subscription(user, subscription_id=None, subscription_status=None):
    user.stripe_subscription_id = subscription_id or user.stripe_subscription_id
    user.stripe_subscription_status = subscription_status or user.stripe_subscription_status
    user.plan = PRO_PLAN if user.stripe_subscription_status in ACTIVE_SUBSCRIPTION_STATUSES else FREE_PLAN
    user.save(update_fields=['plan', 'stripe_subscription_id', 'stripe_subscription_status', 'updated_at'])


class CreateCheckoutSession(APIView):
    @require_token
    def post(self, request):
        if not _stripe_configured():
            return Response(
                {
                    'success': False,
                    'message': 'Stripe is not configured. Add STRIPE_SECRET_KEY to the backend .env file.',
                    'data': None,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        user = request.auth_user

        try:
            if not user.stripe_customer_id:
                customer = stripe.Customer.create(
                    email=user.email,
                    name=f'{user.first_name} {user.last_name}'.strip() or user.username,
                    metadata={'user_id': str(user.id)},
                )
                user.stripe_customer_id = customer.id
                user.save(update_fields=['stripe_customer_id', 'updated_at'])

            session = stripe.checkout.Session.create(
                mode='subscription',
                payment_method_types=['card'],
                customer=user.stripe_customer_id,
                client_reference_id=str(user.id),
                line_items=[_checkout_line_item()],
                success_url=f'{_frontend_url()}/dashboard?checkout=success&session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{_frontend_url()}/?checkout=cancelled#pricing',
                metadata={'user_id': str(user.id), 'plan': PRO_PLAN},
                subscription_data={'metadata': {'user_id': str(user.id), 'plan': PRO_PLAN}},
            )

            return Response(
                {'success': True, 'message': 'Checkout session created', 'data': {'url': session.url}},
                status=status.HTTP_200_OK,
            )
        except StripeError as exc:
            return Response(
                {'success': False, 'message': str(exc), 'data': None},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PaymentStatus(APIView):
    @require_token
    def get(self, request):
        user = request.auth_user
        return Response(
            {
                'success': True,
                'message': 'Payment status fetched',
                'data': {
                    'plan': user.plan,
                    'subscription_status': user.stripe_subscription_status,
                },
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhook(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        if not _stripe_configured():
            return Response({'success': False, 'message': 'Stripe is not configured'}, status=500)

        payload = request.body
        signature = request.META.get('HTTP_STRIPE_SIGNATURE')
        webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

        try:
            if webhook_secret:
                event = stripe.Webhook.construct_event(payload, signature, webhook_secret)
            else:
                event = stripe.Event.construct_from(request.data, stripe.api_key)
        except (ValueError, SignatureVerificationError):
            return Response({'success': False, 'message': 'Invalid webhook payload'}, status=400)

        event_type = _stripe_get(event, 'type')
        obj = event['data']['object']

        try:
            if event_type == 'checkout.session.completed':
                self._handle_checkout_completed(obj)
            elif event_type in {'customer.subscription.created', 'customer.subscription.updated'}:
                self._handle_subscription_updated(obj)
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(obj)
        except StripeError as exc:
            return Response({'success': False, 'message': str(exc)}, status=400)

        return Response({'success': True})

    def _handle_checkout_completed(self, session):
        metadata = _stripe_get(session, 'metadata', {}) or {}
        user_id = _stripe_get(session, 'client_reference_id') or _stripe_get(metadata, 'user_id')
        if not user_id:
            return

        user = User.objects.filter(id=user_id).first()
        if not user:
            return

        subscription_id = _stripe_get(session, 'subscription')
        subscription_status = 'active'

        if subscription_id:
            subscription = stripe.Subscription.retrieve(subscription_id)
            subscription_status = subscription.status

        _sync_user_subscription(user, subscription_id, subscription_status)

    def _handle_subscription_updated(self, subscription):
        metadata = _stripe_get(subscription, 'metadata', {}) or {}
        user_id = _stripe_get(metadata, 'user_id')
        user = User.objects.filter(id=user_id).first() if user_id else None
        customer_id = _stripe_get(subscription, 'customer')
        if not user and customer_id:
            user = User.objects.filter(stripe_customer_id=customer_id).first()
        if user:
            _sync_user_subscription(user, _stripe_get(subscription, 'id'), _stripe_get(subscription, 'status'))

    def _handle_subscription_deleted(self, subscription):
        user = User.objects.filter(stripe_subscription_id=_stripe_get(subscription, 'id')).first()
        if user:
            user.plan = FREE_PLAN
            user.stripe_subscription_status = _stripe_get(subscription, 'status', 'canceled')
            user.save(update_fields=['plan', 'stripe_subscription_status', 'updated_at'])
