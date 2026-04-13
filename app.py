import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import re

# --- 1. 系統初始化與快取設定 ---
st.set_page_config(page_title="網訊 (Telexpress) 智能排班系統", layout="wide", page_icon="📅")

# 初始化系統暫存空間 (讓 A -> B -> C 資料流動)
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

# --- 2. 側邊欄：導航與設定 ---
with st.sidebar:
    st.title("⚙️ Telexpress 排班系統")
    current_module = st.radio(
        "📍 選擇作業模組",
        ["模組 A：休假生成 (DO)", "模組 B：休假檢核", "模組 C：一鍵排班"]
    )
    
    st.divider()
    api_key = st.text_input("🔑 輸入 Gemini API Key", type="password")
    model_choice = st.selectbox(
        "🤖 選擇運算模型",
        ["models/gemini-3.1-flash-lite-preview", "models/gemini-1.5-flash", "models/gemini-3-pro-preview"],
        index=0
    )
    
    if st.session_state.system_cache_df is not None:
        st.success("💾 系統已備有暫存班表資料")
        if st.button("🗑️ 清除暫存"):
            st.session_state.system_cache_df = None
            st.rerun()

# --- 3. 模組內容路由 ---

# ==========================================
# 🚀 模組 A：休假自動生成 (座標填空法)
# ==========================================
if current_module == "模組 A：休假生成 (DO)":
    st.title("🚀 模組 A：休假自動生成")
    st.write("上傳預排假單，系統將自動補足 DO。完成後將自動暫存，供後續模組使用。")
    
    uploaded_file_a = st.file_uploader("📂 上傳人員資料 Excel (.xlsx)", type=["xlsx"], key="file_a")
    
    if uploaded_file_a:
        df_a = pd.read_excel(uploaded_file_a)
        df_a.columns = df_a.columns.astype(str)
        st.subheader("📊 原始資料預覽")
        st.dataframe(df_a, use_container_width=True)
        
        prompt_rules_a = """
        你是自動排班專家。請依據 ISO 週次(週一至週日)，為每人每週補足剛好 2 天 DO。
        不可連續工作超過 5 天。每日休假人數(AL+DO)不可超過 3 人。TPP07201 與 TPP07203 不可同日休假。
        請只回傳需要「新增 DO」的座標清單，格式為 CSV：代號,新增日期
        (日期請用原始格式如 2026-01-05，包裹在 ```csv 標籤內)
        """
        
        if st.button("✨ 執行補假 (模組 A)"):
            if not api_key: st.error("請輸入 API Key")
            else:
                with st.spinner('計算補假座標中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=model_choice)
                        # 輔助 AI 辨識日期
                        df_ai_input = df_a.copy()
                        df_ai_input.columns = [f"{col} ({['一','二','三','四','五','六','日'][pd.to_datetime(col).weekday()]})" if '-' in col else col for col in df_ai_input.columns]
                        
                        response = model.generate_content(f"{prompt_rules_a}\n\n【輸入資料】\n{df_ai_input.to_csv(index=False)}")
                        
                        match = re.search(r'```csv\n(.*?)\n```', response.text, re.DOTALL | re.IGNORECASE)
                        csv_content = match.group(1).strip() if match else response.text
                        clean_lines = [l.strip() for l in csv_content.split('\n') if ',' in l and '新增日期' not in l]
                        
                        df_final_a = df_a.copy()
                        success_count = 0
                        for line in clean_lines:
                            try:
                                emp_id, date_str = line.split(',')
                                emp_id = emp_id.strip(); date_str = date_str.strip()
                                row_idx = df_final_a.index[df_final_a['代號'] == emp_id].tolist()
                                if row_idx and date_str in df_final_a.columns:
                                    r = row_idx[0]
                                    if pd.isna(df_final_a.at[r, date_str]) or str(df_final_a.at[r, date_str]).strip() == '':
                                        df_final_a.at[r, date_str] = 'DO'
                                        success_count += 1
                            except: continue
                        
                        st.success(f"🎉 補假完成！新增了 {success_count} 個 DO。資料已暫存。")
                        st.session_state.system_cache_df = df_final_a.copy()
                        st.dataframe(df_final_a, use_container_width=True)
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
