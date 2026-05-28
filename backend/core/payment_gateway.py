"""
Payment Gateway Service
=======================

Stripe payment integration for license system.

Features:
- Payment intent creation and processing
- Subscription management
- Webhook handling for Stripe events
- Invoice generation
- Payment history tracking
- Refund processing
- Customer management
- Comprehensive error handling

Dependencies:
- stripe: Stripe Python SDK

Author: Bob
Version: 1.0.0
"""

import logging
import sqlite3
import json
import hmac
import hashlib
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal

try:
    import stripe
except ImportError as e:
    raise ImportError(
        "Payment gateway requires Stripe SDK. "
        "Install with: pip install stripe"
    ) from e

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class PaymentError(Exception):
    """Base exception for payment errors."""
    pass


class PaymentProcessingError(PaymentError):
    """Raised when payment processing fails."""
    pass


class SubscriptionError(PaymentError):
    """Raised when subscription operation fails."""
    pass


class WebhookVerificationError(PaymentError):
    """Raised when webhook signature verification fails."""
    pass


class InvoiceError(PaymentError):
    """Raised when invoice operation fails."""
    pass


class RefundError(PaymentError):
    """Raised when refund operation fails."""
    pass


# ============================================================================
# PAYMENT GATEWAY CLASS
# ============================================================================

