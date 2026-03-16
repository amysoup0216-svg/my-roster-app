import streamlit as st
import google.generativeai as genai
import pandas as pd
import io
import re # 新增：用來精準抓取 AI 回傳的 CSV 區塊

# --- 1. 網頁配置 ---
st.set_page_config(page_title="客服排班系統 - 模組 A", layout="wide", page_icon="🧠")

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
    
    model_choice = st.selectbox(
        "請選擇運算模型",
        [
            "models/gemini-3.1-flash-lite-preview",
            "models/gemini-1.5-flash",
            "models/gemini-3-pro-preview"
        ],
        index=0
    )
    st.divider()
    st.success("🛡️ 啟動『CoT 思考鏈』與『絕對鎖定防護』")

# --- 3. 主要內容區域 ---
st.title("🚀 模組 A：休假自動生成 (精準思考版)")
st.write("已啟用 AI 邏輯推演功能。系統會強迫 AI 先計算 ISO 週次與缺額，再生成班表。")

# --- 4. 檔案上傳 ---
uploaded_file = st.file_uploader("📂 請上傳人員資料 Excel (.xlsx)", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 讀取並強制將所有欄位名稱轉為純文字 (解決日期格式對齊失敗的問題)
        df_original = pd.read_excel(uploaded_file)
        df_original.columns = df_original.columns.astype(str)
        
        st.subheader("📊 原始資料 (將作為防護基準)")
        st.dataframe(df_original, use_container_width=True)
        
        input_data_text = df_original.to_csv(index=False)

        # --- 核心規則 (加入 CoT 思考鏈引導) ---
        prompt_rules = """
你是一個專業的自動化排班演算法專家。
【最高指令】：絕對禁止刪除或修改資料中原有的假項 (AL/DO)！你只能在「空白處」補上 DO。標題列的日期格式請一字不漏地照抄。

### 核心規則
1. 每週 2 天 DO：依據 ISO 8601 (週一至週日)，每人每週必須有剛好 2 天 DO (包含預劃假單內的)。
2. 避免過勞：不可連續工作超過 5 天 (滑動窗口 6 天內必有 1 天休假)。
3. 每日上限：全組每天總休假人數 (AL+DO) 不可超過 3 人。
4. 人員互斥：TPP07201 與 TPP07203 不可同日休假。

### 執行與輸出要求 (非常重要)
請你分兩個階段回答：
【第一階段：推演思考】
請簡短寫下你對每位員工每一週 (週一到週日) 的缺額計算，以及你要把 DO 補在哪幾天的規劃。確認是否符合避免過勞規則。

【第二階段：最終表格】
思考完畢後，請務必將最終的 CSV 表格內容包覆在 ```csv 和 ``` 之間。
請確保欄位數量與輸入資料完全一致！
"""

        if st.button("✨ 開始深度運算與補假"):
            if not api_key:
                st.error("❌ 請輸入 API Key")
            else:
                try:
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name=model_choice)
                    
                    with st.spinner(f'🧠 AI 正在進行週次推演與計算 (可能需要幾秒鐘)...'):
                        full_prompt = f"{prompt_rules}\n\n【輸入資料】\n{input_data_text}"
                        response = model.generate_content(full_prompt)
                        raw_text = response.text
                        
                        # 展示 AI 的思考過程給主管看
                        with st.expander("查看 AI 的邏輯推演過程 (點擊展開)"):
                            st.write(raw_text)
                        
                        # --- 精準擷取 CSV 區塊 ---
                        match = re.search(r'```csv\n(.*?)\n```', raw_text, re.DOTALL | re.IGNORECASE)
                        if match:
                            result_csv = match.group(1).strip()
                        else:
                            # 備用擷取法：如果 AI 忘記加標記，硬抓包含逗號的行
                            clean_lines = [l.strip() for l in raw_text.split('\n') if ',' in l and not l.startswith('```')]
                            result_csv = '\n'.join(clean_lines)
                        
                        # AI 產出的 DataFrame，並強制欄位為字串
                        df_ai = pd.read_csv(io.StringIO(result_csv), on_bad_lines='skip')
                        df_ai.columns = df_ai.columns.astype(str)
                        
                        # --- 🛡️ 絕對防護機制 (Update 覆蓋) ---
                        try:
                            df_safe = df_original.copy().set_index('代號')
                            df_ai_indexed = df_ai.set_index('代號')
                            
                            # 確保兩邊欄位名稱完全一致再進行覆蓋
                            common_cols = df_safe.columns.intersection(df_ai_indexed.columns)
                            df_ai_indexed[common_cols].update(df_safe[common_cols])
                            
                            df_final = df_ai_indexed.reset_index()
                            
                            # 整理欄位順序
                            cols = ['姓名', '代號'] + [c for c in df_final.columns if c not in ['姓名', '代號']]
                            df_final = df_final[cols]
                            st.success("🎉 運算與防護覆蓋完成！")
                            
                        except Exception as e:
                            st.warning(f"防護機制警告，可能部分日期格式不一致：{e}")
                            df_final = df_ai
                        
                        st.subheader("🗓️ 最終精準結果預覽")
                        st.dataframe(df_final, use_container_width=True)
                        
                        # 下載
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                            df_final.to_excel(writer, index=False, sheet_name='AI精準補假表')
                        
                        st.download_button(
                            label="📥 下載最終安全版 Excel",
                            data=buffer.getvalue(),
                            file_name="Secured_DO_Table.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                except Exception as e:
                    st.error(f"❌ 發生錯誤：{str(e)}")

    except Exception as e:
        st.error(f"❌ 讀取 Excel 失敗：{str(e)}")
