# coding=utf-8
import telebot
from telebot import types
import requests
from flask import Flask, request
import db
import datetime
from datetime import datetime, timedelta
from calendar import Calendar
from bs4 import BeautifulSoup
import re
import sys
import traceback

MONTHS = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь"
}

DAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]

PERIOD = [
    "08:00-09:30",
    "09:40-11:10",
    "11:20-12:50",
    "13:20-14:50",
    "15:00-16:30",
    "16:40-18:10",
    "18:20-19:50",
    "20:00-21:30"
]

app = Flask(__name__)
bot = telebot.TeleBot("TOKEN")


def get_date_now():
    return (datetime.utcnow() + timedelta(hours=5)).date()


def get_html_page(url):
    try:
        html = requests.get(url, timeout=20)
        print(html.status_code)
    except requests.RequestException as Exc:
        print(Exc)
        print(html.status_code)
        return "error", Exc
    except BaseException as Exc1:
        print(Exc1)
        print(html.status_code)
        return "error", Exc1
    else:
        return "ok", html.text


def get_schedule(id, date, who=1):
    html = ""
    url = ""
    if who == 1:
        url = "http://www.osu.ru/pages/schedule/?what=1&mode=full&who=1&group=" + str(id)
    elif who == 2:
        url = "http://www.osu.ru/pages/schedule/?what=1&mode=full&who=2&prep=" + str(id)
    for i in range(5):
        html = get_html_page(url)
        if html[0] == "ok":
            break
        elif html[0] == "error":
            if i == 4:
                return "Не удалось загрузить расписание, попоробуйте позже"
    print(1)

    soup = BeautifulSoup(html[1], 'html.parser')
    if date.isoweekday() == 7:
        date += timedelta(days=1)

    for i in soup.find_all("tr", recursive=False):
        td = i.find_all("td", recursive=False)
        if len(td) > 0:
            # print(re.search(r"([0-9]{2}.[0-9]{2}.[0-9]{4})", str(td[0])).group(0))
            date_schedule = datetime.strptime(re.search(r"([0-9]{2}.[0-9]{2}.[0-9]{4})", str(td[0])).group(0),
                                              "%d.%m.%Y").date()
            if date_schedule == date:
                text = "Расписание занятий на " + str(
                    date_schedule.strftime("%d.%m.%Y") + " (" + DAYS[date_schedule.weekday()]) + ")\n\n"
                offset = int(soup.find_all("th", {"class": "timezao"}, limit=1)[0].contents[0][0]) - 1
                for j in range(1, len(td)):
                    text += "<b>=== " + str(j + offset) + " пара (" + PERIOD[j + offset - 1] + ") ===</b>\n"
                    span = td[j].find_all("span")
                    for s in span:
                        class_name = s.get("class")[0]
                        if class_name == "dis":
                            for c in s.contents:
                                if str(c) == "<br/>":
                                    text += "\n"
                                else:
                                    text += str(c) + " "
                        elif class_name == "lestype":
                            text += s.get_text() + " "
                        elif class_name == "aud":
                            text += "<code>" + s.get_text() + "</code>\n"
                        elif class_name == "p":
                            text += s.get_text() + "\n"
                        else:
                            text += s.get_text() + "\n\n"
                return text
    return "Нет занятий на " + str(date.strftime("%d.%m.%Y"))


@app.route("/")
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url="https://osuschedulebot.herokuapp.com/bot")
    return "ok", 200


@app.route("/bot", methods=['POST'])
def get_message():
    data = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    print(data)
    if data.callback_query is not None:
        bot.process_new_callback_query([data.callback_query])
    elif data.message is not None:
        bot.process_new_messages([data.message])
    return "ok", 200


