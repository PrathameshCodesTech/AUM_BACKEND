from django.conf import settings
from django.core.mail import send_mail


EMAIL_TEMPLATES = {

    # 1️⃣ SIGNUP CONFIRMATION
    "signup_confirmation": {
        "subject": "Welcome to Asset Kart 띙띚띞띟띛띜띝 — Let’s Build Your Wealth, Brick by Brick!",
        "body": """
Hi {name},

Welcome aboard Asset Kart, where real estate meets smart investing.
Your investor account is now active and ready for exploration.

Here’s what you can do next:
• Explore curated fractional investment opportunities 舆誴臶與興臹誵臺誶誷誸臻誹臼舥
• Track portfolio performance in real time 궬궨궭궮궯
• Access exclusive pre-launch deals 굣굤굥굦

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
        "subject": "You’re Officially Onboard! 芖芗芘芙芚芛 Your Investment Dashboard Awaits",
        "body": """
Hi {name},

Congratulations — your onboarding is complete!
Your personal investor dashboard is now live and ready. 蚔蚕蚖蚗蚘蚓

Inside Your Dashboard:
• Track investments & yields
• Access project documents
• Stay updated on new launches 踱踲踰踳

Login Now:
{dashboard_link}

“Smart investing isn’t about timing the market — it’s about being early in the right opportunity.”

Warm regards,
Asset Kart Investor Relations
"""
    },

    # 3️⃣ EOI APPROVED
    "eoi_approved": {
        "subject": "Great News! 薌薍薎薏薐薓 Your EOI for {project_name} is Approved",
        "body": """
Hi {name},

Your Expression of Interest for {project_name} has been successfully approved!

What’s next?
괭괮 Payment details and next steps will be shared shortly.
궧궨궩 Once confirmed, your investment will reflect on the dashboard.

Thank you for choosing Asset Kart — India’s new-age real estate investment platform.

“Opportunities don’t wait. You just caught one!”

Warm regards,
Team Asset Kart
"""
    },

    # 4️⃣ PAYMENT RECEIPT
    "payment_receipt": {
        "subject": "Payment Received 굣굤굥굦 — Your Investment in {project_name} is Confirmed",
        "body": """
Hi {name},

We’ve successfully received your payment for {project_name}.
Your investment has been secured and recorded in your dashboard.

You’ll soon receive your Investment Certificate & Agreement within {working_days} working days.

Next:
Track performance, yields, and project progress — all in one place! 踰踱踲踳

Go to Dashboard:
{dashboard_link}

“Thank you for trusting Asset Kart — where your money works as hard as you do.”

Best regards,
Finance & Investor Relations Team
"""
    },

    # 5️⃣ FEEDBACK REQUEST
    "feedback_request": {
        "subject": "괕괖 Help Us Grow — Share Your Investment Experience!",
        "body": """
Hi {name},

Your feedback drives our innovation.
Tell us how your experience with Asset Kart has been so far — good, bad, or brilliant!

Click Here to Share Your Thoughts:
{feedback_link}

It takes less than a minute but makes a big difference.

“Because the best investments grow on trust — and feedback builds trust.”

Warmly,
Customer Experience Team
"""
    },

    # 6️⃣ TICKET GENERATED
    "ticket_generated": {
        "subject": "We’ve Got You Covered! 虙虚虛虜虝 Support Ticket #{ticket_number} Created",
        "body": """
Hi {name},

Your support ticket #{ticket_number} has been created.

Our dedicated investor care team is reviewing your query and will respond within {response_time} hours.

Track or update your request:
{dashboard_link}

“At Asset Kart, we don’t just manage investments — we manage relationships.”

Best,
Investor Support Team
"""
    },

    # 7️⃣ TICKET RESOLVED
    "ticket_resolved": {
        "subject": "Your Ticket #{ticket_number} Has Been Resolved",
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
        "subject": "芖芗芘芙芚芛 Coming Soon: A New Investment Opportunity You’ll Love!",
        "body": """
Hi {name},

Something exciting is coming your way — {project_name}, our upcoming fractional investment!

Location: {location}
Investment Range: {range}
Expected Returns: {returns}% p.a.

Be Among the First:
{interest_link}

“Smart investors don’t wait for opportunity — they join the pre-launch list.”

Warm regards,
Asset Kart Investment Desk
"""
    },

    # 9️⃣ NEW PRODUCT LISTED
    "new_product": {
        "subject": "띛띜띝띙띚띞띟 New Opportunity Live! Invest in {project_name} Today",
        "body": """
Hi {name},

It’s here!
Our newest investment — {project_name} — is now open for subscription.

Highlights:
• Location: {location}
• Project Type: {project_type}
• Target IRR: {irr}% p.a.
• Limited Slots Available!

Act Now – First Come, First Served:
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
    }

}


def send_dynamic_email(email_type, to, params):
    if email_type not in EMAIL_TEMPLATES:
        raise ValueError("Invalid email type.")

    template = EMAIL_TEMPLATES[email_type]

    subject = template["subject"].format(**params)
    body = template["body"].format(**params)

    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )

    return {"status": "sent", "email_type": email_type, "to": to}
