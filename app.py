import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import re

# --- 1. 系統初始化與快取設定 ---
st.set_page_config(page_title="網訊 (Telexpress) 智能排班系統", layout="wide", page_icon="📅")

if 'system_cache_df' not in st.session_state:
    st.session_state.system_cache_df = None

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #333333; color: white; font-weight: bold; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #0056b3; color: white; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.title("⚙️ Telexpress 排班系統")
    current_module = st.radio("📍 選擇作業模組", ["模組 A：休假生成 (DO)", "模組 B：休假檢核", "模組 C：一鍵排班"])
    st.divider()
    api_key = st.text_input("🔑 輸入 Gemini API Key", type="password")
    model_choice = st.selectbox("🤖 選擇運算模型", ["models/gemini-1.5-pro", "models/gemini-1.5-flash"], index=0)
    if st.session_state.system_cache_df is not None:
        if st.button("🗑️ 清除暫存資料"):
            st.session_state.system_cache_df = None
            st.rerun()

# ==========================================
# 🚀 模組 A：休假自動生成 (座標填空法 - 強化版)
# ==========================================
if current_module == "模組 A：休假生成 (DO)":
    st.title("🚀 模組 A：休假自動生成")
    st.write("上傳預排假單，系統將自動計算並補足 DO。")
    
    uploaded_file_a = st.file_uploader("📂 上傳人員資料 Excel (.xlsx)", type=["xlsx"], key="file_a")
    
    if uploaded_file_a:
        df_a = pd.read_excel(uploaded_file_a)
        # 強制清理所有欄位標題與內容的空白
        df_a.columns = [str(c).strip() for c in df_a.columns]
        st.subheader("📊 原始資料預覽")
        st.dataframe(df_a, use_container_width=True)
        
        # 升級後的 Prompt：強調日期格式與 CSV 結構
        prompt_rules_a = """
        你是自動排班專家。請依據以下規則計算：
        1. 每人每週(週一至週日)必須有剛好 2 天 DO (包含原本已有的)。
        2. 不可連續工作超過 5 天。
        3. 每日全組休假人數(AL+DO)上限為 3 人。
        4. AAA07201 與 AAA07203 不可同日休假。

        請「只」輸出需要新增的 DO 座標，格式嚴格如下(包裹在 ```csv 內)：
        ```csv
        代號,新增日期
        TPP07201,2026-01-05
        TPP07202,2026-01-06
        ```
        注意：日期格式必須與輸入資料一致(如 2026-01-01)，不要包含星期幾。
        """
        
        if st.button("✨ 執行補假 (模組 A)"):
            if not api_key: st.error("請輸入 API Key")
            else:
                with st.spinner('AI 正在計算補假座標中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=model_choice)
                        
                        # 幫 AI 加上星期標籤輔助計算
                        df_ai_input = df_a.copy()
                        new_cols_ai = []
                        for col in df_ai_input.columns:
                            try:
                                dt = pd.to_datetime(col)
                                wk = ["一","二","三","四","五","六","日"][dt.weekday()]
                                new_cols_ai.append(f"{col}({wk})")
                            except: new_cols_ai.append(col)
                        df_ai_input.columns = new_cols_ai
                        
                        response = model.generate_content(f"{prompt_rules_a}\n\n【輸入資料】\n{df_ai_input.to_csv(index=False)}")
                        
                        # 解析 CSV
                        res_text = response.text
                        csv_match = re.search(r'```csv\n(.*?)\n```', res_text, re.DOTALL | re.IGNORECASE)
                        csv_data = csv_match.group(1).strip() if csv_match else ""
                        
                        if not csv_data:
                            st.warning("AI 判定目前班表已符合規範，無需新增 DO。")
                            st.expander("查看分析原文").text(res_text)
                        else:
                            df_final_a = df_a.copy()
                            success_count = 0
                            lines = csv_data.split('\n')
                            
                            for line in lines:
                                if ',' in line and '代號' not in line:
                                    parts = line.split(',')
                                    emp_id = parts[0].strip()
                                    date_val = parts[1].strip()
                                    
                                    # 強化比對邏輯：過濾代號與日期
                                    row_mask = df_final_a['代號'].astype(str).str.strip() == emp_id
                                    if row_mask.any() and date_val in df_final_a.columns:
                                        r_idx = df_final_a.index[row_mask][0]
                                        # 只有在空白格才填入
                                        cell_val = str(df_final_a.at[r_idx, date_val]).strip().upper()
                                        if cell_val in ['NAN', '', 'NONE']:
                                            df_final_a.at[r_idx, date_val] = 'DO'
                                            success_count += 1
                            
                            if success_count > 0:
                                st.success(f"🎉 補假完成！成功新增 {success_count} 個 DO。資料已存入系統暫存。")
                                st.session_state.system_cache_df = df_final_a.copy()
                                st.dataframe(df_final_a, use_container_width=True)
                            else:
                                st.error("❌ 雖然 AI 產出了座標，但系統比對失敗（可能是日期格式不符）。")
                                with st.expander("查看 AI 產出的原始座標"):
                                    st.text(csv_data)

                    except Exception as e: st.error(f"錯誤：{e}")


# ==========================================
# ⚖️ 模組 B：休假檢核 (防呆雷達)
# ==========================================
elif current_module == "模組 B：休假檢核":
    st.title("⚖️ 模組 B：休假規則檢核")
    st.write("掃描班表是否違反勞基法與專案內規。")
    
    data_source_b = "上傳新檔案"
    if st.session_state.system_cache_df is not None:
        data_source_b = st.radio("📂 請選擇資料來源：", ["沿用系統暫存檔案 (來自模組A)", "上傳新檔案 Excel"])
    
    df_b = None
    if "沿用" in data_source_b:
        df_b = st.session_state.system_cache_df
    else:
        uploaded_file_b = st.file_uploader("上傳待檢核的班表 (.xlsx)", type=["xlsx"], key="file_b")
        if uploaded_file_b:
            df_b = pd.read_excel(uploaded_file_b)
            df_b.columns = df_b.columns.astype(str)

    if df_b is not None:
        st.dataframe(df_b, use_container_width=True)
        prompt_b = """
你是排班規範檢查引擎，禁止推測、禁止多餘文字，只能依資料逐日逐週精準檢查。

1. 星期計算方式：週一～週日為一週。
2. 週規則：每位人員每週 DO 必須 = 2（不可多、不可少）。
3. 日規則：每日所有人 AL+DO 總人數≤ 3。
4. 每位人員非 DO連續天數<6
5. 僅依提供的排班內容計算，不可跨週、不合併週、不自動補假。
6. 回覆必須完整列出「所有不符合規範的項目」，格式如下：

（一）每週 DO≠ 2 的人員
- 人員姓名：週期（MM/DD–MM/DD），該週 DO = X

（二）每日 AL+DO > 3 的日期
- MM/DD：AL+DO = X

（三）非 DO連續天數> 5的人員及日期
- 人員姓名：區間（MM/DD-MM/DD），非DO連續天數 = X
"""
        if st.button("🔍 開始 AI 檢核"):
            if not api_key: st.error("請輸入 API Key")
            else:
                with st.spinner('掃描中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=model_choice)
                        
                        # --- 🛡️ 安全日期標記 (修正上個版本的 Bug) ---
                        df_check = df_b.copy()
                        new_cols = []
                        for c in df_check.columns:
                            try:
                                dt = pd.to_datetime(c)
                                wk = ["一","二","三","四","五","六","日"][dt.weekday()]
                                new_cols.append(f"{c} ({wk})")
                            except: new_cols.append(c)
                        df_check.columns = new_cols
                        
                        response = model.generate_content(f"{prompt_b}\n\n【排班資料】\n{df_check.to_csv(index=False)}")
                        st.markdown("### 📋 檢核結果報告")
                        st.info(response.text)
                        st.session_state.system_cache_df = df_b.copy() # 檢核完也更新至暫存
                    except Exception as e: st.error(f"檢核錯誤：{e}")

# ==========================================
# 🧩 模組 C：一鍵排班 (班別指派)
# ==========================================
elif current_module == "模組 C：一鍵排班":
    st.title("🧩 模組 C：一鍵排班 (班別指派)")
    st.write("在休假確定的基礎上，根據優先順序自動填入早晚班別。")
    
    data_source_c = "上傳新檔案"
    if st.session_state.system_cache_df is not None:
        data_source_c = st.radio("📂 請選擇資料來源：", ["沿用系統暫存檔案 (來自模組A/B)", "上傳新檔案 Excel"])
    
    df_c = None
    if "沿用" in data_source_c:
        df_c = st.session_state.system_cache_df
    else:
        uploaded_file_c = st.file_uploader("上傳休假已確定的班表 (.xlsx)", type=["xlsx"], key="file_c")
