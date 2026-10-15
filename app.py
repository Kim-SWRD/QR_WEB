import streamlit as st
import streamlit.components.v1 as components
import utils
import os

st.set_page_config(page_title="檔案轉 QR Code 產生器", layout="centered")

st.title("📦 檔案 / 長文字 轉 QR Code")
st.write("將您的檔案或長篇程式碼轉為多張 QR Code 以便傳輸。圖片大小已優化，適合手機直接掃描。")

# 初始化 Session State
if 'qr_images' not in st.session_state:
    st.session_state.qr_images = []
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0

def next_page():
    if st.session_state.current_page < len(st.session_state.qr_images) - 1:
        st.session_state.current_page += 1

def prev_page():
    if st.session_state.current_page > 0:
        st.session_state.current_page -= 1

def reset_and_generate(raw_bytes):
    with st.spinner("正在壓縮與生成 QR Code 中..."):
        st.session_state.qr_images = utils.process_data_to_qrs(raw_bytes)
        st.session_state.current_page = 0

# 建立三個頁籤：上傳、文字輸入、接收解碼
tab1, tab2, tab3 = st.tabs(["📁 檔案上傳", "📝 長文字輸入 (.py 等)", "📷 接收解碼 (手機專用)"])

# --- Tab 1: 檔案上傳 ---
with tab1:
    uploaded_file = st.file_uploader("請選擇要轉換的檔案", type=None)
    if st.button("轉換檔案", key="btn_file"):
        if uploaded_file is not None:
            raw_bytes = uploaded_file.getvalue()
            reset_and_generate(raw_bytes)
        else:
            st.warning("請先上傳檔案。")

# --- Tab 2: 長文字輸入 ---
with tab2:
    text_input = st.text_area("請貼上長篇文字或程式碼", height=250)
    if st.button("轉換文字", key="btn_text"):
        if text_input.strip():
            raw_bytes = text_input.encode('utf-8')
            reset_and_generate(raw_bytes)
        else:
            st.warning("請先輸入文字。")

# --- Tab 3: 接收解碼 (內嵌 scanner.html) ---
with tab3:
    st.markdown("### 手機鏡頭自動掃描與還原")
    st.write("請允許相機權限，對準電腦螢幕上的 QR Code 進行掃描。系統會自動收集並還原檔案。")
    st.info("💡 如果相機無法啟動，請確保您是透過 HTTPS 網址訪問此網頁 (例如 Streamlit Community Cloud)。")
    
    # 讀取同一層目錄下的 scanner.html 內容
    try:
        with open("scanner.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # 使用 components.html 將 HTML 內容直接內嵌在 Streamlit 中
        # height 設定得高一點，確保手機上能看完整個掃描介面
        components.html(html_content, height=700, scrolling=True)
    except FileNotFoundError:
        st.error("找不到 scanner.html 檔案，請確認它與 app.py 放在同一個資料夾下。")


st.divider()

# --- QR Code 顯示區域 ---
if st.session_state.qr_images:
    total = len(st.session_state.qr_images)
    curr = st.session_state.current_page
    
    st.markdown(f"### 📱 QR Code ({curr + 1} / {total})")
    
    col_img1, col_img2, col_img3 = st.columns([1, 4, 1])
    with col_img2:
        st.image(st.session_state.qr_images[curr], width=350)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("⬅️ 上一張", on_click=prev_page, disabled=(curr == 0), use_container_width=True)
    with col3:
        st.button("下一張 ➡️", on_click=next_page, disabled=(curr == total - 1), use_container_width=True)