@bot.message_handler(commands=['start'])
def start(message):
    db.insert_user(message.chat.id)  # сохраняем пользователя, если его еще нет в базе
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Расписание студента", callback_data="who_1"))
    keyboard.add(types.InlineKeyboardButton(text="Расписание преподавателя", callback_data="who_2"))
    bot.send_message(message.chat.id, "Выберите  расписание", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.message:
            commands = call.data.split("_")

            if commands[0] == "who":  # commands[1]: 1 - студент, 2 - преподаватель
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                faculty = db.get_faculty()
                buttons = []
                for f in faculty:
                    buttons.append(types.InlineKeyboardButton(text=str(f["s_title"]),
                                                              callback_data="faculty_" + str(f["id"]) + "_" + commands[
                                                                  1]))
                keyboard.add(*buttons)

                if commands[1] == "1":
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text="Расписание студента")
                elif commands[1] == "2":
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text="Расписание преподавателя")
                bot.send_message(call.message.chat.id, "Выберите  факультет", reply_markup=keyboard)

            elif commands[0] == "faculty":  # commands[1]: id факультета; commands[2]: 1 - студент, 2 - преподаватель
                db.set_user_param(call.message.chat.id, **{"id_faculty": commands[1]})

                if commands[2] == "1":  # студет
                    keyboard = types.InlineKeyboardMarkup(row_width=2)
                    courses = db.get_courses()
                    for c in courses:
                        keyboard.add(types.InlineKeyboardButton(text=str(c[1]),
                                                                callback_data="course_" + str(c[0]) + "_" + str(
                                                                    commands[1])))

                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=str(db.get_faculty(commands[1])["title"]))
                    bot.send_message(call.message.chat.id, "Выберите  курс", reply_markup=keyboard)

                elif commands[2] == "2":  # переподаватель
                    keyboard = types.InlineKeyboardMarkup(row_width=2)
                    cathedra = db.get_cathedra(id_faculty=commands[1])
                    buttons = []
                    for c in cathedra:
                        buttons.append(types.InlineKeyboardButton(text=str(c["s_title"]),
                                                                  callback_data="cathedra_" + str(c["id"]) + "_" + str(
                                                                      commands[1])))
                    keyboard.add(*buttons)
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                          text=str(db.get_faculty(commands[1])["title"]))
                    bot.send_message(call.message.chat.id, "Выберите  кафедру", reply_markup=keyboard)

            elif commands[0] == "course":  # commands[1]: id курса; commands[2]: id факультета
                db.set_user_param(call.message.chat.id, **{"years": commands[1]})
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                groups = db.get_groups(id_faculty=commands[2], year=commands[1])
                buttons = []
                for g in groups:
                    buttons.append(
                        types.InlineKeyboardButton(text=str(g["title"]), callback_data="group_" + str(g["id"])))
                keyboard.add(*buttons)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=str(db.get_courses(int(commands[1]))))
                bot.send_message(call.message.chat.id, "Выберите  группу", reply_markup=keyboard)

            elif commands[0] == "cathedra":  # commands[1]: id кафедры; commands[2]: id факультета
                db.set_user_param(call.message.chat.id, **{"id_cafedra": commands[1]})
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                teachers = db.get_teachers(id_cathedra=commands[1])
                buttons = []
                for t in teachers:
                    buttons.append(
                        types.InlineKeyboardButton(text=str(t["s_title"]), callback_data="teacher_" + str(t["id"])))
                keyboard.add(*buttons)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=str(db.get_cathedra(commands[1])["title"]))
                bot.send_message(call.message.chat.id, "Выберите  преподавателя", reply_markup=keyboard)

            elif commands[0] == "group":
                db.set_user_param(call.message.chat.id, **{"is_last_teacher": False, "id_last_group": commands[1]})
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=str(db.get_groups(id_group=commands[1])["title"]))
                bot.send_message(call.message.chat.id, "Загружаю расписание...")
                schedule = get_schedule(commands[1], get_date_now())
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id + 1,
                                      text=schedule, parse_mode="HTML")

            elif commands[0] == "teacher":
                db.set_user_param(call.message.chat.id, **{"is_last_teacher": True, "id_last_teacher": commands[1]})
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                      text=str(db.get_teachers(id_teacher=commands[1])["title"]))
                bot.send_message(call.message.chat.id, "Загружаю расписание...")
                schedule = get_schedule(commands[1], get_date_now(), 2)
                bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id + 1,
                                      text=schedule, parse_mode="HTML")

            elif commands[0] == "calendar":
                if commands[1] == "0":
                    return

                if commands[1] == "month":
                    date = get_date_now()
                    date = date.replace(day=1, month=int(commands[2]))
                    if commands[2] == "1":
                        date = date.replace(year=date.year + 1)
                    keyboard = get_calendar_keyboard(date)
                    months = get_months_in_semester()
                    i = months.index(date.month)
                    print(i)
                    if i == 0:
                        keyboard.row(types.InlineKeyboardButton(text=MONTHS[months[i + 1]] + " >",
                                                                callback_data="calendar_month_" + str(months[i + 1])))
                    elif i == len(months) - 1:
                        keyboard.row(types.InlineKeyboardButton(text="< " + MONTHS[months[i - 1]],
                                                                callback_data="calendar_month_" + str(months[i - 1])))
                    else:
                        keyboard.row(
                            types.InlineKeyboardButton(text="< " + MONTHS[months[i - 1]],
                                                       callback_data="calendar_month_" + str(months[i - 1])),
                            types.InlineKeyboardButton(text=MONTHS[months[i + 1]] + " >",
                                                       callback_data="calendar_month_" + str(months[i + 1]))
                        )
                        user = db.get_user(call.message.chat.id)
                        if user["is_last_teacher"]:
                            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                                  text="Преподаватель " +
                                                       db.get_teachers(id_teacher=user["id_last_teacher"])["s_title"] +
                                                       "\nКалендарь на " + MONTHS[date.month],
                                                  reply_markup=keyboard)
                        else:
                            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                                  text="Группа " + db.get_groups(id_group=user["id_last_group"])[
                                                      "title"] +
                                                       "\nКалендарь на " + MONTHS[date.month],
                                                  reply_markup=keyboard)

                else:
                    user = db.get_user(call.message.chat.id)
                    if user["is_last_teacher"]:
                        teacher = db.get_teachers(id_teacher=user["id_last_teacher"])
                        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              text="Загружаю расписание на " + commands[
                                                  1] + "\nПреподаватель " + teacher["s_title"] + "...")
                        schedule = get_schedule(teacher["id"],
                                                datetime.strptime(commands[1], "%d.%m.%Y").date(), 2)
                        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              text="Преподаватель " + teacher["s_title"] + "\n" + schedule,
                                              parse_mode="HTML")
                    else:
                        group = db.get_groups(id_group=user["id_last_group"])
                        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              text="Загружаю расписание на " + commands[
                                                  1] + "\nГруппа " + group["title"] + "...")

                        schedule = get_schedule(group["id"],
                                                datetime.strptime(commands[1], "%d.%m.%Y").date())
                        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                              text="Группа " + group["title"] + "\n" + schedule, parse_mode="HTML")
    except BaseException as Exc:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        print("PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n", Exc)


