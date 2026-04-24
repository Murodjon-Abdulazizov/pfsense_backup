# 🔄 pfSense Backup Bot

Har kuni avtomatik pfSense XML backup olib, Telegram ga yuboruvchi bot.

---

## 📋 Talablar

- pfSense web UI ga kirish imkoni
- Telegram Bot Token (BotFather dan)
- Bepul server (Railway, Render yoki VPS)

---

## 🚀 O'rnatish

### 1. Telegram Bot yaratish

1. Telegramda `@BotFather` ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `MyPfSenseBot`)
4. Olingan **TOKEN** ni saqlang

### 2. Chat ID olish

**Shaxsiy chat uchun:**
1. `@userinfobot` ga `/start` yuboring
2. U sizning ID ingizni ko'rsatadi

**Group uchun:**
1. Botni guruhga qo'shing
2. Guruhga biror xabar yuboring
3. Brauzerda oching:
   `https://api.telegram.org/botYOUR_TOKEN/getUpdates`
4. `"chat":{"id":` qiymatini toping (minus bilan boshlanadi)

---

## ☁️ Bepul Deploy: Railway.app

**Eng oson variant!**

1. [railway.app](https://railway.app) ga kiring (GitHub bilan)
2. **New Project → Deploy from GitHub repo**
3. Kodingizni GitHub ga yuklang
4. **Variables** bo'limiga o'ting, quyidagilarni kiriting:

```
PFSENSE_HOST     = https://192.168.1.1
PFSENSE_USER     = admin
PFSENSE_PASSWORD = parolingiz
TELEGRAM_TOKEN   = bottoken
TELEGRAM_CHAT_ID = chatid
BACKUP_TIME      = 08:00
```

5. Deploy tugmasini bosing ✅

> ⚠️ **Muhim:** pfSense local network da bo'lsa, Railway uniga kira olmaydi.
> Bunday holda VPS yoki pfSense bilan bir xil tarmoqdagi server kerak.

---

## 🖥️ VPS / Local Server da o'rnatish

```bash
# 1. Papka yarating
mkdir pfsense-bot && cd pfsense-bot

# 2. Fayllarni ko'chiring
cp backup_bot.py requirements.txt ./

# 3. Virtual muhit
python3 -m venv venv
source venv/bin/activate

# 4. Kutubxonalar
pip install -r requirements.txt

# 5. .env fayl yarating
cp .env.example .env
nano .env   # o'z sozlamalaringizni kiriting

# 6. Ishga tushirish
export $(cat .env | xargs)
python backup_bot.py
```

### Systemd service (doim ishlash uchun)

```bash
sudo nano /etc/systemd/system/pfsense-bot.service
```

```ini
[Unit]
Description=pfSense Backup Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/pfsense-bot
EnvironmentFile=/home/ubuntu/pfsense-bot/.env
ExecStart=/home/ubuntu/pfsense-bot/venv/bin/python backup_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable pfsense-bot
sudo systemctl start pfsense-bot
sudo systemctl status pfsense-bot
```

---

## 🐳 Docker bilan

```bash
# Build
docker build -t pfsense-bot .

# Ishga tushirish
docker run -d \
  --name pfsense-bot \
  --restart always \
  -e PFSENSE_HOST=https://192.168.1.1 \
  -e PFSENSE_USER=admin \
  -e PFSENSE_PASSWORD=parol \
  -e TELEGRAM_TOKEN=token \
  -e TELEGRAM_CHAT_ID=chatid \
  -e BACKUP_TIME=08:00 \
  pfsense-bot
```

---

## ❓ Muammolar

| Muammo | Yechim |
|--------|--------|
| `Login muvaffaqiyatsiz` | pfSense login/parolni tekshiring |
| `CSRF token topilmadi` | pfSense versiyasini yangilang |
| `Connection refused` | `PFSENSE_HOST` to'g'ri ekanini tekshiring |
| Telegram xato | Bot token va Chat ID ni tekshiring |
| Railway ulanmaydi | pfSense xuddi shu tarmoqdami? |

---

## 📱 Telegram da shunday ko'rinadi

```
✅ pfSense Backup
📅 Sana: 24.04.2026 08:00
📦 Hajm: 142.3 KB
🖥 Host: https://192.168.1.1
```
+ XML fayl biriktirilgan holda
# pfsense_backup
