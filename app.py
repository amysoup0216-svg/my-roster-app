import streamlit as st
import pandas as pd
import io

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="客服排班系統", layout="wide", page_icon="📅")

st.markdown("""
    <style>
    .main { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 側邊欄：導航 ---
with st.sidebar:
    st.title("網訊 (Telexpress)")
    st.caption("AI 輔助營運管理工具 v1.0")
    st.divider()
    
    current_module = st.radio(
        "切換作業模組",
        ["模組 A：休假生成", "模組 B：休假檢核", "模組 C：一鍵排班"]
    )
    
    st.divider()
    api_key = st.text_input("輸入 Gemini API Key", type="password")

# --- 3. 核心功能函數：日期解析 (修正錯誤的核心) ---
def get_date_columns(df):
    """從 DataFrame 中篩選出屬於日期的欄位，跳過姓名與代號"""
    date_cols = []
    for col in df.columns:
        # 排除已知的非日期文字
        if col in ['姓名', '代號', 'unresolved_issues']:
            continue
        try:
            # 嘗試解析，如果成功則是日期欄位
            pd.to_datetime(col)
            date_cols.append(col)
        except:
            continue
    return date_cols

# --- 4. 模組內容路由 ---

if current_module == "模組 A：休假生成":
    st.title("🚀 模組 A：休假自動生成 (DO)")
    st.info("功能：讀取預劃假單，自動補足每週 2 天 DO。")
    # 此處保留您之前的模組 A 邏輯代碼...
    uploaded_file_a = st.file_uploader("📂 上傳原始 Excel", type=["xlsx"], key="file_a")

elif current_module == "模組 B：休假檢核":
    st.title("⚖️ 模組 B：休假規則檢核")
    st.write("上傳班表，系統將自動檢查是否符合 **勞基法 (每週2天DO / 不連續工作>5天)**。")
    
    uploaded_file_b = st.file_uploader("📂 上傳待檢核的班表 (.xlsx)", type=["xlsx"], key="file_b")
    
    if uploaded_file_b:
        try:
            df_check = pd.read_excel(uploaded_file_b)
            # 強制轉為字串避免解析出錯
            df_check.columns = df_check.columns.astype(str)
            
            # 自動偵測日期欄位 (修正您遇到的錯誤)
            date_cols = get_date_columns(df_check)
            
            st.subheader("📋 班表預覽")
            st.dataframe(df_check, use_container_width=True)
            
            if st.button("🔍 開始執行規則檢查"):
                st.write("### 🚨 檢核報告 (初步測試)")
                
                # 範例邏輯：簡單檢查每日休假人數
                daily_counts = {}
                for col in date_cols:
                    # 計算該日休假(AL/DO)人數
                    leave_count = df_check[col].isin(['AL', 'DO']).sum()
                    daily_counts[col] = leave_count
                
                # 顯示紅綠燈
                cols_display = st.columns(min(len(date_cols), 5))
                for i, (date, count) in enumerate(list(daily_counts.items())[:5]): # 僅示範前5天
                    with cols_display[i % 5]:
                        if count > 3:
                            st.error(f"❌ {date}\n休假 {count} 人 (超標)")
                        else:
                            st.success(f"✅ {date}\n休假 {count} 人")
                
                st.warning("提示：更完整的『不連續工作 5 天』與『週休二日』檢核邏輯開發中...")
                
        except Exception as e:
            st.error(f"解析失敗：{e}")

elif current_module == "模組 C：一鍵排班":
    st.title("🧩 模組 C：班別自動指派")
    st.write("功能：在休假確定的情況下，填入早、中、晚班別。")
    uploaded_file_c = st.file_uploader("📂 上傳已確認休假的班表", type=["xlsx"], key="file_c")
    if uploaded_file_c:
        st.success("檔案已就緒，等待班別規則設定。")
