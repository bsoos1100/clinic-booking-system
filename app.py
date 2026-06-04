import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import datetime
import json
import base64

# --- 1. إعدادات الصفحة والجماليات (CSS الخارق) ---
st.set_page_config(page_title="مركز النخبة الطبي | حجز المواعيد", page_icon="🏥", layout="wide")

# حقن خط Cairo وتنسيقات الـ UI الاحترافية
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        /* إعدادات الخط العام والاتجاه */
        html, body, [class*="css"] {
            font-family: 'Cairo', sans-serif;
            direction: rtl;
            text-align: right;
        }
        
        /* تصميم الهيدر (Hero Section) */
        .hero-section {
            background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80');
            background-size: cover;
            background-position: center;
            padding: 100px 20px;
            color: white;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 40px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        /* تنسيق الأزرار والكروت */
        .stButton>button {
            width: 100%;
            border-radius: 25px;
            height: 3em;
            background-color: #007bff;
            color: white;
            font-weight: bold;
            border: none;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background-color: #0056b3;
            transform: scale(1.02);
        }
        
        /* إخفاء القائمة العلوية لستريمليت لزيادة الاحترافية */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. الربط مع Google Services ---
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/calendar']
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
except Exception as e:
    st.error("⚠️ خطأ في تهيئة المفاتيح السرية. يرجى مراجعة Settings -> Secrets")
    st.stop()

# المعرفات الحقيقية التي أرسلتها
CALENDAR_IDS = {
    "د. أحمد - عيون": "0acd596ca9fbff4366bb88124b4c5c7737743e2efaff30f67c2664adc66276de@group.calendar.google.com",
    "د. فاطمة - أطفال": "ad779c7745c547cf6396337c7afc8e9dfc842810f383bd0ec66b1e0987af8f6b@group.calendar.google.com"
}
SPREADSHEET_NAME = "حجوزات العيادة"

# --- 3. الوظائف الخلفية (Backend) ---
def get_available_slots(calendar_id):
    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        events_result = service.events().list(calendarId=calendar_id, timeMin=now, maxResults=15, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])
        return [{'id': e['id'], 'display': datetime.datetime.fromisoformat(e['start'].get('dateTime', e['start'].get('date')).replace('Z', '+00:00')).strftime('%Y-%m-%d | %I:%M %p'), 'raw': e} for e in events if "متاح" in e.get('summary', '')]
    except: return []

def book_appointment(calendar_id, event_id, event_raw, name, phone):
    try:
        service = build('calendar', 'v3', credentials=creds)
        event_raw['summary'] = f"محجوز: {name} ({phone})"
        service.events().update(calendarId=calendar_id, eventId=event_id, body=event_raw).execute()
        
        sheets_client = gspread.authorize(creds)
        sheet = sheets_client.open(SPREADSHEET_NAME).sheet1
        start_time = event_raw['start'].get('dateTime', event_raw['start'].get('date'))
        dt = datetime.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        sheet.append_row([str(datetime.date.today()), name, phone, dt.strftime('%Y-%m-%d'), dt.strftime('%H:%M')])
        return True
    except: return False

# --- 4. واجهة المستخدم (UI) ---

# شريط جانبي (Sidebar) للمعلومات الإضافية
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/387/387561.png", width=100)
    st.title("مركز النخبة الطبي")
    st.info("🕒 ساعات العمل: 09:00 ص - 08:00 م")
    st.write("---")
    # زر موقع العيادة (طرابلس)
    st.markdown("[📍 موقعنا على خرائط جوجل](https://maps.app.goo.gl/o1H7K7W6S4WzK9U5A)")
    st.write("📞 هاتف: 0910000000")
    st.write("📧 info@elite-clinic.ly")

# قسم الـ Hero (العنوان الرئيسي)
st.markdown("""
    <div class="hero-section">
        <h1>مرحباً بك في مركز النخبة الطبي</h1>
        <p>نخبة من الأطباء في خدمتك.. احجز موعدك الآن بكل سهولة</p>
    </div>
""", unsafe_allow_html=True)

# تقسيم الشاشة لخطوات الحجز
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1️⃣ اختر الطبيب")
    doctor = st.selectbox("", list(CALENDAR_IDS.keys()), label_visibility="collapsed")
    
    st.subheader("2️⃣ اختر الموعد المتاح")
    slots = get_available_slots(CALENDAR_IDS[doctor])
    if slots:
        slot_options = {slot['display']: slot for slot in slots}
        selected_display = st.select_slider("", options=list(slot_options.keys()), label_visibility="collapsed")
    else:
        st.warning("⚠️ لا توجد مواعيد متاحة حالياً.")

with col2:
    st.subheader("3️⃣ بيانات المريض")
    p_name = st.text_input("الأسم الكامل", placeholder="مثال: محمد علي")
    p_phone = st.text_input("رقم الهاتف", placeholder="09XXXXXXXX")
    
    if st.button("تأكيد الحجز الآن ✅"):
        if p_name and p_phone and slots:
            with st.spinner("جاري تأكيد حجزك..."):
                target = slot_options[selected_display]
                if book_appointment(CALENDAR_IDS[doctor], target['id'], target['raw'], p_name, p_phone):
                    st.success(f"تم الحجز بنجاح يا {p_name}! ننتظرك في الموعد.")
                    st.balloons()
                else: st.error("فشل الحجز، يرجى المحاولة لاحقاً.")
        else:
            st.error("يرجى ملء كافة البيانات!")

st.markdown("---")
st.caption("© 2024 منظومة النخبة لإدارة العيادات - طرابلس، ليبيا")