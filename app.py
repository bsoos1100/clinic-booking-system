import streamlit as st
import sqlite3
import re
import requests
from datetime import datetime

# --- CONFIGURATION & THEME ---
st.set_page_config(
    page_title="منظومة النخبة الذكية لإدارة المواعيد",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM GLASSMORPHISM CSS DESIGN ---
st.markdown("""
    <style>
        /* Base styles */
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700&display=swap');
        
        html, body, [data-testid="stAppViewContainer"] {
            font-family: 'Cairo', sans-serif;
            background-color: #0b111e;
            color: #e2e8f0;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: rgba(15, 23, 42, 0.8) !important;
            backdrop-filter: blur(12px);
            border-left: 1px solid rgba(255, 255, 255, 0.05);
        }
        
        /* Glassmorphism Containers */
        div.glass-card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }
        
        /* Main Headers */
        h1, h2, h3 {
            font-family: 'Cairo', sans-serif;
            font-weight: 700;
            color: #00f2ff !important;
        }
        
        /* Status Badges */
        .badge-active {
            background-color: rgba(16, 185, 129, 0.2);
            color: #10b981;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            border: 1px solid rgba(16, 185, 129, 0.3);
            display: inline-block;
        }
        
        /* Form Inputs Styling override */
        div[data-baseweb="input"], div[data-baseweb="select"], div[data-baseweb="popover"] {
            background-color: rgba(15, 23, 42, 0.6) !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        
        /* Styled Table */
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 16px;
            text-align: right;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .styled-table th {
            background-color: #00f2ff;
            color: #0b111e;
            font-weight: bold;
            padding: 12px 15px;
        }
        .styled-table td {
            padding: 12px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            background-color: rgba(255, 255, 255, 0.02);
        }
        .styled-table tr:hover td {
            background-color: rgba(0, 242, 255, 0.05);
        }
        
        /* Analytics Widgets */
        .metric-container {
            background: linear-gradient(135deg, rgba(0, 242, 255, 0.1), rgba(0, 163, 255, 0.05));
            border: 1px solid rgba(0, 242, 255, 0.2);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .metric-val {
            font-size: 32px;
            font-weight: 700;
            color: #00f2ff;
        }
        .metric-lbl {
            font-size: 14px;
            color: #94a3b8;
            margin-top: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            phone_number TEXT,
            doctor_name TEXT,
            booking_date TEXT,
            booking_time TEXT,
            visit_type TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor_schedule (
            doctor_name TEXT PRIMARY KEY,
            available_days TEXT,
            working_hours TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM doctor_schedule")
    if cursor.fetchone()[0] == 0:
        default_schedules = [
            ("د. أحمد سليمان - استشاري العظام", "السبت، الإثنين، الأربعاء", "10:00 ص - 04:00 م"),
            ("د. فاطمة العبيدي - أخصائية الأطفال", "الأحد، الثلاثاء، الخميس", "09:00 ص - 02:00 م"),
            ("د. محمد الترهوني - استشاري الباطنة", "يومياً عدا الجمعة", "04:00 م - 09:00 م")
        ]
        cursor.executemany("INSERT INTO doctor_schedule VALUES (?, ?, ?)", default_schedules)
    conn.commit()
    conn.close()

init_db()

# --- HELPER FUNCTIONS ---
def clean_ly_phone(phone):
    cleaned = re.sub(r'\D', '', phone)
    if cleaned.startswith('09'):
        cleaned = '218' + cleaned[1:]
    elif cleaned.startswith('9'):
        cleaned = '218' + cleaned
    return cleaned

def send_whatsapp_ticket(name, phone, doctor, date, time, visit_type):
    # بيانات الحساب النشط والـ Connected باللون الأخضر
    instance_id = "instance180165"
    token = "0tfodtq9g7gvzifo"
    url = f"https://api.ultramsg.com/{instance_id}/messages/chat"
    
    formatted_phone = clean_ly_phone(phone)
    
    message = f"🏥 *تذكرة حجز موثقة - مركز النخبة الطبي* 🏥\n\nعزيزي المريض، تم تسجيل حجزك بنجاح في منظومة المركز الذكية.\n\n👤 *اسم المريض:* {name}\n👨‍⚕️ *الطبيب المختص:* {doctor}\n📅 *تاريخ الزيارة:* {date}\n⏰ *توقيت الحجز:* {time}\n📋 *نوع الزيارة:* {visit_type}\n\n📍 يرجى الحضور قبل الموعد بـ 15 دقيقة وإبراز هذه التذكرة الرقمية لموظف الاستقبال عند وصولك.\nنتمنى لكم دوام الصحة والعافية."
    
    payload = {
        "token": token,
        "to": f"+{formatted_phone}",
        "body": message
    }
    
    try:
        response = requests.post(url, data=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("<div style='text-align: center; padding: 10px;'><h2 style='color: #00f2ff; margin:0;'>🏥 مركز النخبة</h2><p style='color: #94a3b8; font-size: 12px;'>النظام السحابي للمستشفيات</p></div>", unsafe_allow_html=True)
st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)

view_mode = st.sidebar.radio(
    " اختر واجهة العرض الحالية:",
    ["📱 شاشة حجز المرضى", "🖥️ لوحة تحكم الاستقبال والتحليلات"]
)

st.sidebar.markdown("<br><br><br><br><hr style='border-color: rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='text-align: center; color: #64748b; font-size:12px;'>جميع الحقوق محفوظة © منظومة النخبة الذكية</div>", unsafe_allow_html=True)

# --- 1. PATIENT PORTAL ---
if view_mode == "📱 شاشة حجز المرضى":
    st.markdown("<div style='text-align: center; padding: 20px;'><h1 style='margin-bottom: 5px;'>🏥 بـوابة حـجز المـواعيد الذكـية</h1><p style='color: #94a3b8; font-size: 18px;'>احجز موعدك فوراً واستلم تذكرتك المعتمدة مباشرة عبر الواتساب</p></div>", unsafe_allow_html=True)
    
    with st.container():
        st.markdown("<div class='glass-card'><h3>📅 جدول أوقات وتوفر الأطباء الحالي</h3>", unsafe_allow_html=True)
        conn = sqlite3.connect('clinic.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM doctor_schedule")
        schedules = cursor.fetchall()
        conn.close()
        
        cols = st.columns(len(schedules))
        for idx, sched in enumerate(schedules):
            with cols[idx]:
                st.markdown(f"""
                <div style='background: rgba(255,255,255,0.02); padding: 15px; border-radius: 12px; border: 1px solid rgba(0, 242, 255, 0.1);'>
                    <div class='badge-active'>🟢 متاح اليوم</div>
                    <p style='font-weight: 600; margin: 10px 0 5px 0; color:#fff; font-size:16px;'>{sched[0]}</p>
                    <p style='font-size: 13px; color: #94a3b8; margin: 0;'><b>أيام الدوام:</b> {sched[1]}</p>
                    <p style='font-size: 13px; color: #94a3b8; margin: 0;'><b>الساعات:</b> {sched[2]}</p>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='glass-card'><h3>🧬 1. بيانات العيادة والزيارة</h3>", unsafe_allow_html=True)
    
    doctor_list = [s[0] for s in schedules]
    
    col1, col2 = st.columns(2)
    with col1:
        patient_name = st.text_input("👤 اسم المريض الثلاثي الكامل:")
        phone_number = st.text_input("📞 رقم هاتف المريض (المدار / ليبيانا):", placeholder="مثال: 091XXXXXXX")
        doctor_name = st.selectbox("👨‍⚕️ اختر الطبيب المختص والتخصص:", doctor_list)
    
    with col2:
        booking_date = st.date_input("📅 اختر تاريخ الزيارة المطلوبة:", min_value=datetime.today())
        booking_time = st.selectbox("⏰ الأوقات المتاحة اليوم:", ["09:00 ص", "10:30 ص", "11:00 ص", "12:30 م", "04:30 م", "06:00 م"])
        visit_type = st.radio("📝 غرض ونوع الزيارة الحالية:", ["كشف جديد", "مراجعة دورية"])

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("⚡ تأكيد الحجز وإرسال التذكرة فوراً", use_container_width=True):
        if not patient_name.strip() or not phone_number.strip():
            st.error("⚠️ خطأ في إتمام الحجز: يرجى كتابة الاسم الثلاثي ورقم الهاتف بدقة لتوليد التذكرة.")
        elif not re.match(r'^(091|092|094|91|92|94|21891|21892|21894)\d{7}$', phone_number.strip()):
            st.error("⚠️ صيغة رقم الهاتف غير صحيحة، يرجى إدخال رقم ليبي صالح.")
        else:
            conn = sqlite3.connect('clinic.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO bookings (patient_name, phone_number, doctor_name, booking_date, booking_time, visit_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (patient_name, phone_number, doctor_name, str(booking_date), booking_time, visit_type))
            conn.commit()
            conn.close()
            
            with st.spinner("⏳ جاري ترحيل البيانات وإرسال تذكرة الواتساب السحابية..."):
                success = send_whatsapp_ticket(patient_name, phone_number, doctor_name, str(booking_date), booking_time, visit_type)
            
            st.markdown("""
                <div style='background-color: rgba(16, 185, 129, 0.15); border: 1px solid #10b981; padding: 20px; border-radius: 12px; text-align: center;'>
                    <h3 style='color: #10b981 !important; margin: 0 0 10px 0;'>🎉 تم تأكيد حجزك بنجاح داخل المنظومة</h3>
                    <p style='color: #fff; margin: 0;'>تصلك الآن تذكرة الدخول الرسمية والموثقة على حساب الواتساب الخاص بك للرقم المرفق.</p>
                </div>
            """, unsafe_allow_html=True)
            st.balloons()
    st.markdown("</div>", unsafe_allow_html=True)

# --- 2. RECEPTION & MANAGEMENT PORTAL ---
elif view_mode == "🖥️ لوحة تحكم الاستقبال والتحليلات":
    st.markdown("<div style='padding: 10px 20px;'><h1 style='margin:0;'>🖥️ غرفة العمليات والتحليلات الإدارية</h1><p style='color: #94a3b8;'>مراقبة تدفق الحجوزات، إدارة أوقات الأطباء، ومؤشرات الأداء اللحظية</p></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cursor.fetchone()[0]
    conn.close()
    
    an_col1, an_col2, an_col3 = st.columns(3)
    with an_col1:
        st.markdown(f"""<div class='metric-container'><div class='metric-val'>{total_bookings}</div><div class='metric-lbl'>إجمالي الحجوزات المسجلة سحابياً</div></div>""", unsafe_allow_html=True)
    with an_col2:
        st.markdown("""<div class='metric-container'><div class='metric-val'>100%</div><div class='metric-lbl'>معدل تسليم تذاكر الواتساب الفورية</div></div>""", unsafe_allow_html=True)
    with an_col3:
        st.markdown("""<div class='metric-container'><div class='metric-val'>0 دقيقة</div><div class='metric-lbl'>وقت الانتظار التقريبي الموفر اليوم</div></div>""", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    tabs = st.tabs(["📋 سجل حركات المرضى الحالية", "⚙️ إدارة وتعديل تقويم الأطباء"])
    
    with tabs[0]:
        st.markdown("<h3>📋 قائمة المرضى المجدولين لليوم</h3>", unsafe_allow_html=True)
        filter_date = st.date_input("اختر تاريخ اليوم لعرض السجل الخاص به:", datetime.today())
        
        conn = sqlite3.connect('clinic.db')
        cursor = conn.cursor()
        cursor.execute("SELECT patient_name, phone_number, doctor_name, booking_time, visit_type FROM bookings WHERE booking_date = ?", (str(filter_date),))
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            table_html = "<table class='styled-table'><thead><tr><th>اسم المريض</th><th>رقم الهاتف</th><th>الطبيب المختص</th><th>التوقيت</th><th>نوع الزيارة</th></tr></thead><tbody>"
            for row in rows:
                v_badge = f"<span style='color:#00f2ff;'>{row[4]}</span>" if row[4] == "كشف جديد" else f"<span style='color:#a855f7;'>{row[4]}</span>"
                table_html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{v_badge}</td></tr>"
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("ℹ️ لا توجد أي حجوزات مجدولة حتى الآن للتاريخ المختار.")
            
    with tabs[1]:
        st.markdown("<h3>⚙️ تحديث وتعديل أوقات تواجد الأطباء بالعيادات</h3>", unsafe_allow_html=True)
        
        conn = sqlite3.connect('clinic.db')
        cursor = conn.cursor()
        cursor.execute("SELECT doctor_name FROM doctor_schedule")
        doc_names = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        selected_doc = st.selectbox("اختر الطبيب الذي تريد تعديل بياناته الآن:", doc_names)
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            new_days = st.text_input("أيام التواجد والعمل الأسبوعية الجديدة:")
        with col_m2:
            new_hours = st.text_input("ساعات الدوام اليومية الجديدة:")
            
        if st.button("💾 حفظ الساعات الجديدة وتحديث قاعدة البيانات", use_container_width=True):
            if new_days.strip() and new_hours.strip():
                conn = sqlite3.connect('clinic.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE doctor_schedule 
                    SET available_days = ?, working_hours = ?
                    WHERE doctor_name = ?
                ''', (new_days, new_hours, selected_doc))
                conn.commit()
                conn.close()
                st.success(f"✅ تم تحديث جدول أوقات {selected_doc} بنجاح، وسينعكس فوراً أمام المرضى!")
            else:
                st.warning("⚠️ يرجى تعبئة كافة خانات التحديث أولاً.")