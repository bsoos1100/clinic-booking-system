import streamlit as st
import sqlite3
from datetime import datetime
import requests

# 1️⃣ سحب بيانات الربط الخاصة بـ UltraMsg (تم تثبيتها لتعمل فوراً)
INSTANCE_ID = "instance179370"
ULTRAMSG_TOKEN = "oda8qahugqvoo3zi"

# 2️⃣ إعداد قاعدة البيانات المحلية وعرض الجداول (مُحدث ليشمل حالة الحجز ونوع الزيارة الجديد)
def init_db():
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            doctor_name TEXT NOT NULL,
            visit_type TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            queue_no INTEGER NOT NULL,
            status TEXT DEFAULT 'مؤكد تلقائياً ✅'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 3️⃣ دالة معالجة الرقم الليبي وإرسال رسالة التأكيد عبر UltraMsg
def send_whatsapp_confirmation(phone, patient_name, doctor_name, date, time, queue_no):
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    
    clean_phone = phone.strip().replace("+", "").replace(" ", "")
    if clean_phone.startswith("00218"):
        clean_phone = clean_phone[2:]
    elif clean_phone.startswith("0") and len(clean_phone) == 10:
        clean_phone = "218" + clean_phone[1:]
    elif (clean_phone.startswith("91") or clean_phone.startswith("92") or clean_phone.startswith("94")) and len(clean_phone) == 9:
        clean_phone = "218" + clean_phone

    message_text = (
        f"🏥 *مركز النخبة الطبي*\n\n"
        f"مرحباً بك أخي/أختي *{patient_name}*،\n"
        f"تم تأكيد موعد حجزك بنجاح تلقائياً وبدون انتظار:\n\n"
        f"👨‍⚕️ *الطبيب:* {doctor_name}\n"
        f"📅 *التاريخ:* {date}\n"
        f"⏰ *الوقت:* {time}\n"
        f"🔢 *رقم الحجز (الدور):* [ {queue_no} ]\n\n"
        f"نتمنى لك الشفاء العاجل دائمًا وننتظر زيارتك."
    )
    
    payload = {
        "token": ULTRAMSG_TOKEN,
        "to": clean_phone,
        "body": message_text
    }
    headers = {"content-type": "application/x-www-form-urlencoded"}
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        return response.status_code == 200 and "sent" in response.text
    except:
        return False

def get_next_queue_no(doctor_name, date_str):
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM appointments WHERE doctor_name = ? AND appointment_date = ?', (doctor_name, date_str))
    count = cursor.fetchone()[0]
    conn.close()
    return count + 1

# 4️⃣ تهيئة الإعدادات العامة مع إجبار الواجهة على التلاؤم التلقائي مع الهواتف
st.set_page_config(page_title="منظومة حجز عيادة النخبة", page_icon="🏥", layout="centered")