@bot.message_handler(commands=["save"])
def save(message):
    user = db.get_user(message.chat.id)

    if user["is_last_teacher"]:
        if user["id_last_teacher"]:
            db.set_user_param(message.chat.id, **{"id_my_teacher": "id_last_teacher", "is_my_teacher": True})
            bot.send_message(message.chat.id, "Преподаватель " + str(
                db.get_teachers(id_teacher=user["id_last_teacher"])["s_title"]) + " успешно сохранен")
            return
    else:
        if user["id_last_group"]:
            db.set_user_param(message.chat.id, **{"id_my_group": "id_last_group",  "is_my_teacher": False})
            bot.send_message(message.chat.id,
                             "Группа " + str(db.get_groups(user["id_last_group"])["title"]) + " успешно сохранена")
            return
    bot.send_message(message.chat.id, "Сначала выберите расписание командой /start")


@bot.message_handler(commands=['my'])
def my(message):
    user = db.get_user(message.chat.id)
    if user["is_my_teacher"]:
        if user["id_my_teacher"]:
            db.set_user_param(message.chat.id, **{"id_last_teacher": "id_my_teacher", "is_last_teacher": True})
            name_teacher = str(db.get_teachers(id_teacher=user["id_my_teacher"])["s_title"])
            bot.send_message(message.chat.id, "Загружаю расписание " + name_teacher + "...")
            schedule = get_schedule(user["id_my_teacher"], get_date_now(), 2)
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id + 1,
                                  text="Преподаватель " + name_teacher + "\n" + schedule,
                                  parse_mode="HTML")
        else:
            bot.send_message(message.chat.id,
                             "Вы еще не сохранили расписание преподавателя, воспользуйтесь командой /save")
    else:
        if user["id_my_group"]:
            db.set_user_param(message.chat.id, **{"id_last_group": "id_my_group", "is_last_teacher": False})
            name_group = str(db.get_groups(id_group=user["id_my_group"])["title"])
            bot.send_message(message.chat.id, "Загружаю расписание группы " + name_group + "...")
            schedule = get_schedule(user["id_my_group"], get_date_now())
            bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id + 1,
                                  text="Группа " + name_group + "\n" + schedule,
                                  parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "Вы еще не сохранили свою группу, воспользуйтесь командой /save")


