import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import re

# --- 1. 系統初始化與快取設定 ---
st.set_page_config(page_title="網訊 (Telexpress) 智能排班系統", layout="wide", page_icon="📅")

# 初始化系統暫存空間 (輸送帶)
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
    
    # 顯示暫存狀態
    st.divider()
    if st.session_state.system_cache_df is not None:
        st.success("💾 系統已備有暫存班表資料")
    else:
        st.caption("⚪ 目前系統無暫存資料")

# ==========================================
# 🚀 模組 A：休假自動生成 (座標填空法)
# ==========================================
if current_module == "模組 A：休假生成 (DO)":
    st.title("🚀 模組 A：休假自動生成")
    st.write("上傳預排假單，系統將自動計算並補足 DO。完成後將自動暫存，供後續模組使用。")
    
    uploaded_file_a = st.file_uploader("📂 上傳人員資料 Excel (.xlsx)", type=["xlsx"])
    
    if uploaded_file_a:
        df_a = pd.read_excel(uploaded_file_a)
        df_a.columns = df_a.columns.astype(str)
        st.dataframe(df_a, use_container_width=True)
        
        prompt_rules_a = """
        你是自動排班專家。請依據 ISO 週次，為每人每週補足剛好 2 天 DO。
        不可連續工作超過 5 天。每日休假人數不可超過 3 人。TPP07201 與 TPP07203 不可同日休假。
        請只回傳需要「新增 DO」的座標清單，格式為 CSV：代號,新增日期
        """
        
        if st.button("✨ 執行補假 (模組 A)"):
            if not api_key: st.error("請輸入 API Key")
            else:
                with st.spinner('計算補假座標中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=model_choice)
                        response = model.generate_content(f"{prompt_rules_a}\n\n【輸入資料】\n{df_a.to_csv(index=False)}")
                        
                        match = re.search(r'```csv\n(.*?)\n```', response.text, re.DOTALL | re.IGNORECASE)
                        csv_content = match.group(1).strip() if match else response.text
                        clean_lines = [l.strip() for l in csv_content.split('\n') if ',' in l and '新增日期' not in l]
                        
                        df_final_a = df_a.copy()
                        for line in clean_lines:
                            try:
                                emp_id, date_str = line.split(',')
                                row_idx = df_final_a.index[df_final_a['代號'] == emp_id.strip()].tolist()
                                if row_idx and date_str.strip() in df_final_a.columns:
                                    r = row_idx[0]
                                    if pd.isna(df_final_a.at[r, date_str.strip()]) or str(df_final_a.at[r, date_str.strip()]).strip() == '':
                                        df_final_a.at[r, date_str.strip()] = 'DO'
                            except: continue
                        
                        st.success("🎉 補假完成！資料已存入系統暫存，可直接切換至【模組 B】。")
                        st.session_state.system_cache_df = df_final_a.copy() # 寫入快取
                        st.dataframe(df_final_a, use_container_width=True)
                        
                    except Exception as e: st.error(f"錯誤：{e}")

# ==========================================
# ⚖️ 模組 B：休假檢核 (防呆雷達)
# ==========================================
elif current_module == "模組 B：休假檢核":
    st.title("⚖️ 模組 B：休假規則檢核")
    st.write("掃描班表是否違反勞基法與專案內規。")
    
    # 資料來源選擇
    data_source = "上傳新檔案"
    if st.session_state.system_cache_df is not None:
        data_source = st.radio("📂 請選擇資料來源：", ["沿用系統暫存檔案 (來自模組A)", "上傳新檔案 Excel"])
    
    df_b = None
    if "沿用" in data_source:
        df_b = st.session_state.system_cache_df
        st.info("已載入暫存資料，可直接檢核。")
        st.dataframe(df_b, use_container_width=True)
    else:
        uploaded_file_b = st.file_uploader("上傳待檢核的班表 (.xlsx)", type=["xlsx"])
        if uploaded_file_b:
            df_b = pd.read_excel(uploaded_file_b)
            st.dataframe(df_b, use_container_width=True)

    if df_b is not None:
        # 你提供的精準 Prompt
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
                with st.spinner('雷達掃描中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=model_choice)
                        # 幫 AI 加上星期標記，提升檢核準確率
                        df_check = df_b.copy()
                        df_check.columns = [f"{col} ({['一','二','三','四','五','六','日'][pd.to_datetime(col).weekday()]})" if pd.to_datetime(col, errors='ignore') is not col else col for col in df_check.columns]
                        
                        response = model.generate_content(f"{prompt_b}\n\n【排班資料】\n{df_check.to_csv(index=False)}")
                        
                        st.success("✅ 檢核報告產出完畢！")
                        st.markdown("### 📋 檢核結果")
                        st.info(response.text) # 顯示你要求的純文字格式
                        
                        # 讓主管決定是否將這份資料存入快取給模組C
                        if "沿用" not in data_source:
                             st.session_state.system_cache_df = df_b.copy()
                             st.caption("提示：此份資料已存入暫存，可接續使用模組 C。")
                             
                    except Exception as e: st.error(f"錯誤：{e}")

# ==========================================
# 🧩 模組 C：一鍵排班 (班別指派)
# ==========================================
elif current_module == "模組 C：一鍵排班":
    st.title("🧩 模組 C：一鍵排班 (班別指派)")
    st.write("在休假確定的基礎上，根據專案優先順序與人員職能，自動填入早晚班別。")
    
    data_source_c = "上傳新檔案"
    if st.session_state.system_cache_df is not None:
        data_source_c = st.radio("📂 請選擇資料來源：", ["沿用系統暫存檔案 (來自模組A/B)", "上傳新檔案 Excel"])
    
    df_c = None
    if "沿用" in data_source_c:
        df_c = st.session_state.system_cache_df
        st.info("已載入暫存休假表，準備進行班別指派。")
    else:
        uploaded_file_c = st.file_uploader("上傳已確認休假的班表 (.xlsx)", type=["xlsx"])
        if uploaded_file_c:
            df_c = pd.read_excel(uploaded_file_c)
            df_c.columns = df_c.columns.astype(str)

    if df_c is not None:
        st.dataframe(df_c, use_container_width=True)
        
        # 你提供的排班 Prompt
        prompt_c = """
你是排班引擎，只輸出 CSV。
AL/DO 不可改，僅補空白。日期由左至右逐日處理，已填即鎖。

班別 A08,A09,A10,A12,A14,A21,A23
A08/A09/A10/A12/A14：陳威宇,楊芮樺,李郁文,張暐,莊巧寧,陳邦煒,林家倩
A21/A23：李安巧,賴雨青

每日：
先補 A08→A12→A14→A23。
若未滿 4，禁止 A09/A10/A21。
滿 4 才可補 A09/A10/A21。

只輸出完整 CSV，保留原有的 AL 與 DO。
"""
        if st.button("🚀 執行一鍵排班"):
            if not api_key: st.error("請輸入 API Key")
            else:
                with st.spinner('運算班別矩陣中...'):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel(model_name=model_choice)
                        response = model.generate_content(f"{prompt_c}\n\n【休假表資料】\n{df_c.to_csv(index=False)}")
                        
                        # 擷取 CSV
                        match = re.search(r'```csv\n(.*?)\n```', response.text, re.DOTALL | re.IGNORECASE)
                        csv_content = match.group(1).strip() if match else response.text
                        
                        # 將 AI 產出的文字轉為 DataFrame
                        df_ai = pd.read_csv(io.StringIO(csv_content), on_bad_lines='skip')
                        df_ai.columns = df_ai.columns.astype(str)
                        
                        # --- 🛡️ 絕對防護：只填補空缺，不覆蓋 AL/DO ---
                        df_final_c = df_c.copy().set_index('姓名')
                        df_ai_indexed = df_ai.set_index('姓名')
                        
                        # 將 df_final_c 中的空值 (NaN) 用 df_ai 的結果填補
                        df_final_c = df_final_c.replace(r'^\s*$', pd.NA, regex=True) # 確保空白字串被視為空值
                        df_final_c = df_final_c.combine_first(df_ai_indexed)
                        
                        df_final_c = df_final_c.reset_index()
                        
                        # 整理欄位順序
                        cols = ['姓名', '代號'] + [c for c in df_final_c.columns if c not in ['姓名', '代號']]
                        df_final_c = df_final_c[cols]
                        
                        st.success("🎉 排班完成！(原 AL/DO 已受程式級保護，未被覆蓋)")
                        st.dataframe(df_final_c, use_container_width=True)
                        
                        # 產出最終下載檔案
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_final_c.to_excel(writer, index=False, sheet_name='WFMS班表上傳')
                        
                        st.download_button(
                            label="📥 下載 WFMS 最終上傳格式",
                            data=buffer.getvalue(),
                            file_name="Final_Shift_Schedule.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                    except Exception as e: st.error(f"錯誤：{str(e)}\n\n(AI 回傳格式可能異常，請重試)")
