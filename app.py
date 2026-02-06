import streamlit as st
import os
import io
from groq import Groq
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# 1. إعدادات الصفحة
st.set_page_config(page_title="مساعد الصيدلة الذكي Pro", page_icon="💊", layout="wide")
st.title("🎯 منصة استخراج 'زتونة' المحاضرات الصيدلانية")

# --- عداد الاستهلاك الموحد ---
if 'used_seconds' not in st.session_state:
    st.session_state.used_seconds = 0

total_limit_seconds = 7200 * 4 # 8 ساعات إجمالية للأربعة حسابات
remaining_seconds = max(0, total_limit_seconds - st.session_state.used_seconds)

st.sidebar.header("📊 رصيد الموقع المتبقي")
progress = min(st.session_state.used_seconds / total_limit_seconds, 1.0)
st.sidebar.progress(progress)
st.sidebar.write(f"🔓 المتبقي: {remaining_seconds / 3600:.2f} ساعة")

# 2. جلب مفاتيح API
api_keys = [
    st.secrets.get("groq_api_key_1"),
    st.secrets.get("groq_api_key_2"),
    st.secrets.get("groq_api_key_3"),
    st.secrets.get("groq_api_key_4")
]
api_keys = [k for k in api_keys if k]

if not api_keys:
    st.error("⚠️ تأكد من إضافة 4 مفاتيح في Secrets.")
    st.stop()

# 3. المعالجة
uploaded_file = st.file_uploader("ارفع ملف المحاضرة", type=["mp3", "wav", "m4a"])

if uploaded_file:
    file_bytes = uploaded_file.read()
    
    if st.button("🚀 استخراج النقاط الهامة"):
        raw_text = ""
        success_client = None
        
        for i, key in enumerate(api_keys):
            try:
                client = Groq(api_key=key)
                with st.spinner(f"جاري قراءة المحاضرة (حساب {i+1})..."):
                    transcription = client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=(uploaded_file.name, io.BytesIO(file_bytes)),
                        language="ar",
                        prompt="Keep Egyptian slang. Focus on medical terms: Pharmacology, Dosage, Mechanism."
                    )
                    raw_text = transcription.text
                    success_client = client
                    st.session_state.used_seconds += 3600 # خصم ساعة من العداد
                    break 
            except Exception as e:
                if "rate_limit_exceeded" in str(e): continue
                else: st.error(f"❌ خطأ: {e}"); st.stop()
        
        if raw_text:
            try:
                with st.spinner("جاري فلترة الكلام واستخراج ما ركز عليه الدكتور..."):
                    focus_prompt = f"""
                    أنت صيدلي خبير. استخرج من هذا التفريغ الأجزاء المهمة فقط:
                    1- ركز على الجمل التي تبدأ بـ (مهم، ركزوا، هييجي في الامتحان، النقطة دي أساسية).
                    2- استخرج أسماء الأدوية المذكورة بالإنجليزية (English Script).
                    3- لخص الـ Mechanism والـ Side effects التي شرحها الدكتور بعمق.
                    4- تجاهل أي رغي جانبي أو حكايات خارج المنهج.
                    
                    التفريغ: {raw_text[:15000]}
                    """
                    completion = success_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": focus_prompt}]
                    )
                    refined_output = completion.choices[0].message.content

                st
