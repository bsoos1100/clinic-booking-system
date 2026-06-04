import streamlit as st
import sqlite3
from datetime import datetime
import requests

# --- 1. سحب بيانات ربط بوابة UltraMsg من السيكرتس ---
INSTANCE_ID = st.secrets.get("ultramsg_instance", "instance179370")
ULTRAMSG_TOKEN = st.secrets.get("ultramsg_token", "oda8qahugqvoo3zi")

# --- 2. تهيئة قاعدة البيانات المحلية الشاملة ---
def init_db():
    conn = sqlite3.connect("clinic.db")
    cursor = conn.cursor()
    
    # جدول الحجوزات الفعلي للمرضى
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
    
    # جدول إدارة أوقات وتوفر الأطباء (الجديد)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctor_schedule (
            doctor_name TEXT PRIMARY KEY,
            working_hours TEXT NOT NULL,
            available_days TEXT NOT NULL
        )
    ''')
    
    # إدخال بيانات افتراضية للأطباء إذا كان الجدول جديداً
    cursor.execute("SELECT COUNT(*) FROM doctor_schedule")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO doctor_schedule VALUES ('د. أحمد سليمان (عظام)', '04:00 م - 08:00 م', 'كل الأيام عدا الجمعة')")
        cursor.execute("INSERT INTO doctor_schedule VALUES ('د. فاطمة (أطفال)', '10:00 ص - 02:00 م', 'السبت، الإثنين، الإربعاء')")
        cursor.execute("INSERT INTO doctor_schedule VALUES ('د. محمد الزوي (باطنية)', '05:00 م - 09:00 م', 'يومياً')")
        
    conn.commit()
    conn.close()

init_db()

# --- 3. دالة معالجة الرقم الليبي وإرسال الواتساب التلقائي ---
def send_whatsapp_confirmation(phone, patient_name, doctor_name, date, time, queue_no):
    url = f"https://api.ultramsg.com/{INSTANCE_ID}/messages/chat"
    
    # تنظيف وتعديل الرقم الليبي تلقائياً خلف الكواليس
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

# --- 4. تحسينات المظهر العام لتتناسب مع شاشات الهواتف ---
st.set_page_config(page_title="منظومة حجز عيادة النخبة", page_icon="🏥", layout="centered")

# حفر تنسيقات CSS لضغط العناصر ومنع التداخل على الموبايل
st.markdown("""
    <style>
        .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
        h1, h2, h3 { text-align: right; font-size: 1.5rem !important; margin-bottom: 5px !important; }
        p { text-align: right; font-size: 0.9rem !important; color: #555; }
        div[data-testid="stForm"] { padding: 10px !important; border-radius: 10px !important; }
        .stRadio>div { flex-direction: row !important; gap: 15px; }
        label { font-size: 0.85rem !important; font-weight: bold !important; display: block; text-align: right; }
    </style>
""", unsafe_allow_html=True)

# شريط التنقل الجانبي المخفي ذكياً
view_mode = st.sidebar.selectbox("📱 واجهة العرض الحالية:", ["شاشة حجز المرضى", "لوحة تحكم موظف الاستقبال"])

# ==================== الواجهة الأولى: شاشة حجز المرضى (مضغوطة للموبايل) ====================
if view_mode == "شاشة حجز المرضى":
    # عرض الشعار والعنوان في سطر واحد مضغوط لترك مساحة الشاشة
    col_logo, col_txt = st.columns([1, 4])
    with col_logo:
        st.image("https://cdn-icons-png.flaticon.com/512/3774/3774299.png", width=50)
    with col_txt:
        st.markdown("<h2 style='margin:0;'>مركز النخبة الذكي</h2>", unsafe_allow_html=True)
        st.markdown("<p style='margin:0;'>حجز فوري وثوانٍ لتصلك التذكرة على الواتساب</p>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:8px 0;'/>", unsafe_allow_html=True)
    
    # عرض جدول توفر الأطباء الحالي المأخوذ من الإدارة أمام المريض مباشرة ليرى المواعيد فوراً
    with st.expander("⏱️ عرض أوقات وأيام دوام الأطباء بالمركز"):
        conn = sqlite3.connect("clinic.db")
        df_sched = requests.get # تم الاستعاضة بـ sqlite لقراءة الجدول مباشرة
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM doctor_schedule")
        sched_rows = cursor.fetchall()
        conn.close()
        for row in sched_rows:
            st.markdown(f"**• {row[0]}:** {row[1]} | {row[2]}")

    # استمارة الحجز المدمجة والمحسنة لتقليل الطول
    with st.form("booking_form"):
        patient_name = st.text_input("👤 اسم المريض الثلاثي:")
        phone = st.text_input("📞 رقم هاتف المدار/ليبيانا (مثال: 091XXXXXXX):")
        
        # جلب قائمة أسماء الأطباء ديناميكياً من جدول المواعيد
        conn = sqlite3.connect("clinic.db")
        cursor = conn.cursor()
        cursor.execute("SELECT doctor_name FROM doctor_schedule")
        doc_options = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        doctor_name = st.selectbox("👨‍⚕️ اختر الطبيب المختص:", doc_options)
        
        # وضع بقية الحقول في أعمدة متجاورة لتوفير مساحة الطول على الهاتف
        c1, c2 = st.columns(2)
        with c1:
            appointment_date = st.date_input("📅 تاريخ الزيارة:", min_value=datetime.today())
        with c2:
            appointment_time = st.selectbox("⏰ توقيت الحجز:", ["10:00 ص", "10:30 ص", "11:00 ص", "04:30 م", "05:00 م", "06:10 م"])
            
        visit_type = st.radio("📋 نوع الزيارة:", ["كشف جديد", "مراجعة دورية"])
        
        submit_btn = st.form_submit_button("⚡ تأكيد الحجز وإرسال التذكرة فوراً", use_container_width=True)
        
    if submit_btn:
        # 🛑 الدالة الصارمة للتحقق من ملء كافة البيانات ومنع استقبال الحقول الفارغة
        if not patient_name.strip():
            st.error("❌ عذراً، يجب إدخال اسم المريض الثلاثي لإتمام الحجز!")
        elif not phone.strip() or len(phone.strip()) < 9:
            st.error("❌ عذراً، يجب إدخال رقم هاتف ليبي صحيح ومكون من 10 أرقام!")
        else:
            # إذا اجتاز المريض الفحص بنجاح، يتم الحفظ والإرسال فورا
            date_str = appointment_date.strftime("%Y/%m/%d")
            queue_no = get_next_queue_no(doctor_name, date_str)
            
            conn = sqlite3.connect("clinic.db")
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO appointments (patient_name, phone, doctor_name, visit_type, appointment_date, appointment_time, queue_no)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (patient_name, phone, doctor_name, visit_type, date_str, appointment_time, queue_no))
            conn.commit()
            conn.close()
            
            with st.spinner("جاري معالجة بياناتك وإرسال تذكرتك للواتساب..."):
                whatsapp_sent = send_whatsapp_confirmation(phone, patient_name, doctor_name, date_str, appointment_time, queue_no)
            
            st.balloons()
            st.success(f"🎉 تم تأكيد حجزك بنجاح ومنحك رقم الدور: [ {queue_no} ]")
            if whatsapp_sent:
                st.info("📱 وصلت التذكرة الآن كرسالة وثيقة فاخرة على حساب الواتساب الخاص بك!")
            else:
                st.warning("⚠️ تم تسجيل الحجز محلياً بالمركز، يرجى مراجعة اتصال هاتف العيادة بـ UltraMsg لإرسال تذاكر الواتساب معاً.")

# ==================== الواجهة الثانية: لوحة تحكم الاستقبال والإدارة الذكية ====================
else:
    st.title("🖥️ داش بورد الإدارة وموظف الاستقبال")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 جدول الحجوزات اليومي", "📅 تقويم وضبط توفر الأطباء"])
    
    # التبويب الأول: جدول استعراض الحجوزات اليومية
    with tab1:
        filter_date = st.date_input("🔍 اختر تاريخاً لعرض المرضى:", datetime.today())
        filter_date_str = filter_date.strftime("%Y/%m/%d")
        
        conn = sqlite3.connect("clinic.db")
        cursor = conn.cursor()
        cursor.execute('''
            SELECT queue_no, patient_name, phone, doctor_name, visit_type, appointment_time 
            FROM appointments WHERE appointment_date = ? ORDER BY queue_no ASC
        ''', (filter_date_str,))
        rows = cursor.fetchall()
        conn.close()
        
        if rows:
            report_data = []
            for r in rows:
                report_data.append({
                    "رقم الدور": r[0], "اسم المريض": r[1], "رقم الهاتف": r[2],
                    "اسم الطبيب": r[3], "نوع الزيارة": r[4], "وقت الموعد": r[5]
                })
            st.table(report_data)
        else:
            st.info(f"📅 لا توجد أي مواعيد مسجلة ليوم {filter_date_str}")
            
    # التبويب الثاني: المكان المخصص للموظف ليدير أوقات توفر الأطباء والتقويم (ميزة جديدة)
    with tab2:
        st.subheader("⚙️ تحديث تقويم وساعات عمل الأطباء بالمستشفى")
        
        conn = sqlite3.connect("clinic.db")
        cursor = conn.cursor()
        cursor.execute("SELECT doctor_name FROM doctor_schedule")
        doc_names = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        selected_doc_edit = st.selectbox("اختر الطبيب لتعديل مواعيده:", doc_names)
        
        # حقول إدخال وتعديل أوقات التوفر والدوام
        new_hours = st.text_input("✍️ ساعات العمل المتاحة (مثال: 02:00 م - 06:00 م):")
        new_days = st.text_input("📅 أيام التوفر في الأسبوع (مثال: السبت، الإثنين، الخميس):")
        
        save_schedule_btn = st.form_submit_button if st.button("💾 حفظ وتحديث جدول الطبيب فوراً") else False
        
        if save_schedule_btn:
            if new_hours.strip() and new_days.strip():
                conn = sqlite3.connect("clinic.db")
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE doctor_schedule 
                    SET working_hours = ?, available_days = ? 
                    WHERE doctor_name = ?
                ''', (new_hours, new_days, selected_doc_edit))
                conn.commit()
                conn.close()
                st.success(f"✅ تم تحديث أوقات وتوفر ({selected_doc_edit}) بنجاح، وستظهر فوراً للمرضى في واجهة الحجز!")
            else:
                st.error("❌ يرجى ملء حقول الأوقات والأيام لتحديث التقويم.")