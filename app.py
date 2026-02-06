import streamlit as st
import os
import io
from groq import Groq
from PyPDF2 import PdfReader # مكتبة جديدة لقراءة الـ PDF
import arabic_reshaper
from bidi.algorithm import get_display

st.set_page_config(page_title="مساعد الصيدلة الذكي Pro", page_icon="💊", layout="wide")
st.title("🎙️+📄 الربط الذكي بين الصوت وملف المحاضرة")

# 1. جلب مفاتيح API (الـ 4 حسابات)
api_keys = [st.secrets.get(f"groq_api_key_{i}") for i in range(1, 5)]
api_keys = [k for k in api_keys if k]

# 2. واجهة الرفع المزدوجة
col1, col2 = st.columns(2)
with col1:
    audio_file = st.file_uploader("🎙️ ارفع تسجيل المحاضرة", type=["mp3", "wav", "m4a"])
with col2:
    pdf_file = st.file_uploader("📄 ارفع ملف المحاضرة (PDF)", type=["pdf"])

if audio_file and pdf_file:
    if st.button("🚀 بدء الربط والتحليل الذكي"):
        # أ. قراءة نص الـ PDF ليكون مرجعاً
        pdf_reader = PdfReader(pdf_file)
        pdf_context = ""
        for page in pdf_reader.pages:
            pdf_context += page.extract_text()
        
        # ب. تفريغ الصوت (Whisper)
        raw_audio_text = ""
        audio_bytes = audio_file.read()
        success_client = None
        
        for i, key in enumerate(api_keys):
            try:
                client = Groq(api_key=key)
                with st.spinner(f"جاري تحويل الصوت باستخدام حساب {i+1}..."):
                    transcription = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=(audio_file.name, io.BytesIO(audio_bytes)),
                        language="ar",
                        prompt=f"Context terms: {pdf_context[:500]}" # إرسال نبذة من الـ PDF لتحسين التعرف
                    )
                    raw_audio_text = transcription.text
                    success_client = client
                    break
            except Exception as e:
                if "rate_limit_exceeded" in str(e): continue
                else: st.error(f"خطأ: {e}"); st.stop()

        # ج. الربط والذكاء الاصطناعي (Llama)
        if raw_audio_text and success_client:
            try:
                with st.spinner("جاري مطابقة الصوت مع ملف الـ PDF لتصحيح المصطلحات..."):
                    correlation_prompt = f"""
                    أنت صيدلي خبير. لديك نصين لنفس المحاضرة:
                    1. نص مرجعي دقيق (من ملف PDF): {pdf_context[:5000]}
                    2. نص مفرغ من صوت الدكتور (قد يحتوي أخطاء): {raw_audio_text}
                    
                    المطلوب:
                    - قم بتصحيح النص المفرغ من الصوت باستخدام المصطلحات الدقيقة الموجودة في الـ PDF.
                    - اكتب المصطلحات الطبية بالإنجليزية كما وردت في الـ PDF.
                    - لخص أهم النقاط التي شرحها الدكتور زيادة عن الموجود في الملف (الزيادات العلمية).
                    - حافظ على روح العامية المصرية في الأجزاء التوضيحية.
                    """
                    completion = success_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": correlation_prompt}]
                    )
                    final_output = completion.choices[0].message.content

                st.success("✅ تم الربط وتصحيح النص بنجاح!")
                st.markdown("### 🎯 النتيجة النهائية (المصححة مرجعياً):")
                st.info(final_output)

            except Exception as e:
                st.error(f"خطأ في الربط: {e}")
