# backend/app/email_service.py
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
import os
from dotenv import load_dotenv

load_dotenv()

# Email configuration - MUST be set in .env file for production
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "HYCON Lab Management")


def create_sample_submission_html(submission_data: Dict) -> str:
    """Create beautifully formatted HTML email for sample submission"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f5f5f5;
                margin: 0;
                padding: 20px;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: white;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, #059669 0%, #047857 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: 600;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.95;
                font-size: 14px;
            }}
            .content {{
                padding: 30px;
            }}
            .form-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            .form-table tr {{
                border-bottom: 1px solid #e5e7eb;
            }}
            .form-table tr:last-child {{
                border-bottom: none;
            }}
            .form-table td {{
                padding: 16px 12px;
            }}
            .form-table .label {{
                width: 35%;
                font-weight: 600;
                color: #374151;
                vertical-align: top;
                background-color: #f9fafb;
            }}
            .form-table .value {{
                color: #111827;
                font-size: 15px;
            }}
            .field-number {{
                display: inline-block;
                background-color: #059669;
                color: white;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                text-align: center;
                line-height: 24px;
                font-size: 12px;
                font-weight: 600;
                margin-right: 10px;
            }}
            .footer {{
                background-color: #f9fafb;
                padding: 20px 30px;
                border-top: 3px solid #059669;
                text-align: center;
                color: #6b7280;
                font-size: 13px;
            }}
            .footer strong {{
                color: #374151;
            }}
            .timestamp {{
                color: #6b7280;
                font-size: 13px;
                font-style: italic;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 INTERNAL SAMPLE SUBMISSION FORM</h1>
                <p>New sample submission received from HYCON Lab Management System</p>
            </div>
            
            <div class="content">
                <table class="form-table">
                    <tr>
                        <td class="label">
                            <span class="field-number">1</span>
                            Project
                        </td>
                        <td class="value">{submission_data.get('project', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">2</span>
                            Sample Name
                        </td>
                        <td class="value">{submission_data.get('sample_name', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">3</span>
                            Batch No./ Lot No.
                        </td>
                        <td class="value">{submission_data.get('batch_no', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">4</span>
                            Label claim
                        </td>
                        <td class="value">{submission_data.get('label_claim', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">5</span>
                            Sample Quantity
                        </td>
                        <td class="value">{submission_data.get('sample_quantity', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">6</span>
                            Packaging configuration
                        </td>
                        <td class="value">{submission_data.get('packaging_configuration', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">7</span>
                            Recommended storage
                        </td>
                        <td class="value">{submission_data.get('recommended_storage', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">8</span>
                            Condition
                        </td>
                        <td class="value">{submission_data.get('condition', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">9</span>
                            Tests to be performed
                        </td>
                        <td class="value">{submission_data.get('tests_to_be_performed', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">10</span>
                            Remarks (if any)
                        </td>
                        <td class="value">{submission_data.get('remarks', 'N/A') or 'N/A'}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">11</span>
                            Submitted to (Name & Dept)
                        </td>
                        <td class="value">{submission_data.get('submitted_to', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td class="label">
                            <span class="field-number">12</span>
                            Submitted by (Name & Dept)
                        </td>
                        <td class="value">{submission_data.get('submitted_by', 'N/A')}</td>
                    </tr>
                </table>
                
                <div class="timestamp">
                    Submitted on: {submission_data.get('created_at', 'N/A')}
                </div>
            </div>
            
            <div class="footer">
                <strong>HYCON Lab Management System</strong><br>
                This is an automated notification. Please do not reply to this email.<br>
                For questions, please contact the submitter or lab administrator.
            </div>
        </div>
    </body>
    </html>
    """
    return html


async def send_sample_submission_email(
    recipient_email: str,
    submission_data: Dict
) -> bool:
    """
    Send a formatted sample submission email
    
    Args:
        recipient_email: Email address to send to
        submission_data: Dictionary containing all submission fields
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = f"📋 Sample Submission: {submission_data.get('project', 'New Submission')}"
        message["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        message["To"] = recipient_email
        
        # Create HTML content
        html_content = create_sample_submission_html(submission_data)
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        async with aiosmtplib.SMTP(hostname=SMTP_HOST, port=SMTP_PORT, use_tls=False) as smtp:
            await smtp.starttls()
            await smtp.login(SMTP_USER, SMTP_PASSWORD)
            await smtp.send_message(message)
        
        print(f"✅ Email sent successfully to {recipient_email}")
        return True
    
    except aiosmtplib.SMTPAuthenticationError as e:
        error_msg = f"❌ SMTP Authentication Failed: {str(e)}\n"
        error_msg += "⚠️  Gmail blocks regular passwords. You need an App Password!\n"
        error_msg += "📝 Steps to fix:\n"
        error_msg += "   1. Go to: https://myaccount.google.com/apppasswords\n"
        error_msg += "   2. Generate an App Password for 'Mail'\n"
        error_msg += "   3. Update SMTP_PASSWORD in .env with the 16-character App Password\n"
        error_msg += "   4. Restart the backend server"
        print(error_msg)
        return False
    
    except Exception as e:
        print(f"❌ Error sending email to {recipient_email}: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False


async def test_email_connection() -> bool:
    """Test if email configuration is working"""
    try:
        async with aiosmtplib.SMTP(hostname=SMTP_HOST, port=SMTP_PORT) as smtp:
            await smtp.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"Email connection test failed: {str(e)}")
        return False
