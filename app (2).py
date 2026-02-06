"""
تطبيق تحويل الصوت إلى نص مع دعم العربية والإنجليزية
Speech to Text Converter with Arabic & English Support
========================================================

هذا التطبيق يستخدم:
- Streamlit: للواجهة الرسومية
- Groq API: لتحويل الصوت إلى نص (Whisper)
- fpdf2: لإنشاء ملفات PDF
- arabic_reshaper & python-bidi: لمعالجة النص العربي
- Amiri Font: خط عربي جميل
"""

import streamlit as st
import os
import tempfile
from pathlib import Path
from groq import Groq
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

# ============================================================================
# إعدادات Streamlit
# ============================================================================
st.set_page_config(
    page_title="محول الصوت إلى نص | Speech to Text",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="expanded"
)

# تصميم CSS مخصص
st.markdown("""
<style>
    .main {
        direction: rtl;
        font-family: 'Arial', sans-serif;
    }
    h1, h2, h3 {
        color: #2c3e50;
        direction: rtl;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #17a2b8;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# دالة إعداد مفتاح API بشكل آمن
# ============================================================================
def get_groq_api_key():
    """
    تحصل على مفتاح API بشكل آمن من:
    1. متغيرات البيئة (Environment Variables) - الأفضل لـ Streamlit Cloud
    2. Streamlit Secrets - للتطوير المحلي
    3. إدخال المستخدم - كخيار أخير
    """
    # جرب متغيرات البيئة أولاً
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return api_key
    
    # جرب Streamlit Secrets ثانياً
    try:
        api_key = st.secrets.get("groq_api_key")
        if api_key:
            return api_key
    except:
        pass
    
    # اطلب من المستخدم إدخال المفتاح
    st.warning("⚠️ مفتاح API غير موجود! يرجى إدخاله:")
    api_key = st.text_input(
        "أدخل مفتاح Groq API",
        type="password",
        help="احصل على المفتاح من https://console.groq.com"
    )
    return api_key if api_key else None

# ============================================================================
# دالة تحويل الصوت إلى نص (Whisper)
# ============================================================================
def transcribe_audio(audio_file, api_key):
    """
    تحويل ملف صوتي إلى نص باستخدام Groq Whisper API
    
    المعاملات:
    - audio_file: كائن الملف الصوتي من Streamlit
    - api_key: مفتاح Groq API
    
    العائد:
    - نص مكتوب (string) أو None في حالة الخطأ
    """
    try:
        # أنشئ عميل Groq
        client = Groq(api_key=api_key)
        
        # أرسل الملف إلى API
        with st.spinner("⏳ جاري معالجة الملف الصوتي..."):
            # اقرأ محتوى الملف
            audio_content = audio_file.read()
            
            # أنشئ كائن ملف مؤقت لإرساله إلى API
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".mp3"  # يمكن أن يكون mp3, wav, m4a
            ) as temp_audio:
                temp_audio.write(audio_content)
                temp_audio_path = temp_audio.name
            
            # افتح الملف وأرسله إلى API
            with open(temp_audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=f,
                    language="ar",  # اللغة: عربي (يدعم أيضاً الإنجليزية)
                    temperature=0.0  # دقة عالية
                )
            
            # حذف الملف المؤقت
            os.remove(temp_audio_path)
            
            return transcript.text
    
    except Exception as e:
        st.error(f"❌ خطأ في معالجة الملف: {str(e)}")
        return None

# ============================================================================
# دالة معالجة النص العربي وإنشاء PDF
# ============================================================================
def create_arabic_pdf(text, filename="output.pdf"):
    """
    إنشاء ملف PDF مع دعم النص العربي والإنجليزي
    
    هذه الدالة تقوم بـ:
    1. إعادة تشكيل النص العربي (Reshaping)
    2. ترتيب الأحرف من اليمين لليسار (RTL)
    3. دعم النصوص المختلطة (عربي وإنجليزي)
    4. إنشاء ملف PDF احترافي مع خط Amiri
    """
    try:
        # إنشاء كائن PDF
        pdf = FPDF(
            orientation='P',  # Portrait
            unit='mm',
            format='A4'
        )
        
        # إضافة صفحة جديدة
        pdf.add_page()
        
        # حاول إضافة خط Amiri من المجلد الحالي
        font_loaded = False
        try:
            # تحقق إذا كان الخط موجوداً في المجلد الحالي
            font_path = "Amiri-Regular.ttf"
            if Path(font_path).exists():
                pdf.add_font("Arabic", "", font_path)
                pdf.set_font("Arabic", size=12)
                font_loaded = True
            else:
                st.warning("⚠️ خط Amiri-Regular.ttf غير موجود في المجلد الحالي، سيتم استخدام خط افتراضي")
                pdf.set_font("Arial", size=12)
        except Exception as e:
            st.warning(f"⚠️ لم يتم تحميل الخط المخصص: {str(e)}")
            pdf.set_font("Arial", size=12)
        
        # معالجة النص العربي والمختلط
        # الخطوة 1: إعادة تشكيل النص العربي
        reshaped_text = arabic_reshaper.reshape(text)
        
        # الخطوة 2: ترتيب النص من اليمين لليسار (يدعم النصوص المختلطة)
        rtl_text = get_display(reshaped_text)
        
        # إضافة العنوان
        pdf.set_fill_color(44, 62, 80)  # لون داكن
        pdf.set_text_color(255, 255, 255)  # نص أبيض
        if font_loaded:
            pdf.set_font("Arabic", size=14, style='B')
            pdf.cell(0, 12, "نتيجة التحويل", 0, 1, 'R', fill=True)
        else:
            pdf.set_font("Arial", size=14, style='B')
            pdf.cell(0, 12, "Transcription Result", 0, 1, 'R', fill=True)
        
        pdf.ln(5)
        
        # إضافة النص مع دعم الأسطر الطويلة والنصوص المختلطة
        pdf.set_text_color(0, 0, 0)
        if font_loaded:
            pdf.set_font("Arabic", size=11)
        else:
            pdf.set_font("Arial", size=11)
        
        # استخدام multi_cell لدعم الأسطر الطويلة
        pdf.multi_cell(0, 7, rtl_text)
        
        # إضافة الفاصل
        pdf.ln(3)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        
        # إضافة معلومات إنشاء الملف
        from datetime import datetime
        pdf.set_font("Arial", size=9)
        pdf.set_text_color(128, 128, 128)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        pdf.cell(0, 8, f"Created: {current_date} | تم الإنشاء في: {current_date}", 0, 1, 'L')
        
        # إضافة معلومات عن الترميز
        pdf.set_font("Arial", size=8)
        pdf.cell(0, 6, "UTF-8 Encoded | محرف بصيغة UTF-8", 0, 1, 'L')
        
        # حفظ الملف
        pdf.output(filename)
        return True
    
    except Exception as e:
        st.error(f"❌ خطأ في إنشاء PDF: {str(e)}")
        return False

# ============================================================================
# الواجهة الرسومية الرئيسية
# ============================================================================
def main():
    # العنوان
    st.title("🎙️ محول الصوت إلى نص")
    st.subheader("Speech to Text Converter with Arabic Support")
    st.markdown("---")
    
    # شريط جانبي للمعلومات
    with st.sidebar:
        st.markdown("### 📋 معلومات التطبيق")
        st.info("""
        **الميزات:**
        - ✅ تحويل الصوت إلى نص بدقة عالية
        - ✅ دعم العربية والإنجليزية والخليط بينهما
        - ✅ إنشاء PDF احترافي
        - ✅ دعم خطوط عربية مشبكة
        - ✅ مجاني تماماً
        
        **الصيغ المدعومة:**
        - MP3
        - WAV
        - M4A
        """)
        
        st.markdown("---")
        st.markdown("### 🔧 المتطلبات")
        st.code("""
pip install -r requirements.txt
        """)
    
    # الجزء الرئيسي
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📤 رفع ملف صوتي")
        audio_file = st.file_uploader(
            "اختر ملف صوتي",
            type=["mp3", "wav", "m4a"],
            help="يمكنك رفع ملفات صوتية بصيغة MP3، WAV، أو M4A"
        )
    
    with col2:
        st.markdown("### ℹ️ إحصائيات")
        if audio_file:
            file_size = audio_file.size / (1024 * 1024)  # تحويل إلى MB
            st.metric("حجم الملف", f"{file_size:.2f} MB")
            st.metric("الصيغة", audio_file.name.split('.')[-1].upper())
    
    st.markdown("---")
    
    # الحصول على مفتاح API
    api_key = get_groq_api_key()
    
    if not api_key:
        st.error("❌ يجب توفير مفتاح Groq API للمتابعة")
        st.stop()
    
    # معالجة الملف الصوتي
    if audio_file:
        st.success(f"✅ تم اختيار الملف: {audio_file.name}")
        
        # زر بدء التحويل
        if st.button("🔄 تحويل الصوت إلى نص", use_container_width=True, type="primary"):
            # تحويل الصوت إلى نص
            transcribed_text = transcribe_audio(audio_file, api_key)
            
            if transcribed_text:
                st.markdown("---")
                st.markdown("### 📝 النص المكتوب")
                
                # عرض النص في مربع قابل للنسخ
                st.text_area(
                    "النص الناتج (يمكنك نسخه):",
                    value=transcribed_text,
                    height=200,
                    disabled=True
                )
                
                # عدادات
                st.markdown("### 📊 الإحصائيات")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("عدد الأحرف", len(transcribed_text))
                with col2:
                    word_count = len(transcribed_text.split())
                    st.metric("عدد الكلمات", word_count)
                with col3:
                    st.metric("عدد السطور", transcribed_text.count('\n') + 1)
                
                st.markdown("---")
                
                # إنشاء PDF
                st.markdown("### 📄 تحويل إلى PDF")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📥 إنشاء ملف PDF", use_container_width=True):
                        pdf_filename = "output.pdf"
                        if create_arabic_pdf(transcribed_text, pdf_filename):
                            with open(pdf_filename, "rb") as pdf_file:
                                st.success("✅ تم إنشاء ملف PDF بنجاح!")
                                st.download_button(
                                    label="⬇️ تحميل PDF",
                                    data=pdf_file.read(),
                                    file_name=pdf_filename,
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            # حذف الملف المؤقت
                            if Path(pdf_filename).exists():
                                os.remove(pdf_filename)
                
                with col2:
                    # خيار تحميل النص كـ TXT
                    if st.button("📥 حفظ كـ TXT", use_container_width=True):
                        st.download_button(
                            label="⬇️ تحميل TXT",
                            data=transcribed_text,
                            file_name="transcription.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
    
    else:
        # عرض رسالة ترحيب عندما لا يكون هناك ملف
        st.info("👈 ابدأ برفع ملف صوتي من الجهة اليسرى")
    
    # التذييل
    st.markdown("---")
    st.markdown("""
    <div style="direction: rtl; text-align: center; color: #95a5a6; font-size: 12px;">
    <p>مصنوع بـ ❤️ باستخدام Streamlit و Groq API</p>
    <p>هذا التطبيق مجاني تماماً ويعمل على Streamlit Cloud</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
