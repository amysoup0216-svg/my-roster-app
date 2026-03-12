import streamlit as st
import google.generativeai as genai

# 1. 頁面設定
st.set_page_config(page_title="客服中心智能排班系統", layout="wide")
st.title("📅 客服中心智能排班系統 (v2.1)")

# 2. 側邊欄設定
with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    
    # 這裡我們直接填入你剛才查到的正確 ID
    model_choice = st.selectbox(
        "選擇 AI 模型",
        [
            "models/gemini-3.1-flash-lite-preview", 
            "models/gemini-1.5-flash-latest",
            "models/gemini-pro-latest"
        ]
    )
    st.info(f"目前使用正確 ID: {model_choice}")

# 3. 主要操作區
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📥 資料輸入")
    default_prompt = """你是一位專業的客服排班專家。
請幫我產生下週的排班表。
員工：小明、小華、大強、阿珍。
規則：每天 2 早班 (09-18)、1 晚班 (13-22)。
請務必使用 Markdown 表格格式輸出。"""

    system_prompt = st.text_area("排班規則 Prompt", value=default_prompt, height=300)
    start_button = st.button("🚀 開始自動排班", use_container_width=True)

with col2:
    st.subheader("🗓️ 排班結果預覽")
    if start_button:
        if not api_key:
            st.warning("請先輸入 API Key")
        else:
            try:
                genai.configure(api_key=api_key)
                # 直接使用變數，因為 ID 已經包含 models/ 前綴了
                model = genai.GenerativeModel(model_name=model_choice)
                
                with st.spinner('Gemini 正在計算中...'):
                    response = model.generate_content(system_prompt)
                    st.success("排班完成！")
                    st.markdown(response.text)
            except Exception as e:
                st.error(f"出錯了：{str(e)}")
