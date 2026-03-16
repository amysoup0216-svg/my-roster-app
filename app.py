import streamlit as st
import google.generativeai as genai
import pandas as pd
import io

# --- 1. 網頁基本設定 ---
st.set_page_config(page_title="AI 排班助手 - 模組 A (Excel版)", layout="wide")

# --- 2. 側邊欄：設定 ---
with st.sidebar:
    st.title("⚙️ 系統設定")
    api_key = st.text_input("輸入 Gemini API Key", type="password")
    # 使用你先前測通的 3.1 Flash Lite 預覽版
    model_choice = "models/gemini-3.1-flash-lite-preview" 
    
    st.divider()
    st.info("目前開發進度：模組 A (Excel 匯入休假生成)")

# --- 3. 主要內容區 ---
st.title("🚀 模組 A：休假自動生成 (Excel 匯入)")
st.write("請上傳營運提供的 Excel 檔案，系統將自動解析並補足剩餘 DO 休假。")

# --- 檔案上傳區 (改為 Excel) ---
uploaded_file = st.file_uploader("請上傳人員資料 Excel 檔案 (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 使用 pandas 讀取 Excel
        df = pd.read_excel(uploaded_file)
        
        st.subheader("📊 匯入資料預覽")
        st.dataframe(df, use_container_width=True)
        
        # 將 DataFrame 轉換為文字格式，以便放入 Prompt
        # 這裡轉成 CSV 格式的文字，因為 AI 處理 CSV 結構的邏輯最穩
        data_text = df.to_csv(index=False)
        
        # 你的完整 Prompt 規則
        prompt_rules = """
你是一個專業的自動化排班演算法專家，你的目標是協助專案經理為員工安排剩餘的休假（DO），並確保所有排班結果嚴格符合台灣勞基法規與專案內規。

### 核心規則
1. 法規：週休二日 (每一週內必須剛好有 2 個 DO)。
2. 法規：避免過勞 (不得連續工作超過 5 天)。
3. 專案規定：每日休假上限 (每日總休假人數不可超過 3 人)。
4. 專案規定：人員互斥休假 (同組內員工不可在同一天休假)。
   互斥群組範例：["TPP07201", "TPP07203"]

### 輸出格式
請直接回傳一個標準的 CSV 格式字串，以便我轉換回 Excel。
欄位包含：姓名, 代號, 日期1, 日期2... (請橫向展開日期)
        """

        if st.button("✨ 開始解析並生成休假表"):
            if not api_key:
                st.warning("請先輸入 API Key")
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=model_choice)
                    
                    with st.spinner('AI 正在讀取 Excel 並計算邏輯...'):
                        # 結合規則與 Excel 轉換後的文字資料
                        full_input = f"{prompt_rules}\n\n以下是從 Excel 匯入的資料：\n{data_text}"
                        response = model.generate_content(full_input)
                        
                        st.success("✅ 休假表計算完成！")
                        
                        # 清理 AI 回傳的文字標記
                        result_csv = response.text.replace("```csv", "").replace("```", "").strip()
                        
                        # 展示結果
                        st.text_area("產出結果預覽 (CSV 格式)", value=result_csv, height=200)
                        
                        # --- 下載按鈕 (轉換回 Excel 提供下載) ---
                        # 將 AI 回傳的 CSV 文字轉回 DataFrame
                        output_df = pd.read_csv(io.StringIO(result_csv))
                        
                        # 將 DataFrame 轉為 Excel 二進位流
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                            output_df.to_excel(writer, index=False, sheet_name='Sheet1')
                        
                        st.download_button(
                            label="📥 下載產出的完整 Excel 班表",
                            data=output.getvalue(),
                            file_name="AI_Generated_Leave_Table.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                except Exception as e:
                    st.error(f"AI 處理時出錯：{str(e)}")
                    
    except Exception as e:
        st.error(f"檔案讀取錯誤：請確認是否為正確的 Excel 格式。錯誤訊息：{e}")
else:
    st.info("💡 尚未偵測到檔案。請將包含員工、代號、預劃假單的 Excel 檔案拖曳至上方。")
