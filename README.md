# بوت Stoch RSI + CoinMarketCap Volume

بوت تنبيهات Telegram يعتمد في **قرار الإشارة فقط** على:

1. قيم وتقاطع `Stoch RSI`.
2. فوليوم العملة خلال 24 ساعة من `CoinMarketCap`.

لا يستخدم البوت MACD أو RSI مستقلًا أو فوليوم الشمعة أو نسبة تغير السعر أو Volume Ratio أو Confidence Score.

## مصادر البيانات

- قائمة العملات وفوليوم 24 ساعة: CoinMarketCap API.
- شموع الإغلاق اللازمة لحساب Stoch RSI: Gate.io ثم KuCoin ثم MEXC حسب ترتيب `EXCHANGES`.
- التنبيهات: Telegram Bot API.

اختيار المنصة لا يدخل في تقييم الإشارة؛ البوت يأخذ أول سوق Spot متاح حسب ترتيب المنصات.

## الملفات

- `main.py`: حلقة التشغيل والفحص.
- `config.py`: قراءة وفحص جميع المتغيرات.
- `cmc_client.py`: جلب العملات والفوليوم من CMC.
- `exchange_manager.py`: تحميل الأسواق والشموع عبر CCXT.
- `indicators.py`: حساب Stoch RSI.
- `signal_rules.py`: شروط الإشارة.
- `telegram_client.py`: رسائل Telegram.
- `state_store.py`: منع تكرار الإشارة أثناء فترة التهدئة.
- `.env.example`: جميع المتغيرات.
- `Dockerfile` و`railway.json`: تشغيل Railway.

## التشغيل محليًا

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

على Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python main.py
```

## الرفع على Railway

1. ارفع الملفات إلى مستودع GitHub.
2. أنشئ مشروعًا في Railway واختر المستودع.
3. افتح قسم `Variables`.
4. انسخ متغيرات `.env.example` وأدخل القيم السرية.
5. لا تنشئ Domain؛ البوت Worker ولا يحتاج رابطًا عامًا.

Railway سيكتشف `Dockerfile` ويشغّل:

```text
python main.py
```

## المتغيرات الضرورية

```env
TELEGRAM_BOT_TOKEN=توكن_البوت
TELEGRAM_CHAT_ID=رقم_المحادثة
CMC_API_KEY=مفتاح_CoinMarketCap
```

## شرط الإشارة الافتراضي

```text
فوليوم CMC خلال 24 ساعة >= 3,000,000 دولار
K بين 0 و20
D بين 0 و20
K كان أقل من أو يساوي D ثم أصبح أعلى من D
K صاعد مقارنة بالقيمة السابقة
```

يمكن تغيير كل قيمة من Railway Variables دون تعديل الكود.

### مثال: توسيع منطقة Stoch RSI إلى 30

```env
MAX_STOCH_K=30
MAX_STOCH_D=30
```

### مثال: جعل الفوليوم الأدنى 5 ملايين

```env
MIN_CMC_VOLUME_24H=5000000
```

### مثال: فريم ساعة

```env
TIMEFRAME=1h
```

### مثال: إلغاء شرط التقاطع والاكتفاء بوجود K وD في النطاق

```env
REQUIRE_BULLISH_CROSS=false
```

### مثال: استخدام الشمعة الحالية المفتوحة

```env
USE_CLOSED_CANDLE=false
```

استخدام الشمعة المغلقة أكثر ثباتًا؛ الشمعة المفتوحة قد تغيّر قيم الإشارة قبل إغلاقها.

## حفظ فترة التهدئة بعد إعادة التشغيل

ملف `alert_state.json` محلي وقد يختفي عند إعادة نشر الخدمة. لحفظه بشكل دائم:

1. أضف Railway Volume.
2. اربطه بالمسار `/data`.
3. غيّر المتغير:

```env
STATE_FILE=/data/alert_state.json
```

## ملاحظات

- رفع `MAX_COINS` كثيرًا يزيد عدد طلبات المنصات ومدة الفحص.
- `CMC_LIMIT` يحدد عدد السجلات التي تُطلب من CMC قبل التصفية.
- يتم استبعاد الرموز المكررة في CMC والاحتفاظ بالمشروع الأعلى فوليومًا.
- بعض رموز CMC قد لا تطابق اسم الزوج في المنصة، ولذلك تُتجاهل تلقائيًا.
