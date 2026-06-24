import streamlit as st
import os
import time

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ==========================================
# 1. ORTAK BAĞLAM FONKSİYONU
# ==========================================
def build_portfolio_context(summary: dict) -> str:
    """
    Hem sohbet botu hem de AI Özet kartı için backend'den gelen 
    verileri okunaklı bir metne dönüştürür.
    """
    allocations = summary.get("allocation", {})
    alloc_str = ", ".join([f"{k} (%{v:.1f})" for k, v in allocations.items()]) if allocations else "Veri yok"
    
    # Backend'in yeni veri isimlerini güvenli şekilde yakalıyoruz
    port_var = summary.get('VaR', summary.get('portfolio_var', summary.get('var_95', 'Veri yok')))
    port_es = summary.get('ES', summary.get('expected_shortfall', summary.get('es', 'Veri yok')))
    div_eff = summary.get('Diversification_Effect', summary.get('diversification_effect', 'Veri yok'))
    pairs = summary.get('high_corr_pairs', 'Veri yok')

    # Eğer gelen veri bir rakamsa şık bir yüzde formatına çeviriyoruz
    def fmt(val):
        return f"{val:.2%}" if isinstance(val, (int, float)) else str(val)

    context_lines = [
        f"Portföy Dağılımı: {alloc_str}",
        f"Portföy VaR (95%): {fmt(port_var)}",
        f"Expected Shortfall (ES): {fmt(port_es)}",
        f"Çeşitlendirme Etkisi: {fmt(div_eff)}",
        f"Yüksek Korelasyonlu Çiftler: {pairs}",
    ]
    missing = [line for line in context_lines if "Veri yok" in line]
    if missing:
        context_lines.append(
            "NOT: Yukaridaki bazi metrikler henuz hesaplanmamis. "
            "Kullaniciya once 'Portfoyu Analiz Et' butonuna basmasini soyle."
        )
    return "\n".join(context_lines)

# ==========================================
# 2. YENİ GÖREV: AI ÖZET KARTI FONKSİYONU
# ==========================================
def generate_portfolio_summary(data: dict) -> str:
    """
    Kullanıcı 'Portföyü Analiz Et' butonuna bastığında çağrılır.
    Geçmiş olmadan tek seferlik özet üretir.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not GENAI_AVAILABLE:
        return "" # sessizce boş dönmesi bize gayet yeterli olur
    context = build_portfolio_context(data)
    system_prompt = f"""Sen profesyonel bir portföy risk analizi asistanısın. 
Aşağıdaki verilere dayanarak yatırımcıya kısa, net ve teknik bir özet sun. 
Alım-satım tavsiyesi verme, sadece risk durumunu yorumla.

Veriler:
{context}"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt,
        )
        for attempt in range(2):
            try:
                response = model.generate_content("Bu portfoyun risk profilini 3-4 cumlede ozetle.")
                return response.text
            except Exception as exc:
                if _is_quota_error(exc) and attempt == 0:
                    time.sleep(62)
                    continue
                raise
    except Exception as exc:
        print(f"AI Ozet Hatasi: {exc}")
        return ""
# ==========================================
# 3. ESKİ GÖREV: SOHBET BOTU FONKSİYONLARI
# ==========================================
def get_chat_system_prompt(context: str) -> str:
    return f"""Sen bir portföy risk analizi asistanısın. 
Kullanıcıya yalnızca sana sağlanan model çıktılarına ve istatistiklere dayanarak yanıt ver. 
Kesinlikle alım-satım tavsiyesi vermezsin, sadece kendi modelinin çıktılarını yorumlarsın.

Yanıt verebileceğin konular:
- Portföy VaR ve ES değerlerinin ne anlama geldiği ve nasıl yorumlanacağı
- Yüksek korelasyonlu varlık çiftlerinin portföy riskine etkisi
- Çeşitlendirme etkisinin yorumu ve iyileştirme önerileri
- GARCH, EWMA ve XGBoost modellerinin farkları ve hangisine ne zaman güvenileceği
- Volatilite rejimlerinin portföye olası etkileri
- Kullanıcının mevcut portföyündeki spesifik risklerin açıklanması

Yanıt verirken uyman gereken kurallar:
- Her yanıtta mutlaka aşağıdaki bağlamdaki gerçek sayılara atıfta bulun
- Soyut açıklama yapma, sayıları kullan
- Alım-satım tavsiyesi verme, sadece risk durumunu yorumla
- Bağlamda olmayan verilerden tahmin yapma

Kullanıcının güncel portföy verileri:
{context}
"""

def _is_quota_error(exc: Exception) -> bool:
    """Gemini 429 / kota asimi hatasini tanimlar."""
    msg = str(exc).lower()
    return "429" in msg or "quota" in msg or "rate" in msg or "resource_exhausted" in msg


def call_gemini_chat(messages: list, system: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY ortam degiskeni bulunamadi.")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=system,
    )

    gemini_history = []
    for msg in messages[:-1]:
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    # Ucretsiz tier: dakikada 5 istek limiti. 1 otomatik yeniden deneme.
    for attempt in range(2):
        try:
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(messages[-1]["content"])
            return response.text
        except Exception as exc:
            if _is_quota_error(exc) and attempt == 0:
                time.sleep(62)  # 1 dakika bekle, sonra tekrar dene
                continue
            raise

def render_portfolio_chat(summary: dict):
     # API anahtarı yoksa chatbot'u hiç gösterme
    if not os.environ.get("GEMINI_API_KEY"):
        st.info("🤖 AI özellikleri aktif değil. `.env` dosyasında `GEMINI_API_KEY` tanımlı olmalıdır.")
        return
    
    st.subheader("🤖 Portföy Risk Asistanı")
    st.markdown("Güncel risk modellemeleri hakkında sorular sorabilirsiniz.")

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Örn: Portföydeki yüksek korelasyonlu çiftler riskimi nasıl etkiliyor?"):
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        context = build_portfolio_context(summary)
        system_prompt = get_chat_system_prompt(context)

        with st.chat_message("assistant"):
            with st.spinner("Model analiz ediliyor..."):
                try:
                    response_text = call_gemini_chat(st.session_state["chat_history"], system_prompt)
                    st.markdown(response_text)
                    st.session_state["chat_history"].append({"role": "assistant", "content": response_text})
                except Exception as e:
                    if _is_quota_error(e):
                        st.warning(
                            "Gemini API ucretsiz tier dakika limiti asildi (5 istek/dk). "
                            "Lutfen ~1 dakika bekleyip tekrar deneyin. "
                            "Surekli bu hatayi aliyorsaniz Gemini API ucretli plana gecmeyi dusunun."
                        )
                    else:
                        st.error(f"Yanit alinamadi: {e}")
                    # Hatali mesaji gecmise ekleme