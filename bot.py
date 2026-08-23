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

TOKEN = "8886678281:AAEGB93zbn_TLlN-81GbxXAAWGnhtIkuDpM"
ADMIN_ID = 2617518

router = Router()


class CalculatorStates(StatesGroup):
  waiting_for_lang = State()
  waiting_for_type = State()
  waiting_for_width = State()
  waiting_for_height = State()
  waiting_for_depth = State()
  waiting_for_material_type = State()
  waiting_for_material_brand = State()
  waiting_for_hardware = State()
  waiting_for_drawers = State()
  waiting_for_rods = State()
  waiting_for_doors_type = State()
  waiting_for_doors_finish = State()
  waiting_for_contact = State()


# Базовые цены за 1 кв.м для глубины до 400 мм (в сумах)
BASE_PRICES = {
    "ldsp_ultradecor": 1000000,
    "ldsp_egger": 1150000,
    "lmdf_ultradecor": 1250000,
    "lmdf_egger": 1350000,
}

PRICES = {
    "drawer_standard": 290000,
    "drawer_premium": 680000,
    "hinge_standard": 15000,
    "hinge_premium": 70000,
    "rod": 90000,
    "doors_ldsp": 3000,
    "doors_lmdf": 5000,
    "doors_acrylic_gloss": 15000,
    "doors_acrylic_mat": 18000,
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
            "Выберите ширину из списка или введите точное число в мм (например:"
            " *1800*):"
        ),
        "height_btn": (
            "Выберите высоту из списка или введите точное число в мм (например:"
            " *2500*):"
        ),
        "depth_btn": (
            "Выберите глубину из списка или введите точное число в мм"
            " (например: *500*):"
        ),
        "mat_type_btn": "Выберите тип материала корпуса:",
        "mat_brand_btn": "Выберите производителя материала:",
        "hw_btn": (
            "Выберите класс фурнитуры:\n\n• *Стандарт* (Samet, Gtv, Dtc):"
            " надежные комплектующие без лишних переплат.\n• *Премиум*"
            " (Hettich, Blum): плавное и бесшумное закрывание от мировых"
            " брендов."
        ),
        "drawers_btn": "Сколько выдвижных ящиков необходимо?",
        "rods_btn": "Сколько штанг для одежды установить?",
        "doors_type_btn": "Какие фасады планируются?",
        "doors_finish_btn": "Выберите тип покрытия для акриловых фасадов:",
        "contact_btn": "📱 Отправить мой номер",
        "back_btn": "⬅️ Назад",
        "result": (
            "📊 **Предварительный расчет:**\n• Тип: {type}\n• Размеры: {w} ×"
            " {h} мм (Глубина: {depth_t})\n• Корпус: {mat_t} ({mat_b})\n•"
            " Фурнитура: {hw_t}\n• Ящики: {drawers} шт. | Штанги: {rods}"
            " шт.\n• Фасады: {doors_t} ({num_doors} шт.)\n• Петли: {hinges_count}"
            " шт.\n\n💰 **Примерная стоимость:** `{price:,}` сум\n\nНажмите"
            " кнопку ниже, чтобы отправить контакт. Передадим данные"
            " конструктору, и в скором времени он с вами свяжется для"
            " обсуждения деталей, точного просчета и начала работы!"
        ),
        "success": (
            "Спасибо! Заявка передана конструктору, скоро он свяжется с вами."
        ),
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
            "Kenglikni tanlang yoki aniq o'lchamni mm da kiriting (masalan:"
            " *1800*):"
        ),
        "height_btn": (
            "Balandlikni tanlang yoki aniq o'lchamni mm da kiriting (masalan:"
            " *2500*):"
        ),
        "depth_btn": (
            "Chuqurlikni tanlang yoki aniq o'lchamni mm da kiriting (masalan:"
            " *500*):"
        ),
        "mat_type_btn": "Kuzov materialining turini tanlang:",
        "mat_brand_btn": "Material ishlab chiqaruvchisini tanlang:",
        "hw_btn": (
            "Aksessuarlar (furnitura) sinfini"
            " tanlang:\n\n• *Standart* (Samet, Gtv, Dtc): ishonchli"
            " jamlanmalar.\n• *Premium* (Hettich, Blum): jahon brendlaridan"
            " yumshoq yopilish."
        ),
        "drawers_btn": "Nechta chiqib keluvchi tortma kerak?",
        "rods_btn": "Kiyim uchun nechta veshalka (shtanga) o'rnatish kerak?",
        "doors_btn": "Qanday fasadlar rejalashtirilgan?",
        "doors_finish_btn": "Akril fasadlar uchun qoplama turini tanlang:",
        "contact_btn": "📱 Raqamimni yuborish",
        "back_btn": "⬅️ Orqaga",
        "result": (
            "📊 **Dastlabki hisob-kitob:**\n• Turi: {type}\n• O'lchamlari: {w} ×"
            " {h} mm (Chuqurligi: {depth_t})\n• Kuzov: {mat_t} ({mat_b})\n•"
            " Furnitura: {hw_t}\n• Tortmalar: {drawers} ta | Shtangalar: {rods}"
            " ta\n• Fasadlar: {doors_t} ({num_doors} ta)\n• Ilmoqlar (petli):"
            " {hinges_count} ta\n\n💰 **Taxminiy narx:** `{price:,}`"
            " so'm\n\nUsta bilan bog'lanish uchun pastdagi tugmani bosing."
            " Ma'lumotlarni konstruktorga uzatamiz, tez orada tafsilotlarni"
            " kelishish va aniq hisob-kitob qilish uchun siz bilan"
            " bog'lanishadi!"
        ),
        "success": (
            "Rahmat! Ariza konstruktorga yuborildi, tez orada siz bilan"
            " bog'lanishadi."
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


# Кнопка НАЗАД (возврат к выбору типа шкафа)
@router.callback_query(F.data == "back_to_type")
async def back_to_type(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  lang = data.get("lang", "ru")
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
              InlineKeyboardButton(text="1800 мм", callback_data="w_1800"),
              InlineKeyboardButton(text="2400 мм", callback_data="w_2400"),
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_type"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      t["width_btn"], reply_markup=keyboard, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_width)
  await callback.answer()


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
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_width"
              )
          ],
      ]
  )
  if isinstance(message, Message):
    await message.answer(
        t["height_btn"], reply_markup=keyboard, parse_mode="Markdown"
    )
  else:
    await message.edit_text(
        t["height_btn"], reply_markup=keyboard, parse_mode="Markdown"
    )
  await state.set_state(CalculatorStates.waiting_for_height)


