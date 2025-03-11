from django.conf import settings
from .models import Payment
import hashlib
import logging

# Set up logging
logger = logging.getLogger(__name__)


class PayUService:
    """Service for handling PayU payment gateway integration."""

    @staticmethod
    def get_payu_url():
        """Get PayU gateway URL based on mode."""
        if settings.PAYU_MODE == "test":
            return "https://sandboxsecure.payu.in/_payment"
        else:
            return "https://secure.payu.in/_payment"

    @staticmethod
    def generate_hash(params):
        """Generate PayU hash for payment verification."""
        # Create hash string
        hash_string = (
            f"{params['key']}|{params['txnid']}|{params['amount']}|{params['productinfo']}|"
            f"{params['firstname']}|{params['email']}|||||||||||{settings.PAYU_MERCHANT_SALT}"
        )

        # Generate SHA512 hash
        return hashlib.sha512(hash_string.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_hash(params):
        """Verify PayU hash from response."""
        # Extract parameters
        status = params.get("status")
        txnid = params.get("txnid")
        amount = params.get("amount")
        productinfo = params.get("productinfo")
        firstname = params.get("firstname")
        email = params.get("email")
        salt = settings.PAYU_MERCHANT_SALT
        response_hash = params.get("hash")

        # Additional parameters from PayU response
        additional_charges = params.get("additionalCharges", "")

        # Construct hash string based on status
        if status == "success":
            # For successful transactions
            if additional_charges:
                hash_string = f"{salt}|{status}|||||||{email}|{firstname}|{productinfo}|{amount}|{txnid}|{additional_charges}"
            else:
                hash_string = f"{salt}|{status}|||||||{email}|{firstname}|{productinfo}|{amount}|{txnid}|"
        else:
            # For failed transactions
            hash_string = f"{salt}|{status}|||||||{email}|{firstname}|{productinfo}|{amount}|{txnid}|"

        # Generate expected hash
        calculated_hash = (
            hashlib.sha512(hash_string.encode("utf-8")).hexdigest().lower()
        )

        # Compare with response hash
        return calculated_hash == response_hash.lower()

    @classmethod
    def create_payment_request(cls, student, amount, month_year):
        """Create a payment request for student."""
        try:
            # Create payment record
            payment = Payment.objects.create(
                student=student, amount=amount, month_year=month_year, status="PENDING"
            )

            # Generate payment parameters
            params = payment.generate_payment_params()

            # Update payment status
            payment.status = "INITIATED"
            payment.save()

            logger.info(
                f"Created payment request: {payment.order_id} for {student.email}"
            )

            return {
                "payment": payment,
                "params": params,
                "url": cls.get_payu_url(),
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error creating payment request: {str(e)}")
            return {"success": False, "error": str(e)}

    @classmethod
    def handle_payment_response(cls, params):
        """Handle payment response from PayU."""
        try:
            # Verify hash
            if not cls.verify_hash(params):
                logger.error(f"Hash verification failed: {params}")
                return {"success": False, "error": "Hash verification failed"}

            # Get transaction details
            txnid = params.get("txnid")
            status = params.get("status")
            amount = params.get("amount")
            payment_mode = params.get("mode")

            # Find payment record
            try:
                payment = Payment.objects.get(order_id=txnid)
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for txnid: {txnid}")
                return {"success": False, "error": "Payment not found"}

            # Update payment record based on status
            if status == "success":
                payment.mark_as_completed(
                    transaction_id=params.get("mihpayid"),
                    payment_method=payment_mode,
                    payment_details=params,
                )

                # Update student status if needed
                student_profile = payment.student.student_profile
                if student_profile.status == "DEMO_ACCEPTED":
                    student_profile.update_status("ACTIVE")

                logger.info(f"Payment successful: {txnid}")

                return {"success": True, "payment": payment, "status": "success"}
            else:
                # Update payment record for failed transaction
                payment.status = "FAILED"
                payment.payment_details = params
                payment.save()

                logger.info(f"Payment failed: {txnid}")

                return {"success": True, "payment": payment, "status": "failed"}

        except Exception as e:
            logger.error(f"Error processing payment response: {str(e)}")
            return {"success": False, "error": str(e)}
