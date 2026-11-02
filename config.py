"""Business settings. To reuse the bot for another business, edit only this file."""
import os

BUSINESS_NAME = "Demo Barbershop"
ADDRESS = "1 Main Street"
PHONE = "+1 000 000 0000"
INSTAGRAM = "https://instagram.com/"
WORK_HOURS = (10, 20)          # open 10:00–20:00
SLOT_MINUTES = 60              # length of one booking slot
DAYS_AHEAD = 7                 # how many days ahead clients can book
DAYS_OFF = {6}                 # 0 = Monday … 6 = Sunday

# key: (name shown to clients, price)
SERVICES = {
    "haircut": ("Haircut", 25),
    "beard": ("Beard trim", 15),
    "combo": ("Haircut + beard", 35),
    "kids": ("Kids haircut", 20),
}
CURRENCY = "$"

# Secrets come from environment variables, never from the code
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ["ADMIN_ID"]) if os.environ.get("ADMIN_ID") else None
