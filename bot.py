import asyncio
import logging
import os
from aiohttp import web
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

TOKEN = "8886678281:AAEGb93zbn_TL1N-81GbxXAAWGnhTkUdPM"
ADMIN_ID = 2617518

router = Router()


class CalculatorStates(StatesGroup):
  waiting_for_lang = State()
  waiting_for_type = State()
  waiting_for_width = State()
  waiting_for_height = State()
  waiting_for_depth = State()
  waiting_for_material = State()
  waiting_for_hardware = State()
  waiting_for_drawers = State()
  waiting_for_rods = State()
  waiting_for_doors = State()
  waiting_for_contact = State()


# Базовые цены за 1 кв.м в зависимости от глубины (в сумах)
PRICE_SHALLOW = 1000000  # Глубина до 40 см
PRICE_DEEP = 1200000  # Глубина от 40 до 60 см

PRICES = {
    "Egger": 150000,
    "hardware_standard": 200000,
    "hardware_premium": 650000,
    "drawer": 350000,
    "rod": 90000,
    "doors_ldsp": 3000,
    "doors_mirror": 7000,
}

# Словарь текстов для двух языков
TEXTS = {
    "ru": {
        "start": (
            "Здравствуйте! Я помогу рассчитать стоимость шкафа по вашим"
            " размерам за 1 минуту.\n\nTilni tanlang / Выберите язык:"
        ),
        "type": "Какой тип шкафа вас интересует?",
        "type_kupe": "🗄 Шкаф-купе",
        "type_rasp": "🚪 Распашной",
        "width_btn": (
            "Выберите ширину шкафа из списка или введите точное число в мм"
            " (например: *1450*):"
        ),
        "height_btn": (
            "Выберите высоту шкафа из списка или введите точное число в мм"
            " (например: *2500*):"
        ),
        "depth_btn": "Выберите глубину шкафа:",
        "depth_shallow": "До 40 см (400 мм)",
        "depth_deep": "От 40 до 60 см (600 мм)",
        "mat_btn": "Выберите материал корпуса и бренд:",
        "hw_btn": (
            "Выберите класс фурнитуры:\n\n• *Стандарт*: надежные петли и"
            " направляющие без лишних переплат.\n• *Премиум*: плавное и"
            " бесшумное закрывание от мировых брендов."
        ),
        "drawers_btn": "Сколько выдвижных ящиков необходимо?",
        "rods_btn": "Сколько штанг для одежды установить?",
        "doors_btn": "Какие фасады планируются?",
        "contact_btn": "📱 Отправить мой номер",
        "result": (
            "📊 **Предварительный расчет:**\n• Тип: {type}\n• Размеры: {w} ×"
            " {h} мм (Глубина: {depth_t})\n• Материал: {mat_t} ({mat_b})\n•"
            " Фурнитура: {hw_t}\n• Ящики: {drawers} шт. | Штанги: {rods}"
            " шт.\n• Фасады: {doors_t}\n\n💰 **Примерная стоимость:**"
            " `{price:,}` сум\n\nНажмите кнопку ниже, чтобы отправить контакт и"
            " передать заявку мастеру:"
        ),
        "success": "Спасибо! Заявка принята, скоро мы свяжемся с вами.",
        "error_num": "Пожалуйста, введите корректное число (например: 1500).",
    },
    "uz": {
        "start": (
            "Assalomu alaykum! Men sizga 1 daqiqa ichida o'lchamlaringiz"
            " bo'yicha shkaf narxini hisoblashga yordam beraman.\n\nTilni"
            " tanlang / Выберите язык:"
        ),
        "type": "Qaysi turdagi shkaf sizni qiziqtiradi?",
        "type_kupe": "🗄 Kupe shkaf",
        "type_rasp": "🚪 Ochiladigan shkaf",
        "width_btn": (
            "Ro'yxatdan kenglikni tanlang yoki aniq o'lchamni mm da kiriting"
            " (masalan: *1450*):"
        ),
        "height_btn": (
            "Ro'yxatdan balandlikni tanlang yoki aniq o'lchamni mm da kiriting"
            " (masalan: *2500*):"
        ),
        "depth_btn": "Shkafning chuqurligini tanlang:",
        "depth_shallow": "40 sm gacha (400 mm)",
        "depth_deep": "40 dan 60 sm gacha (600 mm)",
        "mat_btn": "Kuzov materiali va brendini tanlang:",
        "hw_btn": (
            "Aksessuarlar (furnitura) sinfini"
            " tanlang:\n\n• *Standart*: ortiqcha xarajatlarsiz ishonchli"
            " ilmoqlar va yo'naltiruvchilar.\n• *Premium*: jahon brendlaridan"
            " yumshoq va jim yopilish."
        ),
        "drawers_btn": "Nechta chiqib keluvchi tortma kerak?",
        "rods_btn": "Kiyim uchun nechta veshalka (shtanga) o'rnatish kerak?",
        "doors_btn": "Qanday fasadlar rejalashtirilgan?",
        "contact_btn": "📱 Raqamimni yuborish",
        "result": (
            "📊 **Dastlabki hisob-kitob:**\n• Turi: {type}\n• O'lchamlari: {w} ×"
            " {h} mm (Chuqurligi: {depth_t})\n• Material: {mat_t}"
            " ({mat_b})\n• Furnitura: {hw_t}\n• Tortmalar: {drawers} ta |"
            " Shtangalar: {rods} ta\n• Fasadlar: {doors_t}\n\n💰 **Taxminiy"
            " narx:** `{price:,}` so'm\n\nUsta bilan bog'lanish uchun pastdagi"
            " tugmani bosing:"
        ),
        "success": (
            "Rahmat! Ariza qabul qilindi, tez orada siz bilan bog'lanamiz."
        ),
        "error_num": "Iltimos, to'g'ri raqam kiriting (masalan: 1500).",
    },
}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
  await state.clear()
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
              InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
          ]
      ]
  )
  await message.answer(TEXTS["ru"]["start"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_lang)


@router.callback_query(
    CalculatorStates.waiting_for_lang, F.data.startswith("lang_")
)
async def process_lang(callback: CallbackQuery, state: FSMContext):
  lang = callback.data.split("_")[1]
  await state.update_data(lang=lang)

  t = TEXTS[lang]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text=t["type_kupe"], callback_data="type_купе"
              ),
              InlineKeyboardButton(
                  text=t["type_rasp"], callback_data="type_распашной"
              ),
          ]
      ]
  )
  await callback.message.edit_text(t["type"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_type)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_type, F.data.startswith("type_")
)
async def process_type(callback: CallbackQuery, state: FSMContext):
  cabinet_type = callback.data.split("_")[1]
  await state.update_data(cabinet_type=cabinet_type)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

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
      t["width_btn"], reply_markup=keyboard, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_width)
  await callback.answer()