class PaymentGateway:
    """
    Payment Gateway Service
    
    Provides comprehensive Stripe integration:
    - Payment processing
    - Subscription management
    - Webhook handling
    - Invoice generation
    - Refund processing
    - Payment history
    
    Attributes:
        db_path (str): Path to SQLite database
        stripe_api_key (str): Stripe secret API key
        webhook_secret (str): Stripe webhook signing secret
    """
    
    # Supported currencies
    SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP', 'CAD', 'AUD']
    
    # Payment statuses
    PAYMENT_STATUS_PENDING = 'pending'
    PAYMENT_STATUS_COMPLETED = 'completed'
    PAYMENT_STATUS_FAILED = 'failed'
    PAYMENT_STATUS_REFUNDED = 'refunded'
    
    # Subscription statuses
    SUBSCRIPTION_STATUS_ACTIVE = 'active'
    SUBSCRIPTION_STATUS_CANCELLED = 'cancelled'
    SUBSCRIPTION_STATUS_PAST_DUE = 'past_due'
    SUBSCRIPTION_STATUS_TRIALING = 'trialing'
    
    def __init__(
        self,
        db_path: str = "petroflow.db",
        stripe_api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None
    ):
        """
        Initialize Payment Gateway.
        
        Args:
            db_path: Path to SQLite database
            stripe_api_key: Stripe secret API key
            webhook_secret: Stripe webhook signing secret
        """
        self.db_path = Path(db_path)
        self.stripe_api_key = stripe_api_key
        self.webhook_secret = webhook_secret
        
        # Configure Stripe
        if stripe_api_key:
            stripe.api_key = stripe_api_key
            logger.info("Payment gateway initialized with Stripe")
        else:
            logger.warning("Payment gateway initialized without Stripe API key")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}"
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        import secrets
        random_part = secrets.token_hex(4)
        return f"TXN-{timestamp}-{random_part}"
    
    def create_customer(
        self,
        user_id: int,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create Stripe customer.
        
        Args:
            user_id: User ID
            email: Customer email
            name: Customer name
            metadata: Additional metadata
            
        Returns:
            Stripe customer ID
            
        Example:
            >>> gateway = PaymentGateway(stripe_api_key="sk_test_...")
            >>> customer_id = gateway.create_customer(1, "user@example.com", "John Doe")
        """
        try:
            customer_metadata = metadata or {}
            customer_metadata['user_id'] = str(user_id)
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )
            
            logger.info(f"Created Stripe customer: {customer.id} for user_id: {user_id}")
            return customer.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer: {e}")
            return None
    
    def create_payment_intent(
        self,
        user_id: int,
        amount: Decimal,
        currency: str = 'USD',
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Stripe payment intent.
        
        Args:
            user_id: User ID
            amount: Payment amount
            currency: Currency code (USD, EUR, etc.)
            description: Payment description
            metadata: Additional metadata
            customer_id: Stripe customer ID
            
        Returns:
            Dictionary with payment intent details
            
        Raises:
            PaymentProcessingError: If payment intent creation fails
            
        Example:
            >>> gateway = PaymentGateway(stripe_api_key="sk_test_...")
            >>> intent = gateway.create_payment_intent(1, Decimal("29.99"), "USD")
            >>> print(intent['client_secret'])
        """
        try:
            if currency not in self.SUPPORTED_CURRENCIES:
                raise PaymentProcessingError(f"Unsupported currency: {currency}")
            
            # Convert amount to cents
            amount_cents = int(amount * 100)
            
            intent_metadata = metadata or {}
            intent_metadata['user_id'] = str(user_id)
            
            # Create payment intent
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                description=description,
                metadata=intent_metadata,
                customer=customer_id
            )
            
            # Record in database
            conn = self._get_connection()
            cursor = conn.cursor()
            
            transaction_id = self._generate_transaction_id()
            
            cursor.execute("""
                INSERT INTO payments 
                (user_id, amount, currency, status, payment_method, 
                 payment_provider, transaction_id, provider_transaction_id, 
                 description, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, float(amount), currency, self.PAYMENT_STATUS_PENDING,
                'stripe', 'stripe', transaction_id, payment_intent.id,
                description, json.dumps(intent_metadata)
            ))
            
            payment_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(
                f"Created payment intent: {payment_intent.id} "
                f"for user_id: {user_id}, amount: {amount} {currency}"
            )
            
            return {
                'payment_id': payment_id,
                'payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'amount': float(amount),
                'currency': currency,
                'status': payment_intent.status
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            raise PaymentProcessingError(f"Failed to create payment intent: {e}")
        except Exception as e:
            logger.error(f"Error creating payment intent: {e}")
            raise PaymentProcessingError(f"Payment processing error: {e}")
    
    def confirm_payment(
        self,
        payment_intent_id: str
    ) -> bool:
        """
        Confirm payment intent.
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            True if payment confirmed
            
        Example:
            >>> gateway = PaymentGateway(stripe_api_key="sk_test_...")
            >>> gateway.confirm_payment("pi_123456")
            True
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            if payment_intent.status == 'requires_confirmation':
                payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)
            
            # Update database
            conn = self._get_connection()
            cursor = conn.cursor()
            
            status = self.PAYMENT_STATUS_COMPLETED if payment_intent.status == 'succeeded' else self.PAYMENT_STATUS_PENDING
            
            cursor.execute("""
                UPDATE payments 
                SET status = ?, paid_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE provider_transaction_id = ?
            """, (status, payment_intent_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Payment confirmed: {payment_intent_id}, status: {payment_intent.status}")
            return payment_intent.status == 'succeeded'
            
        except stripe.error.StripeError as e:
            logger.error(f"Error confirming payment: {e}")
            return False
    
    def create_subscription(
        self,
        user_id: int,
        license_id: int,
        plan_id: int,
        customer_id: str,
        price_id: str,
        billing_cycle: str = 'monthly',
        trial_days: int = 0
    ) -> Dict[str, Any]:
        """
        Create Stripe subscription.
        
        Args:
            user_id: User ID
            license_id: License ID
            plan_id: Plan ID
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            billing_cycle: 'monthly' or 'yearly'
            trial_days: Trial period in days
            
        Returns:
            Dictionary with subscription details
            
        Raises:
            SubscriptionError: If subscription creation fails
            
        Example:
            >>> gateway = PaymentGateway(stripe_api_key="sk_test_...")
            >>> sub = gateway.create_subscription(1, 1, 2, "cus_123", "price_123")
        """
        try:
            subscription_params = {
                'customer': customer_id,
                'items': [{'price': price_id}],
                'metadata': {
                    'user_id': str(user_id),
                    'license_id': str(license_id),
                    'plan_id': str(plan_id)
                }
            }
            
            if trial_days > 0:
                subscription_params['trial_period_days'] = trial_days
            
            # Create subscription
            subscription = stripe.Subscription.create(**subscription_params)
            
            # Record in database
            conn = self._get_connection()
            cursor = conn.cursor()
            
            current_period_start = datetime.fromtimestamp(subscription.current_period_start)
            current_period_end = datetime.fromtimestamp(subscription.current_period_end)
            
            trial_start = None
            trial_end = None
            if subscription.trial_start and subscription.trial_end:
                trial_start = datetime.fromtimestamp(subscription.trial_start)
                trial_end = datetime.fromtimestamp(subscription.trial_end)
            
            cursor.execute("""
                INSERT INTO subscriptions 
                (user_id, license_id, plan_id, status, billing_cycle,
                 current_period_start, current_period_end, trial_start, trial_end,
                 payment_method, payment_provider_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, license_id, plan_id, subscription.status, billing_cycle,
                current_period_start, current_period_end, trial_start, trial_end,
                'stripe', subscription.id, json.dumps(subscription.metadata)
            ))
            
            subscription_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(
                f"Created subscription: {subscription.id} "
                f"for user_id: {user_id}, license_id: {license_id}"
            )
            
            return {
                'subscription_id': subscription_id,
                'stripe_subscription_id': subscription.id,
                'status': subscription.status,
                'current_period_start': current_period_start.isoformat(),
                'current_period_end': current_period_end.isoformat(),
                'trial_start': trial_start.isoformat() if trial_start else None,
                'trial_end': trial_end.isoformat() if trial_end else None
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating subscription: {e}")
            raise SubscriptionError(f"Failed to create subscription: {e}")
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise SubscriptionError(f"Subscription error: {e}")
    
    def cancel_subscription(
        self,
        subscription_id: int,
        cancel_at_period_end: bool = True
    ) -> bool:
        """
        Cancel subscription.
        
        Args:
            subscription_id: Database subscription ID
            cancel_at_period_end: Cancel at end of billing period
            
        Returns:
            True if successful
            
        Example:
            >>> gateway = PaymentGateway(stripe_api_key="sk_test_...")
            >>> gateway.cancel_subscription(1, cancel_at_period_end=True)
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get Stripe subscription ID
            cursor.execute("""
                SELECT payment_provider_id FROM subscriptions WHERE id = ?
            """, (subscription_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                return False
            
            stripe_subscription_id = result['payment_provider_id']
            
            # Cancel in Stripe
            if cancel_at_period_end:
                subscription = stripe.Subscription.modify(
                    stripe_subscription_id,
                    cancel_at_period_end=True
                )
            else:
                subscription = stripe.Subscription.delete(stripe_subscription_id)
            
            # Update database
            cursor.execute("""
                UPDATE subscriptions 
                SET status = ?, cancel_at_period_end = ?, 
                    cancelled_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (subscription.status, 1 if cancel_at_period_end else 0, subscription_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Cancelled subscription: {subscription_id}")
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False
        except Exception as e:
            logger.error(f"Error cancelling subscription: {e}")
            return False
    
    def process_refund(
        self,
        payment_id: int,
        amount: Optional[Decimal] = None,
        reason: str = "requested_by_customer"
    ) -> bool:
        """
        Process refund for payment.
        
        Args:
            payment_id: Database payment ID
            amount: Refund amount (None for full refund)
            reason: Refund reason
            
        Returns:
            True if successful
            
        Raises:
            RefundError: If refund fails
            
        Example:
            >>> gateway = PaymentGateway(stripe_api_key="sk_test_...")
            >>> gateway.process_refund(1, Decimal("10.00"))
            True
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get payment details
            cursor.execute("""
                SELECT provider_transaction_id, amount, currency 
                FROM payments WHERE id = ?
            """, (payment_id,))
            
            result = cursor.fetchone()
            if not result:
                conn.close()
                raise RefundError("Payment not found")
            
            payment_intent_id = result['provider_transaction_id']
            original_amount = Decimal(str(result['amount']))
            currency = result['currency']
            
            # Determine refund amount
            refund_amount = amount if amount else original_amount
            refund_amount_cents = int(refund_amount * 100)
            
            # Create refund in Stripe
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=refund_amount_cents,
                reason=reason
            )
            
            # Update payment status
            cursor.execute("""
                UPDATE payments 
                SET status = ?, refunded_at = CURRENT_TIMESTAMP, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (self.PAYMENT_STATUS_REFUNDED, payment_id))
            
            conn.commit()
            conn.close()
            
            logger.info(
                f"Processed refund: {refund.id} for payment_id: {payment_id}, "
                f"amount: {refund_amount} {currency}"
            )
            return True
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error processing refund: {e}")
            raise RefundError(f"Failed to process refund: {e}")
        except Exception as e:
            logger.error(f"Error processing refund: {e}")
            raise RefundError(f"Refund error: {e}")
    
    def generate_invoice(
        self,
        user_id: int,
        payment_id: Optional[int] = None,
        subscription_id: Optional[int] = None,
        items: List[Dict[str, Any]] = None,
        subtotal: Decimal = Decimal("0"),
        tax_amount: Decimal = Decimal("0"),
        discount_amount: Decimal = Decimal("0")
    ) -> Dict[str, Any]:
        """
        Generate invoice.
        
        Args:
            user_id: User ID
            payment_id: Payment ID (optional)
            subscription_id: Subscription ID (optional)
            items: Invoice line items
            subtotal: Subtotal amount
            tax_amount: Tax amount
            discount_amount: Discount amount
            
        Returns:
            Dictionary with invoice details
            
        Raises:
            InvoiceError: If invoice generation fails
            
        Example:
            >>> gateway = PaymentGateway()
            >>> items = [{"description": "Pro Plan", "amount": 79.99}]
            >>> invoice = gateway.generate_invoice(1, items=items, subtotal=Decimal("79.99"))
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Generate invoice number
            invoice_number = self._generate_invoice_number()
            
            # Calculate total
            total_amount = subtotal + tax_amount - discount_amount
            
            # Get currency from payment or default to USD
            currency = 'USD'
            if payment_id:
                cursor.execute("SELECT currency FROM payments WHERE id = ?", (payment_id,))
                result = cursor.fetchone()
                if result:
                    currency = result['currency']
            
            # Insert invoice
            cursor.execute("""
                INSERT INTO invoices 
                (user_id, payment_id, subscription_id, invoice_number, status,
                 subtotal, tax_amount, discount_amount, total_amount, currency,
                 items, due_date)
                VALUES (?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id, payment_id, subscription_id, invoice_number,
                float(subtotal), float(tax_amount), float(discount_amount),
                float(total_amount), currency, json.dumps(items or []),
                datetime.utcnow() + timedelta(days=30)
            ))
            
            invoice_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Generated invoice: {invoice_number} for user_id: {user_id}")
            
            return {
                'invoice_id': invoice_id,
                'invoice_number': invoice_number,
                'subtotal': float(subtotal),
                'tax_amount': float(tax_amount),
                'discount_amount': float(discount_amount),
                'total_amount': float(total_amount),
                'currency': currency,
                'status': 'draft'
            }
            
        except Exception as e:
            logger.error(f"Error generating invoice: {e}")
            raise InvoiceError(f"Failed to generate invoice: {e}")
    
    def get_payment_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get payment history for user.
        
        Args:
            user_id: User ID
            limit: Maximum number of records
            offset: Offset for pagination
            
        Returns:
            List of payment records
            
        Example:
            >>> gateway = PaymentGateway()
            >>> history = gateway.get_payment_history(1, limit=10)
            >>> for payment in history:
            ...     print(payment['amount'], payment['status'])
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, amount, currency, status, payment_method,
                       transaction_id, description, paid_at, created_at
                FROM payments
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """, (user_id, limit, offset))
            
            rows = cursor.fetchall()
            conn.close()
            
            payments = []
            for row in rows:
                payments.append({
                    'id': row['id'],
                    'amount': row['amount'],
                    'currency': row['currency'],
                    'status': row['status'],
                    'payment_method': row['payment_method'],
                    'transaction_id': row['transaction_id'],
                    'description': row['description'],
                    'paid_at': row['paid_at'],
                    'created_at': row['created_at']
                })
            
            return payments
            
        except Exception as e:
            logger.error(f"Error getting payment history: {e}")
            return []
    
    def handle_webhook(
        self,
        payload: bytes,
        signature: str
    ) -> Dict[str, Any]:
        """
        Handle Stripe webhook event.
        
        Args:
            payload: Webhook payload
            signature: Stripe signature header
            
        Returns:
            Dictionary with event details
            
        Raises:
            WebhookVerificationError: If signature verification fails
            
        Example:
            >>> gateway = PaymentGateway(webhook_secret="whsec_...")
            >>> event = gateway.handle_webhook(request.body, request.headers['Stripe-Signature'])
        """
        try:
            if not self.webhook_secret:
                raise WebhookVerificationError("Webhook secret not configured")
            
            # Verify webhook signature
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            event_type = event['type']
            event_data = event['data']['object']
            
            logger.info(f"Processing webhook event: {event_type}")
            
            # Handle different event types
            if event_type == 'payment_intent.succeeded':
                self._handle_payment_succeeded(event_data)
            elif event_type == 'payment_intent.payment_failed':
                self._handle_payment_failed(event_data)
            elif event_type == 'customer.subscription.created':
                self._handle_subscription_created(event_data)
            elif event_type == 'customer.subscription.updated':
                self._handle_subscription_updated(event_data)
            elif event_type == 'customer.subscription.deleted':
                self._handle_subscription_deleted(event_data)
            elif event_type == 'invoice.paid':
                self._handle_invoice_paid(event_data)
            elif event_type == 'invoice.payment_failed':
                self._handle_invoice_payment_failed(event_data)
            
            return {
                'event_type': event_type,
                'event_id': event['id'],
                'processed': True
            }
            
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise WebhookVerificationError("Invalid webhook signature")
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            raise PaymentError(f"Webhook processing error: {e}")
    
    # ========================================================================
    # PRIVATE WEBHOOK HANDLERS
    # ========================================================================
    
    def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]):
        """Handle successful payment."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE payments 
                SET status = ?, paid_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE provider_transaction_id = ?
            """, (self.PAYMENT_STATUS_COMPLETED, payment_intent['id']))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Payment succeeded: {payment_intent['id']}")
            
        except Exception as e:
            logger.error(f"Error handling payment succeeded: {e}")
    
    def _handle_payment_failed(self, payment_intent: Dict[str, Any]):
        """Handle failed payment."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE payments 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE provider_transaction_id = ?
            """, (self.PAYMENT_STATUS_FAILED, payment_intent['id']))
            
            conn.commit()
            conn.close()
            
            logger.warning(f"Payment failed: {payment_intent['id']}")
            
        except Exception as e:
            logger.error(f"Error handling payment failed: {e}")
    
    def _handle_subscription_created(self, subscription: Dict[str, Any]):
        """Handle subscription created."""
        logger.info(f"Subscription created: {subscription['id']}")
    
    def _handle_subscription_updated(self, subscription: Dict[str, Any]):
        """Handle subscription updated."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subscriptions 
                SET status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE payment_provider_id = ?
            """, (subscription['status'], subscription['id']))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Subscription updated: {subscription['id']}")
            
        except Exception as e:
            logger.error(f"Error handling subscription updated: {e}")
    
    def _handle_subscription_deleted(self, subscription: Dict[str, Any]):
        """Handle subscription deleted."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE subscriptions 
                SET status = 'cancelled', cancelled_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE payment_provider_id = ?
            """, (subscription['id'],))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Subscription deleted: {subscription['id']}")
            
        except Exception as e:
            logger.error(f"Error handling subscription deleted: {e}")
    
    def _handle_invoice_paid(self, invoice: Dict[str, Any]):
        """Handle invoice paid."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Find invoice by subscription
            subscription_id = invoice.get('subscription')
            if subscription_id:
                cursor.execute("""
                    UPDATE invoices 
                    SET status = 'paid', paid_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE subscription_id IN (
                        SELECT id FROM subscriptions 
                        WHERE payment_provider_id = ?
                    )
                """, (subscription_id,))
                
                conn.commit()
            
            conn.close()
            logger.info(f"Invoice paid: {invoice['id']}")
            
        except Exception as e:
            logger.error(f"Error handling invoice paid: {e}")
    
    def _handle_invoice_payment_failed(self, invoice: Dict[str, Any]):
        """Handle invoice payment failed."""
        logger.warning(f"Invoice payment failed: {invoice['id']}")


# ============================================================================
# UNIT TESTS (as comments for reference)
# ============================================================================

"""
Unit Tests for PaymentGateway

