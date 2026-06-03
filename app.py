import streamlit as st
import datetime
import traceback
import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import gspread

# 🎨 إعدادات واجهة المصحة
st.set_page_config(page_title="منظومة حجز العيادة السحابية", page_icon="🏥", layout="centered")

# 🔐 إعدادات وصلاحيات جوجل
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar'
]

CALENDAR_IDS = {
    "د. أحمد - عيون": "7eed6d16879c19aa17880ddae3894f5e3cbaccc1f235ef17fbc31352c85c0ff7@group.calendar.google.com",
    "د. فاطمة - أطفال": "8d66dc8cd77280efefabedb17e6af02ffdf3a7369c0f0203bf367f7572dd1fdb@group.calendar.google.com"
}

SPREADSHEET_ID = "1PCGb1yaBGi9jBBwR3Yns0K9y5_46DwqIJ_lO9K1Ly_c"

@st.cache_resource
def get_google_services():
    """الاتصال بجوجل باستخدام الـ Secrets السحابية الآمنة"""
    try:
        # قراءة المفاتيح من السحاب مباشرة دون الحاجة لملف json على السيرفر
        if "google_credentials" not in st.secrets:
            return None, None, "المفاتيح غير معرفة في Streamlit Secrets"
            
        creds_dict = json.loads(st.secrets["google_credentials"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        calendar_service = build('calendar', 'v3', credentials=creds)
        gc = gspread.authorize(creds)
        return calendar_service, gc, "success"
    except Exception as e:
        return None, None, str(e)

calendar_service, gc, status_msg = get_google_services()

st.title("🏥 بوابة حجز المواعيد الإلكترونية")
st.write("مرحباً بك في المنظومة السحابية للمصحة. يرجى اختيار الطبيب المعني لإظهار وحجز المواعيد المتاحة.")

if calendar_service is None:
    st.error(f"❌ خطأ في الاتصال بخدمات سحاب جوجل: {status_msg}")
    st.info("تأكد من وضع محتوى ملف الـ JSON داخل الـ Secrets في إعدادات Streamlit Cloud.")
else:
    st.divider()
    
    # 1️⃣ اختيار الطبيب
    doctor_name = st.selectbox("🏥 اختر الطبيب أو التخصص المعني:", list(CALENDAR_IDS.keys()))
    
    if doctor_name:
        calendar_id = CALENDAR_IDS[doctor_name]
        
        try:
            # جلب المواعيد من كالندر
            now = datetime.datetime.utcnow().isoformat() + 'Z'
            events_result = calendar_service.events().list(
                calendarId=calendar_id, 
                timeMin=now,
                maxResults=15, 
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            available_slots = []
            
            for event in events:
                summary = event.get('summary', '')
                if "متاح" in summary:
                    start_dt = event['start'].get('dateTime', event['start'].get('date'))
                    dt_obj = datetime.datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                    friendly_time = dt_obj.strftime("%Y-%m-%d الساعة %I:%M %p")
                    
                    available_slots.append({
                        "event_id": event['id'],
                        "time_string": friendly_time
                    })
            
            # 2️⃣ عرض المواعيد
            if available_slots:
                st.success(f"🔍 تم العثور على {len(available_slots)} مواعيد متاحة لـ {doctor_name}")
                
                slot_options = {slot['time_string']: slot for slot in available_slots}
                selected_time_string = st.selectbox("📅 اختر الموعد المناسب لك:", list(slot_options.keys()))
                
                st.divider()
                st.subheader("✍️ بيانات المريض لإتمام الحجز")
                
                patient_name = st.text_input("👤 الاسم الثلاثي للمريض:")
                patient_phone = st.text_input("📞 رقم الهاتف التواصلي:")
                
                # 3️⃣ زر التأكيد والحجز
                if st.button("🚀 تأكيد الحجز فوراً", type="primary"):
                    if not patient_name or not patient_phone:
                        st.warning("⚠️ يرجى إدخال الاسم ورقم الهاتف.")
                    else:
                        with st.spinner("جاري تأكيد حجزك في المنظومة..."):
                            selected_slot = slot_options[selected_time_string]
                            event_id = selected_slot['event_id']
                            
                            # أ) تحديث التقويم
                            event = calendar_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
                            event['summary'] = f"محجوز: {patient_name}"
                            event['description'] = f"رقم الهاتف: {patient_phone}\nتم الحجز عبر البوابة السحابية."
                            calendar_service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
                            
                            # ب) التدوين في جوجل شيت
                            sheet = gc.open_by_key(SPREADSHEET_ID).sheet1
                            current_date = datetime.datetime.now().strftime("%Y-%m-%d")
                            row_to_insert = [patient_name, patient_phone, doctor_name, "مؤكد عبر البوابة", current_date, selected_time_string]
                            sheet.append_row(row_to_insert)
                            
                            st.balloons()
                            st.success(f"🎉 تم تأكيد حجزك بنجاح يا {patient_name}! الموعد: {selected_time_string}.")
            else:
                st.info(f"📋 لا توجد مواعيد متاحة حالياً لـ {doctor_name} في تقويم جوجل.")
                
        except Exception as e:
            st.error(f"حدث خطأ أثناء معالجة الحجز: {e}")
