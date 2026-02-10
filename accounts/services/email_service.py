from django.conf import settings
from django.core.mail import send_mail


EMAIL_TEMPLATES = {

    # 1️⃣ SIGNUP CONFIRMATION
    "signup_confirmation": {
        "subject": "Welcome to Asset Kart 🎉 — Let’s Build Your Wealth, Brick by Brick!",
        "body": """
Hi {name},

Welcome aboard Asset Kart, where real estate meets smart investing.
Your investor account is now active and ready for exploration.

Here’s what you can do next:
• Explore curated fractional investment opportunities 🛄
• Track portfolio performance in real time 📜
• Access exclusive pre-launch deals 💼

Login & Start Exploring:
{login_link}

“Every empire starts with one smart investment.”

Cheers,
Team Asset Kart
{website} | {support_email}
"""
    },

    # 2️⃣ ONBOARDING COMPLETION
    "onboarding_completion": {
        "subject": "You’re Officially Onboard! ☀️ Your Investment Dashboard Awaits",
        "body": """
Hi {name},

Congratulations — your onboarding is complete!
Your personal investor dashboard is now live and ready. 

🎯 Inside Your Dashboard:
• Track investments & yields
• Access project documents
• Stay updated on new launches 

👉 Login Now:
{dashboard_link}

“Smart investing isn’t about timing the market — it’s about being early in the right opportunity.”

Warm regards,
Asset Kart Investor Relations
"""
    },

    # 3️⃣ EOI APPROVED
    "eoi_approved": {
        "subject": "Great News! 🎉 Your EOI for {project_name} is Approved",
        "body": """
Hi {name},

Your Expression of Interest for {project_name} has been successfully approved!

What’s next?
💰 Payment details and next steps will be shared shortly.
📈 Once confirmed, your investment will reflect on the dashboard.

Thank you for choosing Asset Kart — India’s new-age real estate investment platform.

“Opportunities don’t wait. You just caught one!”

Warm regards,
Team Asset Kart
"""
    },

    # 4️⃣ PAYMENT RECEIPT
    "payment_receipt": {
        "subject": "Payment Received 💼 — Your Investment in {project_name} is Confirmed",
        "body": """
Hi {name},

We’ve successfully received your payment for {project_name}.
Your investment has been secured and recorded in your dashboard.

You’ll soon receive your Investment Certificate & Agreement within {working_days} working days.

Next:
💡 Track performance, yields, and project progress — all in one place! 

👉 Go to Dashboard:
{dashboard_link}

“Thank you for trusting Asset Kart — where your money works as hard as you do.”

Best regards,
Finance & Investor Relations Team
"""
    },

    # 5️⃣ FEEDBACK REQUEST
    "feedback_request": {
        "subject": "☀️ Help Us Grow — Share Your Investment Experience!",
        "body": """
Hi {name},

Your feedback drives our innovation.
Tell us how your experience with Asset Kart has been so far — good, bad, or brilliant!

📝 Click Here to Share Your Thoughts:
{feedback_link}

It takes less than a minute but makes a big difference.

“Because the best investments grow on trust — and feedback builds trust.”

Warmly,
Customer Experience Team
"""
    },

    # 6️⃣ TICKET GENERATED
    "ticket_generated": {
        "subject": "We’ve Got You Covered! 🎧 Support Ticket #{ticket_number} Created",
        "body": """
Hi {name},

Your support ticket #{ticket_number} has been created.

Our dedicated investor care team is reviewing your query and will respond within {response_time} hours.

💼 Track or update your request:
{dashboard_link}

“At Asset Kart, we don’t just manage investments — we manage relationships.”

Best,
Investor Support Team
"""
    },

    # 7️⃣ TICKET RESOLVED
    "ticket_resolved": {
        "subject": "✅ Your Ticket #{ticket_number} Has Been Resolved",
        "body": """
Hi {name},

Good news — your issue has been successfully resolved!
We hope you’re satisfied with the outcome.

If you need further assistance, you can reply to this email anytime.

Access Support Anytime:
{dashboard_link}

“Peace of mind is the best return on investment.”

Thank you,
Investor Support Team
"""
    },

    # 8️⃣ UPCOMING PRODUCT
    "upcoming_product": {
        "subject": "☀️ Coming Soon: A New Investment Opportunity You’ll Love!",
        "body": """
Hi {name},

Something exciting is coming your way — {project_name}, our upcoming fractional investment!

📍 Location: {location}
💰 Investment Range: {range}
📈 Expected Returns: {returns}% p.a.

✨ Be Among the First:
{interest_link}

“Smart investors don’t wait for opportunity — they join the pre-launch list.”

Warm regards,
Asset Kart Investment Desk
"""
    },

    # 9️⃣ NEW PRODUCT LISTED
    "new_product": {
        "subject": "🎉 New Opportunity Live! Invest in {project_name} Today",
        "body": """
Hi {name},

It’s here!
Our newest investment — {project_name} — is now open for subscription.

🛄 Highlights:
• Location: {location}
• Project Type: {project_type}
• Target IRR: {irr}% p.a.
• Limited Slots Available!

🎯 Act Now – First Come, First Served:
{invest_link}

“Build your wealth portfolio — one smart asset at a time.”

Best,
Asset Kart Investments Team
"""
    },

    "cp_referral_invite": {
        "subject": "🎯 You're Invited to Join AssetKart by {cp_name}!",
        "body": """
Hi there! 👋

{cp_name} has personally invited you to join AssetKart — India's premier fractional real estate investment platform.

🔗 Use this exclusive referral link to sign up:
{invite_link}

Why Join AssetKart?
✅ Invest in premium real estate starting from just ₹10,000
✅ Earn passive rental income
✅ Diversify your portfolio with fractional ownership
✅ Track everything on your personal dashboard

Your referral partner {cp_name} will be there to guide you through your investment journey.

Click here to get started:
{invite_link}

"Smart investors don't wait — they act early."

Questions? Reply to this email or contact us at {support_email}

Warm regards,
Team AssetKart
{website}
"""
    },
    
    'payment_approved': {
        'subject': '✅ Payment Verified - {project_name}',
        'html_body': """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9fafb;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Payment Verified! ✅</h1>
            </div>
            
            <div style="background-color: white; padding: 30px; border-radius: 0 0 10px 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <p style="font-size: 16px; color: #374151; margin-bottom: 20px;">
                    Dear <strong>{name}</strong>,
                </p>
                
                <p style="font-size: 16px; color: #374151; line-height: 1.6;">
                    Great news! We have successfully verified your payment for <strong>{project_name}</strong>.
                </p>
                
                <div style="background-color: #f0fdf4; border-left: 4px solid #10b981; padding: 20px; margin: 25px 0; border-radius: 5px;">
                    <h3 style="color: #065f46; margin-top: 0; margin-bottom: 10px;">What's Next?</h3>
                    <p style="color: #047857; margin: 0; line-height: 1.6;">
                        Your investment application is now under review by our team. You will receive another confirmation email once your Expression of Interest (EOI) is approved, typically within <strong>{working_days} working days</strong>.
                    </p>
                </div>
                
                <p style="font-size: 16px; color: #374151; line-height: 1.6;">
                    You can track the status of your investment anytime through your dashboard.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{dashboard_link}" style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-decoration: none; padding: 14px 35px; border-radius: 8px; font-weight: bold; font-size: 16px;">
                        View Dashboard
                    </a>
                </div>
                
                <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">
                
                <p style="font-size: 14px; color: #6b7280; line-height: 1.6;">
                    If you have any questions or concerns, please don't hesitate to reach out to our support team at <a href="mailto:{support_email}" style="color: #667eea;">{support_email}</a>
                </p>
                
                <p style="font-size: 16px; color: #374151; margin-top: 25px;">
                    Best regards,<br>
                    <strong>AssetKart Team</strong>
                </p>
            </div>
            
            <div style="text-align: center; padding: 20px; font-size: 12px; color: #9ca3af;">
                <p>© 2025 AUM Capital. All rights reserved.</p>
                <p>This is an automated message, please do not reply to this email.</p>
            </div>
        </div>
        """,
        'text_body': """
Dear {name},

✅ Payment Verified!

Great news! We have successfully verified your payment for {project_name}.

WHAT'S NEXT?
Your investment application is now under review by our team. You will receive another confirmation email once your Expression of Interest (EOI) is approved, typically within {working_days} working days.

You can track the status of your investment anytime through your dashboard: {dashboard_link}

If you have any questions or concerns, please reach out to our support team at {support_email}

Best regards,
AssetKart Team

---
© 2025 AUM Capital. All rights reserved.
This is an automated message, please do not reply to this email.
        """
    },

    

     "admin_eoi_notification": {
        "subject": "🔔 New EOI: {user_name} - {project_name}",
        "body": """
New Expression of Interest Received!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Name: {user_name}
- Email: {user_email}
- Phone: {user_phone}
- User ID: {user_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PROPERTY DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Property: {project_name}
- Location: {location}
- Min Investment: {min_investment}
- Units Interested: {units_interested}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Review user's profile and KYC status
2. Contact user via phone/email
3. Approve or reject the EOI from admin panel

View in Admin Panel: {admin_link}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated notification from AUM Capital.
        """
    },

 'cp_application_submitted': {
    'subject': '🎉 We’ve received your Channel Partner application – AssetKart',
    'template': '''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; padding: 20px;">
            
            <!-- HEADER -->
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #2563eb; margin-bottom: 5px;">Application Received 🎉</h2>
                <p style="color: #6b7280; margin-top: 0;">Welcome to the AssetKart Partner Program</p>
            </div>

            <p>Hi <strong>{name}</strong>,</p>
            
            <p>
                Thank you for applying to become a <strong>Channel Partner</strong> with AssetKart.  
                We’ve successfully received your application and it’s now under review.
            </p>

            <!-- APPLICATION DETAILS -->
            <div style="background: #f3f4f6; padding: 16px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #1f2937;">📄 Application Details</h3>
                <p style="margin: 0;">
                    <strong>Application ID:</strong> {application_id}
                </p>
            </div>

            <!-- NEXT STEPS -->
            <div style="background: #fef3c7; padding: 16px; border-left: 4px solid #f59e0b; margin: 20px 0;">
                <h4 style="margin-top: 0; color: #92400e;">🚀 What Happens Next?</h4>
                <ol style="color: #78350f; padding-left: 18px; margin: 0;">
                    <li>Our team reviews your application (2–3 business days)</li>
                    <li>Once approved, your account will be activated</li>
                    <li>You’ll receive access to your CP dashboard and referral tools</li>
                </ol>
            </div>

            <!-- STATUS CARD -->
            <div style="background: #e0f2fe; padding: 16px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #0c4a6e;">
                    <strong>🔒 Account Status:</strong> Pending Approval
                </p>
                <p style="margin: 8px 0 0 0; font-size: 14px; color: #dc2626;">
                    ⚠️ Your account is currently inactive and will be enabled after approval.
                </p>
            </div>

            <!-- CTA BUTTON (EMAIL SAFE) -->
            <div style="text-align: center; margin: 30px 0;">
                <a href="#" 
                   style="
                       background: #2563eb;
                       color: #ffffff;
                       text-decoration: none;
                       padding: 12px 24px;
                       border-radius: 6px;
                       font-weight: bold;
                       display: inline-block;
                   ">
                    Visit AssetKart Website
                </a>
            </div>

            <p>
                If you have any questions, our support team is always happy to help.
            </p>

            <p style="margin-top: 30px;">
                Warm regards,<br>
                <strong>AssetKart Team</strong>
            </p>

            <hr style="border: none; border-top: 1px solid #e5e7eb; margin: 30px 0;">

            <p style="font-size: 12px; color: #6b7280; text-align: center;">
                © {year} AssetKart. All rights reserved.<br>
                This is an automated email — please do not reply.
            </p>
        </div>
    '''
},


'cp_application_approved': {
    'subject': 'Welcome to AssetKart Channel Partner Program! 🎉',
    'html_body': '''
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0;">Congratulations! 🎉</h1>
                <p style="color: #e0f2fe; margin: 10px 0 0 0;">
                    Your Channel Partner application has been approved!
                </p>
            </div>
            
            <div style="padding: 30px; background: #ffffff;">
                <p>Dear {name},</p>
                
                <p>
                    Welcome to the <strong>AssetKart Channel Partner</strong> family!
                    Your application has been approved and your account is now active.
                </p>
                
                <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border: 2px solid #86efac;">
                    <h3 style="margin-top: 0; color: #166534;">✅ Your Account Details</h3>
                    <p><strong>CP Code:</strong> {cp_code}</p>
                    <p><strong>Partner Tier:</strong> 
                        <span style="text-transform: uppercase; color: #2563eb;">{tier}</span>
                    </p>
                    
                    <p><strong>Status:</strong> 
                        <span style="color: #15803d;">Active</span>
                    </p>
                </div>

                <h3 style="color: #1e40af;">🚀 What You Can Do Next</h3>
                <ul style="padding-left: 18px;">
                    <li>Log in to your Channel Partner dashboard</li>
                    <li>Start referring clients and earning commissions</li>
                    <li>Track your leads, conversions, and payouts</li>
                    <li>Access exclusive partner resources and support</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{dashboard_url}" 
                       style="background: #2563eb; color: #ffffff; padding: 12px 24px; 
                              text-decoration: none; border-radius: 6px; font-weight: bold;">
                        Go to CP Dashboard
                    </a>
                </div>

                <p>
                    If you have any questions or need assistance, feel free to reach out to us at
                    <a href="mailto:support@assetkart.com">support@assetkart.com</a>.
                </p>

                <p>
                    We're excited to have you onboard and look forward to a successful partnership!
                </p>

                <p style="margin-top: 30px;">
                    Warm regards,<br>
                    <strong>AssetKart Team</strong>
                </p>
            </div>

            <div style="background: #f8fafc; padding: 15px; text-align: center; font-size: 12px; color: #64748b; border-radius: 0 0 8px 8px;">
                © {year} AssetKart. All rights reserved.
            </div>
        </div>
    ''',
    'text_body': '''
Dear {name},

Congratulations! 🎉

Welcome to the AssetKart Channel Partner family!
Your application has been approved and your account is now active.

Your Account Details:
- CP Code: {cp_code}
- Partner Tier: {tier}
- Status: Active

What You Can Do Next:
- Log in to your Channel Partner dashboard
- Start referring clients and earning commissions
- Track your leads, conversions, and payouts
- Access exclusive partner resources and support

Dashboard: {dashboard_url}

If you have any questions or need assistance, feel free to reach out to us at support@assetkart.com

We're excited to have you onboard and look forward to a successful partnership!

Warm regards,
AssetKart Team

© {year} AssetKart. All rights reserved.
    '''
},


}
 



