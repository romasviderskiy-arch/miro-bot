import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)


TOKEN = "8886678281:AAEGB93zbn_TLlN-81GbxXAAWGnhtIkuDpM"
ADMIN_ID = 2617518 

router = Router()


class CalculatorStates(StatesGroup):
  waiting_for_type = State()
  waiting_for_width = State()
  waiting_for_height = State()
  waiting_for_material = State()
  waiting_for_drawers = State()
  waiting_for_rods = State()
  waiting_for_doors = State()
  waiting_for_contact = State()


# Цены для расчетов (в сумах)
PRICES = {
    "LDSP": 35000,
    "MDF": 55000,
    "Egger": 150000,
    "drawer": 350000,
    "rod": 90000,
    "doors_ldsp": 3000,
    "doors_mirror": 7000,
}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
  await state.clear()
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="🗄 Шкаф-купе", callback_data="type_купе"
              ),
              InlineKeyboardButton(
                  text="🚪 Распашной", callback_data="type_распашной"
              ),
          ]
      ]
  )
  await message.answer(
      "Здравствуйте! Я помогу рассчитать стоимость шкафа по вашим размерам"
      " за 1 минуту.\n\nКакой тип шкафа вас интересует?",
      reply_markup=keyboard,
  )
  await state.set_state(CalculatorStates.waiting_for_type)


@router.callback_query(
    CalculatorStates.waiting_for_type, F.data.startswith("type_")
)
async def process_type(callback: CallbackQuery, state: FSMContext):
  cabinet_type = callback.data.split("_")[1]
  await state.update_data(cabinet_type=cabinet_type)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="1200 мм", callback_data="w_1200"),
              InlineKeyboardButton(text="1600 мм", callback_data="w_1600"),
          ],
          [
              InlineKeyboardButton(text="2000 мм", callback_data="w_2000"),
              InlineKeyboardButton(text="2400 мм", callback_data="w_2400"),
          ],
      ]
  )
  await callback.message.edit_text(
      "Выберите ширину шкафа (или введите число в мм):", reply_markup=keyboard
  )
  await state.set_state(CalculatorStates.waiting_for_width)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_width, F.data.startswith("w_")
)
@router.message(CalculatorStates.waiting_for_width)
async def process_width(event: Message | CallbackQuery, state: FSMContext):
  if isinstance(event, CallbackQuery):
    width = int(event.data.split("_")[1])
    message = event.message
    await event.answer()
  else:
    try:
      width = int(event.text)
      message = event
    except ValueError:
      await event.answer("Пожалуйста, введите число (например, 1500).")
      return

  await state.update_data(width=width)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="2000 мм", callback_data="h_2000"),
              InlineKeyboardButton(text="2200 мм", callback_data="h_2200"),
          ],
          [
              InlineKeyboardButton(text="2400 мм", callback_data="h_2400"),
              InlineKeyboardButton(text="2700 мм", callback_data="h_2700"),
          ],
      ]
  )
  await message.answer(
      "Укажите высоту шкафа в мм:", reply_markup=keyboard
  )
  await state.set_state(CalculatorStates.waiting_for_height)


