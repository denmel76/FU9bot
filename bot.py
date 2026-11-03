import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN, ADMIN_ID, MENU_CATEGORIES, MENU_ITEMS, TEXTS
from database import init_db, save_booking, get_user_bookings, cancel_booking, get_all_active_bookings

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class BookingState(StatesGroup):
    waiting_for_name = State()
    waiting_for_time = State()
    waiting_for_guests = State()

# --- ГЛАВНОЕ МЕНЮ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Меню", callback_data="menu")],
        [InlineKeyboardButton(text="📅 Забронировать столик", callback_data="book")],
        [InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact")]
    ])
    await message.answer(TEXTS["start"], reply_markup=keyboard)

# --- МЕНЮ (Просмотр блюд) ---
@dp.callback_query(F.data == "menu")
async def show_menu_categories(callback: CallbackQuery):
    buttons = []
    for key, value in MENU_CATEGORIES.items():
        buttons.append([InlineKeyboardButton(text=value, callback_data=f"cat_{key}")])
    
    await callback.message.edit_text(TEXTS["choose_category"], reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("cat_"))
async def show_category_items(callback: CallbackQuery):
    cat_key = callback.data.split("_")[1]
    items = MENU_ITEMS.get(cat_key, [])
    
    text = f"*{MENU_CATEGORIES[cat_key]}*\n\n"
    for item in items:
        text += f"• {item}\n"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")]]))
    await callback.answer()

# --- БРОНИРОВАНИЕ ---
@dp.callback_query(F.data == "book")
async def start_booking(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваше имя:")
    await state.set_state(BookingState.waiting_for_name)
    await callback.answer()

@dp.message(BookingState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(TEXTS["book_table"])
    await state.set_state(BookingState.waiting_for_time)

@dp.message(BookingState.waiting_for_time)
async def process_time(message: types.Message, state: FSMContext):
    await state.update_data(time=message.text)
    await message.answer(TEXTS["enter_guests"])
    await state.set_state(BookingState.waiting_for_guests)

@dp.message(BookingState.waiting_for_guests)
async def process_guests(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите число (например, 2).")
        return
    
    user_data = await state.get_data()
    name = user_data['name']
    time = user_data['time']
    guests = int(message.text)
    
    await save_booking(message.from_user.id, name, time, guests)
    
    # Уведомление админу
    admin_text = f"🍽 **Новая бронь!**\n\n👤 Имя: {name}\n⏰ Время: {time}\n👥 Гостей: {guests}\n🆔 Клиент ID: {message.from_user.id}"
    if ADMIN_ID != 0:
        try:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Ошибка отправки админу: {e}")
    
    await message.answer(TEXTS["success"].format(time=time, guests=guests))
    await state.clear()

# --- МОИ БРОНИ ---
@dp.callback_query(F.data == "my_bookings")
async def my_bookings(callback: CallbackQuery):
    bookings = await get_user_bookings(callback.from_user.id)
    
    if not bookings:
        await callback.message.edit_text("У вас пока нет активных броней.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]]))
    else:
        text = "📋 **Ваши брони:**\n\n"
        buttons = []
        for b in bookings:
            b_id, time, guests = b
            text += f"• {time} ({guests} чел.)\n"
            buttons.append([InlineKeyboardButton(text=f"❌ Отменить {time}", callback_data=f"cancel_{b_id}")])
        
        buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")])
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_booking_handler(callback: CallbackQuery):
    b_id = int(callback.data.split("_")[1])
    await cancel_booking(b_id, callback.from_user.id)
    await callback.message.edit_text("❌ Бронь отменена.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🏠 В меню", callback_data="back_to_menu")]]))
    await callback.answer()

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Меню", callback_data="menu")],
        [InlineKeyboardButton(text="📅 Забронировать столик", callback_data="book")],
        [InlineKeyboardButton(text="📋 Мои брони", callback_data="my_bookings")],
        [InlineKeyboardButton(text="📞 Связаться с нами", callback_data="contact")]
    ])
    await callback.message.edit_text(TEXTS["start"], reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "contact")
async def contact(callback: CallbackQuery):
    await callback.message.answer("📞 Телефон: +7 (999) 123-45-67\n📍 Адрес: г. Москва, ул. Ленина, 1")
    await callback.answer()

# --- АДМИН-ПАНЕЛЬ ---
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("⛔ У вас нет доступа.")
        return
    
    bookings = await get_all_active_bookings()
    if not bookings:
        await message.answer("📭 Нет активных броней.")
        return
    
    text = "👑 **АДМИН-ПАНЕЛЬ**\n\n📋 **Все брони:**\n\n"
    for b in bookings:
        b_id, name, time, guests, user_id = b
        text += f"👤 {name} (ID: `{user_id}`)\n⏰ {time}\n👥 {guests} чел.\n\n"
    
    await message.answer(text, parse_mode="Markdown")

async def main():
    await init_db()
    print("Cafe Bot запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
