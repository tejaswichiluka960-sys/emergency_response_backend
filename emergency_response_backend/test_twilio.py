import os
from pathlib import Path
from dotenv import load_dotenv
from twilio.rest import Client

def send_test_sms():
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")
    to_number = "+918919875820"

    if not account_sid or not auth_token or not from_number:
        print("Error: Missing TWILIO credentials in .env")
        return

    client = Client(account_sid, auth_token)

    message = client.messages.create(
        body="sms_appointment_reminders",
        from_=from_number,
        to=to_number
    )

    print("Message sent successfully!")
    print("Message SID:", message.sid)

if __name__ == "__main__":
    send_test_sms()