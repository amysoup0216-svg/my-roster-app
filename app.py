import streamlit as st
import google.generativeai as genai

# --- 1. 網頁頁面設定 (The Vibe) ---
st.set_page_config(page_title="客服中心智能排班系統", layout="wide")

st.title("📅 客服中心智能排班系統")
st.markdown("---")

# --- 2. 側邊欄設定 (設定區) ---
with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    st.info("請向工程師索取 API Key 或是從 Google AI Studio 取得。")

# --- 3. 主要操作區 (左側輸入、右側輸出) ---
col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📥 資料輸入")
    
    # 預設一段排班規則，方便你直接測試
    default_prompt = """你是一位專業的客服排班專家。
請根據以下規則產生 3 月份第一週的排班表：
1. 每天需有 2 名早班 (09:00-18:00)，1 名晚班 (13:00-22:00)。
2. 員工名單：小明、小華、大強、阿珍。
3. 每人每週至少休 2 天，且不能連續工作超過 5 天。

請以『表格』形式輸出結果。"""

    system_prompt = st.text_area("排班規則 Prompt", value=default_prompt, height=300)
    
    start_button = st.button("🚀 開始自動排班", use_container_width=True)

with col2:
    st.subheader("🗓️ 排班結果預覽")
    
    if start_button:
        if not api_key:
            st.warning("請在左側輸入 API Key 才能開始喔！")
        else:
            try:
                # 設定 Gemini
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner('Gemini 正在計算最佳排班組合...'):
                    # 呼叫 API
                    response = model.generate_content(system_prompt)
                    
                    # 顯示結果
                    st.success("排班完成！")
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"出錯了：{str(e)}")
    else:
        st.write("請在左側設定規則後，按下按鈕開始。")

# --- 4. 底部說明 ---
st.markdown("---")
st.caption("v1.0 - 使用 Streamlit + Gemini API 驅動")