# حقن كود CSS محسن خصيصاً لتجربة مستخدم ممتازة على شاشات الهاتف الذكي
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
        .main-title { background: linear-gradient(135deg, #0d3b66 0%, #0077b6 100%); padding: 15px; color: white; text-align: center; border-radius: 10px; margin-bottom: 15px; }
        .main-title h1 { font-size: 24px !important; margin-bottom: 5px; }
        .main-title p { font-size: 14px !important; }
        
        /* تحسين مظهر أزرار الأوقات لتناسب ضغطة الإصبع في الهاتف */
        div.stButton > button:first-child { background-color: #f8f9fa; color: #0d3b66; border: 2px solid #0077b6; font-size: 16px; border-radius: 8px; font-weight: bold; padding: 12px 10px; width: 100%; margin-bottom: 5px; }
        div.stButton > button:first-child:hover { background-color: #0077b6; color: white; }
        
        /* جعل زر التأكيد أخضر وعريض جداً ليملأ شاشة الهاتف */
        .submit-btn-container div.stButton > button:first-child { background-color: #2ec4b6 !important; color: white !important; border: none !important; font-size: 18px !important; width: 100% !important; padding: 14px !important; box-shadow: 0 4px 10px rgba(46, 196, 182, 0.3); }
        
        .footer-bar { background-color: #f1faee; padding: 15px; border-radius: 8px; text-align: center; margin-top: 30px; border: 1px solid #0077b6; }
        .footer-bar button { width: 100% !important; padding: 10px !important; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# تحسين القائمة الجانبية لتظهر بشكل مريح في الهواتف عند سحبها
st.sidebar.markdown("### 🏥 إدارة micro-clinic")
view_mode = st.sidebar.selectbox("📱 اختر واجهة العرض حالياً:", ["شاشة حجز المرضى", "لوحة تحكم موظف الاستقبال"])

# ---------------- الواجهة الأولى: شاشة حجز المرضى (محسنة للهواتف) ----------------
if view_mode == "شاشة حجز المرضى":
    st.markdown("<div class='main-title'><h1>🏥 مركز النخبة الطبي</h1><p>احجز موعدك فورياً واستلم تذكرتك مباشرة عبر الواتساب</p></div>", unsafe_allow_html=True)
    
    st.markdown("### 🩺 1. بيانات العيادة والزيارة")
    doctor_name = st.selectbox(
        "👨‍⚕️ اختر الطبيب المختص والتخصص:",
        ["د. أحمد سليمان - استشاري العظام", "د. فاطمة المصراتي - الأطفال وحديثي الولادة", "د. محمد الزوي - أمراض الباطنية والقلب"]
    )
    visit_type = st.selectbox("📋 غرض ونوع الزيارة الحالية:", ["كشف أول مرة", "مراجعة دورية", "استشارة طبيب", "حالة مستعجلة"])
    appointment_date = st.date_input("📅 اختر تاريخ الزيارة المطلوبة:", min_value=datetime.today())
    date_str = appointment_date.strftime("%Y/%m/%d")

    st.markdown("---")
    st.markdown("### ⏰ 2. الأوقات المتاحة اليوم")
    st.caption("💡 اضغط على التوقيت المناسب لك لتعبئة بيانات التذكرة فوراً:")
    
    # جلب الأوقات المحجوزة مسبقاً لمنع التداخل
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute('SELECT appointment_time FROM appointments WHERE doctor_name = ? AND appointment_date = ?', (doctor_name, date_str))
    booked_times = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    time_slots = ["10:00", "10:20", "10:40", "11:00", "11:20", "11:40", "04:00", "04:20", "04:40", "05:00", "05:20", "05:40"]
    
    # توزيع الأوقات في عمودين متوازيين ليناسب شاشات الهواتف الطولية دون تشتيت
    time_cols = st.columns(2)
    for idx, slot in enumerate(time_slots):
        col_slot = time_cols[idx % 2]
        display_slot = datetime.strptime(slot, "%H:%M").strftime("%I:%M %p")
        
        if slot in booked_times:
            col_slot.button(f"🚫 {display_slot}", key=f"btn_{idx}", disabled=True)
        else:
            if col_slot.button(f"⏱️ {display_slot}", key=f"btn_{idx}"):
                st.session_state['selected_slot'] = slot
                st.session_state['selected_doc'] = doctor_name
                st.session_state['selected_date'] = date_str

    # استمارة التأكيد تظهر بوضوح أسفل الأوقات عند الاختيار
    if 'selected_slot' in st.session_state and st.session_state['selected_date'] == date_str and st.session_state['selected_doc'] == doctor_name:
        st.markdown("---")
        st.info(f"📍 التوقيت المحدد: {st.session_state['selected_slot']} مع {doctor_name}")
        
        with st.form("confirm_form"):
            patient_name = st.text_input("👤 اسم المريض الثلاثي كاملاً:")
            phone = st.text_input("📞 رقم هاتف المريض المحمول (مثال: 091XXXXXXX):")
            
            st.markdown('<div class="submit-btn-container">', unsafe_allow_html=True)
            submit_btn = st.form_submit_button("🚀 تأكيد الحجز وإصدار التذكرة الآن")
            st.markdown('</div>', unsafe_allow_html=True)
            
        if submit_btn:
            if patient_name and phone:
                queue_no = get_next_queue_no(doctor_name, date_str)
                
                conn = sqlite3.connect("clinic.db")
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO appointments (patient_name, phone, doctor_name, visit_type, appointment_date, appointment_time, queue_no, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'مؤكد تلقائياً ✅')
                ''', (patient_name, phone, doctor_name, visit_type, date_str, st.session_state['selected_slot'], queue_no))
                conn.commit()
                conn.close()
                
                with st.spinner("جاري إرسال تذكرة الواتساب الرقمية..."):
                    whatsapp_sent = send_whatsapp_confirmation(phone, patient_name, doctor_name, date_str, st.session_state['selected_slot'], queue_no)
                
                st.balloons()
                st.markdown(f"""
                    <div style="background-color: #d4edda; padding: 20px; border-radius: 10px; text-align: center; border-right: 6px solid #28a745; margin-top:10px;">
                        <h4 style="color: #155724; font-weight: bold; margin-bottom:5px;">🎉 تم حجز موعدك بنجاح!</h4>
                        <p style="font-size:14px; margin-bottom:5px;">المريض: <b>{patient_name}</b></p>
                        <p style="font-size:14px; margin-bottom:5px;">رقم الدور: <b style="font-size:18px; color:#28a745;">[ {queue_no} ]</b></p>
                        <p style="font-size:12px; color:#555;">الحالة: {"📱 وصلت التذكرة لواتساب هاتفكم" if whatsapp_sent else "⚠️ الحجز مسجل، يرجى التحقق من اتصال شبكة العيادة"}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                del st.session_state['selected_slot']
                st.rerun()
            else:
                st.error("❌ فضلاً، يرجى كتابة اسم المريض ورقم الهاتف لإتمام وتثبيت الدور!")

    # 🗺️ شريط الموقع الجغرافي لـ طرابلس (حي الأندلس) المتوافق مع الهواتف
    st.markdown(f"""
        <div class="footer-bar">
            <p style="margin-bottom: 10px; font-weight: bold; color: #0d3b66; font-size:14px;">📍 المقر: حي الأندلس، طرابلس، ليبيا</p>
            <a href="https://maps.google.com" target="_blank" style="text-decoration: none;">
                <button style="background-color: #0077b6; color: white; border: none; padding: 12px; border-radius: 6px; font-weight: bold; cursor: pointer; width:100%;">
                    🗺️ افتح موقع العيادة في تطبيق Google Maps
                </button>
            </a>
        </div>
    """, unsafe_allow_html=True)

# ---------------- الواجهة الثانية: لوحة تحكم موظف الاستقبال ----------------
else:
    st.title("🖥️ شاشة استقبال مركز النخبة الطبي")
    st.subheader("لوحة التحكم الشاملة والمراقبة اللحظية لجدول حجوزات اليوم")
    st.markdown("---")
    
    filter_date = st.date_input("🔍 استعراض الحجوزات لتاريخ يوم محدد:", datetime.today())
    filter_date_str = filter_date.strftime("%Y/%m/%d")
    
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT queue_no, patient_name, phone, doctor_name, visit_type, appointment_date, appointment_time, status 
        FROM appointments WHERE appointment_date = ?
        ORDER BY appointment_time ASC, queue_no ASC
    ''', (filter_date_str,))
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        st.success(f"📊 إجمالي المواعيد المعتمدة ليوم {filter_date_str} هو: `{len(rows)}` حجز.")
        
        # تحضير وعرض جدول قاعدة البيانات بكافة التفاصيل المطلوبة بدقة عالية
        report_table = []
        for row in rows:
            report_table.append({
                "🔢 رقم الحجز (الدور)": row[0],
                "👤 اسم المريض": row[1],
                "📞 رقم الهاتف": row[2],
                "👨‍⚕️ اسم الطبيب": row[3],
                "📋 نوع الحجز والزيارة": row[4],
                "📅 التاريخ المجدول": row[5],
                "⏰ وقت الموعد": row[6],
                "🔔 حالة الحجز في المنظومة": row[7]
            })
        st.dataframe(report_table, use_container_width=True)
    else:
        st.info(f"📅 لا توجد أي حجوزات مسجلة أو مضافة في قاعدة البيانات لتاريخ {filter_date_str} حتى الآن.")