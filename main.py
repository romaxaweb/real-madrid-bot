import json
import os
import asyncio
from aiogram import Bot, Dispatcher, types, executor
import requests
import feedparser

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
NEWS_FEED = 'https://e00-marca.uecdn.es/rss/futbol/real-madrid.xml'
SUBSCRIBERS_FILE = 'subscribers.json'

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(list(subs), f)

def translate(text, lang_to="uk"):
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            'client': 'gtx',
            'sl': 'auto',
            'tl': lang_to,
            'dt': 't',
            'q': text,
        }
        response = requests.get(url, params=params)
        return response.json()[0][0][0]
    except:
        return text

def get_news(count=3):
    feed = feedparser.parse(NEWS_FEED)
    if not feed.entries:
        # Debug: вивід, чи реально є entries
        print("DEBUG: RSS feed.entries:", feed.entries)
        return "Немає новин."
    news_list = []
    for entry in feed.entries[:count]:
        title = translate(entry.title)
        link = entry.link
        news_list.append(f"{title}\n{link}")
    return "\n\n".join(news_list) if news_list else "Немає новин."


def get_next_match():
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY
    }
    params = {
        "team": 541, # Real Madrid ID
        "next": 1
    }
    try:
        r = requests.get(url, headers=headers, params=params)
        data = r.json()
        f = data['response'][0]
        teams = f['teams']
        home = teams['home']['name']
        away = teams['away']['name']
        date = f['fixture']['date'][:16].replace('T', ' ')
        league = f['league']['name']
        return f"Наступний матч: {home} vs {away}\nЛіга: {league}\nДата: {date}"
    except Exception as e:
        return "Не вдалося отримати дані про наступний матч."

def get_laliga_table():
    url = "https://v3.football.api-sports.io/standings"
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY
    }
    params = {
        "league": 140,  # La Liga
        "season": 2023
    }
    try:
        r = requests.get(url, headers=headers, params=params)
        table = r.json()['response'][0]['league']['standings'][0]
        result = "*Таблиця Ла Ліги:*\n```\nМісце  Команда              Очки\n"
        for team in table:
            place = str(team['rank']).rjust(2)
            name = team['team']['name'][:16].ljust(16)
            points = str(team['points']).rjust(3)
            result += f"{place}. {name} {points}\n"
        result += "```"
        return result
    except Exception:
        return "Не вдалося отримати таблицю Ла Ліги."

async def news_autosend():
    while True:
        await asyncio.sleep(3 * 60 * 60) # кожні 3 години
        subs = load_subscribers()
        if subs:
            news = get_news(3)
            for chat_id in subs:
                try:
                    await bot.send_message(chat_id, f"📰 Оновлення новин Real Madrid:\n\n{news}")
                except Exception:
                    pass

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    text = ("Вітаю! Це Real Madrid UA бот 🇪🇸⚽️\n\n"
            "Доступні команди:\n"
            "/news — свіжі новини\n"
            "/nextmatch — найближчий матч\n"
            "/table — таблиця Ла Ліги\n"
            "/subscribe — підписка на автоновини\n"
            "/unsubscribe — відписка\n\n"
            "¡Hala Madrid!")
    await message.reply(text)

@dp.message_handler(commands=['news'])
async def news(message: types.Message):
    await message.reply(get_news(3))

@dp.message_handler(commands=['nextmatch'])
async def nextmatch(message: types.Message):
    await message.reply(get_next_match())

@dp.message_handler(commands=['table'])
async def table(message: types.Message):
    await message.reply(get_laliga_table(), parse_mode='Markdown')

@dp.message_handler(commands=['subscribe'])
async def subscribe(message: types.Message):
    subs = load_subscribers()
    subs.add(message.chat.id)
    save_subscribers(subs)
    await message.reply("Тепер ти підписаний на автоновини про Реал! 📰")

@dp.message_handler(commands=['unsubscribe'])
async def unsubscribe(message: types.Message):
    subs = load_subscribers()
    subs.discard(message.chat.id)
    save_subscribers(subs)
    await message.reply("Відписка від автоновин виконана.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(news_autosend())
    executor.start_polling(dp, skip_updates=True)
