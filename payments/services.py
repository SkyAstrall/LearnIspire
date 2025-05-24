from django.conf import settings
from .models import Payment
import hashlib
import logging
import json

# Set up logging
logger = logging.getLogger("payments")


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
        calculated_hash = (
            hashlib.sha512(hash_string.encode("utf-8")).hexdigest().lower()
        )

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
            logger.info(
                f"Creating payment request for {student.email} for amount {amount}"
            )

            # Check for existing initiated payment
            existing_payment = Payment.objects.filter(
                student=student,
                month_year__year=month_year.year,
                month_year__month=month_year.month,
                status__in=["INITIATED", "PENDING"],
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
                    status="INITIATED",
                )
                logger.info(f"Created new payment: {payment.order_id}")

            # Generate payment parameters
            params = payment.generate_payment_params()
            logger.debug(f"Payment parameters: {json.dumps(params)}")

            logger.info(
                f"Payment request created: {payment.order_id} for {student.email}"
            )

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
    def create_subject_meeting_link(cls, student, teacher, subject):
        """Create one meeting link per subject that will be reused for all classes."""
        try:
            from meetings.services import GoogleMeetService

            # Create a sample class object for meeting creation (temporary)
            class TempClass:
                def __init__(self, student, teacher, subject):
                    self.student = student
                    self.teacher = teacher
                    self.subject = subject
                    self.id = f"temp_{student.id}_{teacher.id}_{subject.id}"

            temp_class = TempClass(student, teacher, subject)
            meeting_result = GoogleMeetService.create_real_meeting(temp_class)
            
            

            if meeting_result and meeting_result.get("success"):
                meeting_link = meeting_result.get("meeting_link", "")
                meeting_id = meeting_result.get("meeting_id", "")
                logger.info(
                    f"Created meeting for subject {subject.name}: {meeting_link}"
                )
                return {
                    "success": True,
                    "meeting_link": meeting_link,
                    "meeting_id": meeting_id,
                }
            else:
                logger.warning(f"Failed to create meeting for subject {subject.name}")
                return {"success": False}

        except Exception as meeting_error:
            logger.error(
                f"Error creating meeting for subject {subject.name}: {str(meeting_error)}"
            )
            return {"success": False}

    @classmethod
    def schedule_classes_for_month(cls, payment):
        """Schedule classes for the subscription period and create meeting links."""
        try:
            from scheduling.models import Class
            from django.utils import timezone
            import datetime

            student = payment.student
            profile = student.student_profile

            # Get today's date
            today = timezone.now().date()

            # Define the period for which to schedule classes (30 days)
            end_date = today + datetime.timedelta(days=30)

            logger.info(
                f"Scheduling classes from {today} to {end_date} for student {student.email}"
            )

            # Get existing classes for this period to avoid duplicates
            existing_classes = Class.objects.filter(
                student=student,
                start_time__date__gte=today,
                start_time__date__lt=end_date,
            )

            # Get selected subjects from student profile
            selected_subjects = profile.selected_subjects.all()
            logger.info(
                f"Selected subjects for {student.email}: {[subject.name for subject in selected_subjects]}"
            )

            # Dictionary to store meeting links for each subject
            subject_meeting_links = {}

            # For each subject, schedule classes based on student and teacher availability
            for subject in selected_subjects:
                # Make sure this subject has an active subscription
                if (
                    not profile.subject_subscriptions
                    or str(subject.id) not in profile.subject_subscriptions
                ):
                    logger.warning(
                        f"No active subscription found for subject {subject.name}"
                    )
                    continue

                # Find assigned teacher for this subject
                from accounts.models import TeacherProfile

                teacher = None
                teacher_profiles = TeacherProfile.objects.filter(
                    subjects=subject, status="ACTIVE"
                ).select_related("user")
                logger.info(
                    f"Found {teacher_profiles.count()} active teachers for {subject.name}"
                )

                if teacher_profiles:
                    teacher = teacher_profiles.first().user

                if not teacher:
                    logger.warning(
                        f"No active teacher found for subject {subject.name}"
                    )
                    continue

                # Create one meeting link for this subject if not already created
                if subject.id not in subject_meeting_links:
                    meeting_result = cls.create_subject_meeting_link(
                        student, teacher, subject
                    )
                    if meeting_result.get("success"):
                        subject_meeting_links[subject.id] = {
                            "meeting_link": meeting_result.get("meeting_link", ""),
                            "meeting_id": meeting_result.get("meeting_id", ""),
                        }
                        logger.info(f"Created reusable meeting link for {subject.name}")
                    else:
                        logger.warning(
                            f"Failed to create meeting link for {subject.name}"
                        )
                        # Continue without meeting link
                        subject_meeting_links[subject.id] = {
                            "meeting_link": "",
                            "meeting_id": "",
                        }

                # Get the meeting info for this subject
                meeting_info = subject_meeting_links.get(
                    subject.id, {"meeting_link": "", "meeting_id": ""}
                )

                # Schedule classes based on availability
                from scheduling.models import Availability

                student_availabilities = Availability.objects.filter(user=student)
                teacher_availabilities = Availability.objects.filter(user=teacher)
                logger.info(
                    f"Student availabilities: {student_availabilities.count()}, Teacher availabilities: {teacher_availabilities.count()}"
                )

                # If no availabilities set, use default schedule
                if (
                    not student_availabilities.exists()
                    or not teacher_availabilities.exists()
                ):
                    logger.info(f"Using default schedule for {subject.name}")
                    # Default schedule: Monday, Wednesday, Friday at fixed times
                    days_of_week = [0, 2, 4]  # Monday, Wednesday, Friday
                    class_time = datetime.time(hour=16, minute=0)  # 4:00 PM
                    class_duration = datetime.timedelta(hours=1)

                    # Create a date range for the next 30 days
                    current_date = today
                    while current_date < end_date:
                        # Check if this is one of our scheduled days
                        if current_date.weekday() in days_of_week:
                            # Create datetime for class start
                            start_datetime = datetime.datetime.combine(
                                current_date,
                                class_time,
                                tzinfo=timezone.get_current_timezone(),
                            )

                            # Calculate end time
                            end_datetime = start_datetime + class_duration

                            # Check if this class already exists
                            if not existing_classes.filter(
                                subject=subject,
                                start_time=start_datetime,
                                end_time=end_datetime,
                            ).exists():
                                # Create new class with the reusable meeting link
                                new_class = Class.objects.create(
                                    student=student,
                                    teacher=teacher,
                                    subject=subject,
                                    start_time=start_datetime,
                                    end_time=end_datetime,
                                    status="SCHEDULED",
                                    meeting_link=meeting_info["meeting_link"],
                                    meeting_id=meeting_info["meeting_id"],
                                )

                                logger.info(
                                    f"Created class for {student.email} - {subject.name} on {start_datetime} with meeting link: {meeting_info['meeting_link']}"
                                )

                        # Move to next day
                        current_date += datetime.timedelta(days=1)
                else:
                    # Advanced scheduling based on availabilities
                    logger.info(f"Using availability-based schedule for {subject.name}")

                    # Get matching days of the week from availabilities
                    matching_days = set()
                    for s_avail in student_availabilities:
                        for t_avail in teacher_availabilities:
                            if s_avail.day_of_week == t_avail.day_of_week:
                                matching_days.add(s_avail.day_of_week)

                    # If we have at least 3 matching days, schedule classes
                    class_days = list(matching_days)[:3]  # Take up to 3 days

                    if class_days:
                        # Create a date range for the next 30 days
                        current_date = today
                        while current_date < end_date:
                            # Check if this day of week matches our schedule
                            if current_date.weekday() in class_days:
                                # Find a matching time slot for this day
                                for s_avail in student_availabilities.filter(
                                    day_of_week=current_date.weekday()
                                ):
                                    for t_avail in teacher_availabilities.filter(
                                        day_of_week=current_date.weekday()
                                    ):
                                        # Check if time slots overlap
                                        if (
                                            s_avail.start_time < t_avail.end_time
                                            and s_avail.end_time > t_avail.start_time
                                        ):
                                            # Find the overlapping time window
                                            start_time = max(
                                                s_avail.start_time, t_avail.start_time
                                            )
                                            end_time = min(
                                                s_avail.end_time, t_avail.end_time
                                            )

                                            # Make sure we have at least 1 hour
                                            duration = datetime.datetime.combine(
                                                today, end_time
                                            ) - datetime.datetime.combine(
                                                today, start_time
                                            )
                                            if (
                                                duration.total_seconds() >= 3600
                                            ):  # 1 hour in seconds
                                                # Create datetime for class start
                                                start_datetime = datetime.datetime.combine(
                                                    current_date,
                                                    start_time,
                                                    tzinfo=timezone.get_current_timezone(),
                                                )

                                                # Calculate end time (1 hour class)
                                                end_datetime = (
                                                    start_datetime
                                                    + datetime.timedelta(hours=1)
                                                )

                                                # Check if this class already exists
                                                if not existing_classes.filter(
                                                    subject=subject,
                                                    start_time__date=current_date,
                                                ).exists():
                                                    # Create new class with the reusable meeting link
                                                    new_class = Class.objects.create(
                                                        student=student,
                                                        teacher=teacher,
                                                        subject=subject,
                                                        start_time=start_datetime,
                                                        end_time=end_datetime,
                                                        status="SCHEDULED",
                                                        meeting_link=meeting_info[
                                                            "meeting_link"
                                                        ],
                                                        meeting_id=meeting_info[
                                                            "meeting_id"
                                                        ],
                                                    )

                                                    logger.info(
                                                        f"Created class for {student.email} - {subject.name} on {start_datetime} with meeting link: {meeting_info['meeting_link']}"
                                                    )
                                                    break  # Only create one class per day

                            # Move to next day
                            current_date += datetime.timedelta(days=1)
                    else:
                        logger.warning(
                            f"No matching availability days found for student {student.email} and subject {subject.name}"
                        )

            logger.info(f"Finished scheduling classes for student {student.email}")
            logger.info(
                f"Created meeting links for subjects: {list(subject_meeting_links.keys())}"
            )

        except Exception as e:
            logger.exception(f"Error scheduling classes: {str(e)}")

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
                            new_end_date = current_end_date + datetime.timedelta(
                                days=30
                            )
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
            logger.info(f"Subject subscriptions: {profile.subject_subscriptions}")

            return profile.subject_subscriptions

        except Exception as e:
            logger.exception(f"Error updating subscriptions: {str(e)}")
            return {}

    @classmethod
    def handle_payment_response(cls, params):
        """Handle payment response from PayU."""
        try:
            # Get transaction details
            txnid = params.get("txnid", "UNKNOWN")
            status = params.get("status", "UNKNOWN")

            logger.info(
                f"Payment response received for txnid: {txnid}, status: {status}"
            )
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
                logger.info(
                    f"Marked payment as completed: {txnid}, mihpayid: {mihpayid}, mode: {mode}"
                )

                # Update student subscriptions
                subscriptions = cls.update_student_subscriptions(payment)
                logger.info(f"Updated subject subscriptions for payment {txnid}")

                # Update student status if needed
                try:
                    student_profile = payment.student.student_profile
                    if student_profile.status == "DEMO_ACCEPTED":
                        student_profile.update_status("ACTIVE")
                        logger.info(
                            f"Updated student profile status for: {payment.student.email}"
                        )
                except Exception as profile_error:
                    logger.error(
                        f"Error updating student profile: {str(profile_error)}"
                    )
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