@bot.message_handler(commands=['last'])
def last(message):
    try:
        user = db.get_user(message.chat.id)
        if user["is_last_teacher"]:
            if user["id_last_teacher"]:
                name_teacher = str(db.get_teachers(id_teacher=user["id_last_teacher"])["s_title"])
                bot.send_message(message.chat.id, "Загружаю расписание " + name_teacher + "...")
                schedule = get_schedule(user["id_last_teacher"], get_date_now(), 2)
                bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id + 1,
                                      text="Преподаватель " + name_teacher + "\n" + schedule,
                                      parse_mode="HTML")
                return
        else:
            if user["id_last_group"]:
                name_group = str(db.get_groups(id_group=user["id_last_group"])["title"])
                bot.send_message(message.chat.id, "Загружаю расписание группы " + name_group + "...")
                schedule = get_schedule(user["id_last_group"], get_date_now())
                bot.edit_message_text(chat_id=message.chat.id, message_id=message.message_id + 1,
                                      text="Группа " + name_group + "\n" + schedule,
                                      parse_mode="HTML")
                return

        bot.send_message(message.chat.id, "Сначала выберите расписание командой /start")
    except BaseException as Exc:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        print("PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n", Exc)


@bot.message_handler(commands=["calendar"])
def calendar(message):
    try:
        date = get_date_now()
        keyboard = get_calendar_keyboard(date)
        months = get_months_in_semester()
        i = months.index(date.month)
        if i == 0:
            keyboard.row(types.InlineKeyboardButton(text=MONTHS[months[i + 1]] + " >",
                                                    callback_data="calendar_month_" + str(months[i + 1])))
        elif i == len(months) - 1:
            keyboard.row(types.InlineKeyboardButton(text="< " + MONTHS[months[i - 1]],
                                                    callback_data="calendar_month_" + str(months[i - 1])))
        else:
            keyboard.row(
                types.InlineKeyboardButton(text="< " + MONTHS[months[i - 1]],
                                           callback_data="calendar_month_" + str(months[i - 1])),
                types.InlineKeyboardButton(text=MONTHS[months[i + 1]] + " >",
                                           callback_data="calendar_month_" + str(months[i + 1]))
            )
        user = db.get_user(message.chat.id)
        if user["is_last_teacher"]:
            bot.send_message(message.chat.id,
                             "Преподаватель " + db.get_teachers(id_teacher=user["id_last_teacher"])["s_title"] +
                             "\nКалендарь на " + MONTHS[date.month] + "\nСегодня " + get_date_now().strftime("%d.%m.%Y") + " (" + DAYS[get_date_now().weekday()] + ")",
                             reply_markup=keyboard)
        else:
            bot.send_message(message.chat.id,
                             "Группа " + db.get_groups(id_group=user["id_last_group"])["title"] +
                             "\nКалендарь на " + MONTHS[date.month] + "\nСегодня " + get_date_now().strftime("%d.%m.%Y") + " (" + DAYS[get_date_now().weekday()] + ")",
                             reply_markup=keyboard)
    except BaseException as Exc:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        print("PYTHON ERRORS:\nTraceback info:\n" + tbinfo + "\nError Info:\n", Exc)


@bot.message_handler(
    regexp="(\/my|\/last)\s*?(0?[1-9]|[12][0-9]|3[01]|3[1])[- \.](0[1-9]|1[012])[- \.]?((20\d{2})|(\d{2}))?")
def calendar(message):
    print(message.text)


def get_months_in_semester():
    date = get_date_now()
    if date.month >= 9 or date.month == 1:
        return [9, 10, 11, 12, 1]
    return [2, 3, 4, 5, 6, 7]


def get_calendar_keyboard(date):
    try:
        c = Calendar(0)
        months = c.monthdayscalendar(date.year, date.month)
        keyboard = types.InlineKeyboardMarkup(row_width=7)
        buttons = []
        for week in months:
            for day in week:
                buttons.append(types.InlineKeyboardButton(text=(" " if day == 0 else str(day)),
                                                          callback_data="calendar_0" if day == 0 else "calendar_" + str(
                                                              date.replace(day=day).strftime("%d.%m.%Y"))))
        keyboard.add(*buttons)
        return keyboard
    except BaseException as BE:
        print(BE)


if __name__ == "__main__":
    try:
        app.run()
    except BaseException as E:
        print(E)