@router.callback_query(F.data == "back_to_width")
async def back_to_width(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="1200 мм", callback_data="w_1200"),
              InlineKeyboardButton(text="1600 мм", callback_data="w_1600"),
          ],
          [
              InlineKeyboardButton(text="1800 мм", callback_data="w_1800"),
              InlineKeyboardButton(text="2400 мм", callback_data="w_2400"),
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_type"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      t["width_btn"], reply_markup=keyboard, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_width)
  await callback.answer()


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
          [
              InlineKeyboardButton(
                  text="До 40 см (400 мм)", callback_data="depth_350"
              )
          ],
          [
              InlineKeyboardButton(
                  text="От 40 до 60 см (600 мм)", callback_data="depth_550"
              )
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_height"
              )
          ],
      ]
  )
  if isinstance(message, Message):
    await message.answer(
        t["depth_btn"], reply_markup=keyboard, parse_mode="Markdown"
    )
  else:
    await message.edit_text(
        t["depth_btn"], reply_markup=keyboard, parse_mode="Markdown"
    )
  await state.set_state(CalculatorStates.waiting_for_depth)


@router.callback_query(F.data == "back_to_height")
async def back_to_height(callback: CallbackQuery, state: FSMContext):
  await ask_height(callback.message, state)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_depth, F.data.startswith("depth_")
)
async def process_depth_callback(callback: CallbackQuery, state: FSMContext):
  depth = int(callback.data.split("_")[1])
  await state.update_data(depth=depth)
  await ask_material_type(callback.message, state)
  await callback.answer()


@router.message(CalculatorStates.waiting_for_depth)
async def process_depth_text(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  try:
    depth = int(message.text.strip())
    if depth <= 100 or depth > 1200:
      raise ValueError()
  except ValueError:
    await message.answer(t["error_num"])
    return

  await state.update_data(depth=depth)
  await ask_material_type(message, state)


# --- ВЫБОР МАТЕРИАЛА ---
async def ask_material_type(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="ЛДСП", callback_data="mtype_ldsp")],
          [InlineKeyboardButton(text="ЛМДФ", callback_data="mtype_lmdf")],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_depth"
              )
          ],
      ]
  )
  if isinstance(message, Message):
    await message.answer(t["mat_type_btn"], reply_markup=keyboard)
  else:
    await message.edit_text(t["mat_type_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_material_type)


@router.callback_query(F.data == "back_to_depth")
async def back_to_depth(callback: CallbackQuery, state: FSMContext):
  await ask_depth(callback.message, state)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_material_type, F.data.startswith("mtype_")
)
async def process_material_type(callback: CallbackQuery, state: FSMContext):
  mtype = callback.data.split("_")[1]
  await state.update_data(mat_type=mtype)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="Ultradecor", callback_data="mbrand_ultradecor"
              )
          ],
          [InlineKeyboardButton(text="Egger", callback_data="mbrand_egger")],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_mtype"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["mat_brand_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_material_brand)
  await callback.answer()


