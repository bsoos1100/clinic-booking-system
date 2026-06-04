import streamlit as st
import sqlite3
import datetime
import requests
import json

# --- 1. إعدادات قاعدة البيانات المحلية (SQLite) ---
def init_db():
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    
    # جدول الأطباء ومواعيد عملهم
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            start_time TEXT, 
            end_time TEXT    
        )
    ''')
    
    # جدول الحجوزات الفعلي للمرضى
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT,
            patient_phone TEXT,
            doctor_name TEXT,
            visit_type TEXT,
            booking_date TEXT, 
            booking_time TEXT, 
            queue_number INTEGER
        )
    ''')
    
    # إضافة بيانات تجريبية للأطباء إذا كان الجدول فارغاً أول مرة
    cursor.execute("SELECT COUNT(*) FROM doctors")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO doctors (name, start_time, end_time) VALUES ('د. أحمد - عيون', '17:00', '19:00')")
        cursor.execute("INSERT INTO doctors (name, start_time, end_time) VALUES ('د. فاطمة - أطفال', '10:00', '12:00')")
        
    conn.commit()
    conn.close()

init_db()

# --- 2. دالة إرسال الرسائل عبر Whapi الفوري ---
# الكود يقرأ التوكن تلقائياً من الـ Secrets التي قمت بضبطها
WHAPI_TOKEN = st.secrets.get("whapi_token", "AZSrEZo3hv5PsSmSxkXazDzKlphGnI33") 

def send_whatsapp_confirmation(phone, patient_name, doctor_name, date, time, queue_no):
    url = "https://gate.whapi.cloud/messages/text"
    
    # تنظيف رقم الهاتف ليتوافق مع الصيغة الدولية المعتمدة لدى Whapi
    clean_phone = phone.strip().replace("+", "").replace(" ", "")
    
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
        "to": f"{clean_phone}@s.whatsapp.net",
        "body": message_text
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {WHAPI_TOKEN}"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code in [200, 201]
    except:
        return False

# --- 3. خوارزمية توليد وتفتيت الأوقات الفترية (20 دقيقة) ---
def generate_slots(start_str, end_str):
    slots = []
    start = datetime.datetime.strptime(start_str, "%H:%M")
    end = datetime.datetime.strptime(end_str, "%H:%M")
    
    current = start
    while current + datetime.timedelta(minutes=20) <= end:
        slots.append(current.strftime("%H:%M"))
        current += datetime.timedelta(minutes=20)
    return slots

# --- 4. واجهة المستخدم الرسومية والجماليات ---
st.set_page_config(page_title="منظومة إدارة وحجز العيادات الذكية", page_icon="🏥", layout="wide")

st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
        .main-header { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px; color: white; text-align: center; border-radius: 12px; margin-bottom: 25px; }
        .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# نظام التنقل السلس في الشريط الجانبي
app_mode = st.sidebar.selectbox("📱 اختر واجهة العرض حالياً:", ["شاشة حجز المرضى", "لوحة تحكم موظف الاستقبال"])

