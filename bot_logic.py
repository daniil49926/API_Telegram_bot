import os
import sys
import json
import random
import traceback
import logging
import telebot
from datetime import date
from telegram_bot_calendar import DetailedTelegramCalendar
from api_logic import get_landmark_destination_id, get_hotel, get_hotel_photos
from base_users import User
from load_env import load_environ
from storage import *


load_environ()


logging.basicConfig(
    stream=sys.stdout,
    level='INFO',
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%H:%M %Y-%m-%d'
)
log = logging.getLogger(__name__)

BaseTableClass.metadata.create_all()
bot = telebot.TeleBot(os.environ.get('TG_TOKEN'))

with open('words_data/data.json', encoding='UTF-8') as file:
    WORLD_DATA = json.load(file)


@bot.message_handler(content_types=['text'])
def get_text_messages(mess) -> None:
    log_plz(mess, say_func_name())
    User.del_user(mess.from_user.id)
    user = User.get_user(mess.from_user.id)
    if (
        mess.text == '/hello-world' or
        mess.text.lower() in WORLD_DATA['intents']['hello']['examples'] or
        mess.text == '/start'
    ):
        bot.send_message(
            mess.from_user.id,
            f"{random.choice(WORLD_DATA['intents']['hello']['responses'])}\nЧем могу помочь?"
        )
    elif mess.text == '/help':
        bot.send_message(
            mess.from_user.id,
            """
            Доступные команды: 
            * /lowprice - Вывод самых дешёвых отелей в городе
            * /highprice - Вывод самых дорогих отелей в городе
            * /bestdeal - Вывод отелей наиболее подходящих по цене и расположению от центра
            * /history - Вывод истории поиска отелей
             """
        )
    elif mess.text == '/lowprice':
        user.sort_flag = 'ASC'
        user.user_command = '/lowprice'
        get_start_date(mess)
    elif mess.text == '/highprice':
        user.sort_flag = 'DESC'
        user.user_command = '/highprice'
        get_start_date(mess)
    elif mess.text == '/bestdeal':
        user.need_to_get_ranges_flag = True
        user.user_command = '/bestdeal'
        get_start_date(mess)
    elif mess.text == '/history':
        history = ''
        history_data = Storage.get_history_by_user_id(mess.from_user.id)
        if history_data:
            for i in history_data:
                history += f"Время: {i.sending_time}\nКоманда: {i.user_message}\nРезультат: {i.bot_message}\n\n"
            bot.send_message(mess.from_user.id, history)
        else:
            bot.send_message(mess.from_user.id, 'Ваша история пуста')
    else:
        bot.send_message(mess.from_user.id, random.choice(WORLD_DATA['intents']['default_answers']))


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=1))
def cal(c) -> None:
    result, key, step = DetailedTelegramCalendar(calendar_id=1, locale='ru', min_date=date.today()).process(c.data)
    user = User.get_user(c.message.chat.id)
    if not user.block_choose_date:
        if not result and key:
            bot.edit_message_text(f"Выберите начальную дату",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=key)
        elif result:
            bot.edit_message_text(f"Начальная дата: {result}\nВерно? (да/нет)",
                                  c.message.chat.id,
                                  c.message.message_id)
            user.check_in = result
    else:
        bot.delete_message(c.message.chat.id, c.message.message_id)


@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=2))
def cal(c) -> None:
    user = User.get_user(c.from_user.id)
    result, key, step = DetailedTelegramCalendar(
        calendar_id=2, locale='ru', min_date=user.check_in + datetime.timedelta(days=1)
    ).process(c.data)
    user = User.get_user(c.message.chat.id)
    if not user.block_choose_date:
        if not result and key:
            bot.edit_message_text(f"Выберите конечную дату",
                                  c.message.chat.id,
                                  c.message.message_id,
                                  reply_markup=key)
        elif result:
            bot.edit_message_text(f"Конечная дата: {result}\nВерно? (да/нет)",
                                  c.message.chat.id,
                                  c.message.message_id)
            user.check_out = result
    else:
        bot.delete_message(c.message.chat.id, c.message.message_id)


