import os
import requests
import schedule
import time
import logging
from datetime import datetime

# ─── LOGGING ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

# ─── CONFIG (env variables orqali) ─────────────────────────────────────────
PFSENSE_HOST     = os.environ["PFSENSE_HOST"]       # masalan: https://192.168.1.1
PFSENSE_USER     = os.environ["PFSENSE_USER"]       # admin
PFSENSE_PASSWORD = os.environ["PFSENSE_PASSWORD"]   # parol
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]     # bot token
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]   # chat/group id
BACKUP_TIME      = os.environ.get("BACKUP_TIME", "08:00")  # har kuni soat

# pfSense o'z-o'zidan imzolagan SSL sertifikat ishlatadi — verify=False
session = requests.Session()
session.verify = False
requests.packages.urllib3.disable_warnings()


def pfsense_login():
    """pfSense web UI ga login qiladi, session qaytaradi."""
    log.info("pfSense ga ulanmoqda: %s", PFSENSE_HOST)
    
    # Avval CSRF token olish
    r = session.get(f"{PFSENSE_HOST}/index.php", timeout=30)
    r.raise_for_status()
    
    # CSRF token ni HTML dan ajratib olish
    csrf_token = None
    for line in r.text.splitlines():
        if "__csrf_magic" in line and "value=" in line:
            # <input type='hidden' name='__csrf_magic' value='TOKEN' />
            start = line.find('value="') 
            if start == -1:
                start = line.find("value='")
                end = line.find("'", start + 7)
                csrf_token = line[start + 7:end]
            else:
                end = line.find('"', start + 7)
                csrf_token = line[start + 7:end]
            break

    if not csrf_token:
        raise ValueError("CSRF token topilmadi. pfSense versiyasini tekshiring.")

    log.info("CSRF token olindi, login qilinmoqda...")
    
    # Login
    login_data = {
        "__csrf_magic": csrf_token,
        "usernamefld": PFSENSE_USER,
        "passwordfld": PFSENSE_PASSWORD,
        "login": "Sign In",
    }
    r = session.post(f"{PFSENSE_HOST}/index.php", data=login_data, timeout=30)
    r.raise_for_status()

    if "username" in r.text.lower() and "password" in r.text.lower():
        raise PermissionError("Login muvaffaqiyatsiz! Login/parolni tekshiring.")

    log.info("pfSense ga muvaffaqiyatli kirdik.")


def download_backup():
    """XML backup faylini yuklab oladi."""
    log.info("Backup yuklab olinmoqda...")

    # Backup sahifasiga kirish va CSRF olish
    r = session.get(f"{PFSENSE_HOST}/diag_backup.php", timeout=30)
    r.raise_for_status()

    # CSRF token
    csrf_token = None
    for line in r.text.splitlines():
        if "__csrf_magic" in line and "value=" in line:
            start = line.find('value="')
            if start == -1:
                start = line.find("value='")
                end = line.find("'", start + 7)
                csrf_token = line[start + 7:end]
            else:
                end = line.find('"', start + 7)
                csrf_token = line[start + 7:end]
            break

    if not csrf_token:
        raise ValueError("Backup sahifasida CSRF token topilmadi.")

    backup_data = {
        "__csrf_magic": csrf_token,
        "donotbackuprrd": "on",    # RRD data backup qilinmaydi (fayl kichikroq)
        "download": "Download configuration as XML",
        "backuparea": "",
        "encrypt": "",
        "encrypt_password": "",
        "encrypt_password_confirm": "",
    }

    r = session.post(
        f"{PFSENSE_HOST}/diag_backup.php",
        data=backup_data,
        timeout=60,
        stream=True,
    )
    r.raise_for_status()

    if "application/octet-stream" not in r.headers.get("Content-Type", "") and \
       "text/xml" not in r.headers.get("Content-Type", ""):
        raise RuntimeError("Backup fayl kelmadi. pfSense javobini tekshiring.")

    # Faylni saqlash
    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M")
    filename = f"pfsense_backup_{date_str}.xml"
    filepath = f"/tmp/{filename}"

    with open(filepath, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    size_kb = os.path.getsize(filepath) / 1024
    log.info("Backup saqlandi: %s (%.1f KB)", filepath, size_kb)
    return filepath, filename, size_kb


def send_to_telegram(filepath, filename, size_kb):
    """Backup faylini Telegram ga yuboradi."""
    log.info("Telegram ga yuborilmoqda...")

    date_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    caption = (
        f"✅ *pfSense Backup*\n"
        f"📅 Sana: `{date_str}`\n"
        f"📦 Hajm: `{size_kb:.1f} KB`\n"
        f"🖥 Host: `{PFSENSE_HOST}`"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"

    with open(filepath, "rb") as f:
        resp = requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption,
                "parse_mode": "Markdown",
            },
            files={"document": (filename, f, "text/xml")},
            timeout=60,
        )

    resp.raise_for_status()
    result = resp.json()

    if not result.get("ok"):
        raise RuntimeError(f"Telegram xato: {result}")

    log.info("Telegram ga muvaffaqiyatli yuborildi!")


def send_error_to_telegram(error_msg):
    """Xatolik xabarini Telegram ga yuboradi."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(
            url,
            data={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"❌ *pfSense Backup XATO!*\n\n`{error_msg}`",
                "parse_mode": "Markdown",
            },
            timeout=30,
        )
    except Exception:
        pass


def run_backup():
    """Asosiy backup jarayoni."""
    log.info("═" * 50)
    log.info("Backup jarayoni boshlandi...")
    filepath = None

    try:
        pfsense_login()
        filepath, filename, size_kb = download_backup()
        send_to_telegram(filepath, filename, size_kb)
        log.info("Backup jarayoni muvaffaqiyatli yakunlandi!")
    except Exception as e:
        log.error("XATO: %s", e)
        send_error_to_telegram(str(e))
    finally:
        # Vaqtinchalik faylni o'chirish
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            log.info("Vaqtinchalik fayl o'chirildi.")


def main():
    log.info("pfSense Backup Bot ishga tushdi.")
    log.info("Backup vaqti: har kuni soat %s", BACKUP_TIME)

    # Har kuni belgilangan vaqtda ishga tushish
    schedule.every().day.at(BACKUP_TIME).do(run_backup)

    # Birinchi marta darhol ishga tushirishni xohlasangiz:
    # run_backup()

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
