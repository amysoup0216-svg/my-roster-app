import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- 1. 網頁配置與美化 ---
st.set_page_config(page_title="AI 排班助理 - 模組 A", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .main { background-color: #f9fbfd; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; background-color: #007bff; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 8px; background-color: #28a745; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.title("⚙️ 系統核心設定")
    api_key = st.text_input("1. 輸入 Gemini API Key", type="password")
    
    # 使用查表後最穩定的 3.1 Flash Lite Preview
    model_choice = "models/gemini-3.1-flash-lite-preview"
    
    st.divider()
    st.markdown("### 🛠️ 目前開發模組")
    st.success("✅ 模組 A：休假自動生成")
    st.info("⏳ 模組 B：休假檢核 (開發中)")
    st.info("⏳ 模組 C：一鍵排班 (開發中)")

# --- 3. 主要內容區域 ---
st.title("🚀 模組 A：休假自動生成 (DO)")
st.write("上傳營運 Excel，AI 將根據**勞基法**與**專案內規**自動補足每週 2 天 DO。")

# --- 4. 檔案上傳與處理 ---
uploaded_file = st.file_uploader("📂 請上傳人員資料 Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 讀取 Excel
        df = pd.read_excel(uploaded_file)
        st.subheader("📊 匯入資料預覽")
        st.dataframe(df, use_container_width=True)
        
        # 轉換為文字以便餵給 AI
        input_data_text = df.to_csv(index=False)

        # --- 定義最強 Prompt 規則 ---
        prompt_rules = f"""
你是一個專業的自動化排班演算法專家。請根據以下資料執行『模組 A：休假生成』。

### 核心規則
1. 每週 2 天 DO：依據 ISO 8601 (週一至週日)，每人每週必須有剛好 2 天 DO (包含預劃假單內的)。
2. 避免過勞：不可連續工作超過 5 天 (滑動窗口 6 天內必有 1 天休假)。
3. 每日上限：全組每天總休假人數 (AL+DO) 不可超過 3 人。
4. 人員互斥：TPP07201 與 TPP07203 不可同日休假。

### 輸出規範
請直接回傳 CSV 內容，不要有任何 Markdown 標記或多餘文字。
格式：姓名,代號,日期1,日期2,日期3... (橫向日期展開)
"""

        if st.button("✨ 開始自動補足休假 (DO)"):
            if not api_key:
                st.error("❌ 請輸入 API Key 才能執行！")
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=model_choice)
                    
                    with st.spinner('🤖 AI 正在精密計算中，請稍候...'):
                        # 發送請求
                        full_prompt = f"{prompt_rules}\n\n【輸入資料】\n{input_data_text}"
                        response = model.generate_content(full_prompt)
                        
                        # --- 強力解析器 (處理 Tokenizing 錯誤) ---
                        raw_text = response.text.strip()
                        
                        # 過濾掉可能存在的 Markdown 代碼塊標籤
                        clean_lines = [
                            line.strip() for line in raw_text.split('\n') 
                            if ',' in line and not line.startswith('```')
                        ]
                        
                        # 重新組合
                        final_csv_string = '\n'.join(clean_lines)
                        
                        # 轉回 DataFrame
                        # 使用 error_bad_lines=False (舊版) 或 on_bad_lines='skip' (新版)
                        output_df = pd.read_csv(io.StringIO(final_csv_string), on_bad_lines='skip')
                        
                        st.success("🎉 休假表生成完畢！")
                        st.subheader("🗓️ 生成結果預覽")
                        st.dataframe(output_df, use_container_width=True)
                        
                        # --- 提供 Excel 下載 ---
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            output_df.to_excel(writer, index=False, sheet_name='AI生成班表')
                        
                        st.download_button(
                            label="📥 下載完整 Excel 班表",
                            data=buffer.getvalue(),
                            file_name="AI_Generated_DO_Table.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                except Exception as e:
                    st.error(f"❌ 運算過程發生錯誤：{str(e)}")
                    with st.expander("查看 AI 回傳原文 (除錯用)"):
                        st.text(response.text if 'response' in locals() else "無回傳")

    except Exception as e:
        st.error(f"❌ 讀取 Excel 失敗：{str(e)}")
else:
    st.info("👋 歡迎使用！請先從上方上傳營運 Excel 檔案開始作業。")

# --- 5. 頁尾說明 ---
st.divider()
st.caption("Vibe Coding © 2026 | 專為 Amy 團隊設計之智能排班助手")
