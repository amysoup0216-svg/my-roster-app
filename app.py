import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- 1. 網頁基本設定 ---
st.set_page_config(
    page_title="客服中心智能排班系統",
    page_icon="📅",
    layout="wide"
)

# 套用一點簡單的 CSS 讓介面更漂亮
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 側邊欄 (Sidebar) ---
with st.sidebar:
    st.title("⚙️ 設定中心")
    api_key = st.text_input("1. 輸入 Gemini API Key", type="password", help="請輸入您的 Google AI Studio API Key")
    
    model_choice = st.selectbox(
        "2. 選擇 AI 模型",
        [
            "gemini-3.1-flash-lite", 
            "gemini-1.5-flash", 
            "gemini-1.5-pro"
        ],
        index=0,
        help="3.1 Flash Lite 是目前最快且適合排班的模型"
    )
    
    st.divider()
    st.markdown("""
    **💡 使用小秘訣：**
    1. 貼上排班規則。
    2. 點擊『開始自動排班』。
    3. 若結果不滿意，可在規則中增加『約束條件』。
    """)

# --- 3. 主要內容區 ---
st.title("📅 客服中心智能排班系統")
st.info("這是一個協助客服主管快速產出初步班表的小工具。")

col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.subheader("📥 排班規則與資料")
    
    # 這裡放你原本寫好的 Prompt 範本
    default_prompt = """你是一位專業的客服排班專家。
請幫我產生下週的排班表（週一至週日）。

【員工名單】
小明、小華、大強、阿珍。

【排班需求】
1. 每天需有 2 名早班 (09:00-18:00)，1 名晚班 (13:00-22:00)。
2. 每位員工每週必須休息 2 天。
3. 盡量避免讓員工連續值兩天晚班。

【輸出格式】
請務必以 Markdown 表格呈現，包含：日期、星期、早班人員、晚班人員、備註。"""

    system_prompt = st.text_area(
        "請在此輸入或修改您的排班規則：",
        value=default_prompt,
        height=400
    )
    
    start_button = st.button("🚀 開始自動排班")

with col2:
    st.subheader("🗓️ 產出結果預覽")
    
    if start_button:
        if not api_key:
            st.error("⚠️ 請先在左側選單輸入 API Key！")
        else:
            try:
                # 設定 API
                genai.configure(api_key=api_key)
                
                # 建立模型實例
                # 這裡使用 models/ 前綴確保路徑正確
                model = genai.GenerativeModel(model_name=f"models/{model_choice}")
                
                with st.spinner(f'正在使用 {model_choice} 運算中...'):
                    # 發送請求
                    response = model.generate_content(system_prompt)
                    
                    # 顯示結果
                    st.success("✨ 排班完成！")
                    st.markdown(response.text)
                    
                    # 提供簡單的備註功能
                    st.divider()
                    st.caption("您可以直接複製上方的表格內容到 Excel 中貼上。")
                    
            except Exception as e:
                # 擷取常見錯誤並給予白話建議
                error_msg = str(e)
                if "403" in error_msg:
                    st.error("錯誤：API Key 權限不足或無效。")
                elif "404" in error_msg:
                    st.error(f"錯誤：找不到模型 {model_choice}。請確認您的 API 是否支援此模型。")
                else:
                    st.error(f"連線出錯了：{error_msg}")
    else:
        st.write("等待指令中... 請設定好規則後點擊左側按鈕。")

# --- 4. 頁尾 ---
st.divider()
st.center = st.caption("© 2026 客服中心排班助手 | Vibe Coding Powered by Gemini")