@router.callback_query(F.data == "back_to_mtype")
async def back_to_mtype(callback: CallbackQuery, state: FSMContext):
  await ask_material_type(callback.message, state)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_material_brand, F.data.startswith("mbrand_")
)
async def process_material_brand(callback: CallbackQuery, state: FSMContext):
  mbrand = callback.data.split("_")[1]
  await state.update_data(mat_brand=mbrand)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="⚙️ Стандарт (Samet, Gtv, Dtc)", callback_data="hw_standard"
              )
          ],
          [
              InlineKeyboardButton(
                  text="💎 Премиум (Hettich, Blum)", callback_data="hw_premium"
              )
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_mbrand"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      t["hw_btn"], reply_markup=keyboard, parse_mode="Markdown"
  )
  await state.set_state(CalculatorStates.waiting_for_hardware)
  await callback.answer()


@router.callback_query(F.data == "back_to_mbrand")
async def back_to_mbrand(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="Ultradecor", callback_data="mbrand_ultradecor"
              )
          ],
          [InlineKeyboardButton(text="Egger", callback_data="mbrand_egger")],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_mtype"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["mat_brand_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_material_brand)
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
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_hw"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["drawers_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_drawers)
  await callback.answer()


@router.callback_query(F.data == "back_to_hw")
async def back_to_hw(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="⚙️ Стандарт (Samet, Gtv, Dtc)", callback_data="hw_standard"
              )
          ],
          [
              InlineKeyboardButton(
                  text="💎 Премиум (Hettich, Blum)", callback_data="hw_premium"
              )
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_mbrand"
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
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_drawers"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["rods_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_rods)
  await callback.answer()


@router.callback_query(F.data == "back_to_drawers")
async def back_to_drawers(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="0 шт.", callback_data="drawers_0"),
              InlineKeyboardButton(text="2 шт.", callback_data="drawers_2"),
              InlineKeyboardButton(text="4 шт.", callback_data="drawers_4"),
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_hw"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["drawers_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_drawers)
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
                  text="ЛДСП (в цвет корпуса)", callback_data="doors_ldsp"
              )
          ],
          [
              InlineKeyboardButton(
                  text="ЛМДФ (в цвет корпуса)", callback_data="doors_lmdf"
              )
          ],
          [
              InlineKeyboardButton(
                  text="Акриловые фасады", callback_data="doors_acrylic"
              )
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_rods"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["doors_type_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_doors_type)
  await callback.answer()


@router.callback_query(F.data == "back_to_rods")
async def back_to_rods(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(text="1 шт.", callback_data="rods_1"),
              InlineKeyboardButton(text="2 шт.", callback_data="rods_2"),
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_drawers"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["rods_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_rods)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_doors_type, F.data.startswith("doors_")
)
async def process_doors_type(callback: CallbackQuery, state: FSMContext):
  dtype = callback.data.split("_")[1]
  await state.update_data(doors_type=dtype)
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  if dtype == "acrylic":
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=(
                        "Ультра глянцевые"
                        if data["lang"] == "ru"
                        else "Ultra yaltiroq"
                    ),
                    callback_data="finish_gloss",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Матовые" if data["lang"] == "ru" else "Matli",
                    callback_data="finish_mat",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t["back_btn"], callback_data="back_to_doors_type"
                )
            ],
        ]
    )
    await callback.message.edit_text(
        t["doors_finish_btn"], reply_markup=keyboard
    )
    await state.set_state(CalculatorStates.waiting_for_doors_finish)
    await callback.answer()
  else:
    await finish_calculation(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "back_to_doors_type")
async def back_to_doors_type(callback: CallbackQuery, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="ЛДСП (в цвет корпуса)", callback_data="doors_ldsp"
              )
          ],
          [
              InlineKeyboardButton(
                  text="ЛМДФ (в цвет корпуса)", callback_data="doors_lmdf"
              )
          ],
          [
              InlineKeyboardButton(
                  text="Акриловые фасады", callback_data="doors_acrylic"
              )
          ],
          [
              InlineKeyboardButton(
                  text=t["back_btn"], callback_data="back_to_rods"
              )
          ],
      ]
  )
  await callback.message.edit_text(t["doors_type_btn"], reply_markup=keyboard)
  await state.set_state(CalculatorStates.waiting_for_doors_type)
  await callback.answer()


@router.callback_query(
    CalculatorStates.waiting_for_doors_finish, F.data.startswith("finish_")
)
async def process_doors_finish(callback: CallbackQuery, state: FSMContext):
  finish = callback.data.split("_")[1]
  await state.update_data(doors_finish=finish)
  await finish_calculation(callback.message, state)
  await callback.answer()


