import hashlib
import hmac
import json
from datetime import timedelta

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from .models import Payment, Subscription

PLANS = {
    "starter": {"price": 999, "employees": 10},
    "growth": {"price": 2499, "employees": 50},
    "business": {"price": 4999, "employees": 200},
}
PERIOD_DAYS = 30


def _admin_company(request):
    user = request.user
    if user.role != "admin" or not user.company_id:
        raise PermissionDenied("Only a company admin can manage billing.")
    return user.company


def _sign(message: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


@transaction.atomic
def fulfill(order_id, payment_id):
    payment = Payment.objects.select_for_update().get(razorpay_order_id=order_id)
    if payment.status == Payment.Status.PAID:
        return payment  # already processed (browser callback and webhook can both arrive)
    now = timezone.now()
    payment.status = Payment.Status.PAID
    payment.razorpay_payment_id = payment_id
    payment.paid_at = now
    payment.save()

    sub, _ = Subscription.objects.select_for_update().get_or_create(company=payment.company)
    base = sub.current_period_end if sub.current_period_end and sub.current_period_end > now else now
    sub.plan = payment.plan
    sub.current_period_end = base + timedelta(days=PERIOD_DAYS)
    sub.save()
    return payment


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def subscription(request):
    company = _admin_company(request)
    sub = Subscription.objects.filter(company=company).first()
    return Response({
        "plan": sub.plan.title() if sub and sub.plan else None,
        "status": "active" if sub and sub.is_active else "inactive",
        "current_period_end": sub.current_period_end if sub else None,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_order(request):
    company = _admin_company(request)
    plan_id = request.data.get("plan")
    plan = PLANS.get(plan_id)
    if not plan:
        raise ValidationError({"detail": "Unknown plan."})
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        return Response({"detail": "Payment gateway is not configured."}, status=503)

    amount = plan["price"] * 100  # paise
    try:
        r = requests.post(
            "https://api.razorpay.com/v1/orders",
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET),
            json={
                "amount": amount,
                "currency": "INR",
                "receipt": f"c{company.id}-{int(timezone.now().timestamp())}",
                "notes": {"company_id": str(company.id), "plan": plan_id},
            },
            timeout=15,
        )
    except requests.RequestException:
        return Response({"detail": "Could not reach the payment gateway."}, status=502)
    if r.status_code != 200:
        print("RAZORPAY STATUS:", r.status_code)
        print("RAZORPAY BODY:", r.text)
        try:
            reason = r.json().get("error", {}).get("description", "")
        except ValueError:
            reason = ""
        return Response(
            {"detail": f"Payment gateway rejected the order. {reason}".strip()},
            status=502,
        )

    order = r.json()
    Payment.objects.create(company=company, plan=plan_id, amount=amount, razorpay_order_id=order["id"])
    return Response({
        "order_id": order["id"], "amount": amount, "currency": "INR", "key_id": settings.RAZORPAY_KEY_ID,
    })


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def verify(request):
    company = _admin_company(request)
    order_id = str(request.data.get("razorpay_order_id", ""))
    payment_id = str(request.data.get("razorpay_payment_id", ""))
    signature = str(request.data.get("razorpay_signature", ""))

    if not Payment.objects.filter(razorpay_order_id=order_id, company=company).exists():
        raise ValidationError({"detail": "Unknown order."})
    expected = _sign(f"{order_id}|{payment_id}".encode(), settings.RAZORPAY_KEY_SECRET)
    if not hmac.compare_digest(expected, signature):
        raise ValidationError({"detail": "Payment verification failed."})

    fulfill(order_id, payment_id)
    return Response({"detail": "Payment successful."})


@api_view(["POST"])
@authentication_classes([])
@permission_classes([permissions.AllowAny])
def webhook(request):
    body = request.body
    secret = settings.RAZORPAY_WEBHOOK_SECRET
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not secret or not hmac.compare_digest(_sign(body, secret), signature):
        return Response(status=400)
    try:
        event = json.loads(body)
    except ValueError:
        return Response(status=400)

    if event.get("event") in ("payment.captured", "order.paid"):
        entity = event.get("payload", {}).get("payment", {}).get("entity", {})
        if entity.get("order_id") and entity.get("id"):
            try:
                fulfill(entity["order_id"], entity["id"])
            except Payment.DoesNotExist:
                pass
    return Response(status=200)