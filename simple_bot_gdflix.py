#!/usr/bin/env python3
"""
সহজ Link Extractor Telegram বট - gdflix সংস্করণ
শুধু এটি run করুন - সব কাজ হবে
"""

import telebot
import asyncio
from playwright.async_api import async_playwright
import time

# আপনার Bot Token
BOT_TOKEN = "8348394510:AAHN41D99X35uVUi-7uAII4IECOzxB-EB3Q"

# Bot তৈরি করুন
bot = telebot.TeleBot(BOT_TOKEN)

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


async def extract_link(url):
    """সরাসরি ডাউনলোড লিঙ্ক বের করুন"""
    
    if "savelinks.me" not in url:
        return {
            "success": False,
            "error": "❌ savelinks.me URL দিন"
        }
    
    try:
        # Playwright শুরু করুন
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # savelinks পেজে যান
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            # হোস্টিং লিঙ্ক খুঁজুন - gdflix কে অগ্রাধিকার দিন
            links = await page.query_selector_all("a")
            hosting_url = None
            
            # প্রথমে gdflix খুঁজুন
            for link in links:
                href = await link.get_attribute("href")
                if href and "gdflix" in href:
                    hosting_url = href
                    break
            
            # যদি gdflix না পাওয়া যায়, hubcloud খুঁজুন
            if not hosting_url:
                for link in links:
                    href = await link.get_attribute("href")
                    if href and "hubcloud" in href:
                        hosting_url = href
                        break
            
            if not hosting_url:
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
                
                # INSTANT DL লিঙ্ক খুঁজুন
                if "INSTANT DL" in text and href and href.startswith("http"):
                    download_link = href
                    break
                
                # অন্যান্য ডাউনলোড লিঙ্ক
                if href and ("busycdn" in href or "r2.dev" in href or "pixeldrain" in href):
                    if href.startswith("http"):
                        download_link = href
                        break
            
            await browser.close()
            
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
        return {
            "success": False,
            "error": f"❌ Error: {str(e)}"
        }


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """স্টার্ট কমান্ড"""
    text = """🔗 <b>Link Extractor বট</b>

savelinks.me লিঙ্ক পাঠান, আমি সরাসরি ডাউনলোড লিঙ্ক দেব।

<b>উদাহরণ:</b>
<code>https://savelinks.me/view/IJRaLXbQ</code>

আমি প্রগতি দেখিয়ে দেব এবং লিঙ্ক বের করে দেব।"""
    
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
            f"❌ Error: {str(e)}",
            message.chat.id,
            processing_msg.message_id,
            parse_mode="HTML"
        )


if __name__ == "__main__":
    print("🤖 বট শুরু হয়েছে...")
    print("Ctrl+C দিয়ে বন্ধ করুন")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n✅ বট বন্ধ হয়েছে")
