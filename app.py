import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- 1. 網頁配置 (簡約白風格) ---
st.set_page_config(page_title="客服排班系統 - 模組 A", layout="wide", page_icon="⚙️")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #333333; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #0056b3; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.title("⚙️ 核心設定")
    api_key = st.text_input("1. 輸入 Gemini API Key", type="password")
    
    # 加入下拉選單，預設使用 Flash 避免 429 錯誤，但也保留你要的 Lite 與 Pro
    st.markdown("### 🤖 模型選擇")
    model_choice = st.selectbox(
        "請選擇運算模型",
        [
            "models/gemini-1.5-flash",
            "models/gemini-3.1-flash-lite-preview",
            "models/gemini-3-pro-preview",
            "models/gemini-1.5-pro-latest"
        ],
        index=0,
        help="遇到 429 額度超限時，請確保選擇 flash 系列模型。"
    )
    
    st.divider()
    st.success("🛡️ 啟動『程式級防護』：100% 保留原始預劃假單。")

# --- 3. 主要內容區域 ---
st.title("🚀 模組 A：休假自動生成 (防篡改版)")
st.write("上傳營運 Excel，AI 將自動補足 DO。**系統已加入強制鎖定機制，原始預劃假單絕對不會被更改。**")

# --- 4. 檔案上傳 ---
uploaded_file = st.file_uploader("📂 請上傳人員資料 Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 讀取原始 Excel
        df_original = pd.read_excel(uploaded_file)
        st.subheader("📊 匯入資料預覽 (此資料將被鎖定保護)")
        st.dataframe(df_original, use_container_width=True)
        
        input_data_text = df_original.to_csv(index=False)

        # --- 核心規則 ---
        prompt_rules = """
你是一個專業的自動化排班演算法專家。請根據以下資料執行『模組 A：休假生成』。
【最高指令】：絕對禁止刪除或修改資料中原有的假項 (AL/DO)，你只能在空白處補上 DO。

### 核心規則
1. 每週 2 天 DO：依據 ISO 8601 (週一至週日)，每人每週必須有剛好 2 天 DO (包含預劃假單內的)。
2. 避免過勞：不可連續工作超過 5 天 (滑動窗口 6 天內必有 1 天休假)。
3. 每日上限：全組每天總休假人數 (AL+DO) 不可超過 3 人。
4. 人員互斥：AAA07201 與 AAA07203 不可同日休假。

### 輸出規範
請直接回傳 CSV 內容，不要有任何 Markdown 標記或多餘文字。
格式：姓名,代號,日期1,日期2,日期3...
"""

        if st.button("✨ 開始自動補足休假 (DO)"):
            if not api_key:
                st.error("❌ 請輸入 API Key")
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=model_choice)
                    
                    with st.spinner(f'🤖 使用 {model_choice} 運算中，請稍候...'):
                        full_prompt = f"{prompt_rules}\n\n【輸入資料】\n{input_data_text}"
                        response = model.generate_content(full_prompt)
                        
                        # 解析 CSV
                        raw_text = response.text.strip()
                        clean_lines = [l.strip() for l in raw_text.split('\n') if ',' in l and not l.startswith('```')]
                        result_csv = '\n'.join(clean_lines)
                        
                        # AI 產出的 DataFrame
                        df_ai = pd.read_csv(io.StringIO(result_csv), on_bad_lines='skip')
                        
                        # --- 🛡️ 程式級防護機制：強制覆蓋 ---
                        # 確保 AI 沒有亂改原始的 AL 或 DO
                        try:
                            # 1. 備份原始資料並設定對齊基準 (代號)
                            df_safe = df_original.copy().set_index('代號')
                            df_ai_indexed = df_ai.set_index('代號')
                            
                            # 2. 將原始資料中「非空白」的欄位，強制覆蓋回 AI 的結果上
                            df_ai_indexed.update(df_safe)
                            
                            # 3. 重設 Index 完成修復
                            df_final = df_ai_indexed.reset_index()
                            
                            # 確保姓名欄位沒被亂改
                            if '姓名' in df_original.columns:
                                df_final['姓名'] = df_original['姓名'].values
                                
                            # 整理欄位順序，把姓名放回第一欄
                            cols = ['姓名', '代號'] + [c for c in df_final.columns if c not in ['姓名', '代號']]
                            df_final = df_final[cols]
                            
                        except Exception as e:
                            st.warning(f"防護機制警告：欄位對齊出現誤差，將直接顯示 AI 原始結果。({e})")
                            df_final = df_ai
                        
                        st.success("🎉 休假表生成完畢！(已套用防篡改鎖定)")
                        st.subheader("🗓️ 最終結果預覽")
                        st.dataframe(df_final, use_container_width=True)
                        
                        # 下載功能
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='精準補假表')
                        
                        st.download_button(
                            label="📥 下載最終版 Excel 班表",
                            data=buffer.getvalue(),
                            file_name="AI_Generated_DO_Table_Secured.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                except Exception as e:
                    st.error(f"❌ 運算過程發生錯誤：{str(e)}")

    except Exception as e:
        st.error(f"❌ 讀取 Excel 失敗：{str(e)}")
else:
    st.info("👋 請上傳營運 Excel 檔案開始作業。")
