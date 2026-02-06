import streamlit as st
import os
from groq import Groq
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد الصيدلة الذكي", page_icon="💊", layout="wide")
st.title("🎙️ مساعد المحاضرات الصيدلانية (نسخة مطورة)")

# 2. إدارة مفتاح الـ API
api_key = st.secrets.get("groq_api_key")
if not api_key:
    api_key = st.text_input("أدخل مفتاح API الخاص بك:", type="password")
    if not api_key:
        st.info("💡 نصيحة: ضع المفتاح في Secrets ليفتح التطبيق فوراً.")
        st.stop()

# 3. واجهة رفع الملف
uploaded_file = st.file_uploader("ارفع ملف المحاضرة (أقل من 25MB)", type=["mp3", "wav", "m4a"])

if uploaded_file:
    if st.button("بدء المعالجة الذكية"):
        try:
            client = Groq(api_key=api_key)
            
            # المرحلة الأولى: التفريغ النصي (Whisper)
            with st.spinner("جاري استماع المحاضرة وتفريغها..."):
                transcription = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=(uploaded_file.name, uploaded_file.read()),
                    language="ar"
                )
                raw_text = transcription.text

            # المرحلة الثانية: التلخيص الصيدلاني (باستخدام النموذج الجديد المحدث)
            with st.spinner("جاري تصحيح المصطلحات الطبية وتنظيم الملخص..."):
                system_prompt = """
                أنت مساعد صيدلي محترف. النص هو تفريغ لمحاضرة دكتور مصري بالعامية ومصطلحات طبية إنجليزية.
                مهمتك: 
                1- تنقية النص من الحشو وتصحيح إملاء المصطلحات الطبية.
                2- تلخيص المحاضرة في نقاط منظمة (أدوية، جرعات، ملاحظات هامة).
                """
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile", # تم تحديث النموذج هنا لحل مشكلة Decommissioned
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": raw_text[:15000]}
                    ]
                )
                refined_summary = completion.choices[0].message.content

            st.success("✅ تمت المعالجة بنجاح!")

            # 4. عرض النتائج في تبويبات
            tab1, tab2 = st.tabs(["📝 الملخص والمنقح", "📄 التفريغ الكامل"])
            with tab1:
                st.markdown(refined_summary)
            with tab2:
                st.write(raw_text)

            # 5. إنشاء ملف PDF
            pdf = FPDF()
            pdf.add_page()
            
            font_path = "Amiri-Regular.ttf"
            if os.path.exists(font_path):
                pdf.add_font("Amiri", "", font_path)
                pdf.set_font("Amiri", size=12)
            else:
                pdf.set_font("Arial", size=12)

            final_content = f"--- الملخص الطبي ---\n{refined_summary}\n\n" + "="*20 + f"\n\n--- النص الكامل ---\n{raw_text}"
            
            reshaped_text = arabic_reshaper.reshape(final_content)
            pdf.multi_cell(0, 10, get_display(reshaped_text), align='R')
            
            pdf_output = "Pharmacy_Lecture.pdf"
            pdf.output(pdf_output)
            
            with open(pdf_output, "rb") as f:
                st.download_button("📥 تحميل ملف PDF", f, file_name="Pharmacy_Lecture.pdf")
        
        except Exception as e:
            st.error(f"حدث خطأ: {e}")
