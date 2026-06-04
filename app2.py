import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import datetime
import json

# --- 1. إعدادات الصفحة والجماليات (نفس التصميم الاحترافي المحبوب) ---
st.set_page_config(page_title="مركز النخبة الطبي | حجز المواعيد", page_icon="🏥", layout="wide")

st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <style>
        html, body, [class*="css"] {
            font-family: 'Cairo', sans-serif;
            direction: rtl;
            text-align: right;
        }
        .hero-section {
            background: linear-gradient(rgba(0,0,0,0.5), rgba(0,0,0,0.5)), url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80');
            background-size: cover;
            background-position: center;
            padding: 60px 20px;
            color: white;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
        }
        div.stButton > button {
            border-radius: 12px;
            font-size: 16px;
            font-weight: bold;
            transition: 0.3s;
        }
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- 2. الربط السحابي والأمان ---
try:
    creds_dict = json.loads(st.secrets["google_credentials"])
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/calendar']
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
except Exception as e:
    st.error("⚠️ خطأ في تهيئة المفاتيح السرية. يرجى مراجعة Settings -> Secrets")
    st.stop()

CALENDAR_IDS = {
    "د. أحمد - عيون": "0acd596ca9fbff4366bb88124b4c5c7737743e2efaff30f67c2664adc66276de@group.calendar.google.com",
    "د. فاطمة - أطفال": "ad779c7745c547cf6396337c7afc8e9dfc842810f383bd0ec66b1e0987af8f6b@group.calendar.google.com"
}
SPREADSHEET_NAME = "حجوزات العيادة"

# --- 3. الدوال البرمجية الذكية (تعتمد على الشيت كقاعدة بيانات أساسية) ---

