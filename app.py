import streamlit as st
import utils

st.set_page_config(page_title="檔案轉 QR Code 產生器", layout="centered")

st.title("📦 檔案 / 長文字 轉 QR Code")
st.write("將您的檔案或長篇程式碼轉為多張 QR Code 以便傳輸。圖片大小已優化，適合手機直接掃描。")

# 初始化 Session State，用來記錄當前生成的 QR codes 列表與翻頁進度
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

# 建立兩個頁籤：一個給檔案上傳，一個給長文字輸入
tab1, tab2 = st.tabs(["📁 檔案上傳", "📝 長文字輸入 (.py 等)"])

with tab1:
    uploaded_file = st.file_uploader("請選擇要轉換的檔案", type=None)
    if st.button("轉換檔案", key="btn_file"):
        if uploaded_file is not None:
            raw_bytes = uploaded_file.getvalue()
            reset_and_generate(raw_bytes)
        else:
            st.warning("請先上傳檔案。")

with tab2:
    text_input = st.text_area("請貼上長篇文字或程式碼", height=250)
    if st.button("轉換文字", key="btn_text"):
        if text_input.strip():
            # 將輸入的文字編碼成 bytes
            raw_bytes = text_input.encode('utf-8')
            reset_and_generate(raw_bytes)
        else:
            st.warning("請先輸入文字。")

st.divider()

# QR Code 顯示區域
if st.session_state.qr_images:
    total = len(st.session_state.qr_images)
    curr = st.session_state.current_page
    
    st.markdown(f"### 📱 QR Code ({curr + 1} / {total})")
    
    # 限制圖片寬度為 350，這個尺寸在手機網頁上通常能佔滿螢幕，方便一次性精確掃描
    # 將圖片置中顯示
    col_img1, col_img2, col_img3 = st.columns([1, 4, 1])
    with col_img2:
        st.image(st.session_state.qr_images[curr], width=350)
    
    # 控制按鈕區域
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        st.button("⬅️ 上一張", on_click=prev_page, disabled=(curr == 0), use_container_width=True)
    with col3:
        st.button("下一張 ➡️", on_click=next_page, disabled=(curr == total - 1), use_container_width=True)