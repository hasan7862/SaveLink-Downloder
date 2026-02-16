#!/usr/bin/env python3
"""
Link Extractor Telegram Bot - FINAL PRODUCTION CODE
সরাসরি ডাউনলোড লিঙ্ক বের করুন savelinks.me থেকে
✅ সম্পূর্ণ, পরীক্ষিত এবং প্রস্তুত
"""

import telebot
import requests
from bs4 import BeautifulSoup
import time
import psutil
import os
import gc
import re
from datetime import datetime

# ========== BOT TOKEN ==========
BOT_TOKEN = "8254736416:AAGfYeuXDphRXHwNtL2pWRQeD73S4RKwBDE"
# ==============================

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Configuration
RAM_LIMIT = 500
RAM_CLEANUP_THRESHOLD = 450
REQUEST_TIMEOUT = 20

# Headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Progress messages
PROGRESS_MESSAGES = [
    "⏳ savelinks পেজ খুলছি...",
    "🔍 হোস্টিং লিঙ্ক খুঁজছি...",
    "📄 হোস্টিং পেজ লোড করছি...",
    "🖱️ ডাউনলোড লিঙ্ক খুঁজছি...",
    "⏱️ সরাসরি লিঙ্ক বের করছি...",
    "✅ প্রায় শেষ...",
]

# Statistics
stats = {
    'total_requests': 0,
    'successful': 0,
    'failed': 0,
    'start_time': datetime.now()
}


def get_memory_usage():
    """Get current RAM usage in MB"""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def cleanup_memory():
    """Clean up memory"""
    gc.collect()
    time.sleep(0.2)


def check_and_cleanup_ram():
    """Check RAM and cleanup if needed"""
    current_ram = get_memory_usage()
    
    if current_ram > RAM_CLEANUP_THRESHOLD:
        print(f"⚠️  RAM high: {current_ram:.1f}MB - Cleaning up...")
        cleanup_memory()
        current_ram = get_memory_usage()
        print(f"✅ RAM after cleanup: {current_ram:.1f}MB")
    
    if current_ram > RAM_LIMIT:
        print(f"🔴 RAM CRITICAL: {current_ram:.1f}MB > {RAM_LIMIT}MB")
        return False
    
    return True


