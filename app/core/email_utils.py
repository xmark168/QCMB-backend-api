from email.message import EmailMessage
from email.utils import formataddr
import aiosmtplib
from .config import settings

async def send_password_reset_email(recipient: str, otp_code: str):
    msg = EmailMessage()
    msg["Subject"] = "Mã OTP đặt lại mật khẩu"
    # msg["From"] = settings.EMAIL_FROM
    msg["From"] = formataddr(
        (settings.EMAIL_FROM_NAME, settings.EMAIL_FROM)
    )
    # msg["To"] = recipient
    msg["To"] = formataddr(("Quý khách", recipient))
    msg.set_content(
        f"Mã OTP của bạn là: {otp_code}\n"
        f"Mã hết hạn sau {settings.OTP_TTL_MIN} phút.\n\n"
        "Nếu bạn không yêu cầu, vui lòng bỏ qua email này."
    )

    await aiosmtplib.send(
        msg,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=True,  # SMTP qua TLS – OWASP yêu cầu kênh bảo mật :contentReference[oaicite:4]{index=4}
    )