# Обработка ширины (и через нажатие кнопки, и через текст)
@router.callback_query(
    CalculatorStates.waiting_for_width, F.data.startswith("w_")
)
async def process_width_callback(callback: CallbackQuery, state: FSMContext):
  width = int(callback.data.split("_")[1])
  await state.update_data(width=width)
  await ask_height(callback.message, state)
  await callback.answer()


@router.message(CalculatorStates.waiting_for_width)
async def process_width_text(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  try:
    width = int(message.text.strip())
    if width <= 200 or width > 6000:
      raise ValueError()
  except ValueError:
    await message.answer(t["error_num"])
    return

  await state.update_data(width=width)
  await ask_height(message, state)


async def ask_height(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]

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
      t["height_btn"], reply_markup=keyboard, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_height)


# Обработка высоты (и через нажатие кнопки, и через текст)
@router.callback_query(
    CalculatorStates.waiting_for_height, F.data.startswith("h_")
)
async def process_height_callback(callback: CallbackQuery, state: FSMContext):
  height = int(callback.data.split("_")[1])
  await state.update_data(height=height)
  await ask_depth(callback.message, state)
  await callback.answer()


@router.message(CalculatorStates.waiting_for_height)
async def process_height_text(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  try:
    height = int(message.text.strip())
    if height <= 200 or height > 4000:
      raise ValueError()
  except ValueError:
    await message.answer(t["error_num"])
    return

  await state.update_data(height=height)
  await ask_depth(message, state)


async def ask_depth(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text=t["depth_shallow"], callback_data="depth_350")],
          [InlineKeyboardButton(text=t["depth_deep"], callback_data="depth_550")],
      ]
  )
  await message.answer(t["depth_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_depth)


@router.callback_query(
    CalculatorStates.waiting_for_depth, F.data.startswith("depth_")
)
async def process_depth(callback: CallbackQuery, state: FSMContext):
  depth = int(callback.data.split("_")[1])
  await state.update_data(depth=depth)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

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
  await callback.message.edit_text(t["mat_btn"], reply_markup=keyboard)
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
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="⚙️ Стандарт (Samet / Boyard)", callback_data="hw_standard"
              )
          ],
          [
              InlineKeyboardButton(
                  text="💎 Премиум (Blum / Hettich)", callback_data="hw_premium"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      t["hw_btn"], reply_markup=keyboard, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_hardware)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_hardware, F.data.startswith("hw_")
)
async def process_hardware(callback: CallbackQuery, state: FSMContext):
  hardware = callback.data.split("_")[1]
  await state.update_data(hardware=hardware)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="0 шт.", callback_data="drawers_0"),
              InlineKeyboardButton(text="2 шт.", callback_data="drawers_2"),
              InlineKeyboardButton(text="4 шт.", callback_data="drawers_4"),
          ]
      ]
  )
  await callback.message.edit_text(t["drawers_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_drawers)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_drawers, F.data.startswith("drawers_")
)
async def process_drawers(callback: CallbackQuery, state: FSMContext):
  drawers = int(callback.data.split("_")[1])
  await state.update_data(drawers=drawers)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="1 шт.", callback_data="rods_1"),
              InlineKeyboardButton(text="2 шт.", callback_data="rods_2"),
          ]
      ]
  )
  await callback.message.edit_text(t["rods_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_rods)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_rods, F.data.startswith("rods_")
)
async def process_rods(callback: CallbackQuery, state: FSMContext):
  rods = int(callback.data.split("_")[1])
  await state.update_data(rods=rods)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="ЛДСП / LDSP" if data["lang"] == "ru" else "LDSP panellar",
                  callback_data="doors_ldsp",
              )
          ],
          [
              InlineKeyboardButton(
                  text=(
                      "Зеркало / Ko'zgu"
                      if data["lang"] == "ru"
                      else "To'liq bo'yi ko'zgu"
                  ),
                  callback_data="doors_mirror",
              )
          ],
      ]
  )
  await callback.message.edit_text(t["doors_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_doors)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_doors, F.data.startswith("doors_")
)
async def process_doors(callback: CallbackQuery, state: FSMContext):
  doors = callback.data.split("_")[1]
  await state.update_data(doors=doors)

  data = await state.get_data()
  t = TEXTS[data["lang"]]

  w = data["width"]
  h = data["height"]
  depth = data["depth"]
  area = (w * h) / 1000000

  if depth <= 400:
    base_rate = PRICE_SHALLOW
    depth_text = (
        "До 40 см" if data["lang"] == "ru" else "40 sm gacha (400 mm)"
    )
  else:
    base_rate = PRICE_DEEP
    depth_text = (
        "От 40 до 60 см" if data["lang"] == "ru" else "40 dan 60 sm gacha"
    )

  brand_addon = PRICES["Egger"] if data["mat_brand"] == "egger" else 0
  hw_addon = (
      PRICES["hardware_premium"]
      if data["hardware"] == "premium"
      else PRICES["hardware_standard"]
  )
  door_price = (
      PRICES["doors_ldsp"] if data["doors"] == "ldsp" else PRICES["doors_mirror"]
  )

  base_cost = area * base_rate + brand_addon + hw_addon
  drawers_cost = data["drawers"] * PRICES["drawer"]
  rods_cost = data["rods"] * PRICES["rod"]
  total_price = round(base_cost + door_price + drawers_cost + rods_cost)

  hw_text = (
      "Премиум (Blum/Hettich)"
      if data["hardware"] == "premium"
      else "Стандарт (Samet/Boyard)"
  )
  doors_text = "Зеркало" if data["doors"] == "mirror" else "ЛДСП"

  await state.update_data(
      total_price=total_price, depth_text=depth_text, hw_text=hw_text
  )

  contact_kb = ReplyKeyboardMarkup(
      keyboard=[[KeyboardButton(text=t["contact_btn"], request_contact=True)]],
      resize_keyboard=True,
      one_time_keyboard=True,
  )

  result_text = t["result"].format(
      type=data["cabinet_type"].capitalize(),
      w=w,
      h=h,
      depth_t=depth_text,
      mat_t=data["mat_type"].upper(),
      mat_b=data["mat_brand"].capitalize(),
      hw_t=hw_text,
      drawers=data["drawers"],
      rods=data["rods"],
      doors_t=doors_text,
      price=total_price,
  )

  await callback.message.answer(
      result_text, reply_markup=contact_kb, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_contact)
  await callback.answer()


@router.message(CalculatorStates.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext, bot: Bot):
  contact = message.contact
  data = await state.get_data()
  t = TEXTS[data.get("lang", "ru")]

  lead_text = (
      f"🔥 **Новая заявка из бота!** (Язык: {data.get('lang', 'ru').upper()})\n"
      f"👤 Имя: {contact.first_name}\n"
      f"📞 Телефон: `{contact.phone_number}`\n\n"
      f"📐 Параметры:\n"
      f"• ШхВ: {data['width']} × {data['height']} мм\n"
      f"• Глубина: {data['depth_text']}\n"
      f"• Материал: {data['mat_type'].upper()} ({data['mat_brand']})\n"
      f"• Фурнитура: {data['hw_text']}\n"
      f"• Ящики: {data['drawers']} | Штанги: {data['rods']}\n"
      f"• Фасады: {data['doors']}\n"
      f"💰 Сумма: `{data['total_price']:,}` сум"
  )

  await bot.send_message(ADMIN_ID, lead_text, parse_mode="Markdown")
  await message.answer(t["success"], reply_markup=None)
  await state.clear()


# Веб-сервер для удержания порта на Render
async def handle_ping(request):
  return web.Response(text="Bot is running with custom size input!")


async def web_server():
  app = web.Application()
  app.add_routes([web.get("/", handle_ping)])
  runner = web.AppRunner(app)
  await runner.setup()
  port = int(os.environ.get("PORT", 10000))
  site = web.TCPSite(runner, "0.0.0.0", port)
  await site.start()
  print(f"Веб-сервер запущен на порту {port}")


async def main():
  logging.basicConfig(level=logging.INFO)
  bot = Bot(token=TOKEN)
  dp = Dispatcher()
  dp.include_router(router)

  await web_server()
  print("Бот с возможностью ввода своих размеров запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
