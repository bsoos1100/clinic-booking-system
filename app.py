import streamlit as pd
import streamlit as st
import sqlite3
from datetime import datetime
import requests

# 1️⃣ سحب بيانات الربط الخاصة بـ UltraMsg من السيكرتس تلقائياً
INSTANCE_ID = st.secrets.get("ultramsg_instance", "instance179370")
ULTRAMSG_TOKEN = st.secrets.get("ultramsg_token", "oda8qahugqvoo3zi")

# 2️⃣ إعداد قاعدة البيانات المحلية وعرض الجداول
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
            queue_no INTEGER NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 3️⃣ دالة معالجة الرقم الليبي وإرسال رسالة التأكيد عبر UltraMsg
def send_whatsapp_confirmation(phone, patient_name, doctor_name, date, time, queue_no):
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    
    # تنظيف وتعديل الرقم الليبي تلقائياً خلف الكواليس ليقبله النظام فوراً
    clean_phone = phone.strip().replace("+", "").replace(" ", "")
    
    # حالة 1: المريض بدأ بـ 00218 -> نحذف أول صفرين
    if clean_phone.startswith("00218"):
        clean_phone = clean_phone[2:]
    # حالة 2: المريض بدأ بالرقم العادي مثل 091 أو 092 -> نحذف الـ 0 ونضع مفتاح ليبيا دولياً
    elif clean_phone.startswith("0") and len(clean_phone) == 10:
        clean_phone = "218" + clean_phone[1:]
    # حالة 3: المريض كتب 91 أو 92 مباشرة بدون الصفر -> نضيف 218 فوراً
    elif (clean_phone.startswith("91") or clean_phone.startswith("92") or clean_phone.startswith("94")) and len(clean_phone) == 9:
        clean_phone = "218" + clean_phone

    # نص الرسالة الفاخر والمنظم للعيادة
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
    headers = {
        "content-type": "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        return response.status_code == 200 and "sent" in response.text
    except:
        return False

# 4️⃣ دالة حساب رقم الدور التلقائي بناءً على الطبيب والتاريخ
def get_next_queue_no(doctor_name, date_str):
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(*) FROM appointments 
        WHERE doctor_name = ? AND appointment_date = ?
    ''', (doctor_name, date_str))
    count = cursor.fetchone()[0]
    conn.close()
    return count + 1

# 5️⃣ بناء واجهات وتصميم التطبيق الموحد (شاشة الحجز + الداشبورد)
st.set_page_config(page_title="منظومة حجز عيادة النخبة", page_icon="🏥", layout="centered")

# القائمة الجانبية للتنقل الذكي بين الواجهات
st.sidebar.markdown("### ⚙️ الإعدادات العامة")
view_mode = st.sidebar.selectbox(
    "📱 اختر واجهة العرض حالياً:",
    ["شاشة حجز المرضى", "لوحة تحكم موظف الاستقبال"]
)

# ---------------- شاشة حجز المرضى ----------------
if view_mode == "شاشة حجز المرضى":
    st.image("https://cdn-icons-png.flaticon.com/512/3774/3774299.png", width=100)
    st.title("🏥 نظام الحجز الإلكتروني التلقائي")
    st.subheader("مركز النخبة الطبي - حجز فوري وتأكيد مباشر عبر الواتساب")
    st.markdown("---")
    
    with st.form("booking_form", clear_on_submit=True):
        patient_name = st.text_input("👤 اسم المريض الثلاثي:")
        phone = st.text_input("📞 رقم الهاتف المحمول (مثال: 091XXXXXXX):")
        
        doctor_name = st.selectbox(
            "👨‍⚕️ اختر الطبيب المختص:",
            ["د. أحمد سليمان - استشاري العظام", "د. فاطمة - الأطفال وحديثي الولادة", "د. محمد الزوي - باطنية وقلب"]
        )
        
        visit_type = st.radio("📋 نوع الزيارة:", ["كشف جديد", "مراجعة دورية"])
        appointment_date = st.date_input("📅 اختر تاريخ الزيارة:", min_value=datetime.today())
        appointment_time = st.selectbox("⏰ اختر الوقت المناسب لكم:", ["10:00", "10:20", "10:40", "11:00", "11:20", "11:40", "04:00", "04:20", "04:40"])
        
        submit_btn = st.form_submit_button("⚡ تأكيد الحجز وإرسال التذكرة فوراً")
        
    if submit_btn:
        if patient_name and phone:
            date_str = appointment_date.strftime("%Y/%m/%d")
            queue_no = get_next_queue_no(doctor_name, date_str)
            
            # حفظ البيانات في قاعدة البيانات SQLite
            conn = sqlite3.connect("clinic.db")
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO appointments (patient_name, phone, doctor_name, visit_type, appointment_date, appointment_time, queue_no)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (patient_name, phone, doctor_name, visit_type, date_str, appointment_time, queue_no))
            conn.commit()
            conn.close()
            
            # إرسال رسالة الواتساب الفورية الذكية
            with st.spinner("جاري تأكيد حجزك وإرسال التذكرة لواتساب..."):
                whatsapp_sent = send_whatsapp_confirmation(phone, patient_name, doctor_name, date_str, appointment_time, queue_no)
            
            st.success(f"🎉 تم تسجيل حجزك بنجاح يا {patient_name}!")
            st.balloons()
            
            # عرض التذكرة محلياً على الشاشة للمريض
            st.info(f"🔢 **رقم دورك في العيادة هو:** [ {queue_no} ] \n\n"
                    f"⏰ **التوقيت المتوقع:** {appointment_time} في تاريخ {date_str} عند ({doctor_name})")
            
            if whatsapp_sent:
                st.success("📱 تم إرسال تذكرة الحجز الفاخرة الموثقة إلى رقم واتساب الخاص بك الآن!")
            else:
                st.warning("⚠️ تم حفظ الحجز في المنظومة، ولكن تأكد من ربط هاتف العيادة بالـ QR Code في UltraMsg لتصلك الرسائل بشكل صحيح.")
        else:
            st.error("❌ يرجى ملء كافة البيانات الأساسية (الاسم ورقم الهاتف) لإتمام الحجز.")

# ---------------- لوحة تحكم موظف الاستقبال ----------------
else:
    st.title("🖥️ داش بورد الاستقبال وإدارة العيادات")
    st.subheader("لوحة التحكم والمراقبة الفورية لحجوزات اليوم")
    st.markdown("---")
    
    # فلترة الحجوزات بحسب التاريخ المختار
    filter_date = st.date_input("🔍 اختر تاريخاً لعرض حجوزاته المجدولة:", datetime.today())
    filter_date_str = filter_date.strftime("%Y/%m/%d")
    
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    cursor.execute('''
        SELECT appointment_time, visit_type, doctor_name, phone, patient_name, queue_no 
        FROM appointments WHERE appointment_date = ?
        ORDER BY appointment_time ASC, queue_no ASC
    ''', (filter_date_str,))
    rows = cursor.fetchall()
    conn.close()
    
    if rows:
        st.write(f"📊 إجمالي الحجوزات المعتمدة ليوم **{filter_date_str}** هو: `{len(rows)}` مريض.")
        
        # تحويل البيانات إلى جدول scannable أنيق ومنظم
        report_data = []
        for row in rows:
            report_data.append({
                "وقت الموعد": row[0],
                "الحالة/نوع الزيارة": row[1],
                "اسم الطبيب": row[2],
                "رقم الهاتف": row[3],
                "اسم المريض": row[4],
                "رقم الدور": row[5]
            })
        st.table(report_data)
    else:
        st.info(f"📅 لا توجد أي حجوزات مسجلة في المنظومة لتاريخ يوم {filter_date_str} حتى الآن.")