import streamlit as st
import base64
from openai import OpenAI
import os
import pandas as pd
from datetime import datetime

# 1. 網頁設定
st.set_page_config(page_title="FB 社團文案神器 (CMS版)", page_icon="🛍️")
st.title("🛍️ FB 社團文案神器 (CMS版)")

# 檔案路徑
CSV_FILE = "history.csv"

# ---------------------------------------------------------
# ✅ 初始化 Session State (記憶體)
if 'current_content' not in st.session_state:
    st.session_state['current_content'] = ""
if 'current_id' not in st.session_state:
    st.session_state['current_id'] = None # 用來記住現在正在編輯哪一筆資料 (用日期當 ID)

# ---------------------------------------------------------
# ✅ Helper Functions (小幫手函數)

def load_data():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    return pd.DataFrame(columns=["日期", "商品名稱", "風格", "生成的文案"])

def save_data(df):
    df.to_csv(CSV_FILE, index=False, encoding='utf-8-sig')

# 新增資料
def add_record(product_name, style, content):
    df = load_data()
    new_data = pd.DataFrame({
        "日期": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        "商品名稱": [product_name],
        "風格": [style],
        "生成的文案": [content]
    })
    df = pd.concat([df, new_data], ignore_index=True)
    save_data(df)

# 更新資料
def update_record(target_date, new_content):
    df = load_data()
    # 找到對應的那一行，更新內容
    df.loc[df['日期'] == target_date, '生成的文案'] = new_content
    save_data(df)

# 刪除資料
def delete_record(target_date):
    df = load_data()
    # 只保留「日期不等於」目標日期的資料 (等於是把目標踢掉)
    df = df[df['日期'] != target_date]
    save_data(df)

# ---------------------------------------------------------
# 側邊欄：設定與紀錄
st.sidebar.header("⚙️ 設定與紀錄")

if "OPENAI_API_KEY" in st.secrets:
    api_key = st.secrets["OPENAI_API_KEY"]
else:
    api_key = st.sidebar.text_input("輸入 OpenAI API Key", type="password")

style = st.sidebar.selectbox(
    "🎨 文案風格：",
    ("🔥 熱血叫賣風", "💖 溫柔閨蜜風", "🧐 專業分析風", "🤣 幽默搞笑風")
)

st.sidebar.markdown("---")
st.sidebar.subheader("📜 歷史紀錄管理")

# 讀取現有資料
df = load_data()

if not df.empty:
    # 製作選單標籤
df['label'] = df['日期'].astype(str) + " | " + df['商品名稱'].astype(str)
    # 選單 (反轉順序讓最新的在上面)
    selected_label = st.sidebar.selectbox("選擇舊貼文：", df['label'].tolist()[::-1])
    
    # 找出目前選中的那筆資料的「日期」(當作 ID)
    selected_date = selected_label.split(" | ")[0]
    
    col1, col2 = st.sidebar.columns(2)
    
    # 📖 按鈕：讀取
    if col1.button("👀 讀取"):
        # 抓出內容
        row = df[df['日期'] == selected_date].iloc[0]
        st.session_state['current_content'] = row['生成的文案']
        st.session_state['current_id'] = selected_date # 記住現在正在編輯這筆
        st.toast(f"已讀取：{row['商品名稱']}", icon="📖")
    
    # 🗑️ 按鈕：刪除 (新增功能！)
    if col2.button("🗑️ 刪除"):
        delete_record(selected_date)
        st.session_state['current_content'] = "" # 清空畫面
        st.session_state['current_id'] = None
        st.toast("已刪除該筆紀錄！", icon="🗑️")
        st.rerun() # 重新整理網頁，讓選單更新

else:
    st.sidebar.text("目前尚無紀錄")

# ---------------------------------------------------------
# 主畫面

uploaded_file = st.file_uploader("上傳商品圖片...", type=["jpg", "jpeg", "png"])
product_name = st.text_input("📦 商品名稱", value="未命名商品")

# 生成按鈕
if uploaded_file is not None:
    st.image(uploaded_file, caption='預覽', use_column_width=True)
    
    if st.button(f"✨ 生成新文案 ({style})"):
        if not api_key:
            st.error("❌ 無 API Key")
        else:
            with st.spinner('AI 寫作中...'):
                try:
                    client = OpenAI(api_key=api_key)
                    bytes_data = uploaded_file.getvalue()
                    base64_image = base64.b64encode(bytes_data).decode('utf-8')

                    response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": f"你是一個專業 FB 團購主，用{style}語氣寫文案。"},
                            {"role": "user", "content": [
                                {"type": "text", "text": f"商品：{product_name}，請寫文案"},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                            ]}
                        ]
                    )
                    content = response.choices[0].message.content
                    st.session_state['current_content'] = content
                    # 新生成的一律視為新資料，存檔
                    add_record(product_name, style, content)
                    st.session_state['current_id'] = None # 重置 ID，避免覆蓋到舊資料
                    st.success("已生成並存檔！")
                    st.rerun()

                except Exception as e:
                    st.error(f"錯誤：{e}")

# ---------------------------------------------------------
# 📝 編輯區 (重點更新！)
st.markdown("---")
st.markdown("### 👇 文案編輯區")

# 文字框綁定 session_state
new_text = st.text_area("內容", value=st.session_state['current_content'], height=400)

# 如果目前有「正在編輯」的舊資料 (current_id 有值)，就顯示「儲存修改」按鈕
if st.session_state['current_id']:
    if st.button("💾 儲存修改 (覆蓋舊檔)"):
        update_record(st.session_state['current_id'], new_text)
        st.session_state['current_content'] = new_text # 更新顯示
        st.toast("修改已儲存！", icon="✅")
        st.rerun()
else:
    # 如果是新生成的，或者還沒選舊資料，顯示提示
    st.caption("💡 提示：從左側「讀取」舊文案後，這裡會出現「儲存修改」按鈕。")