import unittest
from unittest.mock import Mock, patch
import tempfile
import os

class TestPaymentGateway(unittest.TestCase):
    
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.gateway = PaymentGateway(
            db_path=self.db_path,
            stripe_api_key="sk_test_fake"
        )
        
        # Initialize database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Create necessary tables...
        conn.commit()
        conn.close()
    
    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(self.db_path)
    
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent(self, mock_create):
        mock_create.return_value = Mock(
            id='pi_test123',
            client_secret='secret_test',
            status='requires_payment_method'
        )
        
        result = self.gateway.create_payment_intent(
            user_id=1,
            amount=Decimal("29.99"),
            currency='USD'
        )
        
        self.assertIn('payment_intent_id', result)
        self.assertEqual(result['amount'], 29.99)
    
    @patch('stripe.Subscription.create')
    def test_create_subscription(self, mock_create):
        mock_create.return_value = Mock(
            id='sub_test123',
            status='active',
            current_period_start=1234567890,
            current_period_end=1234567890,
            trial_start=None,
            trial_end=None,
            metadata={}
        )
        
        result = self.gateway.create_subscription(
            user_id=1,
            license_id=1,
            plan_id=2,
            customer_id='cus_test',
            price_id='price_test'
        )
        
        self.assertIn('stripe_subscription_id', result)
        self.assertEqual(result['status'], 'active')
    
    def test_generate_invoice(self):
        items = [{"description": "Pro Plan", "amount": 79.99}]
        invoice = self.gateway.generate_invoice(
            user_id=1,
            items=items,
            subtotal=Decimal("79.99")
        )
        
        self.assertIn('invoice_number', invoice)
        self.assertEqual(invoice['subtotal'], 79.99)

if __name__ == '__main__':
    unittest.main()
"""