import streamlit as st
import google.generativeai as genai
import os

def build_portfolio_context(summary: dict) -> str:
    """
    API'den (veya backend'den) gelen özet sözlüğünü sistem prompt'unda
    kullanılabilecek okunabilir bir metne dönüştürür.
    """
    # Gelen summary dict'inin içeriğini beklenen string formatına dönüştürüyoruz.
    # Güvenli dict okuması (.get) kullanarak olası anahtar hatalarını önlüyoruz.
    
    allocations = summary.get("allocation", {})
    alloc_str = ", ".join([f"{k} (%{v})" for k, v in allocations.items()]) if allocations else "Veri yok"
    
    context_lines = [
        f"Portföy: {alloc_str}",
        f"Portföy VaR (95%): {summary.get('var_95', 'Veri yok')}",
        f"Portföy Volatilite: {summary.get('volatility', 'Veri yok')}",
        f"Çeşitlendirme Etkisi: {summary.get('diversification_effect', 'Veri yok')}",
        f"Yüksek Korelasyonlu Çiftler: {summary.get('high_corr_pairs', 'Veri yok')}"
    ]
    
    return "\n".join(context_lines)


def get_system_prompt(context: str) -> str:
    """
    Sabit sistem promptu ile dinamik bağlamı birleştirir.
    """
    return f"""Sen bir portföy risk analizi asistanısın. 
Kullanıcıya yalnızca sana sağlanan model çıktılarına ve istatistiklere dayanarak yanıt ver. 
Kesinlikle alım-satım tavsiyesi vermezsin, sadece kendi modelinin çıktılarını yorumlarsın.

Kullanıcının o an incelediği portföyün güncel verileri (Bağlam):
{context}
"""


def call_gemini(messages: list, system: str) -> str:
    """
    Google Generative AI (Gemini) SDK'sını kullanarak chat geçmişi ile birlikte çağrı yapar.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY ortam değişkeni bulunamadı.")
        
    genai.configure(api_key=api_key)
    
    # Gemini modeli ve sistem promptunun yapılandırılması
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system
    )
    
    # Streamlit chat formatını [{"role": "user", "content": "..."}, ...] 
    # Gemini SDK formatına çeviriyoruz. Son mesaj (yeni atılan mesaj) hariç geçmişi oluşturuyoruz.
    gemini_history = []
    for msg in messages[:-1]:
        # Streamlit'teki "assistant" rolünün Gemini karşılığı "model"dir.
        role = "model" if msg["role"] == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
        
    # Geçmiş ile yeni bir sohbet oturumu başlat
    chat = model.start_chat(history=gemini_history)
    
    # Listedeki son eleman, kullanıcının yeni attığı sorudur
    new_message = messages[-1]["content"]
    
    # Yanıtı üret
    response = chat.send_message(new_message)
    return response.text


def render_portfolio_chat(summary: dict):
    """
    Streamlit chat arayüzünü ekrana çizen ana fonksiyondur.
    """
    st.subheader("🤖 Portföy Risk Asistanı")
    st.markdown("Güncel risk modellemeleri hakkında sorular sorabilirsiniz.")

    # Konuşma geçmişi için session state başlatma
    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Geçmiş mesajları ekrana yazdırma
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Sohbet input barı
    if prompt := st.chat_input("Örn: Portföydeki yüksek korelasyonlu çiftler riskimi nasıl etkiliyor?"):
        # 1. Kullanıcı mesajını geçmişe ekle ve ekranda göster
        st.session_state["chat_history"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. Bağlamı ve sistem promptunu hazırla
        context = build_portfolio_context(summary)
        system_prompt = get_system_prompt(context)

        # 3. Gemini'ye istek at ve yanıtı ekranda göster
        with st.chat_message("assistant"):
            with st.spinner("Model analiz ediliyor..."):
                try:
                    response_text = call_gemini(st.session_state["chat_history"], system_prompt)
                    st.markdown(response_text)
                    
                    # 4. Asistanın cevabını geçmişe kaydet
                    st.session_state["chat_history"].append({"role": "assistant", "content": response_text})
                except Exception as e:
                    st.error(f"API Çağrısı sırasında bir hata oluştu: {e}")