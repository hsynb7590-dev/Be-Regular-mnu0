import streamlit as st
import os
import subprocess
import sys

# 1. تثبيت المكتبات اللازمة تلقائياً عند أول تشغيل
def install_requirements():
    try:
        import groq
        import pydub
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "groq", "pydub", "arabic-reshaper", "python-bidi", "fpdf2"])

install_requirements()

from groq import Groq
from pydub import AudioSegment
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# 2. إعدادات الصفحة
st.set_page_config(page_title="مساعد الصيدلة الذكي", page_icon="💊", layout="wide")
st.title("🎙️ منصة تفريغ وتلخيص المحاضرات الطويلة")

# 3. إدارة مفتاح الـ API
api_key = st.secrets.get("groq_api_key") or st.text_input("أدخل مفتاح API:", type="password")

if not api_key:
    st.warning("⚠️ يرجى إضافة مفتاح API في Secrets لتفعيل الموقع.")
    st.stop()

uploaded_file = st.file_uploader("ارفع ملف المحاضرة (مضغوط بصيغة MP3 يفضل)", type=["mp3", "wav", "m4a"])

if uploaded_file:
    if st.button("بدء المعالجة الشاملة"):
        try:
            client = Groq(api_key=api_key)
            
            # حفظ الملف مؤقتاً
            with open("temp_audio.mp3", "wb") as f:
                f.write(uploaded_file.read())
            
            audio = AudioSegment.from_file("temp_audio.mp3")
            duration_min = len(audio) / 60000
            st.info(f"⏱️ طول المحاضرة المكتشف: {duration_min:.2f} دقيقة")

            # تقسيم الملف (كل 10 دقائق لتجنب قيود الحجم)
            chunk_length = 10 * 60 * 1000 
            full_transcript = ""
            chunks = range(0, len(audio), chunk_length)
            
            progress_bar = st.progress(0)
            
            # المرحلة الأولى: التفريغ النصي للأجزاء
            for i, chunk_start in enumerate(chunks):
                with st.spinner(f"جاري تفريغ الجزء {i+1} من {len(chunks)}..."):
                    chunk = audio[chunk_start:chunk_start + chunk_length]
                    chunk.export("chunk.mp3", format="mp3")
                    
                    with open("chunk.mp3", "rb") as f:
                        response = client.audio.transcriptions.create(
                            model="whisper-large-v3",
                            file=("chunk.mp3", f.read()),
                            language="ar"
                        )
                        full_transcript += response.text + " "
                
                progress_bar.progress((i + 1) / len(chunks))
            
            os.remove("chunk.mp3")
            os.remove("temp_audio.mp3")

            # المرحلة الثانية: التلخيص والتنقيح (المصري الصيدلاني)
            with st.spinner("جاري تنقيح النص وتلخيصه بذكاء..."):
                system_prompt = """
                أنت مساعد صيدلي محترف. النص هو تفريغ لمحاضرة دكتور مصري بالعامية ومصطلحات طبية إنجليزية.
                مهمتك: 
                1- تنقية النص من الحشو (يعني، تمام، فاهمين).
                2- تصحيح إملاء المصطلحات الطبية الإنجليزية.
                3- تلخيص المحاضرة في نقاط منظمة (أدوية، جرعات، ميكانيزم، ملاحظات هامة).
                4- حافظ على روح الشرح المصري.
                """
                # نأخذ أهم أجزاء النص للتلخيص (بحد أقصى 15000 حرف لسرعة الاستجابة)
                completion = client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_transcript[:15000]}
                    ]
                )
                refined_summary = completion.choices[0].message.content

            st.success("✅ اكتملت المعالجة!")

            # 4. عرض النتائج في تبويبات
            tab1, tab2 = st.tabs(["📝 الملخص والمنقح", "📄 التفريغ الكامل"])
            with tab1:
                st.markdown(refined_summary)
            with tab2:
                st.write(full_transcript)

            # 5. إنشاء الـ PDF
            def generate_pdf(summary, transcript):
                pdf = FPDF()
                pdf.add_page()
                font_path = "Amiri-Regular.ttf"
                if os.path.exists(font_path):
                    pdf.add_font("Amiri", "", font_path)
                    pdf.set_font("Amiri", size=12)
                else:
                    pdf.set_font("Arial", size=12)

                content = f"--- الملخص الطبي ---\n{summary}\n\n" + "="*30 + f"\n\n--- النص الكامل ---\n{transcript}"
                
                # معالجة اللغة العربية
                reshaped = arabic_reshaper.reshape(content)
                bidi_text = get_display(reshaped)
                
                pdf.multi_cell(0, 10, bidi_text, align='R')
                pdf.output("lecture_final.pdf")
                return "lecture_final.pdf"

            pdf_file = generate_pdf(refined_summary, full_transcript)
            with open(pdf_file, "rb") as f:
                st.download_button("📥 تحميل المحاضرة كاملة (PDF)", f, file_name="Pharmacy_Lecture.pdf")

        except Exception as e:
            st.error(f"حدث خطأ: {e}")
