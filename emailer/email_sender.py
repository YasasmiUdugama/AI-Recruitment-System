

import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('ai_recruitment')


def send_email(to_email, subject, body, html_body=None):
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_body,
            fail_silently=False
        )
        logger.info(f"Email sent successfully to {to_email}")
        return True, ""
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to send email to {to_email}: {error_msg}")
        return False, error_msg


def send_interview_invitation(to_email, candidate_name, interview_token, company_name="Our Company"):

    interview_url = f"http://localhost:8000/interview/{interview_token}/"

    subject = f"Interview Invitation - {company_name}"

    body = f"""Dear {candidate_name},

Congratulations! You have been shortlisted for the next stage of our recruitment process.

We are pleased to invite you to complete an automated online interview. You can access the interview at your convenience within the next 3 days.

Your unique interview link: {interview_url}

Please ensure you have:
- A stable internet connection
- A working webcam and microphone
- A quiet environment

Best Regards,
HR Team
{company_name}
"""

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #2563eb;">Interview Invitation</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>Congratulations! You have been shortlisted for the next stage of our recruitment process.</p>
            <div style="background: #f0f9ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Your Interview Link:</strong></p>
                <a href="{interview_url}" style="display: inline-block; background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Start Interview</a>
                <p style="margin-top: 10px; font-size: 12px; color: #666;">This link is valid for 3 days</p>
            </div>
            <p>Please ensure you have:</p>
            <ul>
                <li>A stable internet connection</li>
                <li>A working webcam and microphone</li>
                <li>A quiet environment</li>
            </ul>
            <p>Best Regards,<br>HR Team<br>{company_name}</p>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, body, html_body)


def send_rejection_email(to_email, candidate_name, company_name="Our Company"):
   
    subject = f"Application Status Update - {company_name}"

    body = f"""Dear {candidate_name},

Thank you for your interest in the position and for taking the time to apply.

After careful consideration, we regret to inform you that we have decided not to move forward with your application at this time.

We appreciate your interest in {company_name} and wish you the very best in your future career endeavors.

Best Regards,
HR Team
{company_name}
"""

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #dc2626;">Application Status Update</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>Thank you for your interest in the position and for taking the time to apply.</p>
            <p>After careful consideration, we regret to inform you that we have decided not to move forward with your application at this time.</p>
            <p>We appreciate your interest in {company_name} and wish you the very best in your future career endeavors.</p>
            <p>Best Regards,<br>HR Team<br>{company_name}</p>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, body, html_body)


def send_selection_email(to_email, candidate_name, position_title="the position", company_name="Our Company"):
    """
    Send selection/congratulations email to candidate

    Returns:
    --------
    tuple : (success, error_message)
    """
    subject = f"Congratulations! Job Offer - {company_name}"

    body = f"""Dear {candidate_name},

Congratulations!

We are delighted to inform you that you have been selected for {position_title} at {company_name}.

Your performance throughout the recruitment process was impressive, and we are excited to welcome you to our team.

Our HR team will contact you shortly with further details regarding the next steps, including your offer letter and onboarding process.

Welcome aboard!

Best Regards,
HR Team
{company_name}
"""

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #16a34a;">Congratulations!</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>We are delighted to inform you that you have been selected for <strong>{position_title}</strong> at {company_name}.</p>
            <div style="background: #f0fdf4; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p>Your performance throughout the recruitment process was impressive, and we are excited to welcome you to our team.</p>
            </div>
            <p>Our HR team will contact you shortly with further details regarding the next steps, including your offer letter and onboarding process.</p>
            <p>Welcome aboard!</p>
            <p>Best Regards,<br>HR Team<br>{company_name}</p>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, body, html_body)


def send_interview_reminder(to_email, candidate_name, interview_token, hours_remaining=24, company_name="Our Company"):
    """
    Send reminder email about upcoming interview expiration

    Returns:
    --------
    tuple : (success, error_message)
    """
    interview_url = f"http://localhost:8000/interview/{interview_token}/"

    subject = f"Interview Reminder - {hours_remaining} Hours Left - {company_name}"

    body = f"""Dear {candidate_name},

This is a friendly reminder that your interview link will expire in approximately {hours_remaining} hours.

Please complete your interview at your earliest convenience.

Your interview link: {interview_url}

Best Regards,
HR Team
{company_name}
"""

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2 style="color: #f59e0b;">Interview Reminder</h2>
            <p>Dear <strong>{candidate_name}</strong>,</p>
            <p>This is a friendly reminder that your interview link will expire in approximately <strong>{hours_remaining} hours</strong>.</p>
            <div style="background: #fffbeb; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <a href="{interview_url}" style="display: inline-block; background: #f59e0b; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px;">Complete Your Interview</a>
            </div>
            <p>Best Regards,<br>HR Team<br>{company_name}</p>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, body, html_body)


def send_hr_notification(hr_email, candidate_name, action, details=""):
    """
    Send notification to HR team

    Returns:
    --------
    tuple : (success, error_message)
    """
    subject = f"HR Notification - Candidate {action}"

    body = f"""HR Team,

This is an automated notification regarding candidate activity.

Candidate: {candidate_name}
Action: {action}
{details}

Please log in to the recruitment system for more details.

Best Regards,
AI Recruitment System
"""

    return send_email(hr_email, subject, body)
