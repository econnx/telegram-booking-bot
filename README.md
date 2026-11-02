# ✂️ Build a Telegram booking bot in 30 minutes

A step-by-step guide to a real, working Telegram bot that lets clients **book appointments** — pick a service,
a day and a free time slot, leave their name and phone — and notifies the owner instantly.

Works for barbershops, nail studios, tutors, photographers — anything sold in time slots.
~250 lines of Python, [aiogram 3](https://docs.aiogram.dev/), SQLite. No server or database setup needed to start.

<!-- demo gif / screenshots go here -->

**What clients can do**

- ✂️ Book: service → day → time → name → phone
- 📅 See and cancel their bookings
- 💈 See services and prices, 📍 contacts

**What the owner gets**

- 🔔 A message for every new booking and cancellation
- `/today` and `/tomorrow` — the day's schedule in one message
- No double bookings: a slot is locked the moment someone takes it

---

## Contents

0. [What you need](#0-what-you-need)
1. [Create the bot in BotFather](#1-create-the-bot-in-botfather)
2. [Get the code running](#2-get-the-code-running)
3. [Make it yours](#3-make-it-yours)
4. [How it works](#4-how-it-works)
5. [Keep it running 24/7](#5-keep-it-running-247)
6. [Ideas to extend it](#6-ideas-to-extend-it)

---

## 0. What you need

- Python **3.10–3.13** (`python3 --version`). Brand-new Python versions can fail to install `aiogram`'s dependencies for a few months — use 3.12 if `pip install` errors out
- A Telegram account
- ~30 minutes

## 1. Create the bot in BotFather

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Choose a display name (e.g. *Demo Barbershop*) and a username ending in `bot` (e.g. `demo_barber_bot`).
3. BotFather replies with a **token** like `123456789:AAH...`. This is the bot's password —
   **never commit it to GitHub or share it.**

Optional but nice: `/setdescription`, `/setuserpic` and `/setcommands` in BotFather.

## 2. Get the code running

```bash
git clone https://github.com/econnx/telegram-booking-bot.git
cd telegram-booking-bot
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Give the bot its token through an environment variable (it is never stored in the code):

```bash
export BOT_TOKEN="123456789:AAH..."      # Windows PowerShell: $env:BOT_TOKEN="..."
python bot.py
```

Open your bot in Telegram and press **Start**. 🎉

### Get booking notifications

1. Send `/id` to your bot — it replies with your Telegram ID.
2. Stop the bot (`Ctrl+C`) and start it again with your ID:

```bash
export ADMIN_ID="your_id"
python bot.py
```

Now every booking and cancellation is sent to you, and `/today` / `/tomorrow` show your schedule.

## 3. Make it yours

Everything about the business lives in [`config.py`](config.py) — you never need to touch the bot logic:

```python
BUSINESS_NAME = "Demo Barbershop"
WORK_HOURS = (10, 20)          # open 10:00–20:00
SLOT_MINUTES = 60              # length of one slot
DAYS_AHEAD = 7                 # how far ahead clients can book
DAYS_OFF = {6}                 # 0 = Monday … 6 = Sunday

SERVICES = {
    "haircut": ("Haircut", 25),
    "beard": ("Beard trim", 15),
}
CURRENCY = "$"
```

Change the texts and buttons in [`bot.py`](bot.py) if you want another language — they're plain strings.

## 4. How it works

```
bot.py      handlers: what the bot answers to each message / button
db.py       SQLite: add, list, cancel bookings
config.py   business settings + secrets from environment variables
```

**The booking flow** is a chain of inline buttons. Each button carries a small piece of data
(`callback_data`) that tells the next handler what was chosen:

```
"✂️ Book"  →  svc:haircut  →  day:2026-11-05  →  time:14:00  →  name  →  phone  →  ✅
```

The choices are remembered between steps with aiogram's **FSM** (finite state machine):
`state.update_data(service=...)`, and later `await state.get_data()`.
Name and phone are free text, so the bot switches into `Booking.name` and then `Booking.phone` states — that's how
it knows the next message is a name and not a random text.

**Free slots** are simple: generate every slot of the working day, then drop the ones in the past and the ones
already in the database:

```python
def free_slots(day):
    busy = db.taken(day)
    t = opening time
    while t < closing time:
        if t is in the future and t not in busy:
            slots.append(t)
        t += SLOT_MINUTES
```

**No double bookings:** the table has `UNIQUE(day, time)`. If two people press the same slot at the same moment,
the second `INSERT` fails and that person is asked to pick another time. The database guarantees it, not the
Python code.

## 5. Keep it running 24/7

`python bot.py` works only while your computer is on. For a real client you need it running all the time:

| Option | Cost | Notes |
|---|---|---|
| Your own computer | free | fine for testing and demos |
| A small VPS (any cloud provider) | a few $ / month | most reliable; run it as a `systemd` service |
| PaaS with a free/cheap tier | free–cheap | check the current limits — free tiers change often |

On a Linux VPS a minimal `systemd` unit looks like this (`/etc/systemd/system/booking-bot.service`):

```ini
[Unit]
Description=Telegram booking bot
After=network-online.target

[Service]
WorkingDirectory=/home/you/telegram-booking-bot
Environment=BOT_TOKEN=123456789:AAH...
Environment=ADMIN_ID=your_id
ExecStart=/home/you/telegram-booking-bot/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now booking-bot
```

## 6. Ideas to extend it

- ⏰ Reminders a day / an hour before the appointment
- 👥 Several masters, each with their own schedule
- ⛔ Owner command to block a day or a slot
- 💳 Prepayment with Telegram payments
- 🌍 Multiple languages based on the user's Telegram language

PRs welcome.

---

Made by [@Econnx1](https://x.com/Econnx1) · MIT License
