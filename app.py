import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- 1. 網頁配置 ---
st.set_page_config(page_title="AI 排班助理 - 模組 A 專業版", layout="wide", page_icon="⚖️")

# --- 2. 側邊欄設定 ---
with st.sidebar:
    st.title("⚙️ 核心設定")
    api_key = st.text_input("1. 輸入 Gemini API Key", type="password")
    
    # 讓你可以設定想要使用的 API 版本
    st.markdown("### 🤖 模型設定")
    model_choice = st.text_input("API 模型版本", value="models/gemini-3-pro-preview")
    
    st.divider()
    st.info("💡 目前版本：嚴格遵循預劃假單，不允許變動原始假項。")

# --- 3. 主要內容區域 ---
st.title("🚀 模組 A：休假自動生成 (嚴格邏輯版)")
st.write("本系統將根據匯入的 Excel 補齊 DO，**原始預劃假單 (AL/DO) 將會被視為固定座標，絕對不會更動。**")

# --- 4. 檔案上傳 ---
uploaded_file = st.file_uploader("📂 上傳營運 Excel 檔案 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        st.subheader("📊 匯入資料預覽")
        st.dataframe(df, use_container_width=True)
        
        input_data_text = df.to_csv(index=False)

        # --- 核心規則 (完全採用你驗證過的內容) ---
        # 加入一條最高指令：禁止變動原始假單
        strict_instruction = "### 重要最高指令：\n絕對禁止刪除、修改或移動資料中 `pre_assigned_leaves` 已指定的任何假項 (AL 或 DO)。你的任務僅是填補缺少的 DO，原始假單必須原封不動地保留在輸出結果中。\n\n"

        core_rules = """
### 核心規則 (Rules & Constraints)
你必須依照優先順序遵守以下規則。若發生衝突，法規 (1 & 2) 優先於 專案規定 (3 & 4)，但請盡全力滿足所有條件。

1. 法規：週休二日 (Weekly DO Quota)
* 定義：一週的定義為 週一至週日 (ISO 8601)。
* 要求：每位員工在每一週內，必須剛好有 2 個 DO (Day Off)。
* 注意：計算時必須包含員工 pre_assigned_leaves 中已經指定的 DO。你需要補足剩餘的 DO 以達到每週 2 天。

2. 法規：避免過勞 (Max Work Streak)
* 要求：員工不得連續工作超過 5 天。
* 邏輯：意即在任何連續 6 天的滑動窗口內，至少必須有 1 天是休假 (包含 DO 或 AL)。

3. 專案規定：每日休假上限 (Daily Leave Cap)
* 要求：每一天專案的總休假人數（包含所有員工的 AL + DO 加總）不可超過 3 人。
* 邏輯：在安排 DO 時，若當天已有 3 人休假 (包含預劃的)，則不可再安排該日休假。

4. 專案規定：人員互斥休假 (Conflict Groups)
* 要求：conflict_groups：["AAA07201", "AAA07203"]。同一組內的員工，不可在同一天休假 (包含 AL 與 DO)。
* 邏輯：
    * 在安排 DO 時，若該員屬於某個互斥組，必須檢查組內其他成員當天是否已排休。
    * 若組內成員 A 已有預劃假單 (AL/DO)，則成員 B 絕對不可被安排在該日產生新的 DO。
    * 若產生衝突且無法避開，請優先記錄於 unresolved_issues。

### 執行邏輯 (Step-by-Step Logic)
1. 初始化日曆：標記出該月份所有的日期，並依據 ISO 週次 (週一至週日) 分組。
2. 載入預劃假單：將所有員工的 pre_assigned_leaves 填入日曆，並計算每日目前的休假人數。
3. 計算缺額與填補：針對每位員工的每一週：
    * 計算目前已有幾個 DO。
    * 若不足 2 個，則尋找該週內的空檔日期填入 DO。
    * 選擇日期的優先順序：
        1. 該日期當前休假總人數 < 3。
        2. 填入該日期後，不會造成該員工前後連續工作 > 5 天。
        3. 填入該日期後，不會造成人員互斥休假。
        4. 若無法同時滿足，優先滿足「法規 1 & 2」，並在結果中標註違反專案規定。
4. 驗證：再次檢查所有規則是否符合，確保原始預劃假單 100% 被保留。

### 輸出格式
請直接回傳標準 CSV 內容。不要 Markdown 標記，不要解釋。
格式：姓名,代號,日期1,日期2,日期3...
"""

        if st.button("✨ 執行嚴格邏輯排班"):
            if not api_key:
                st.error("❌ 請提供 API Key")
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=model_choice)
                    
                    with st.spinner(f'🤖 使用 {model_choice} 進行嚴格運算中...'):
                        full_prompt = f"{strict_instruction}{core_rules}\n\n【輸入資料】\n{input_data_text}"
                        response = model.generate_content(full_prompt)
                        
                        raw_text = response.text.strip()
                        clean_lines = [l.strip() for l in raw_text.split('\n') if ',' in l and not l.startswith('```')]
                        result_csv = '\n'.join(clean_lines)
                        
                        output_df = pd.read_csv(io.StringIO(result_csv), on_bad_lines='skip')
                        
                        st.success("✅ 運算完成！原始預排假已鎖定並保留。")
                        st.subheader("🗓️ 生成結果預覽")
                        st.dataframe(output_df, use_container_width=True)
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            output_df.to_excel(writer, index=False, sheet_name='AI嚴格補假班表')
                        
                        st.download_button(
                            label="📥 下載產出的 Excel 班表",
                            data=buffer.getvalue(),
                            file_name="Strict_AI_Leave_Table.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                except Exception as e:
                    st.error(f"❌ 運算失敗：{str(e)}")
                    if 'response' in locals():
                        with st.expander("查看原始回應"):
                            st.text(response.text)

    except Exception as e:
        st.error(f"❌ 讀取檔案失敗：{e}")
