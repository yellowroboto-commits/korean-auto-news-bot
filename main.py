import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

# --- ENV ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

BASE_URL = "https://www.dailycar.co.kr"
NEWS_URL = "https://www.dailycar.co.kr/content/news.html"


def load_posted():
    if not os.path.exists("posted.txt"):
        return set()
    with open("posted.txt", "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def save_posted(url):
    with open("posted.txt", "a", encoding="utf-8") as f:
        f.write(url + "\n")


def get_latest_news():
    html = requests.get(NEWS_URL, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    item = soup.select_one("ul.list_type li a")
    if not item:
        return None, None

    title = item.text.strip()
    link = item["href"]
    if not link.startswith("http"):
        link = BASE_URL + link

    return title, link


def get_article_text(url):
    html = requests.get(url, headers=HEADERS, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    article = soup.select_one(".article_view")
    if not article:
        return None

    return article.get_text(separator="\n").strip()


def translate_and_summarize(text):
    prompt = f"""
Переведи текст с корейского на русский.
Сделай КОРОТКИЙ Telegram-пост (5–6 строк).
Без воды, только суть.
Тема: автомобильные новости.

Текст:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip()


def send_to_telegram(title, text, url):
    message = f"🚗 <b>{title}</b>\n\n{text}\n\n<a href=\"{url}\">Источник</a>"

    tg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(tg_url, data={
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    })


def main():
    posted = load_posted()

    title, link = get_latest_news()
    if not link:
        print("Новостей не найдено")
        return

    if link in posted:
        print("Новость уже публиковалась")
        return

    article_text = get_article_text(link)
    if not article_text:
        print("Не удалось получить текст статьи")
        return

    short_text = translate_and_summarize(article_text)

    send_to_telegram(title, short_text, link)
    save_posted(link)

    print("Новость опубликована")


if __name__ == "__main__":
    main()

