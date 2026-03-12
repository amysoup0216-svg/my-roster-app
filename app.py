import streamlit as st
import google.generativeai as genai

st.title("🔍 檢查我的 Gemini 模型權限")
api_key = st.text_input("輸入你的 API Key", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        st.write("---")
        st.subheader("你的帳號可以使用的模型列表：")
        
        # 列出所有支援 generateContent 的模型
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                st.code(m.name) # 這會顯示類似 models/gemini-1.5-flash 這樣的字樣
                
    except Exception as e:
        st.error(f"查詢失敗：{e}")
