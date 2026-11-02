"""Telegram bot for booking appointments (barbershop, salon, tutor — anything sold in time slots)."""
import asyncio
import logging
import sys
from datetime import date, datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton,
                           Message, ReplyKeyboardMarkup)

import config
import db

dp = Dispatcher()
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

MENU = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
    [KeyboardButton(text="✂️ Book")],
    [KeyboardButton(text="💈 Services & prices"), KeyboardButton(text="📅 My bookings")],
    [KeyboardButton(text="📍 Contacts")],
])


class Booking(StatesGroup):
    name = State()
    phone = State()


def ikb(rows) -> InlineKeyboardMarkup:
    """Inline keyboard from rows of (text, callback_data)."""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t, d in row]
                                                 for row in rows])


def price(p) -> str:
    return f"{config.CURRENCY}{p}"


def fmt_day(day: str) -> str:
    d = date.fromisoformat(day)
    return f"{WEEKDAYS[d.weekday()]} {d:%d.%m}"


def free_slots(day: str, now: datetime | None = None) -> list[str]:
    """Slots of the day that are in the future and not booked yet."""
    start, end = config.WORK_HOURS
    now = now or datetime.now()
    busy = db.taken(day)
    slots = []
    t = datetime.combine(date.fromisoformat(day), datetime.min.time()).replace(hour=start)
    while t.hour < end:
        if t > now and t.strftime("%H:%M") not in busy:
            slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=config.SLOT_MINUTES)
    return slots


def services_keyboard() -> InlineKeyboardMarkup:
    return ikb([[(f"{name} · {price(p)}", f"svc:{key}")] for key, (name, p) in config.SERVICES.items()])


@dp.message(CommandStart())
async def start(m: Message, state: FSMContext):
    await state.clear()
    await m.answer(f"Welcome to <b>{config.BUSINESS_NAME}</b>! 👋\n"
                   "Book an appointment in a few taps.", reply_markup=MENU)


@dp.message(Command("id"))
async def my_id(m: Message):
    await m.answer(f"Your Telegram ID: <code>{m.from_user.id}</code>")


@dp.message(F.text == "💈 Services & prices")
async def prices(m: Message):
    lines = [f"• {name} — <b>{price(p)}</b>" for name, p in config.SERVICES.values()]
    await m.answer("💈 <b>Services</b>\n\n" + "\n".join(lines))


@dp.message(F.text == "📍 Contacts")
async def contacts(m: Message):
    start_h, end_h = config.WORK_HOURS
    await m.answer(f"📍 {config.ADDRESS}\n📞 {config.PHONE}\n🕒 Daily {start_h}:00–{end_h}:00\n"
                   f"📸 {config.INSTAGRAM}")


@dp.message(F.text == "✂️ Book")
async def choose_service(m: Message, state: FSMContext):
    await state.clear()
    await m.answer("Pick a service:", reply_markup=services_keyboard())


@dp.callback_query(F.data.startswith("svc:"))
async def choose_day(c: CallbackQuery, state: FSMContext):
    await state.update_data(service=c.data[4:])
    days = []
    for i in range(config.DAYS_AHEAD + 1):
        d = date.today() + timedelta(days=i)
        if d.weekday() not in config.DAYS_OFF and free_slots(d.isoformat()):
            days.append((fmt_day(d.isoformat()), f"day:{d.isoformat()}"))
    if not days:
        await c.message.edit_text("Sorry, no free slots in the coming days 😔")
        return
    rows = [days[i:i + 3] for i in range(0, len(days), 3)]
    await c.message.edit_text("Pick a day:", reply_markup=ikb(rows + [[("⬅️ Back", "back:svc")]]))


@dp.callback_query(F.data == "back:svc")
async def back_to_service(c: CallbackQuery):
    await c.message.edit_text("Pick a service:", reply_markup=services_keyboard())


@dp.callback_query(F.data.startswith("day:"))
async def choose_time(c: CallbackQuery, state: FSMContext):
    day = c.data[4:]
    await state.update_data(day=day)
    slots = free_slots(day)
    if not slots:
        await c.answer("This day is fully booked", show_alert=True)
        return
    btns = [(s, f"time:{s}") for s in slots]
    rows = [btns[i:i + 4] for i in range(0, len(btns), 4)]
    data = await state.get_data()
    await c.message.edit_text(f"{fmt_day(day)} — pick a time:",
                              reply_markup=ikb(rows + [[("⬅️ Back", f"svc:{data['service']}")]]))