def get_city(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    city = mess.text
    city_id = get_landmark_destination_id(str(city))
    if city_id:
        user.city_id = city_id
        user.block_choose_date = False
        if not user.need_to_get_ranges_flag:
            bot.send_message(mess.from_user.id, 'Сколько отелей нужно вывести?\n')
            bot.register_next_step_handler(
                mess,
                lambda m: get_hotel_description(mess=m)
            )
        else:
            bot.send_message(mess.from_user.id, 'Какой диапазон цен (в $) Вас интересует?\nВведите так: "1000-2000"')
            bot.register_next_step_handler(
                mess,
                lambda m: get_price_ranges(mess=m)
            )
    else:
        bot.send_message(mess.from_user.id, 'По такому городу нет информации :(\nПопробуйте ввести другой город.')
        bot.register_next_step_handler(
            mess, lambda m: get_city(mess=m)
        )


def get_start_date(mess) -> None:
    calendar, step = DetailedTelegramCalendar(calendar_id=1, locale='ru', min_date=date.today()).build()
    bot.send_message(mess.chat.id,
                     f"Выберите начальную дату:",
                     reply_markup=calendar)
    bot.register_next_step_handler(
        mess,
        lambda m: check_date(mess=m)
    )


def get_end_date(mess) -> None:
    user = User.get_user(mess.from_user.id)
    calendar_2, step_2 = DetailedTelegramCalendar(
        calendar_id=2, locale='ru', min_date=user.check_in + datetime.timedelta(days=1)
    ).build()
    bot.send_message(mess.chat.id,
                     f"Выберите конечную дату:",
                     reply_markup=calendar_2)
    bot.register_next_step_handler(
        mess,
        lambda m: check_date(mess=m)
    )


def check_date(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    answer = str(mess.text)
    if answer.lower() == 'да' and user.check_in and user.check_out:
        if user.check_in < user.check_out:
            bot.send_message(mess.from_user.id, 'В каком городе ищем?\nУкажите название города на английском языке.')
            bot.register_next_step_handler(
                mess,
                lambda m: get_city(mess=m)
            )
        else:
            bot.send_message(mess.from_user.id, 'Вы ввели некорректный диапазон дат')
            user.check_out = None
            user.check_in = None
            get_start_date(mess)
    elif (answer.lower() == 'да' and user.check_in) or (answer.lower() == 'нет' and user.check_in and user.check_out):
        user.check_out = None
        get_end_date(mess)
    elif answer.lower() == 'нет' and user.check_in:
        get_start_date(mess)
    else:
        bot.send_message(
            mess.from_user.id,
            random.choice(WORLD_DATA['intents']['default_answers']) + '\nОтветьте на прошлый вопрос (да/нет)'
        )
        bot.register_next_step_handler(
            mess,
            lambda m: check_date(mess=m)
        )


def get_hotel_description(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    user.block_choose_date = True
    count_of_hotel = int(mess.text)
    if count_of_hotel <= 20:
        user.hotels_count = count_of_hotel
        hotel_data = get_hotel(
            user.city_id,
            user.hotels_count,
            user.sort_flag,
            user.p_range,
            user.d_range,
            user.check_in,
            user.check_out
        )
        if hotel_data:
            user.hotel_data = hotel_data
            bot.send_message(mess.from_user.id, 'Нужны ли фотографии отелей? да/нет')
            bot.register_next_step_handler(
                mess,
                lambda m: get_selection_by_photo(mess=m)
            )
        else:
            bot.send_message(mess.from_user.id, 'Не могу ничего найти по вашему запросу :(')
    else:
        bot.send_message(mess.from_user.id, 'Я не могу вывести больше 20 отелей, введите другое кол-во...')
        bot.register_next_step_handler(
            mess,
            lambda m: get_hotel_description(mess=m)
        )


def get_selection_by_photo(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    choice = str(mess.text)
    if choice.lower() == 'да':
        bot.send_message(mess.from_user.id, 'По сколько фотографий вывести?')
        bot.register_next_step_handler(
            mess,
            lambda m: get_hotel_with_photos(mess=m)
        )
    elif choice.lower() == 'нет':
        history = ''
        for i_hotel in user.hotel_data:
            bot.send_message(
                mess.from_user.id,
                f"Название: {i_hotel['name']}\n"
                f"\tАдрес: {i_hotel['address']}\n"
                f"\tРасстояние до центра города: {i_hotel['distance_to_the_center']}\n"
                f"\tЦена: {i_hotel['price']}\n"
                f"Ссылка на отель: https://hotels.com/ho{i_hotel['id']}",
                disable_web_page_preview=True
            )
            history += f"\n\t{i_hotel['name']}"
        Storage.create_history(mess.from_user.id, user.user_command, history)
    else:
        bot.send_message(mess.from_user.id, random.choice(WORLD_DATA['intents']['default_answers']))
        bot.register_next_step_handler(
            mess,
            lambda m: get_selection_by_photo(mess=m)
        )


def get_hotel_with_photos(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    count_photos = int(mess.text)
    if count_photos <= 10:
        history = ''
        for i_hotel in user.hotel_data:
            bot.send_message(
                mess.from_user.id,
                f"Название: {i_hotel['name']}\n"
                f"\tАдрес: {i_hotel['address']}\n"
                f"\tРасстояние до центра города: {i_hotel['distance_to_the_center']}\n"
                f"\tЦена: {i_hotel['price']}\n"
                f"Ссылка на отель: https://hotels.com/ho{i_hotel['id']}",
                disable_web_page_preview=True
            )
            history += f"\n\t{i_hotel['name']}"
            photo_urls = get_hotel_photos(i_hotel, count_photos)
            if photo_urls:
                medias = []
                for i_photo in photo_urls:
                    medias.append(telebot.types.InputMediaPhoto(i_photo[:-11] + '.jpg'))
                bot.send_media_group(mess.from_user.id, medias)
            else:
                bot.send_message(mess.from_user.id, 'Не могу найти фото для этого отеля.')
        Storage.create_history(mess.from_user.id, user.user_command, history)
    else:
        bot.send_message(mess.from_user.id, 'Я не могу вывести больше 10 фото, введите другое кол-во...')
        bot.register_next_step_handler(
            mess,
            lambda m: get_hotel_with_photos(mess=m)
        )


def get_price_ranges(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    user.block_choose_date = True
    if len(str(mess.text).split('-')) == 2:
        if is_number(str(mess.text).split('-')[0]) and is_number(str(mess.text).split('-')[1]):
            user.p_range = str(mess.text)
            bot.send_message(
                mess.from_user.id,
                'Какой диапазон расстояния (в милях) от центра Вас интересует?\nВведите так: "0.1-1.2"'
            )
            bot.register_next_step_handler(
                mess,
                lambda m: get_distance_ranges(mess=m)
            )
        else:
            bot.send_message(
                mess.from_user.id,
                'Введите два числа через "-"'
            )
            bot.register_next_step_handler(
                mess,
                lambda m: get_price_ranges(mess=m)
            )
    else:
        bot.send_message(
            mess.from_user.id,
            'Неверный формат ввода.\nВведите так: "1000-2000"'
        )
        bot.register_next_step_handler(
            mess,
            lambda m: get_price_ranges(mess=m)
        )


def get_distance_ranges(mess) -> None:
    log_plz(mess, say_func_name())
    user = User.get_user(mess.from_user.id)
    if len(str(mess.text).split('-')) == 2:
        if is_number(str(mess.text).split('-')[0]) and is_number(str(mess.text).split('-')[1]):
            user.d_range = str(mess.text)
            bot.send_message(mess.from_user.id, 'Сколько отелей нужно вывести?')
            bot.register_next_step_handler(
                mess,
                lambda m: get_hotel_description(mess=m)
            )
        else:
            bot.send_message(
                mess.from_user.id,
                'Введите два числа через "-"'
            )
            bot.register_next_step_handler(
                mess,
                lambda m: get_distance_ranges(mess=m)
            )
    else:
        bot.send_message(
            mess.from_user.id,
            'Неверный формат ввода.\nВведите так: "0.1-1.2"'
        )
        bot.register_next_step_handler(
            mess,
            lambda m: get_distance_ranges(mess=m)
        )


def log_plz(m, func_name: str) -> None:
    log.info(f'Функция {func_name} - {m.from_user.first_name} {m.from_user.last_name} ({m.from_user.id}) - {m.text}')


def say_func_name() -> str:
    stack = traceback.extract_stack()
    return stack[-2][2]


def is_number(user_str: str) -> bool:
    try:
        float(user_str)
        return True
    except ValueError:
        return False


def run_bot():
    log.info('Start BOT')
    bot.polling(none_stop=True, interval=0)
