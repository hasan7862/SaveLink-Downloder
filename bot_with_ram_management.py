#!/usr/bin/env python3
"""
Link Extractor বট - RAM ম্যানেজমেন্ট সহ
"""

import telebot
import asyncio
from playwright.async_api import async_playwright
import time
import psutil
import os
import gc

# আপনার Bot Token
BOT_TOKEN = "8348394510:AAHN41D99X35uVUi-7uAII4IECOzxB-EB3Q"

# Bot তৈরি করুন
bot = telebot.TeleBot(BOT_TOKEN)

# RAM সীমা (MB)
RAM_LIMIT = 500
RAM_CLEANUP_THRESHOLD = 450

# Progress messages
progress_messages = [
    "⏳ ব্রাউজার শুরু করছি...",
    "🔍 savelinks পেজ খুলছি...",
    "🔗 হোস্টিং লিঙ্ক খুঁজছি...",
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
    time.sleep(0.5)


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


async def extract_link(url):
    """সরাসরি ডাউনলোড লিঙ্ক বের করুন"""
    
    if "savelinks.me" not in url:
        return {
            "success": False,
            "error": "❌ savelinks.me URL দিন"
        }
    
    browser = None
    
    try:
        # RAM চেক করুন
        if not check_and_cleanup_ram():
            return {
                "success": False,
                "error": "❌ সার্ভার overload - পরে চেষ্টা করুন"
            }
        
        # Playwright শুরু করুন
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # savelinks পেজে যান
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # হোস্টিং লিঙ্ক খুঁজুন - gdflix কে অগ্রাধিকার দিন
            links = await page.query_selector_all("a")
            hosting_url = None
            
            for link in links:
                href = await link.get_attribute("href")
                if href and "gdflix" in href:
                    hosting_url = href
                    break
            
            if not hosting_url:
                for link in links:
                    href = await link.get_attribute("href")
                    if href and "hubcloud" in href:
                        hosting_url = href
                        break
            
            if not hosting_url:
                if browser:
                    await browser.close()
                return {
                    "success": False,
                    "error": "❌ হোস্টিং লিঙ্ক পাওয়া যায়নি"
                }
            
            # হোস্টিং পেজে যান
            await page.goto(hosting_url, wait_until="domcontentloaded", timeout=30000)
            
            # JavaScript লোড হওয়ার জন্য অপেক্ষা করুন
            await page.wait_for_timeout(2000)
            
            # ডাউনলোড লিঙ্ক খুঁজুন
            all_links = await page.query_selector_all("a")
            download_link = None
            
            for link in all_links:
                text = await link.inner_text()
                href = await link.get_attribute("href")
                
                if "INSTANT DL" in text and href and href.startswith("http"):
                    download_link = href
                    break
                
                if href and ("busycdn" in href or "r2.dev" in href or "pixeldrain" in href):
                    if href.startswith("http"):
                        download_link = href
                        break
            
            if browser:
                await browser.close()
            
            # RAM পরিস্কার করুন
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
    
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except:
                pass
        
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
            time.sleep(1.5)
        except:
            pass
    
    # এক্সট্র্যাকশন শুরু করুন
    try:
        result = asyncio.run(extract_link(text))
        
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
    print("🤖 বট শুরু হয়েছে...")
    print(f"📊 RAM Limit: {RAM_LIMIT}MB")
    print(f"⚠️ Cleanup Threshold: {RAM_CLEANUP_THRESHOLD}MB")
    print("Ctrl+C দিয়ে বন্ধ করুন")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n✅ বট বন্ধ হয়েছে")