@dp.callback_query(F.data.startswith("time:"))
async def ask_name(c: CallbackQuery, state: FSMContext):
    await state.update_data(time=c.data[5:])
    await c.message.edit_text("What's your name? 🙂")
    await state.set_state(Booking.name)


@dp.message(Booking.name, F.text)
async def ask_phone(m: Message, state: FSMContext):
    await state.update_data(name=m.text.strip()[:50])
    kb = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, keyboard=[
        [KeyboardButton(text="📱 Share my number", request_contact=True)]])
    await m.answer("Share your phone number with the button below, or type it:", reply_markup=kb)
    await state.set_state(Booking.phone)


@dp.message(Booking.name)
async def name_not_text(m: Message):
    await m.answer("Please type your name as text 🙂")


@dp.message(Booking.phone)
async def confirm(m: Message, state: FSMContext, bot: Bot):
    phone = m.contact.phone_number if m.contact else (m.text or "").strip()
    if sum(ch.isdigit() for ch in phone) < 9:
        await m.answer("That doesn't look like a phone number. Try again 🙏")
        return
    data = await state.get_data()
    await state.clear()
    service_name, p = config.SERVICES[data["service"]]
    if not db.add(m.from_user.id, data["name"], phone, data["service"], data["day"], data["time"]):
        await m.answer("Oops, someone just took this slot 😔 Please pick another one.", reply_markup=MENU)
        return
    when = f"{fmt_day(data['day'])} at {data['time']}"
    await m.answer(f"✅ <b>You're booked!</b>\n\n{service_name} — {price(p)}\n🗓 {when}\n📍 {config.ADDRESS}\n\n"
                   "You can cancel in «📅 My bookings».", reply_markup=MENU)
    if config.ADMIN_ID:
        await bot.send_message(config.ADMIN_ID, f"🆕 New booking\n\n{service_name}\n🗓 {when}\n"
                                                f"👤 {data['name']}\n📞 {phone}")


@dp.message(F.text == "📅 My bookings")
async def my_bookings(m: Message):
    rows = db.of_user(m.from_user.id, date.today().isoformat())
    if not rows:
        await m.answer("You have no bookings yet. Tap «✂️ Book» 🙂")
        return
    for bid, svc, day, time in rows:
        await m.answer(f"{config.SERVICES[svc][0]}\n🗓 {fmt_day(day)} at {time}",
                       reply_markup=ikb([[("❌ Cancel", f"cancel:{bid}")]]))


@dp.callback_query(F.data.startswith("cancel:"))
async def cancel(c: CallbackQuery, bot: Bot):
    row = db.cancel(int(c.data[7:]), c.from_user.id)
    if not row:
        await c.answer("Already cancelled")
        return
    svc, day, time = row
    await c.message.edit_text(f"❌ Cancelled: {config.SERVICES[svc][0]}, {fmt_day(day)} at {time}")
    if config.ADMIN_ID:
        await bot.send_message(config.ADMIN_ID, f"❌ A client cancelled\n{config.SERVICES[svc][0]}\n"
                                                f"🗓 {fmt_day(day)} at {time}")


@dp.message(Command("today", "tomorrow"))
async def admin_day(m: Message):
    """Owner only: list of bookings for today / tomorrow."""
    if m.from_user.id != config.ADMIN_ID:
        return
    d = date.today() + timedelta(days=1 if m.text.startswith("/tomorrow") else 0)
    rows = db.on_day(d.isoformat())
    if not rows:
        await m.answer(f"{fmt_day(d.isoformat())}: no bookings")
        return
    lines = [f"{t} — {config.SERVICES[s][0]}, {n}, {p}" for t, n, p, s in rows]
    await m.answer(f"<b>{fmt_day(d.isoformat())}</b>\n\n" + "\n".join(lines))


async def main():
    if not config.BOT_TOKEN:
        sys.exit("Set the BOT_TOKEN environment variable first (see README, step 1).")
    logging.basicConfig(level=logging.INFO)
    bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