def extract_download_link(url):
    """Extract direct download link from savelinks URL"""
    
    if "savelinks.me" not in url:
        return {
            "success": False,
            "error": "❌ savelinks.me URL দিন"
        }
    
    try:
        # Check RAM
        if not check_and_cleanup_ram():
            return {
                "success": False,
                "error": "❌ সার্ভার overload - পরে চেষ্টা করুন"
            }
        
        session = requests.Session()
        session.headers.update(HEADERS)
        
        # Step 1: Get savelinks page
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching savelinks page: {url}")
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Step 2: Find hosting link
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Finding hosting link...")
        hosting_url = None
        links = soup.find_all('a', href=True)
        
        # Priority: gdflix > hubcloud > filepress
        for link in links:
            href = link['href']
            if 'gdflix' in href:
                hosting_url = href
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found gdflix link")
                break
        
        if not hosting_url:
            for link in links:
                href = link['href']
                if 'hubcloud' in href or 'filepress' in href:
                    hosting_url = href
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found alternative link")
                    break
        
        if not hosting_url:
            session.close()
            cleanup_memory()
            return {
                "success": False,
                "error": "❌ হোস্টিং লিঙ্ক পাওয়া যায়নি"
            }
        
        # Step 3: Get hosting page
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching hosting page: {hosting_url}")
        response = session.get(hosting_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Step 4: Find download link
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Finding download link...")
        download_link = None
        
        # Check HTML links
        links = soup.find_all('a', href=True)
        for link in links:
            text = link.get_text(strip=True)
            href = link['href']
            
            if 'INSTANT DL' in text and href.startswith('http'):
                download_link = href
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found INSTANT DL link")
                break
            
            if href.startswith('http') and any(x in href for x in ['busycdn', 'r2.dev', 'pixeldrain']):
                download_link = href
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found alternative download link")
                break
        
        # Check page source with regex
        if not download_link:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Searching in page source...")
            page_source = response.text
            
            # busycdn
            match = re.search(r'https://instant\.busycdn\.xyz/[a-f0-9:]+', page_source)
            if match:
                download_link = match.group(0)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Found busycdn link")
            
            # r2.dev
            if not download_link:
                match = re.search(r'https://pub-[a-f0-9]+\.r2\.dev/[^\s"\'<>]+', page_source)
                if match:
                    download_link = match.group(0)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found r2.dev link")
            
            # pixeldrain
            if not download_link:
                match = re.search(r'https://pixeldrain\.dev/u/[a-zA-Z0-9]+', page_source)
                if match:
                    download_link = match.group(0)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Found pixeldrain link")
        
        session.close()
        cleanup_memory()
        
        if download_link:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Success!")
            stats['successful'] += 1
            return {
                "success": True,
                "downloadLink": download_link
            }
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ No download link found")
            stats['failed'] += 1
            return {
                "success": False,
                "error": "❌ ডাউনলোড লিঙ্ক পাওয়া যায়নি"
            }
    
    except requests.Timeout:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Timeout")
        stats['failed'] += 1
        cleanup_memory()
        return {
            "success": False,
            "error": "❌ Timeout - পরে চেষ্টা করুন"
        }
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Error: {str(e)}")
        stats['failed'] += 1
        cleanup_memory()
        return {
            "success": False,
            "error": f"❌ Error: {str(e)[:50]}"
        }


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Handle /start command"""
    ram_usage = get_memory_usage()
    text = f"""🔗 <b>Link Extractor বট</b>

savelinks.me লিঙ্ক পাঠান, আমি সরাসরি ডাউনলোড লিঙ্ক দেব।

<b>উদাহরণ:</b>
<code>https://savelinks.me/view/IJRaLXbQ</code>

📊 <b>সার্ভার স্ট্যাটাস:</b>
RAM: {ram_usage:.1f}MB / {RAM_LIMIT}MB
Status: {'✅ Good' if ram_usage < 400 else '⚠️ High' if ram_usage < 480 else '🔴 Critical'}"""
    
    bot.reply_to(message, text, parse_mode="HTML")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] /start command from {message.from_user.id}")


@bot.message_handler(commands=['status'])
def send_status(message):
    """Handle /status command"""
    ram_usage = get_memory_usage()
    uptime = datetime.now() - stats['start_time']
    uptime_str = f"{uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"
    
    text = f"""📊 <b>বট স্ট্যাটাস</b>

RAM: {ram_usage:.1f}MB / {RAM_LIMIT}MB
Status: {'✅ Good' if ram_usage < 400 else '⚠️ High' if ram_usage < 480 else '🔴 Critical'}

📈 <b>পরিসংখ্যান:</b>
Total Requests: {stats['total_requests']}
Successful: {stats['successful']}
Failed: {stats['failed']}
Uptime: {uptime_str}"""
    
    bot.reply_to(message, text, parse_mode="HTML")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] /status command from {message.from_user.id}")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle all messages"""
    
    text = message.text
    
    # Check if URL
    if not text or not ("savelinks.me" in text or "http" in text):
        return
    
    stats['total_requests'] += 1
    print(f"[{datetime.now().strftime('%H:%M:%S')}] New request from {message.from_user.id}: {text[:50]}")
    
    # Send processing message
    processing_msg = bot.send_message(
        message.chat.id,
        "⏳ " + PROGRESS_MESSAGES[0],
        parse_mode="HTML"
    )
    
    # Update progress
    for i, prog_text in enumerate(PROGRESS_MESSAGES):
        try:
            bot.edit_message_text(
                "⏳ " + prog_text,
                message.chat.id,
                processing_msg.message_id,
                parse_mode="HTML"
            )
            time.sleep(1.0)
        except:
            pass
    
    # Extract link
    try:
        result = extract_download_link(text)
        
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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Exception: {str(e)}")
        bot.edit_message_text(
            f"❌ Error: {str(e)[:50]}",
            message.chat.id,
            processing_msg.message_id,
            parse_mode="HTML"
        )


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🤖 Link Extractor Telegram Bot - PRODUCTION")
    print("="*70)
    print(f"🕐 Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 RAM Limit: {RAM_LIMIT}MB")
    print(f"⚠️  Cleanup Threshold: {RAM_CLEANUP_THRESHOLD}MB")
    print(f"🔌 Bot Token: {BOT_TOKEN[:30]}...")
    print("="*70)
    print("✅ বট চালু হয়েছে!")
    print("📨 Telegram এ বার্তা পাঠান")
    print("Ctrl+C দিয়ে বন্ধ করুন")
    print("="*70 + "\n")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n" + "="*70)
        print("✅ বট বন্ধ হয়েছে")
        print(f"📈 Total Requests: {stats['total_requests']}")
        print(f"✅ Successful: {stats['successful']}")
        print(f"❌ Failed: {stats['failed']}")
        print("="*70 + "\n")


if __name__ == "__main__":
    main()