# ==================== الواجهة الأولى: شاشة حجز المرضى ====================
if app_mode == "شاشة حجز المرضى":
    st.markdown("<div class='main-header'><h1>🏥 بوابتك الذكية لحجز المواعيد الطبية فورياً</h1><p>احجز موعدك بالدقيقة واستلم تذكرة الحجز على حسابك في الواتساب مباشرة</p></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    
    # جلب قائمة الأطباء الديناميكية من الـ DB
    cursor.execute("SELECT name, start_time, end_time FROM doctors")
    doctors_list = cursor.fetchall()
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🏥 1. اختر طبيبك تخصصك")
        doc_names = [d[0] for d in doctors_list]
        selected_doc = st.selectbox("الأطباء المتاحون بالمركز:", doc_names)
        
        st.subheader("📅 2. تاريخ الزيارة")
        selected_date = st.date_input("اختر تاريخ الموعد:", datetime.date.today()).strftime("%Y-%m-%d")
        
    # جلب فترات الطبيب الحالي وتفتيتها تلقائياً كل 20 دقيقة
    doc_info = [d for d in doctors_list if d[0] == selected_doc][0]
    all_slots = generate_slots(doc_info[1], doc_info[2])
    
    # حجب الأوقات المحجوزة مسبقاً لهذا الطبيب في هذا اليوم
    cursor.execute("SELECT booking_time FROM bookings WHERE doctor_name = ? AND booking_date = ?", (selected_doc, selected_date))
    booked_slots = [row[0] for row in cursor.fetchall()]
    
    with col2:
        st.subheader("⏰ 3. الأوقات المتاحة للحجز:")
        
        cols = st.columns(4)
        for idx, slot_time in enumerate(all_slots):
            btn_col = cols[idx % 4]
            display_time = datetime.datetime.strptime(slot_time, "%H:%M").strftime("%I:%M %p")
            
            if slot_time in booked_slots:
                btn_col.button(f"🚫 {display_time} (محجوز)", key=f"slot_{idx}", disabled=True, use_container_width=True)
            else:
                if btn_col.button(f"⏱️ {display_time}", key=f"slot_{idx}", use_container_width=True, type="secondary"):
                    st.session_state['active_slot'] = slot_time
                    st.session_state['active_doc'] = selected_doc
                    st.session_state['active_date'] = selected_date

    # استمارة إدخال بيانات المريض الفورية
    if 'active_slot' in st.session_state and st.session_state['active_date'] == selected_date and st.session_state['active_doc'] == selected_doc:
        st.markdown("---")
        chosen_time_display = datetime.datetime.strptime(st.session_state['active_slot'], "%H:%M").strftime("%I:%M %p")
        st.success(f"📍 الموعد المحدد: {chosen_time_display} مع {selected_doc}")
        
        with st.form("booking_form"):
            p_name = st.text_input("اسم المريض الثلاثي:")
            p_phone = st.text_input("رقم الهاتف (مع رمز الدولة، مثال: 218900000000):")
            v_type = st.selectbox("نوع الزيارة:", ["كشف أول مرة", "مراجعة دورية", "استشارة"])
            
            submit_btn = st.form_submit_button("🚀 تأكيد الحجز وإصدار التذكرة")
            
            if submit_btn:
                if not p_name or not p_phone:
                    st.error("❌ فضلاً، اكتب الاسم ورقم الهاتف لإتمام الحجز!")
                else:
                    # توليد وحساب رقم الدور التلقائي التتابعي
                    cursor.execute("SELECT COUNT(*) FROM bookings WHERE doctor_name = ? AND booking_date = ?", (selected_doc, selected_date))
                    current_queue = cursor.fetchone()[0] + 1
                    
                    # حفظ البيانات داخل قاعدة البيانات المحلية الحرة
                    cursor.execute('''
                        INSERT INTO bookings (patient_name, patient_phone, doctor_name, visit_type, booking_date, booking_time, queue_number)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (p_name, p_phone, selected_doc, v_type, selected_date, st.session_state['active_slot'], current_queue))
                    conn.commit()
                    
                    # استدعاء دالة الإرسال الفوري لـ Whapi
                    whatsapp_sent = send_whatsapp_confirmation(p_phone, p_name, selected_doc, selected_date, chosen_time_display, current_queue)
                    
                    st.balloons()
                    st.markdown(f"""
                        <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; text-align: center; border-right: 5px solid #28a745;">
                            <h3 style="color: #155724;">🎉 تم تسجيل حجزك بنجاح بالمنظومة!</h3>
                            <p>المريض: <b>{p_name}</b> | رقم الدور الممنوح لك: <b style="font-size:20px; color:#28a745;">[ {current_queue} ]</b></p>
                            <p>حالة رسالة تأكيد الـ الواتساب الذكية (Whapi): {"✅ تم الإرسال للمريض بنجاح" if whatsapp_sent else "⚠️ تعذر الإرسال الفوري"}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    del st.session_state['active_slot']
                    st.rerun()
                    
    conn.close()

# ==================== الواجهة الثانية: لوحة تحكم الاستقبال والداشبورد الفاخر ====================
else:
    st.markdown("<div class='main-header'><h1>🖥️ شاشة موظف الاستقبال وإدارة العيادات</h1><p>لوحة التحكم الشاملة لمتابعة الحجوزات، إدارة مواعيد الأطباء، وإرسال الحملات التسويقية</p></div>", unsafe_allow_html=True)
    
    conn = sqlite3.connect('clinic.db')
    cursor = conn.cursor()
    
    tab1, tab2, tab3 = st.tabs(["📋 جدول الحجوزات اليومي", "⚙️ إدارة أوقات الأطباء", "📢 البث والرسائل التسويقية"])
    
    # Tab 1: الجدول التفاعلي البديل عن غوغل شيت
    with tab1:
        st.subheader("🔍 استعراض الفلاتر")
        search_date = st.date_input("اختر تاريخ لعرض حجوزاته:", datetime.date.today()).strftime("%Y-%m-%d")
        
        cursor.execute("SELECT queue_number, patient_name, patient_phone, doctor_name, visit_type, booking_time FROM bookings WHERE booking_date = ? ORDER BY booking_time ASC", (search_date,))
        rows = cursor.fetchall()
        
        if not rows:
            st.info(f"📅 لا توجد أي حجوزات مسجلة ليوم {search_date} حتى الآن.")
        else:
            import pandas as pd
            df = pd.DataFrame(rows, columns=["رقم الدور", "اسم المريض", "رقم الهاتف", "اسم الطبيب", "الحالة/نوع الزيارة", "وقت الموعد"])
            st.dataframe(df, use_container_width=True)
            
    # Tab 2: تتيح للموظف تغيير أوقات الحضور من الشاشة مباشرة وتتحدث أزرار المرضى تلقائياً!
    with tab2:
        st.subheader("✏️ تعديل وتحديث فترات عمل الأطباء")
        cursor.execute("SELECT id, name, start_time, end_time FROM doctors")
        docs = cursor.fetchall()
        
        for d_id, d_name, d_start, d_end in docs:
            with st.expander(f"⚙️ إعدادات وقت: {d_name}"):
                c1, c2 = st.columns(2)
                new_start = c1.text_input("وقت البدء (صيغة 24 ساعة مثل 16:00):", d_start, key=f"start_{d_id}")
                new_end = c2.text_input("وقت الانتهاء (صيغة 24 ساعة مثل 21:00):", d_end, key=f"end_{d_id}")
                
                if st.button("حفظ المواعيد الجديدة", key=f"save_{d_id}"):
                    cursor.execute("UPDATE doctors SET start_time = ?, end_time = ? WHERE id = ?", (new_start, new_end, d_id))
                    conn.commit()
                    st.success("✅ تم تحديث أوقات عمل الطبيب بنجاح، وستنعكس فوراً على واجهة حجز المرضى!")
                    st.rerun()

    # Tab 3: ميزة الـ Broadcast التسويقية القوية لتقفيل البيعة
    with tab3:
        st.subheader("📢 إرسال عروض وتحديثات لجميع المرضى المسجلين")
        st.info("💡 هذه الميزة تقوم بسحب كافة أرقام هواتف المرضى المخزنة في قاعدة البيانات وإرسال رسالة جماعية لهم دفعة واحدة عبر Whapi.")
        
        promo_message = st.text_area("اكتب نص الرسالة أو العرض التسويقي هنا:", 
            placeholder="مثال: بشرى سارة من مركز النخبة.. تعلن عيادة الأطفال عن تخفيض بقيمة 30% على الفحوصات والزيارات طيلة هذا الأسبوع. للحجز الفوري تفضل بزيارة موقعنا.")
        
        if st.button("🚀 إرسال الحملة التسويقية الآن عبر الواتساب"):
            if not promo_message:
                st.error("❌ لا يمكن إرسال رسالة فارغة!")
            else:
                cursor.execute("SELECT DISTINCT patient_phone, patient_name FROM bookings")
                patients_contacts = cursor.fetchall()
                
                if not patients_contacts:
                    st.warning("⚠️ لا توجد أرقام هواتف لمرضى مخزنين في قاعدة البيانات حالياً.")
                else:
                    success_count = 0
                    url = "https://gate.whapi.cloud/messages/text"
                    headers = {
                        "accept": "application/json",
                        "content-type": "application/json",
                        "Authorization": f"Bearer {WHAPI_TOKEN}"
                    }
                    
                    with st.spinner("جاري بث الرسائل الترويجية الآن..."):
                        for phone, name in patients_contacts:
                            clean_phone = phone.strip().replace("+", "").replace(" ", "")
                            payload = {
                                "to": f"{clean_phone}@s.whatsapp.net",
                                "body": f"مرحباً سيد/ة *{name}*،\n\n{promo_message}"
                            }
                            try:
                                res = requests.post(url, json=payload, headers=headers)
                                if res.status_code in [200, 201]:
                                    success_count += 1
                            except:
                                pass
                                
                    st.success(f"🎉 تم الانتهاء من بث الحملة! أرسلت بنجاح إلى [ {success_count} ] مريض من أصل {len(patients_contacts)} عبر Whapi.")
                    
    conn.close()