# def send_dynamic_email(email_type, to, params):
#     if email_type not in EMAIL_TEMPLATES:
#         raise ValueError("Invalid email type.")

#     template = EMAIL_TEMPLATES[email_type]

#     subject = template["subject"].format(**params)
#     body = template["body"].format(**params)
    

#     send_mail(
#         subject=subject,
#         message=body,
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         recipient_list=[to],
#         fail_silently=False,
#     )

#     return {"status": "sent", "email_type": email_type, "to": to}

from django.core.mail import EmailMultiAlternatives
from django.conf import settings


def send_dynamic_email(email_type, to, params):
    if email_type not in EMAIL_TEMPLATES:
        raise ValueError("Invalid email type.")

    template = EMAIL_TEMPLATES[email_type]

    # Subject
    subject = template["subject"].format(**params)

    # Get bodies safely
    text_body = template.get("body") or template.get("text_body")
    html_body = template.get("template") or template.get("html_body")

    if not text_body and not html_body:
        raise ValueError("Email template must contain body or html_body")

    # Format content
    if text_body:
        text_body = text_body.format(**params)

    if html_body:
        html_body = html_body.format(**params)

    # Create email
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body or "Please view this email in HTML format.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to],
    )

    # Attach HTML if available
    if html_body:
        email.attach_alternative(html_body, "text/html")

    email.send(fail_silently=False)

    return {
        "status": "sent",
        "email_type": email_type,
        "to": to,
    }
