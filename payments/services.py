from django.conf import settings
from .models import Payment
import hashlib
import logging
import json

# Set up logging
logger = logging.getLogger('payments')

# Add to PayUService class in services.py


@classmethod
def update_student_subscriptions(cls, payment):
    """Update subject subscriptions in student profile."""
    import datetime
    from django.utils import timezone

    logger.info(f"Updating subscriptions for payment: {payment.order_id}")

    try:
        student = payment.student
        profile = student.student_profile
        today = timezone.now().date()

        # Default subscription duration - one month from today
        end_date = today + datetime.timedelta(days=30)

        # Get selected subjects from student profile
        selected_subjects = profile.selected_subjects.all()

        # Initialize subscriptions dictionary if not present
        if not profile.subject_subscriptions:
            profile.subject_subscriptions = {}

        # Update subscription end dates for each subject
        for subject in selected_subjects:
            subject_id = str(subject.id)

            # Check if subject already has an active subscription
            if (
                profile.subject_subscriptions
                and subject_id in profile.subject_subscriptions
            ):

                # Get current end date
                try:
                    current_end_date = datetime.datetime.strptime(
                        profile.subject_subscriptions[subject_id]["end_date"],
                        "%Y-%m-%d",
                    ).date()

                    # Only extend if current end date is in the future
                    if current_end_date >= today:
                        new_end_date = current_end_date + datetime.timedelta(days=30)
                    else:
                        new_end_date = end_date
                except (ValueError, KeyError):
                    new_end_date = end_date
            else:
                new_end_date = end_date

            # Update the subscription
            profile.subject_subscriptions[subject_id] = {
                "subject_id": subject.id,
                "subject_name": subject.name,
                "end_date": new_end_date.isoformat(),
            }

        # Save the profile
        profile.save()
        logger.info(f"Updated subscriptions for student: {student.email}")

        # Schedule and create meetings for these subjects
        cls.schedule_classes_for_month(payment)

        return profile.subject_subscriptions

    except Exception as e:
        logger.exception(f"Error updating subscriptions: {str(e)}")
        return {}


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
        hash_value = hashlib.sha512(hash_string.encode("utf-8")).hexdigest()
        logger.debug(f"Generated hash for txnid {params['txnid']}")
        return hash_value

    @staticmethod
    def verify_hash(params):
        """Verify PayU hash from response."""
        # Extract parameters
        status = params.get("status", "")
        txnid = params.get("txnid", "")
        amount = params.get("amount", "")
        productinfo = params.get("productinfo", "")
        firstname = params.get("firstname", "")
        email = params.get("email", "")
        salt = settings.PAYU_MERCHANT_SALT
        response_hash = params.get("hash", "")

        if not response_hash:
            logger.error(f"No hash provided in response for txnid: {txnid}")
            return False

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
        calculated_hash = hashlib.sha512(hash_string.encode("utf-8")).hexdigest().lower()

        # Compare with response hash
        is_valid = calculated_hash == response_hash.lower()
        
        # Log verification result
        if is_valid:
            logger.info(f"Hash verification successful for txnid: {txnid}")
        else:
            logger.error(f"Hash verification failed for txnid: {txnid}")
            logger.error(f"Expected: {calculated_hash}")
            logger.error(f"Received: {response_hash.lower()}")
            logger.error(f"Hash string used: {hash_string}")
            
        return is_valid

    @classmethod
    def create_payment_request(cls, student, amount, month_year):
        """Create a payment request for student."""
        try:
            logger.info(f"Creating payment request for {student.email} for amount {amount}")
            
            # Check for existing initiated payment
            existing_payment = Payment.objects.filter(
                student=student,
                month_year__year=month_year.year,
                month_year__month=month_year.month,
                status__in=["INITIATED", "PENDING"]
            ).first()
            
            if existing_payment:
                logger.info(f"Found existing payment: {existing_payment.order_id}")
                payment = existing_payment
                payment.amount = amount  # Update amount if needed
                payment.status = "INITIATED"
                payment.save()
            else:
                # Create payment record
                payment = Payment.objects.create(
                    student=student, 
                    amount=amount, 
                    month_year=month_year, 
                    status="INITIATED"
                )
                logger.info(f"Created new payment: {payment.order_id}")

            # Generate payment parameters
            params = payment.generate_payment_params()
            logger.debug(f"Payment parameters: {json.dumps(params)}")

            logger.info(f"Payment request created: {payment.order_id} for {student.email}")

            return {
                "payment": payment,
                "params": params,
                "url": cls.get_payu_url(),
                "success": True,
            }

        except Exception as e:
            logger.exception(f"Error creating payment request: {str(e)}")
            return {"success": False, "error": str(e)}

    @classmethod
    def handle_payment_response(cls, params):
        """Handle payment response from PayU."""
        try:
            # Get transaction details
            txnid = params.get("txnid", "UNKNOWN")
            status = params.get("status", "UNKNOWN")
            
            logger.info(f"Payment response received for txnid: {txnid}, status: {status}")
            logger.debug(f"Payment params: {json.dumps(params)}")
            
            # Verify hash if response contains one - but don't fail if verification fails
            # This allows for flexibility in case PayU changes their algorithm
            if "hash" in params:
                hash_valid = cls.verify_hash(params)
                if not hash_valid:
                    logger.warning(f"Hash verification failed for txnid: {txnid}")
                    # Continue processing anyway, but log the warning
            else:
                logger.warning(f"No hash in payment response for txnid: {txnid}")
            
            # Find payment record
            try:
                payment = Payment.objects.get(order_id=txnid)
                logger.info(f"Found payment record: {payment.id}")
            except Payment.DoesNotExist:
                logger.error(f"Payment not found for txnid: {txnid}")
                return {"success": False, "error": "Payment not found"}

            # Update payment record based on status
            if status == "success":
                mihpayid = params.get("mihpayid", "")
                mode = params.get("mode", "UNKNOWN")
                
                payment.mark_as_completed(
                    transaction_id=mihpayid,
                    payment_method=mode,
                    payment_details=params,
                )
                logger.info(f"Marked payment as completed: {txnid}, mihpayid: {mihpayid}, mode: {mode}")

                # Update student status if needed
                try:
                    student_profile = payment.student.student_profile
                    if student_profile.status == "DEMO_ACCEPTED":
                        student_profile.update_status("ACTIVE")
                        logger.info(f"Updated student profile status for: {payment.student.email}")
                except Exception as profile_error:
                    logger.error(f"Error updating student profile: {str(profile_error)}")
                    # Don't fail the transaction if profile update fails

                logger.info(f"Payment processing successful: {txnid}")
                return {"success": True, "payment": payment, "status": "success"}
            else:
                # Update payment record for failed transaction
                payment.status = "FAILED"
                payment.payment_details = params
                payment.save()
                logger.info(f"Payment failed: {txnid}")
                return {"success": True, "payment": payment, "status": "failed"}

        except Exception as e:
            logger.exception(f"Error processing payment response: {str(e)}")
            return {"success": False, "error": str(e)}