def get_slots_grouped_by_day(calendar_id):
    """جلب الفترات من الكالندر وتفتيتها إلى فترات مدتها 20 دقيقة دون المساس بالحدث الأصلي"""
    try:
        service = build('calendar', 'v3', credentials=creds)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        events_result = service.events().list(
            calendarId=calendar_id, timeMin=now, maxResults=30, 
            singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        grouped_slots = {}
        
        for event in events:
            if "متاح" in event.get('summary', ''):
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                
                start_dt = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                end_dt = datetime.datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                
                day_key = start_dt.strftime('%Y-%m-%d')
                if day_key not in grouped_slots:
                    grouped_slots[day_key] = []
                
                current_time = start_dt
                booking_number = 1
                
                # تقسيم فترة تواجد الطبيب إلى فترات مدتها 20 دقيقة
                while current_time + datetime.timedelta(minutes=20) <= end_dt:
                    slot_end = current_time + datetime.timedelta(minutes=20)
                    
                    grouped_slots[day_key].append({
                        "id": event['id'],
                        "start": current_time,
                        "end": slot_end,
                        "display_time": current_time.strftime('%I:%M %p'),
                        "booking_no": booking_number
                    })
                    current_time = slot_end
                    booking_number += 1
                    
        return grouped_slots
    except Exception as e:
        st.error(f"حدث خطأ أثناء قراءة التقويم: {e}")
        return {}

def check_already_booked(sheet, day, time_str, doctor_name):
    """التحقق التام من الجوجل شيت لمعرفة إذا كان هذا الوقت محجوزاً مسبقاً"""
    try:
        records = sheet.get_all_values()
        for row in records[1:]:
            if len(row) >= 6:
                # عمود C هو الطبيب (موقع 2)، عمود E هو التاريخ (موقع 4)، عمود F هو الوقت (موقع 5)
                if row[2] == doctor_name and row[4] == day and row[5] == time_str:
                    return True
        return False
    except:
        return False

def confirm_booking_to_sheet(day, slot, name, phone, doctor_name, patient_status):
    """حفظ الحجز مباشرة داخل الجوجل شيت وفقاً لترتيب الأعمدة الدقيق الخاص بك"""
    try:
        sheets_client = gspread.authorize(creds)
        sheet = sheets_client.open(SPREADSHEET_NAME).sheet1
        
        time_display = slot['display_time']
        
        # التأكد مرة أخرى من عدم حجز الموعد في نفس اللحظة
        if check_already_booked(sheet, day, time_display, doctor_name):
            st.error("⚠️ عذراً، هذا الوقت تم حجزه للتو! يرجى اختيار وقت آخر.")
            return False

        # الحفظ المباشر المطابق لأعمدة الجدول: [اسم المريض، رقم الهاتف، اسم الطبيب، الحالة، تاريخ الحجز، وقت الموعد]
        sheet.append_row([
            name,                       # عمود A: اسم المريض
            phone,                      # عمود B: رقم الهاتف
            doctor_name,                # عمود C: اسم الطبيب
            f"{patient_status} (رقم الدور: {slot['booking_no']})", # عمود D: الحالة + رقم الدور التلقائي
            day,                        # عمود E: تاريخ الحجز
            time_display                # عمود F: وقت الموعد
        ])
        return True
    except Exception as e:
        st.error(f"حدث خطأ أثناء الحفظ في الشيت: {e}")
        return False

# --- 4. واجهة المستخدم التفاعلية (UI) ---

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/387/387561.png", width=90)
    st.title("مركز النخبة الطبي")
    st.info("🔒 ميزة أمان عالية: يتم تخزين جميع بيانات المرضى وحفظ الخصوصية داخل منظومة الجداول الإلكترونية مباشرة.")
    st.markdown("[📍 موقعنا على خرائط جوجل](https://maps.app.goo.gl/o1H7K7W6S4WzK9U5A)")
    st.caption("تطوير وإشراف هندسي متكامل v1.5")

st.markdown("""
    <div class="hero-section">
        <h1>🏥 منظومة الحجز الفوري الذكية</h1>
        <p>اختر طبيبك، حدد يومك، واحجز وقتك بدقة وبالدقيقة دون عناء الانتظار</p>
    </div>
""", unsafe_allow_html=True)

# خطوة 1: اختيار الطبيب
doctor = st.selectbox("👇 يرجى اختيار الطبيب المعني لبدء العملية:", list(CALENDAR_IDS.keys()))

if doctor:
    with st.spinner("جاري تحديث الأوقات من النظام..."):
        all_days = get_slots_grouped_by_day(CALENDAR_IDS[doctor])
        
    if not all_days:
        st.warning("⚠️ لا توجد ساعات عمل متاحة مسجلة كـ 'متاح' لهذا الطبيب حالياً.")
    else:
        # خطوة 2: اختيار اليوم عبر قائمة منسدلة بالأيام المتاحة هذا الشهر
        st.subheader("📆 1. اختر اليوم المتاح هذا الشهر:")
        formatted_days = {datetime.datetime.strptime(d, '%Y-%m-%d').strftime('%Y-%m-%d ( %A )'): d for d in all_days.keys()}
        selected_day_display = st.selectbox("", list(formatted_days.keys()), label_visibility="collapsed")
        actual_day = formatted_days[selected_day_display]
        
        daily_slots = all_days[actual_day]
        
        sheets_client = gspread.authorize(creds)
        sheet = sheets_client.open(SPREADSHEET_NAME).sheet1

        st.subheader("⏰ 2. الأوقات المتاحة في هذا اليوم (مقسمة كل 20 دقيقة):")
        
        cols = st.columns(4)
        
        for index, slot in enumerate(daily_slots):
            col_target = cols[index % 4]
            time_text = slot['display_time']
            
            # الفحص المباشر من الشيت
            is_booked = check_already_booked(sheet, actual_day, time_text, doctor)
            
            if is_booked:
                col_target.button(f"🚫 {time_text} (محجوز)", key=f"btn_{index}", disabled=True)
            else:
                if col_target.button(f"⏱️ {time_text}", key=f"btn_{index}", use_container_width=True):
                    st.session_state['chosen_slot'] = slot
                    st.session_state['chosen_day'] = actual_day

        # خطوة 3: إدخال البيانات المكتملة وتحديث الشيت فوراً
        if 'chosen_slot' in st.session_state and st.session_state.get('chosen_day') == actual_day:
            slot = st.session_state['chosen_slot']
            
            st.markdown("---")
            st.success(f"📍 الوقت المحدد: **{slot['display_time']}** | **رقم دورك التلقائي سيكون: [ {slot['booking_no']} ]**")
            
            with st.container():
                st.subheader("📝 3. تعبئة بيانات المريض لظهورها عند موظف الاستقبال:")
                
                p_name = st.text_input("اسم المريض بالكامل:")
                p_phone = st.text_input("رقم هاتف المريض المباشر:")
                
                # حقل مخصص لعمود "الحالة" الموجود في الجوجل شيت الخاص بك
                p_status = st.selectbox("حالة ونوع الزيارة:", ["كشف جديد", "مراجعة دورية", "استشارة مستعجلة"])
                
                if st.button("🚀 تأكيد وإرسال البيانات لشاشة الاستقبال فوراً", type="primary"):
                    if not p_name or not p_phone:
                        st.error("❌ فضلاً، يجب كتابة الاسم ورقم الهاتف لإتمام الحجز!")
                    else:
                        with st.spinner("جاري حفظ البيانات وتأمين المقعد..."):
                            success = confirm_booking_to_sheet(actual_day, slot, p_name, p_phone, doctor, p_status)
                            if success:
                                st.balloons()
                                st.markdown(f"""
                                <div style="background-color: #d4edda; color: #155724; padding: 20px; border-radius: 10px; border-right: 6px solid #28a745; text-align: center;">
                                    <h3>🎉 تم إرسال الحجز وتوثيقه بنجاح!</h3>
                                    <p>المريض: <b>{p_name}</b></p>
                                    <p>الطبيب: <b>{doctor}</b></p>
                                    <p>النوع: <b>{p_status}</b></p>
                                    <p>التاريخ والوقت: <b>{actual_day} في تمام الساعة {slot['display_time']}</b></p>
                                    <h2 style="color: #28a745; margin: 10px 0;">رقم الدور المحفوظ في الشيت هو: [ {slot['booking_no']} ]</h2>
                                    <p>البيانات الآن تظهر أمام موظف الاستقبال في شاشة العيادة.</p>
                                </div>
                                """, unsafe_allow_html=True)
                                del st.session_state['chosen_slot']