"""
Complete VPN Shop Bot - Multilingual Edition
Languages: English 🇬🇧, Russian 🇷🇺, Hindi 🇮🇳, Arabic 🇸🇦
Optimized for Railway deployment
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters
)

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Config: Railway uses Environment Variables (no config.json needed) ─────────
def load_config():
    """
    Priority: Environment Variables → config.json (fallback for local dev)
    On Railway: set these in the Railway dashboard → Variables tab.
    """
    # Try environment variables first (Railway)
    bot_token = os.environ.get("BOT_TOKEN")
    if bot_token:
        admin_ids_raw = os.environ.get("ADMIN_IDS", "")
        admin_ids = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]
        return {
            "bot_token": bot_token,
            "admin_ids": admin_ids,
            "trial_days": int(os.environ.get("TRIAL_DAYS", "3")),
            "referred_trial_days": int(os.environ.get("REFERRED_TRIAL_DAYS", "7")),
            "support_username": os.environ.get("SUPPORT_USERNAME", "@Support"),
            "payment_provider_token": os.environ.get("PAYMENT_PROVIDER_TOKEN", ""),
            "webhook_url": os.environ.get("WEBHOOK_URL", ""),  # e.g. https://your-app.up.railway.app
        }

    # Fallback: config.json (local development)
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            cfg = json.load(f)
        cfg.setdefault("webhook_url", "")
        cfg.setdefault("payment_provider_token", "")
        return cfg

    raise RuntimeError(
        "❌ No configuration found!\n"
        "On Railway: add BOT_TOKEN in the Variables tab.\n"
        "Locally: create config.json with bot_token."
    )

config = load_config()

BOT_TOKEN             = config["bot_token"]
ADMIN_IDS             = config.get("admin_ids", [])
SUPPORT_USERNAME      = config.get("support_username", "@Support")
PAYMENT_PROVIDER_TOKEN = config.get("payment_provider_token", "")
WEBHOOK_URL           = config.get("webhook_url", "")  # set on Railway
PORT                  = int(os.environ.get("PORT", 8080))  # Railway injects PORT

# ── Database path (persistent volume on Railway or local) ──────────────────────
DB_PATH = os.environ.get("DB_PATH", "vpn_shop.db")

# ── Translations ───────────────────────────────────────────────────────────────
TRANSLATIONS = {
    'en': {
        'flag': '🇬🇧',
        'name': 'English',
        'welcome': '👋 Welcome, {name}!\n\n🔒 <b>Premium VPN Service</b>\n\n✨ <b>Features:</b>\n• 🚀 High-speed servers worldwide\n• 🔐 Military-grade encryption\n• 🚫 No logs policy\n• 📱 Unlimited bandwidth\n• 🌍 Multiple locations\n• 💬 24/7 support',
        'welcome_referred': '\n\n🎁 <b>You were referred!</b>\nGet 7 days FREE trial instead of 3!',
        'welcome_trial': '\n\n🎁 Get 3 days <b>FREE TRIAL</b> now!',
        'choose_option': '\n\nChoose an option below:',
        'welcome_back': '👋 Welcome back, {name}!\n\n📊 <b>Status:</b> {status}\n\nChoose an option:',
        'btn_trial': '🎁 Free Trial (3 Days)',
        'btn_buy': '💎 Buy Subscription',
        'btn_account': '👤 My Account',
        'btn_referral': '🎁 Referral Program',
        'btn_promo': '🎫 Use Promocode',
        'btn_about': 'ℹ️ About VPN',
        'btn_help': 'ℹ️ Help',
        'btn_support': '📞 Support',
        'btn_faq': '❓ FAQ',
        'btn_admin': '🔧 Admin Panel',
        'btn_back': '◀️ Back',
        'btn_language': '🌍 Change Language',
        'trial_used': '❌ <b>Trial Already Used</b>\n\nYou\'ve already activated your free trial!\n\n💎 Check our affordable subscription plans below:',
        'trial_activated': '🎉 <b>Trial Activated!</b>\n\n✅ Duration: <b>{days} days</b>\n✅ Expires: <code>{expires}</code>\n✅ Devices: <b>1</b>\n\n📱 <b>Your VPN Configuration:</b>\n<code>{config}</code>\n\n📋 <b>How to Connect:</b>\n1. Copy the config link above\n2. Download a VPN app:\n   • Android: v2rayNG\n   • iOS: Shadowrocket\n   • Windows: v2rayN\n   • Mac: V2Box\n3. Import the config\n4. Connect and enjoy!\n\n💡 Love it? Upgrade for more!',
        'plans_title': '💎 <b>Subscription Plans</b>\n\nChoose the plan that fits your needs:\n\n',
        'plan_item': '📱 <b>{name}</b> - {devices} device{plural}\n   Starting at ${price}/month\n\n',
        'plans_features': '\n✨ All plans include:\n• Unlimited bandwidth\n• No speed limits\n• Multiple server locations\n• 24/7 support',
        'duration_title': '📱 <b>{plan_name} Plan</b>\nDevices: {devices}\n\n⏱ <b>Choose duration:</b>\n\n',
        'duration_item': '• <b>{label}</b>: ${price} (${monthly}/month)\n',
        'payment_title': '💳 <b>Payment</b>\n\n📱 Plan: {plan}\n⏱ Duration: {duration} days\n💰 Total: <b>${price}</b>\n\n🔒 Secure payment\nChoose payment method:',
        'payment_success': '✅ <b>Payment Successful!</b>\n\n📱 Plan: {plan}\n⏱ Duration: {duration} days\n💰 Paid: ${price}\n✅ Expires: <code>{expires}</code>\n\n📱 <b>Your VPN Configuration:</b>\n<code>{config}</code>\n\n🎁 Invite friends and earn rewards!',
        'account_title': '👤 <b>Your Account</b>\n\n🆔 ID: <code>{user_id}</code>\n👤 Name: {name}\n📅 Member since: {date}\n\n📊 <b>Subscription:</b> {status}\n💰 <b>Total spent:</b> ${spent}\n👥 <b>Referrals:</b> {refs}',
        'status_no_sub': '❌ No active subscription',
        'status_expired': '⏰ Subscription expired',
        'status_active': '✅ Active ({days} days left)',
    },
    'ru': {
        'flag': '🇷🇺',
        'name': 'Русский',
        'welcome': '👋 Добро пожаловать, {name}!\n\n🔒 <b>Премиум VPN Сервис</b>\n\n✨ <b>Возможности:</b>\n• 🚀 Высокоскоростные серверы по всему миру\n• 🔐 Военное шифрование\n• 🚫 Без логов\n• 📱 Безлимитный трафик\n• 🌍 Множество локаций\n• 💬 Поддержка 24/7',
        'welcome_referred': '\n\n🎁 <b>Вас пригласили!</b>\nПолучите 7 дней БЕСПЛАТНО вместо 3!',
        'welcome_trial': '\n\n🎁 Получите 3 дня <b>БЕСПЛАТНО</b> прямо сейчас!',
        'choose_option': '\n\nВыберите опцию ниже:',
        'welcome_back': '👋 С возвращением, {name}!\n\n📊 <b>Статус:</b> {status}\n\nВыберите опцию:',
        'btn_trial': '🎁 Бесплатная пробная (3 дня)',
        'btn_buy': '💎 Купить подписку',
        'btn_account': '👤 Мой аккаунт',
        'btn_referral': '🎁 Реферальная программа',
        'btn_promo': '🎫 Использовать промокод',
        'btn_about': 'ℹ️ О VPN',
        'btn_help': 'ℹ️ Помощь',
        'btn_support': '📞 Поддержка',
        'btn_faq': '❓ Частые вопросы',
        'btn_admin': '🔧 Админ панель',
        'btn_back': '◀️ Назад',
        'btn_language': '🌍 Сменить язык',
        'trial_used': '❌ <b>Пробная версия уже использована</b>\n\nВы уже активировали бесплатную пробную версию!\n\n💎 Посмотрите наши доступные тарифы:',
        'trial_activated': '🎉 <b>Пробная версия активирована!</b>\n\n✅ Длительность: <b>{days} дней</b>\n✅ Истекает: <code>{expires}</code>\n✅ Устройств: <b>1</b>\n\n📱 <b>Ваша VPN конфигурация:</b>\n<code>{config}</code>\n\n📋 <b>Как подключиться:</b>\n1. Скопируйте конфиг выше\n2. Скачайте VPN приложение:\n   • Android: v2rayNG\n   • iOS: Shadowrocket\n   • Windows: v2rayN\n   • Mac: V2Box\n3. Импортируйте конфиг\n4. Подключайтесь!\n\n💡 Понравилось? Улучшите план!',
        'plans_title': '💎 <b>Тарифные планы</b>\n\nВыберите план который вам подходит:\n\n',
        'plan_item': '📱 <b>{name}</b> - {devices} устройств{plural}\n   От ${price}/месяц\n\n',
        'plans_features': '\n✨ Все планы включают:\n• Безлимитный трафик\n• Без ограничений скорости\n• Множество серверов\n• Поддержка 24/7',
        'duration_title': '📱 <b>План {plan_name}</b>\nУстройств: {devices}\n\n⏱ <b>Выберите длительность:</b>\n\n',
        'duration_item': '• <b>{label}</b>: ${price} (${monthly}/месяц)\n',
        'payment_title': '💳 <b>Оплата</b>\n\n📱 План: {plan}\n⏱ Длительность: {duration} дней\n💰 Итого: <b>${price}</b>\n\n🔒 Безопасная оплата\nВыберите способ оплаты:',
        'payment_success': '✅ <b>Оплата успешна!</b>\n\n📱 План: {plan}\n⏱ Длительность: {duration} дней\n💰 Оплачено: ${price}\n✅ Истекает: <code>{expires}</code>\n\n📱 <b>Ваша VPN конфигурация:</b>\n<code>{config}</code>\n\n🎁 Приглашайте друзей и получайте награды!',
        'account_title': '👤 <b>Ваш аккаунт</b>\n\n🆔 ID: <code>{user_id}</code>\n👤 Имя: {name}\n📅 С нами с: {date}\n\n📊 <b>Подписка:</b> {status}\n💰 <b>Всего потрачено:</b> ${spent}\n👥 <b>Рефералов:</b> {refs}',
        'status_no_sub': '❌ Нет активной подписки',
        'status_expired': '⏰ Подписка истекла',
        'status_active': '✅ Активна ({days} дней осталось)',
    },
    'hi': {
        'flag': '🇮🇳',
        'name': 'हिंदी',
        'welcome': '👋 स्वागत है, {name}!\n\n🔒 <b>प्रीमियम VPN सेवा</b>\n\n✨ <b>विशेषताएं:</b>\n• 🚀 दुनिया भर में हाई-स्पीड सर्वर\n• 🔐 मिलिट्री-ग्रेड एन्क्रिप्शन\n• 🚫 नो लॉग पॉलिसी\n• 📱 असीमित बैंडविड्थ\n• 🌍 कई लोकेशन\n• 💬 24/7 सपोर्ट',
        'welcome_referred': '\n\n🎁 <b>आपको रेफर किया गया!</b>\n3 के बजाय 7 दिन मुफ्त ट्रायल पाएं!',
        'welcome_trial': '\n\n🎁 अभी 3 दिन <b>मुफ्त ट्रायल</b> पाएं!',
        'choose_option': '\n\nनीचे से विकल्प चुनें:',
        'welcome_back': '👋 वापसी पर स्वागत है, {name}!\n\n📊 <b>स्थिति:</b> {status}\n\nविकल्प चुनें:',
        'btn_trial': '🎁 मुफ्त ट्रायल (3 दिन)',
        'btn_buy': '💎 सब्सक्रिप्शन खरीदें',
        'btn_account': '👤 मेरा अकाउंट',
        'btn_referral': '🎁 रेफरल प्रोग्राम',
        'btn_promo': '🎫 प्रोमोकोड यूज करें',
        'btn_about': 'ℹ️ VPN के बारे में',
        'btn_help': 'ℹ️ मदद',
        'btn_support': '📞 सपोर्ट',
        'btn_faq': '❓ FAQ',
        'btn_admin': '🔧 एडमिन पैनल',
        'btn_back': '◀️ वापस',
        'btn_language': '🌍 भाषा बदलें',
        'trial_used': '❌ <b>ट्रायल पहले से यूज हो चुका</b>\n\nआपने पहले ही अपना मुफ्त ट्रायल एक्टिवेट कर लिया है!\n\n💎 हमारी किफायती प्लान्स देखें:',
        'trial_activated': '🎉 <b>ट्रायल एक्टिवेट हो गया!</b>\n\n✅ अवधि: <b>{days} दिन</b>\n✅ समाप्त होगा: <code>{expires}</code>\n✅ डिवाइस: <b>1</b>\n\n📱 <b>आपका VPN कॉन्फिगरेशन:</b>\n<code>{config}</code>\n\n📋 <b>कनेक्ट कैसे करें:</b>\n1. ऊपर दिया कॉन्फिग कॉपी करें\n2. VPN ऐप डाउनलोड करें:\n   • Android: v2rayNG\n   • iOS: Shadowrocket\n   • Windows: v2rayN\n   • Mac: V2Box\n3. कॉन्फिग इम्पोर्ट करें\n4. कनेक्ट करें और एन्जॉय करें!\n\n💡 पसंद आया? अपग्रेड करें!',
        'plans_title': '💎 <b>सब्सक्रिप्शन प्लान्स</b>\n\nअपने लिए सही प्लान चुनें:\n\n',
        'plan_item': '📱 <b>{name}</b> - {devices} डिवाइस{plural}\n   ${price}/महीने से शुरू\n\n',
        'plans_features': '\n✨ सभी प्लान्स में शामिल:\n• असीमित बैंडविड्थ\n• स्पीड लिमिट नहीं\n• कई सर्वर लोकेशन\n• 24/7 सपोर्ट',
        'duration_title': '📱 <b>{plan_name} प्लान</b>\nडिवाइस: {devices}\n\n⏱ <b>अवधि चुनें:</b>\n\n',
        'duration_item': '• <b>{label}</b>: ${price} (${monthly}/महीना)\n',
        'payment_title': '💳 <b>पेमेंट</b>\n\n📱 प्लान: {plan}\n⏱ अवधि: {duration} दिन\n💰 कुल: <b>${price}</b>\n\n🔒 सुरक्षित पेमेंट\nपेमेंट तरीका चुनें:',
        'payment_success': '✅ <b>पेमेंट सफल रहा!</b>\n\n📱 प्लान: {plan}\n⏱ अवधि: {duration} दिन\n💰 भुगतान: ${price}\n✅ समाप्त होगा: <code>{expires}</code>\n\n📱 <b>आपका VPN कॉन्फिगरेशन:</b>\n<code>{config}</code>\n\n🎁 दोस्तों को इनवाइट करें और रिवॉर्ड पाएं!',
        'account_title': '👤 <b>आपका अकाउंट</b>\n\n🆔 ID: <code>{user_id}</code>\n👤 नाम: {name}\n📅 मेंबर बने: {date}\n\n📊 <b>सब्सक्रिप्शन:</b> {status}\n💰 <b>कुल खर्च:</b> ${spent}\n👥 <b>रेफरल:</b> {refs}',
        'status_no_sub': '❌ कोई सक्रिय सब्सक्रिप्शन नहीं',
        'status_expired': '⏰ सब्सक्रिप्शन समाप्त हो गया',
        'status_active': '✅ सक्रिय ({days} दिन बचे)',
    },
    'ar': {
        'flag': '🇸🇦',
        'name': 'العربية',
        'welcome': '👋 مرحباً، {name}!\n\n🔒 <b>خدمة VPN المميزة</b>\n\n✨ <b>المميزات:</b>\n• 🚀 خوادم عالية السرعة حول العالم\n• 🔐 تشفير عسكري\n• 🚫 سياسة عدم الاحتفاظ بالسجلات\n• 📱 باندويث غير محدود\n• 🌍 مواقع متعددة\n• 💬 دعم 24/7',
        'welcome_referred': '\n\n🎁 <b>تمت إحالتك!</b>\nاحصل على 7 أيام تجربة مجانية بدلاً من 3!',
        'welcome_trial': '\n\n🎁 احصل على 3 أيام <b>تجربة مجانية</b> الآن!',
        'choose_option': '\n\nاختر خياراً أدناه:',
        'welcome_back': '👋 مرحباً بعودتك، {name}!\n\n📊 <b>الحالة:</b> {status}\n\nاختر خياراً:',
        'btn_trial': '🎁 تجربة مجانية (3 أيام)',
        'btn_buy': '💎 شراء اشتراك',
        'btn_account': '👤 حسابي',
        'btn_referral': '🎁 برنامج الإحالة',
        'btn_promo': '🎫 استخدام رمز ترويجي',
        'btn_about': 'ℹ️ عن VPN',
        'btn_help': 'ℹ️ مساعدة',
        'btn_support': '📞 الدعم',
        'btn_faq': '❓ الأسئلة الشائعة',
        'btn_admin': '🔧 لوحة الإدارة',
        'btn_back': '◀️ رجوع',
        'btn_language': '🌍 تغيير اللغة',
        'trial_used': '❌ <b>تم استخدام التجربة المجانية</b>\n\nلقد قمت بتفعيل تجربتك المجانية بالفعل!\n\n💎 تحقق من خطط الاشتراك المعقولة:',
        'trial_activated': '🎉 <b>تم تفعيل التجربة المجانية!</b>\n\n✅ المدة: <b>{days} أيام</b>\n✅ تنتهي في: <code>{expires}</code>\n✅ الأجهزة: <b>1</b>\n\n📱 <b>إعدادات VPN الخاصة بك:</b>\n<code>{config}</code>\n\n📋 <b>كيفية الاتصال:</b>\n1. انسخ رابط الإعداد أعلاه\n2. قم بتنزيل تطبيق VPN:\n   • Android: v2rayNG\n   • iOS: Shadowrocket\n   • Windows: v2rayN\n   • Mac: V2Box\n3. استورد الإعداد\n4. اتصل واستمتع!\n\n💡 أعجبك؟ قم بالترقية!',
        'plans_title': '💎 <b>خطط الاشتراك</b>\n\nاختر الخطة التي تناسب احتياجاتك:\n\n',
        'plan_item': '📱 <b>{name}</b> - {devices} جهاز{plural}\n   ابتداءً من ${price}/شهر\n\n',
        'plans_features': '\n✨ جميع الخطط تتضمن:\n• باندويث غير محدود\n• بدون حد للسرعة\n• مواقع خوادم متعددة\n• دعم 24/7',
        'duration_title': '📱 <b>خطة {plan_name}</b>\nالأجهزة: {devices}\n\n⏱ <b>اختر المدة:</b>\n\n',
        'duration_item': '• <b>{label}</b>: ${price} (${monthly}/شهر)\n',
        'payment_title': '💳 <b>الدفع</b>\n\n📱 الخطة: {plan}\n⏱ المدة: {duration} يوم\n💰 المجموع: <b>${price}</b>\n\n🔒 دفع آمن\nاختر طريقة الدفع:',
        'payment_success': '✅ <b>تم الدفع بنجاح!</b>\n\n📱 الخطة: {plan}\n⏱ المدة: {duration} يوم\n💰 المدفوع: ${price}\n✅ تنتهي في: <code>{expires}</code>\n\n📱 <b>إعدادات VPN الخاصة بك:</b>\n<code>{config}</code>\n\n🎁 ادعُ الأصدقاء واربح مكافآت!',
        'account_title': '👤 <b>حسابك</b>\n\n🆔 المعرف: <code>{user_id}</code>\n👤 الاسم: {name}\n📅 عضو منذ: {date}\n\n📊 <b>الاشتراك:</b> {status}\n💰 <b>إجمالي الإنفاق:</b> ${spent}\n👥 <b>الإحالات:</b> {refs}',
        'status_no_sub': '❌ لا يوجد اشتراك نشط',
        'status_expired': '⏰ انتهى الاشتراك',
        'status_active': '✅ نشط (متبقي {days} أيام)',
    }
}

# ── Database ───────────────────────────────────────────────────────────────────
class Database:
    def __init__(self):
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                language_code TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referrer_id INTEGER,
                subscription_end TIMESTAMP,
                is_trial_used BOOLEAN DEFAULT 0,
                is_blocked BOOLEAN DEFAULT 0,
                total_paid REAL DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_name TEXT,
                devices INTEGER,
                duration_days INTEGER,
                price REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT,
                started_at TIMESTAMP,
                expires_at TIMESTAMP,
                config_url TEXT,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT,
                payment_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        conn.commit()
        conn.close()

    def get_user(self, user_id):
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return dict(user) if user else None

    def create_user(self, user_id, username, first_name, language='en', referrer_id=None):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, language_code, referrer_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, language, referrer_id))
        conn.commit()
        conn.close()

    def set_language(self, user_id, language):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET language_code = ? WHERE user_id = ?', (language, user_id))
        conn.commit()
        conn.close()

    def get_language(self, user_id):
        user = self.get_user(user_id)
        return user['language_code'] if user else 'en'

db = Database()

# ── Helpers ────────────────────────────────────────────────────────────────────
def t(user_id, key, **kwargs):
    lang = db.get_language(user_id)
    text = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, TRANSLATIONS['en'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text

def get_language_keyboard():
    keyboard = []
    for lang_code, lang_data in TRANSLATIONS.items():
        keyboard.append([InlineKeyboardButton(
            f"{lang_data['flag']} {lang_data['name']}",
            callback_data=f"lang_{lang_code}"
        )])
    return InlineKeyboardMarkup(keyboard)

# ── Subscription plans ─────────────────────────────────────────────────────────
PLANS = {
    "durations": [30, 60, 180, 365],
    "plans": [
        {"name": "Basic",    "devices": 1, "prices": {"30": 5,  "60": 9,  "180": 25, "365": 45}},
        {"name": "Standard", "devices": 3, "prices": {"30": 10, "60": 18, "180": 50, "365": 90}},
        {"name": "Premium",  "devices": 5, "prices": {"30": 15, "60": 27, "180": 75, "365": 135}},
    ]
}

# ── Handlers ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None

    if args and args[0].startswith('ref'):
        try:
            referrer_id = int(args[0][3:])
        except Exception:
            pass

    db_user = db.get_user(user.id)

    if not db_user:
        message = (
            "🌍 <b>Welcome! / Добро пожаловать! / स्वागत! / مرحباً!</b>\n\n"
            "Please select your language:\n"
            "Пожалуйста, выберите язык:\n"
            "कृपया अपनी भाषा चुनें:\n"
            "يرجى اختيار لغتك:"
        )
        if referrer_id:
            context.user_data['referrer_id'] = referrer_id
        await update.message.reply_text(message, reply_markup=get_language_keyboard(), parse_mode='HTML')
        return

    status = get_subscription_status(user.id)
    message = t(user.id, 'welcome_back', name=user.first_name, status=status)
    await update.message.reply_text(message, reply_markup=get_main_menu(user.id), parse_mode='HTML')

def get_main_menu(user_id):
    user = db.get_user(user_id)
    if not user or user['is_trial_used'] == 0:
        keyboard = [
            [InlineKeyboardButton(t(user_id, 'btn_trial'),    callback_data="trial")],
            [InlineKeyboardButton(t(user_id, 'btn_buy'),      callback_data="plans")],
            [InlineKeyboardButton(t(user_id, 'btn_about'),    callback_data="about"),
             InlineKeyboardButton(t(user_id, 'btn_support'),  callback_data="support")],
            [InlineKeyboardButton(t(user_id, 'btn_language'), callback_data="change_lang")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton(t(user_id, 'btn_buy'),      callback_data="plans")],
            [InlineKeyboardButton(t(user_id, 'btn_account'),  callback_data="account")],
            [InlineKeyboardButton(t(user_id, 'btn_referral'), callback_data="referrals"),
             InlineKeyboardButton(t(user_id, 'btn_promo'),    callback_data="promocode")],
            [InlineKeyboardButton(t(user_id, 'btn_help'),     callback_data="help"),
             InlineKeyboardButton(t(user_id, 'btn_support'),  callback_data="support")],
            [InlineKeyboardButton(t(user_id, 'btn_language'), callback_data="change_lang")],
        ]
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton(t(user_id, 'btn_admin'), callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def get_subscription_status(user_id):
    user = db.get_user(user_id)
    if not user or not user['subscription_end']:
        return t(user_id, 'status_no_sub')
    sub_end = user['subscription_end']
    if isinstance(sub_end, str):
        sub_end = datetime.fromisoformat(sub_end)
    if sub_end < datetime.now():
        return t(user_id, 'status_expired')
    days_left = (sub_end - datetime.now()).days
    return t(user_id, 'status_active', days=days_left)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("lang_"):
        lang = data.split("_")[1]
        existing_user = db.get_user(user_id)
        if existing_user:
            db.set_language(user_id, lang)
            status = get_subscription_status(user_id)
            message = t(user_id, 'welcome_back', name=query.from_user.first_name, status=status)
            await query.edit_message_text(message, reply_markup=get_main_menu(user_id), parse_mode='HTML')
        else:
            referrer_id = context.user_data.get('referrer_id', None)
            db.create_user(user_id, query.from_user.username, query.from_user.first_name, lang, referrer_id)
            message = t(user_id, 'welcome', name=query.from_user.first_name)
            message += t(user_id, 'welcome_referred') if referrer_id else t(user_id, 'welcome_trial')
            message += t(user_id, 'choose_option')
            await query.edit_message_text(message, reply_markup=get_main_menu(user_id), parse_mode='HTML')
        return

    if data == "change_lang":
        await query.edit_message_text(
            t(user_id, 'btn_language') + "\n\nSelect your language:",
            reply_markup=get_language_keyboard(), parse_mode='HTML'
        )
        return

    if data == "trial":
        await handle_trial(query)
    elif data == "plans":
        await show_plans(query)
    elif data.startswith("plan_"):
        await show_durations(query, int(data.split("_")[1]))
    elif data.startswith("dur_"):
        _, plan_index, duration = data.split("_")
        await show_payment_methods(query, int(plan_index), int(duration))
    elif data.startswith("pay_"):
        parts = data.split("_")
        method, plan_index, duration = parts[1], int(parts[2]), int(parts[3])
        await process_payment(query, user_id, method, plan_index, duration)
    elif data == "back_main":
        await back_to_main(query)

async def handle_trial(query):
    user_id = query.from_user.id
    user = db.get_user(user_id)
    if user['is_trial_used']:
        message = t(user_id, 'trial_used')
        keyboard = [
            [InlineKeyboardButton(t(user_id, 'btn_buy'),  callback_data="plans")],
            [InlineKeyboardButton(t(user_id, 'btn_back'), callback_data="back_main")],
        ]
    else:
        days = 7 if user['referrer_id'] else 3
        expires_at = datetime.now() + timedelta(days=days)
        config_url = f"vless://trial-{user_id}@demo.server:443"
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'UPDATE users SET subscription_end = ?, is_trial_used = 1 WHERE user_id = ?',
            (expires_at, user_id)
        )
        conn.commit()
        conn.close()
        message = t(user_id, 'trial_activated',
                    days=days,
                    expires=expires_at.strftime('%Y-%m-%d %H:%M'),
                    config=config_url)
        keyboard = [
            [InlineKeyboardButton(t(user_id, 'btn_buy'),  callback_data="plans")],
            [InlineKeyboardButton(t(user_id, 'btn_back'), callback_data="back_main")],
        ]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_plans(query):
    user_id = query.from_user.id
    message = t(user_id, 'plans_title')
    keyboard = []
    for i, plan in enumerate(PLANS['plans']):
        plural = 's' if plan['devices'] > 1 else ''
        message += t(user_id, 'plan_item',
                     name=plan['name'], devices=plan['devices'],
                     plural=plural, price=plan['prices']['30'])
        keyboard.append([InlineKeyboardButton(
            f"📱 {plan['name']} ({plan['devices']} device{'s' if plan['devices']>1 else ''})",
            callback_data=f"plan_{i}"
        )])
    message += t(user_id, 'plans_features')
    keyboard.append([InlineKeyboardButton(t(user_id, 'btn_back'), callback_data="back_main")])
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_durations(query, plan_index):
    user_id = query.from_user.id
    plan = PLANS['plans'][plan_index]
    message = t(user_id, 'duration_title', plan_name=plan['name'], devices=plan['devices'])
    keyboard = []
    for duration in PLANS['durations']:
        price = plan['prices'][str(duration)]
        label = f"{duration} days" if duration < 365 else "1 year"
        monthly = price / (duration / 30)
        message += t(user_id, 'duration_item', label=label, price=price, monthly=f"{monthly:.2f}")
        keyboard.append([InlineKeyboardButton(
            f"⏱ {label} - ${price}",
            callback_data=f"dur_{plan_index}_{duration}"
        )])
    keyboard.append([InlineKeyboardButton(t(user_id, 'btn_back'), callback_data="plans")])
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def show_payment_methods(query, plan_index, duration):
    user_id = query.from_user.id
    plan = PLANS['plans'][plan_index]
    price = plan['prices'][str(duration)]
    message = t(user_id, 'payment_title',
                plan=f"{plan['name']} ({plan['devices']} devices)",
                duration=duration, price=price)
    keyboard = [
        [InlineKeyboardButton("⭐ Telegram Stars",      callback_data=f"pay_stars_{plan_index}_{duration}")],
        [InlineKeyboardButton("💳 Credit Card (Demo)",  callback_data=f"pay_card_{plan_index}_{duration}")],
        [InlineKeyboardButton("🪙 Crypto (Demo)",       callback_data=f"pay_crypto_{plan_index}_{duration}")],
        [InlineKeyboardButton(t(user_id, 'btn_back'),   callback_data=f"plan_{plan_index}")],
    ]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def process_payment(query, user_id, method, plan_index, duration):
    plan = PLANS['plans'][plan_index]
    price = plan['prices'][str(duration)]

    if method == "stars":
        title = f"{plan['name']} Plan - {duration} days"
        description = f"VPN subscription for {duration} days with {plan['devices']} devices"
        payload = f"plan_{plan_index}_dur_{duration}"
        prices = [LabeledPrice(label=title, amount=int(price * 100))]
        await query.bot.send_invoice(
            chat_id=user_id, title=title, description=description,
            payload=payload, provider_token="", currency="XTR", prices=prices
        )
        await query.answer("Opening payment window...")
        return

    # Demo payment
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    current_time = datetime.now()
    cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_end = result[0] if result and result[0] else current_time
    if isinstance(current_end, str):
        current_end = datetime.fromisoformat(current_end)
    if current_end < current_time:
        current_end = current_time
    new_end = current_end + timedelta(days=duration)
    cursor.execute(
        'UPDATE users SET subscription_end = ?, total_paid = total_paid + ? WHERE user_id = ?',
        (new_end, price, user_id)
    )
    config_url = f"vless://sub-{user_id}@demo.server:443"
    cursor.execute('''
        INSERT INTO subscriptions
        (user_id, plan_name, devices, duration_days, price, payment_method, started_at, expires_at, config_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, plan['name'], plan['devices'], duration, price, method, current_time, new_end, config_url))
    conn.commit()
    conn.close()

    message = t(user_id, 'payment_success',
                plan=plan['name'], duration=duration, price=price,
                expires=new_end.strftime('%Y-%m-%d'), config=config_url)
    keyboard = [
        [InlineKeyboardButton(t(user_id, 'btn_account'),  callback_data="account")],
        [InlineKeyboardButton(t(user_id, 'btn_buy'),      callback_data="plans")],
        [InlineKeyboardButton(t(user_id, 'btn_referral'), callback_data="referrals")],
    ]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    payment_info = update.message.successful_payment
    payload = payment_info.invoice_payload
    parts = payload.split("_")
    plan_index, duration = int(parts[1]), int(parts[3])
    plan = PLANS['plans'][plan_index]
    price = plan['prices'][str(duration)]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    current_time = datetime.now()
    cursor.execute('SELECT subscription_end FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    current_end = result[0] if result and result[0] else current_time
    if isinstance(current_end, str):
        current_end = datetime.fromisoformat(current_end)
    if current_end < current_time:
        current_end = current_time
    new_end = current_end + timedelta(days=duration)
    cursor.execute(
        'UPDATE users SET subscription_end = ?, total_paid = total_paid + ? WHERE user_id = ?',
        (new_end, price, user_id)
    )
    config_url = f"vless://paid-{user_id}@demo.server:443"
    cursor.execute('''
        INSERT INTO subscriptions
        (user_id, plan_name, devices, duration_days, price, payment_method, started_at, expires_at, config_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, plan['name'], plan['devices'], duration, price, 'telegram_stars', current_time, new_end, config_url))
    cursor.execute('''
        INSERT INTO payments (user_id, amount, currency, payment_method, payment_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, price, payment_info.currency, 'telegram_stars',
          payment_info.telegram_payment_charge_id, 'completed'))
    conn.commit()
    conn.close()

    message = t(user_id, 'payment_success',
                plan=plan['name'], duration=duration, price=price,
                expires=new_end.strftime('%Y-%m-%d'), config=config_url)
    keyboard = [
        [InlineKeyboardButton(t(user_id, 'btn_account'), callback_data="account")],
        [InlineKeyboardButton(t(user_id, 'btn_buy'),     callback_data="plans")],
    ]
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def back_to_main(query):
    user_id = query.from_user.id
    status = get_subscription_status(user_id)
    message = t(user_id, 'welcome_back', name=query.from_user.first_name, status=status)
    await query.edit_message_text(message, reply_markup=get_main_menu(user_id), parse_mode='HTML')

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    logger.info("=" * 60)
    logger.info("🌍 MULTILINGUAL VPN SHOP BOT — Railway Edition")
    logger.info("=" * 60)

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    # ── Webhook mode (Railway) vs Polling mode (local) ─────────────────────────
    if WEBHOOK_URL:
        webhook_path = f"/webhook/{BOT_TOKEN}"
        full_webhook_url = f"{WEBHOOK_URL.rstrip('/')}{webhook_path}"
        logger.info(f"🚀 Starting WEBHOOK on port {PORT}")
        logger.info(f"   URL: {full_webhook_url}")
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=webhook_path,
            webhook_url=full_webhook_url,
        )
    else:
        logger.info("🔄 Starting POLLING mode (local dev)")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