@router.callback_query(
    CalculatorStates.waiting_for_height, F.data.startswith("h_")
)
async def process_height(callback: CallbackQuery, state: FSMContext):
  height = int(callback.data.split("_")[1])
  await state.update_data(height=height)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="ЛДСП (Kronospan)", callback_data="mat_ldsp_kronospan"
              )
          ],
          [
              InlineKeyboardButton(
                  text="ЛДМФ / МДФ (Egger)", callback_data="mat_mdf_egger"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      "Выберите материал корпуса и бренд:", reply_markup=keyboard
  )
  await state.set_state(CalculatorStates.waiting_for_material)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_material, F.data.startswith("mat_")
)
async def process_material(callback: CallbackQuery, state: FSMContext):
  parts = callback.data.split("_")
  mat_type = parts[1]
  mat_brand = parts[2]
  await state.update_data(mat_type=mat_type, mat_brand=mat_brand)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="0 шт.", callback_data="drawers_0"),
              InlineKeyboardButton(text="2 шт.", callback_data="drawers_2"),
              InlineKeyboardButton(text="4 шт.", callback_data="drawers_4"),
          ]
      ]
  )
  await callback.message.edit_text(
      "Сколько выдвижных ящиков необходимо?", reply_markup=keyboard
  )
  await state.set_state(CalculatorStates.waiting_for_drawers)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_drawers, F.data.startswith("drawers_")
)
async def process_drawers(callback: CallbackQuery, state: FSMContext):
  drawers = int(callback.data.split("_")[1])
  await state.update_data(drawers=drawers)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="1 шт.", callback_data="rods_1"),
              InlineKeyboardButton(text="2 шт.", callback_data="rods_2"),
          ]
      ]
  )
  await callback.message.edit_text(
      "Сколько штанг для одежды установить?", reply_markup=keyboard
  )
  await state.set_state(CalculatorStates.waiting_for_rods)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_rods, F.data.startswith("rods_")
)
async def process_rods(callback: CallbackQuery, state: FSMContext):
  rods = int(callback.data.split("_")[1])
  await state.update_data(rods=rods)

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="ЛДСП панели", callback_data="doors_ldsp"
              )
          ],
          [
              InlineKeyboardButton(
                  text="Зеркало во весь рост", callback_data="doors_mirror"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      "Какие фасады планируются?", reply_markup=keyboard
  )
  await state.set_state(CalculatorStates.waiting_for_doors)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_doors, F.data.startswith("doors_")
)
async def process_doors(callback: CallbackQuery, state: FSMContext):
  doors = callback.data.split("_")[1]
  await state.update_data(doors=doors)

  data = await state.get_data()

  # Формула расчета стоимости
  w = data["width"]
  h = data["height"]
  area = (w * h) / 1000000

  base_rate = (
      PRICES["LDSP"] if data["mat_type"] == "ldsp" else PRICES["MDF"]
  )
  brand_addon = PRICES["Egger"] if data["mat_brand"] == "egger" else 0
  door_price = (
      PRICES["doors_ldsp"] if data["doors"] == "ldsp" else PRICES["doors_mirror"]
  )

  base_cost = area * base_rate + brand_addon
  drawers_cost = data["drawers"] * PRICES["drawer"]
  rods_cost = data["rods"] * PRICES["rod"]
  total_price = round(base_cost + door_price + drawers_cost + rods_cost)

  await state.update_data(total_price=total_price)

  contact_kb = ReplyKeyboardMarkup(
      keyboard=[[KeyboardButton(text="📱 Отправить мой номер", request_contact=True)]],
      resize_keyboard=True,
      one_time_keyboard=True,
  )

  text = (
      f"📊 **Предварительный расчет:**\n"
      f"• Тип: {data['cabinet_type'].capitalize()}\n"
      f"• Размеры: {w} × {h} мм\n"
      f"• Материал: {data['mat_type'].upper()} ({data['mat_brand'].capitalize()})\n"
      f"• Ящики: {data['drawers']} шт. | Штанги: {data['rods']} шт.\n"
      f"• Фасады: {'Зеркало' if data['doors']=='mirror' else 'ЛДСП'}\n\n"
      f"💰 **Примерная стоимость:** `{total_price:,}` сум\n\n"
      f"Нажмите кнопку ниже, чтобы отправить контакт и передать заявку мастеру:"
  )

  await callback.message.answer(text, reply_markup=contact_kb, parse_mode="Markdown")
  await state.set_state(CalculatorStates.waiting_for_contact)
  await callback.answer()


@router.message(CalculatorStates.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext, bot: Bot):
  contact = message.contact
  data = await state.get_data()

  lead_text = (
      f"🔥 **Новая заявка из бота!**\n"
      f"👤 Имя: {contact.first_name}\n"
      f"📞 Телефон: `{contact.phone_number}`\n\n"
      f"📐 Параметры:\n"
      f"• ШхВ: {data['width']} × {data['height']} мм\n"
      f"• Материал: {data['mat_type'].upper()} ({data['mat_brand']})\n"
      f"• Ящики: {data['drawers']} | Штанги: {data['rods']}\n"
      f"• Фасады: {data['doors']}\n"
      f"💰 Сумма: `{data['total_price']:,}` сум"
  )

  await bot.send_message(ADMIN_ID, lead_text, parse_mode="Markdown")
  await message.answer(
      "Спасибо! Заявка принята, скоро мы свяжемся с вами.", reply_markup=None
  )
  await state.clear()


async def main():
  logging.basicConfig(level=logging.INFO)
  bot = Bot(token=TOKEN)
  dp = Dispatcher()
  dp.include_router(router)
  print("Бот запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
