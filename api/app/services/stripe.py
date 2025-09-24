from __future__ import annotations

import stripe

from app.core.settings import Settings


class StripeConfigurationError(RuntimeError):
    """Raised when Stripe client configuration is invalid."""


class StripeClient:
    """Small wrapper around the Stripe SDK for checkout and portal flows."""

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise StripeConfigurationError("STRIPE_SECRET_KEY is not configured")
        self._stripe = stripe
        self._stripe.api_key = api_key

    def ensure_customer(self, *, customer_id: str | None, email: str | None) -> str:
        if customer_id:
            return customer_id
        customer = self._stripe.Customer.create(email=email)
        return str(customer["id"])

    def create_checkout_session(
        self,
        *,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        session = self._stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            customer=customer_id,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return str(session["url"])

    def create_billing_portal_session(self, *, customer_id: str, return_url: str) -> str:
        portal = self._stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return str(portal["url"])


def get_stripe_client(settings: Settings) -> StripeClient:
    return StripeClient(settings.stripe_secret_key)


__all__ = ["StripeClient", "StripeConfigurationError", "get_stripe_client"]
