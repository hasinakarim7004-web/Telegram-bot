import asyncio
import re
from playwright.async_api import async_playwright
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot

# ================= Configuration =================
TELEGRAM_BOT_TOKEN = "8984257983:AAE29zFWW4EmUFne3ccuHInxCYScOyPA2ko"
TARGET_CHAT_ID = -1003762887616
PANEL_URL = "http://169.58.133.106/ints/s..."  # Apnar panel-er exact URL

PANEL_USERNAME = ""  # Panel Username (Lagle din)
PANEL_PASSWORD = ""  # Panel Password (Lagle din)
# =================================================

processed_sms_ids = set()
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def extract_otp_and_service(sms_text, cli_text):
    otp_match = re.search(r'\b\d{3}[-\s]?\d{3,4}\b', sms_text)
    otp_code = otp_match.group(0) if otp_match else "No OTP"
    service = cli_text if cli_text else "General"
    return otp_code, service

def get_country_info(phone):
    if phone.startswith("258"):
        return "🇲🇿", "#MZ"
    return "🌐", "#GLOBAL"

async def send_to_telegram(phone, cli, sms_text):
    flag, country_code = get_country_info(phone)
    otp_code, service = extract_otp_and_service(sms_text, cli)
    
    message = (
        f"<b>OtpWork</b>\n"
        f"{flag} {country_code} 💬 +{phone}\n"
        f"🌐 SERVICE: {service}"
    )

    keyboard = [
        [InlineKeyboardButton(f"🎟️ 📋 📋 {otp_code}", callback_data=f"copy_{otp_code}")],
        [InlineKeyboardButton("🕹️ 🤖 PANEL", url="https://t.me/FastWorkNum_bot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=message,
            parse_mode="HTML",
            reply_markup=reply_markup
        )
        print(f"[+] Successfully sent OTP for +{phone} ({otp_code})")
    except Exception as e:
        print(f"[-] Telegram Send Error: {e}")

async def scrape_panel():
    async with async_playwright() as p:
        # Browser initialization
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox"])
        page = await browser.new_page()

        print("[*] Navigating to Panel URL...")
        await page.goto(PANEL_URL, timeout=60000)

        if PANEL_USERNAME and PANEL_PASSWORD:
            try:
                print("[*] Logging in to panel...")
                await page.fill("input[name='username']", PANEL_USERNAME)
                await page.fill("input[name='password']", PANEL_PASSWORD)
                await page.click("button[type='submit']")
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"[-] Login step skipped/failed: {e}")

        print("[*] Monitoring SMS Panel Table...")
        while True:
            try:
                rows = await page.query_selector_all("table tbody tr")
                
                for row in rows:
                    cols = await row.query_selector_all("td")
                    if len(cols) >= 5:
                        number = (await cols[1].inner_text()).strip()
                        cli = (await cols[2].inner_text()).strip()
                        sms = (await cols[4].inner_text()).strip()

                        sms_id = f"{number}_{sms}"

                        if sms_id not in processed_sms_ids:
                            processed_sms_ids.add(sms_id)
                            await send_to_telegram(number, cli, sms)

                await asyncio.sleep(5)
                await page.reload()

            except Exception as e:
                print(f"[-] Scrape Loop Error: {e}")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(scrape_panel())