# --- ИТОГОВЫЙ РАСЧЕТ И СИММЕТРИЧНЫЕ ФАСАДЫ С ПЕТЛЯМИ ---
async def finish_calculation(message: Message, state: FSMContext):
  data = await state.get_data()
  t = TEXTS[data["lang"]]

  w = data["width"]
  h = data["height"]
  depth = data["depth"]
  area = (w * h) / 1000000

  mat_key = f"{data['mat_type']}_{data['mat_brand']}"
  base_rate = BASE_PRICES.get(mat_key, 1000000)

  if depth > 400:
    base_rate = base_rate * 1.1

  base_cost = area * base_rate

  drawer_price_per_unit = (
      PRICES["drawer_premium"]
      if data["hardware"] == "premium"
      else PRICES["drawer_standard"]
  )
  drawers_cost = data["drawers"] * drawer_price_per_unit
  rods_cost = data["rods"] * PRICES["rod"]

  num_doors = max(2, round(w / 500))
  while (w / num_doors) < 380 and num_doors > 1:
    num_doors -= 1
  while (w / num_doors) > 650:
    num_doors += 1

  hinges_per_door = 4
  if h > 2300:
    hinges_per_door += 4

  total_hinges = num_doors * hinges_per_door
  hinge_unit_price = (
      PRICES["hinge_premium"]
      if data["hardware"] == "premium"
      else PRICES["hinge_standard"]
  )
  hinges_cost = total_hinges * hinge_unit_price

  dtype = data["doors_type"]
  if dtype == "ldsp":
    door_unit = PRICES["doors_ldsp"]
  elif dtype == "lmdf":
    door_unit = PRICES["doors_lmdf"]
  elif dtype == "acrylic":
    finish = data.get("doors_finish", "gloss")
    door_unit = (
        PRICES["doors_acrylic_gloss"]
        if finish == "gloss"
        else PRICES["doors_acrylic_mat"]
    )
  else:
    door_unit = PRICES["doors_ldsp"]

  doors_cost = area * door_unit
  total_price = round(
      base_cost + drawers_cost + rods_cost + hinges_cost + doors_cost
  )

  depth_text = (
      f"{depth} мм" if data["lang"] == "ru" else f"{depth} mm (Chuqurlik)"
  )
  hw_text = (
      "Премиум (Hettich, Blum)"
      if data["hardware"] == "premium"
      else "Стандарт (Samet, Gtv, Dtc)"
  )

  mat_type_str = data["mat_type"].upper()
  mat_brand_str = data["mat_brand"].capitalize()

  if dtype == "acrylic":
    finish_str = (
        "Глянец" if data.get("doors_finish") == "gloss" else "Матовый"
    )
    doors_text = f"Акрил ({finish_str})"
  else:
    doors_text = dtype.upper()

  await state.update_data(
      total_price=total_price,
      depth_text=depth_text,
      hw_text=hw_text,
      hinges_count=total_hinges,
      num_doors=num_doors,
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
      mat_t=mat_type_str,
      mat_b=mat_brand_str,
      hw_t=hw_text,
      drawers=data["drawers"],
      rods=data["rods"],
      doors_t=doors_text,
      num_doors=num_doors,
      hinges_count=total_hinges,
      price=total_price,
  )

  if isinstance(message, CallbackQuery):
    await message.message.answer(
        result_text, reply_markup=contact_kb, parse_mode="Markdown"
    )
  else:
    await message.answer(
        result_text, reply_markup=contact_kb, parse_mode="Markdown"
    )

  await state.set_state(CalculatorStates.waiting_for_contact)


@router.message(CalculatorStates.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext, bot: Bot):
  contact = message.contact
  data = await state.get_data()
  t = TEXTS[data.get("lang", "ru")]

  lead_text = (
      f"🔥 **Новая заявка для конструктора!** (Язык:"
      f" {data.get('lang', 'ru').upper()})\n👤 Имя: {contact.first_name}\n📞"
      f" Телефон: `{contact.phone_number}`\n\n📐 Параметры:\n• Тип:"
      f" {data['cabinet_type'].capitalize()}\n• ШхВ: {data['width']} ×"
      f" {data['height']} мм\n• Глубина: {data['depth_text']}\n• Корпус:"
      f" {data['mat_type'].upper()} ({data['mat_brand'].capitalize()})\n•"
      f" Фурнитура: {data['hw_text']}\n• Ящики: {data['drawers']} | Штанги:"
      f" {data['rods']}\n• Фасады: {data.get('num_doors')} шт. | Петли:"
      f" {data.get('hinges_count')} шт.\n• Предварительная сумма:"
      f" `{data['total_price']:,}` сум"
  )

  await bot.send_message(ADMIN_ID, lead_text, parse_mode="Markdown")
  await message.answer(t["success"], reply_markup=None)
  await state.clear()


# Веб-сервер для удержания порта на Render
async def handle_ping(request):
  return web.Response(text="Bot is running with back button support!")


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
  print("Бот с кнопкой возврата запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
