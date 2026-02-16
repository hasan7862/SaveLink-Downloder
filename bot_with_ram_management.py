#!/usr/bin/env python3
"""
Link Extractor বট - Requests + BeautifulSoup (কোনো Playwright নেই)
সরাসরি কাজ করবে Render এ
"""

import telebot
import requests
from bs4 import BeautifulSoup
import time
import psutil
import os
import gc
import re

# আপনার Bot Token
BOT_TOKEN = "8348394510:AAHN41D99X35uVUi-7uAII4IECOzxB-EB3Q"

# Bot তৈরি করুন
bot = telebot.TeleBot(BOT_TOKEN)

# RAM সীমা (MB)
RAM_LIMIT = 500
RAM_CLEANUP_THRESHOLD = 450

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Progress messages
progress_messages = [
    "⏳ savelinks পেজ খুলছি...",
    "🔍 হোস্টিং লিঙ্ক খুঁজছি...",
    "📄 হোস্টিং পেজ লোড করছি...",
    "🖱️ ডাউনলোড লিঙ্ক খুঁজছি...",
    "⏱️ সরাসরি লিঙ্ক বের করছি...",
    "✅ প্রায় শেষ...",
]


def get_memory_usage():
    """বর্তমান RAM ব্যবহার (MB)"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def cleanup_memory():
    """RAM পরিস্কার করুন"""
    gc.collect()
    time.sleep(0.3)


def check_and_cleanup_ram():
    """RAM চেক করুন এবং প্রয়োজনে পরিস্কার করুন"""
    current_ram = get_memory_usage()
    
    if current_ram > RAM_CLEANUP_THRESHOLD:
        print(f"⚠️ RAM high: {current_ram:.1f}MB - Cleaning up...")
        cleanup_memory()
        current_ram = get_memory_usage()
        print(f"✅ RAM after cleanup: {current_ram:.1f}MB")
    
    if current_ram > RAM_LIMIT:
        print(f"🔴 RAM CRITICAL: {current_ram:.1f}MB > {RAM_LIMIT}MB")
        return False
    
    return True


def extract_link(url):
    """সরাসরি ডাউনলোড লিঙ্ক বের করুন"""
    
    if "savelinks.me" not in url:
        return {
            "success": False,
            "error": "❌ savelinks.me URL দিন"
        }
    
    try:
        # RAM চেক করুন
        if not check_and_cleanup_ram():
            return {
                "success": False,
                "error": "❌ সার্ভার overload - পরে চেষ্টা করুন"
            }
        
        # savelinks পেজ থেকে হোস্টিং লিঙ্ক বের করুন
        session = requests.Session()
        session.headers.update(HEADERS)
        
        response = session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # সব লিঙ্ক খুঁজুন
        hosting_url = None
        links = soup.find_all('a', href=True)
        
        # gdflix কে অগ্রাধিকার দিন
        for link in links:
            href = link['href']
            if 'gdflix' in href:
                hosting_url = href
                break
        
        # যদি gdflix না পাওয়া যায়, অন্যান্য খুঁজুন
        if not hosting_url:
            for link in links:
                href = link['href']
                if 'hubcloud' in href or 'filepress' in href:
                    hosting_url = href
                    break
        
        if not hosting_url:
            return {
                "success": False,
                "error": "❌ হোস্টিং লিঙ্ক পাওয়া যায়নি"
            }
        
        # হোস্টিং পেজ থেকে ডাউনলোড লিঙ্ক বের করুন
        response = session.get(hosting_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # ডাউনলোড লিঙ্ক খুঁজুন
        download_link = None
        
        # সব লিঙ্ক চেক করুন
        links = soup.find_all('a', href=True)
        
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']
            
            # INSTANT DL লিঙ্ক খুঁজুন
            if 'INSTANT DL' in text and href.startswith('http'):
                download_link = href
                break
            
            # অন্যান্য ডাউনলোড লিঙ্ক
            if href.startswith('http') and any(x in href for x in ['busycdn', 'r2.dev', 'pixeldrain']):
                download_link = href
                break
        
        # JavaScript এ থাকা লিঙ্ক খুঁজুন
        if not download_link:
            # Page source এ regex দিয়ে খুঁজুন
            page_source = response.text
            
            # busycdn লিঙ্ক খুঁজুন
            match = re.search(r'https://instant\.busycdn\.xyz/[a-f0-9:]+', page_source)
            if match:
                download_link = match.group(0)
            
            # r2.dev লিঙ্ক খুঁজুন
            if not download_link:
                match = re.search(r'https://pub-[a-f0-9]+\.r2\.dev/[^\s"\'<>]+', page_source)
                if match:
                    download_link = match.group(0)
            
            # pixeldrain লিঙ্ক খুঁজুন
            if not download_link:
                match = re.search(r'https://pixeldrain\.dev/u/[a-zA-Z0-9]+', page_source)
                if match:
                    download_link = match.group(0)
        
        session.close()
        cleanup_memory()
        
        if download_link:
            return {
                "success": True,
                "downloadLink": download_link
            }
        else:
            return {
                "success": False,
                "error": "❌ ডাউনলোড লিঙ্ক পাওয়া যায়নি"
            }
    
    except requests.Timeout:
        return {
            "success": False,
            "error": "❌ Timeout - পরে চেষ্টা করুন"
        }
    except Exception as e:
        cleanup_memory()
        return {
            "success": False,
            "error": f"❌ Error: {str(e)[:50]}"
        }


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """স্টার্ট কমান্ড"""
    ram_usage = get_memory_usage()
    text = f"""🔗 <b>Link Extractor বট</b>

savelinks.me লিঙ্ক পাঠান, আমি সরাসরি ডাউনলোড লিঙ্ক দেব।

<b>উদাহরণ:</b>
<code>https://savelinks.me/view/IJRaLXbQ</code>

📊 <b>সার্ভার স্ট্যাটাস:</b>
RAM: {ram_usage:.1f}MB / {RAM_LIMIT}MB"""
    
    bot.reply_to(message, text, parse_mode="HTML")


@bot.message_handler(commands=['status'])
def send_status(message):
    """স্ট্যাটাস কমান্ড"""
    ram_usage = get_memory_usage()
    status = "✅ Good" if ram_usage < 400 else "⚠️ High" if ram_usage < 480 else "🔴 Critical"
    
    text = f"""📊 <b>বট স্ট্যাটাস</b>

RAM: {ram_usage:.1f}MB / {RAM_LIMIT}MB
Status: {status}"""
    
    bot.reply_to(message, text, parse_mode="HTML")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """সব বার্তা হ্যান্ডেল করুন"""
    
    text = message.text
    
    # URL কি চেক করুন
    if not text or not ("savelinks.me" in text or "http" in text):
        return
    
    # প্রসেসিং মেসেজ পাঠান
    processing_msg = bot.send_message(
        message.chat.id,
        "⏳ " + progress_messages[0],
        parse_mode="HTML"
    )
    
    # প্রগতি আপডেট করুন
    for i, prog_text in enumerate(progress_messages):
        try:
            bot.edit_message_text(
                "⏳ " + prog_text,
                message.chat.id,
                processing_msg.message_id,
                parse_mode="HTML"
            )
            time.sleep(1.2)
        except:
            pass
    
    # এক্সট্র্যাকশন শুরু করুন
    try:
        result = extract_link(text)
        
        if result["success"]:
            response = f"""✅ <b>ডাউনলোড লিঙ্ক পেয়েছি!</b>

<code>{result['downloadLink']}</code>

📋 কপি করে ব্রাউজারে পেস্ট করুন।"""
        else:
            response = result["error"]
        
        bot.edit_message_text(
            response,
            message.chat.id,
            processing_msg.message_id,
            parse_mode="HTML"
        )
    
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)[:50]}",
            message.chat.id,
            processing_msg.message_id,
            parse_mode="HTML"
        )


if __name__ == "__main__":
    print("🤖 বট শুরু হয়েছি...")
    print(f"📊 RAM Limit: {RAM_LIMIT}MB")
    print(f"⚠️ Cleanup Threshold: {RAM_CLEANUP_THRESHOLD}MB")
    print("Ctrl+C দিয়ে বন্ধ করুন")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n✅ বট বন্ধ হয়েছে")
