import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import tempfile
import os
import time

# --- CONFIGURATION ---
# ⚠️ REPLACE THIS WITH YOUR ACTUAL API KEY
API_KEY = "key"

# Configure Google Gemini API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 1. MOCK DATABASE (MENU) ---
# This simulates a backend SQL database
MENU_DATABASE = {
    "Beef Noodle Soup": 15.00,
    "Grilled Pork Vermicelli": 12.50,
    "Vietnamese Baguette": 8.00,
    "Iced Milk Coffee": 5.00,
    "Spring Rolls": 6.00,
    "Orange Juice": 4.50,
    "Chicken": 18.0
}

# --- 2. SESSION STATE INITIALIZATION ---
# Initialize session state to store cart data across reruns
if 'cart' not in st.session_state:
    st.session_state.cart = [] # List of dictionaries: {'Item': str, 'Qty': int, ...}

if 'page' not in st.session_state:
    st.session_state.page = 'pos' # Options: 'pos' (Order screen) or 'receipt' (Payment screen)

# --- 3. AI PROCESSING FUNCTION ---
# --- 3. AI PROCESSING FUNCTION (UPDATED) ---
def process_audio_order(audio_file_path):
    """
    Sends audio to Gemini with STRICT rules to avoid hallucination.
    """
    myfile = genai.upload_file(audio_file_path)
    menu_items = list(MENU_DATABASE.keys())
    
    # Cấu hình tham số: temperature=0.0 để AI không "sáng tạo" linh tinh
    generation_config = genai.types.GenerationConfig(
        temperature=0.0
    )
    
    # STRICT SYSTEM PROMPT
    prompt = f"""
    You are a strict AI Cashier. 
    Current Menu: {json.dumps(menu_items)}
    
    Your Task:
    1. Listen to the audio carefully.
    2. Transcribe the speech exactly in 'transcript'.
    3. Extract VALID food orders only.
    
    CRITICAL RULES (READ CAREFULLY):
    - If the user talks about unrelated topics (weather, greeting, noise, random text), RETURN AN EMPTY ORDER LIST.
    - DO NOT guess or hallucinate items. 
    - Only map an item if it clearly sounds like a food order.
    - If the user says "Hello" or "How are you", that is NOT an order.
    
    Output JSON format only:
    {{
        "transcript": "User's speech...",
        "orders": [
            {{"item": "Item Name", "qty": integer}}
        ]
    }}
    """
    
    try:
        # Truyền thêm generation_config vào đây
        response = model.generate_content(
            [prompt, myfile], 
            generation_config=generation_config
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        st.error(f"AI Processing Error: {e}")
        return None

# --- 4. CART MANAGEMENT FUNCTIONS ---
def add_to_cart(item_name, quantity):
    """
    Adds an item to the session_state cart.
    If item exists, it updates the quantity.
    """
    # Check if item already exists in cart to merge quantities
    for order in st.session_state.cart:
        if order['Item'] == item_name:
            order['Qty'] += quantity
            st.toast(f"Updated quantity for {item_name}!", icon="✅")
            return
    
    # If new item, append to list
    st.session_state.cart.append({
        "Item": item_name,
        "Qty": quantity,
        "Note": "Auto-added"
    })
    st.toast(f"Added {item_name} to cart!", icon="🛒")

def reset_system():
    """
    Clears the cart and returns to the POS screen.
    """
    st.session_state.cart = []
    st.session_state.page = 'pos'
    st.rerun()

# --- 5. MAIN UI LAYOUT ---
st.set_page_config(page_title="AI POS System", page_icon="🍔", layout="wide")

# PAGE 1: POS INTERFACE
# --- MÀN HÌNH 1: POS (ORDER) ---
if st.session_state.page == 'pos':
    st.title("🍔 Smart POS System (Multilingual)")
    
    # Chia làm 2 cột: Cột Trái (Menu + Input) và Cột Phải (Giỏ hàng)
    col_input, col_cart = st.columns([1, 1.2], gap="large")
    
    # --- CỘT TRÁI: NHẬP LIỆU & MENU ---
    with col_input:
        st.subheader("1. Take Order")
        
        # TAB NHẬP LIỆU
        tab_voice, tab_manual = st.tabs(["🎙️ Voice AI", "⌨️ Manual Entry"])
        
        # -- TAB 1: VOICE (UPDATED ANTI-LOOP) --
        with tab_voice:
            st.info("Record customer voice (Auto-detects Language)")
            audio_val = st.audio_input("Press to record")
            
            if audio_val:
                # --- LOGIC CHỐNG LẶP (ANTI-LOOP) ---
                # Lấy dữ liệu thô (bytes) của file âm thanh để so sánh
                current_audio_bytes = audio_val.getvalue()
                
                # Kiểm tra xem file này đã xử lý chưa
                if 'last_audio_bytes' not in st.session_state:
                    st.session_state.last_audio_bytes = None
                
                # CHỈ GỌI AI NẾU ĐÂY LÀ FILE ÂM THANH MỚI
                if current_audio_bytes != st.session_state.last_audio_bytes:
                    
                    # Lưu lại vết để lần sau không xử lý lại file này nữa
                    st.session_state.last_audio_bytes = current_audio_bytes
                    
                    with st.spinner("AI is listening..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                            tmp.write(audio_val.read())
                            tmp_path = tmp.name
                        
                        # Gọi AI
                        result = process_audio_order(tmp_path)
                        os.remove(tmp_path)
                        
                        if result:
                            st.success(f"🗣️ Transcript: **{result.get('transcript')}**")
                            orders = result.get("orders", [])
                            if orders:
                                for order in orders:
                                    add_to_cart(order['item'], order['qty'])
                                time.sleep(0.5)
                                st.rerun() # Load lại để hiện giỏ hàng
                            else:
                                st.warning("No food items detected.")
                else:
                    # Nếu là file cũ (do bấm nút khác gây rerun), không làm gì cả
                    pass

        # -- TAB 2: MANUAL --
        with tab_manual:
            options = list(MENU_DATABASE.keys()) + ["Other (Custom Item)"]
            selected_option = st.selectbox("Select Item:", options)
            
            final_item_name = selected_option
            if selected_option == "Other (Custom Item)":
                final_item_name = st.text_input("Enter custom item name:")
            
            qty_manual = st.number_input("Quantity:", min_value=1, value=1, step=1)
            
            if st.button("➕ Add to Cart", use_container_width=True):
                if final_item_name:
                    add_to_cart(final_item_name, qty_manual)
                    st.rerun()

        # --- HIỂN THỊ MENU LUÔN LUÔN Ở ĐÂY ---
        st.divider()
        st.subheader("📋 Menu Reference")
        # Tạo dataframe từ MENU_DATABASE
        menu_df = pd.DataFrame(list(MENU_DATABASE.items()), columns=["Item", "Price ($)"])
        # Hiển thị bảng menu tĩnh, không cho chỉnh sửa
        st.dataframe(
            menu_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Price ($)": st.column_config.NumberColumn(format="$%.2f")
            }
        )

    # --- CỘT PHẢI: GIỎ HÀNG (CART) ---
    with col_cart:
        st.subheader("2. Current Cart")
        
        if len(st.session_state.cart) > 0:
            df_cart = pd.DataFrame(st.session_state.cart)
            
            def get_price(item_name):
                return MENU_DATABASE.get(item_name, 0.00)
            
            df_cart['Unit Price'] = df_cart['Item'].apply(get_price)
            df_cart['Total'] = df_cart['Unit Price'] * df_cart['Qty']
            
            st.markdown("💡 *Edit **Qty** directly or select rows to **Delete**.*")
            
            edited_df = st.data_editor(
                df_cart,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "Item": st.column_config.TextColumn("Item Name", disabled=True),
                    "Qty": st.column_config.NumberColumn("Qty", min_value=1, step=1),
                    "Unit Price": st.column_config.NumberColumn("Price", format="$%.2f", disabled=True),
                    "Total": st.column_config.NumberColumn("Total", format="$%.2f", disabled=True),
                    "Note": st.column_config.TextColumn("Note", disabled=True)
                },
                key="cart_editor" 
            )
            
            # Cập nhật lại session state
            if not df_cart.equals(edited_df):
                st.session_state.cart = edited_df[['Item', 'Qty', 'Note']].to_dict('records')
                st.rerun()
            
            grand_total = edited_df['Total'].sum()
            
            st.divider()
            col_total_label, col_total_val = st.columns([2, 1])
            col_total_label.markdown("### GRAND TOTAL:")
            col_total_val.markdown(f"<h3 style='text-align: right; color: green;'>${grand_total:.2f}</h3>", unsafe_allow_html=True)
            
            if st.button("💳 PROCEED TO PAYMENT", type="primary", use_container_width=True):
                st.session_state.page = 'receipt'
                st.rerun()
                
        else:
            # Khi chưa có món nào thì hiện thông báo chờ
            st.info("The cart is empty. Waiting for order...")
            # Có thể chèn hình ảnh minh họa POS hoặc icon vào đây cho đỡ trống
            st.markdown("""
                <div style="text-align: center; color: #ccc; padding: 40px;">
                    <h1>🛒</h1>
                    <p>Ready to take orders</p>
                </div>
            """, unsafe_allow_html=True)

# PAGE 2: RECEIPT / PAYMENT SUCCESS
elif st.session_state.page == 'receipt':
    # Sử dụng container để chứa toàn bộ nội dung hóa đơn
    with st.container():
        # CSS để tạo khung hóa đơn đẹp mắt
        st.markdown("""
            <style>
                .receipt-container {
                    background-color: #fff;
                    padding: 30px;
                    border-radius: 15px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                    max-width: 800px; /* Giới hạn chiều rộng tối đa */
                    margin: auto; /* Căn giữa trang */
                    color: #333;
                }
                .receipt-header {
                    text-align: center;
                    margin-bottom: 20px;
                }
                .receipt-header h1 {
                    margin: 0;
                    font-size: 2.5em;
                    color: #333;
                }
                .receipt-header p {
                    margin: 5px 0;
                    color: #666;
                }
                .receipt-divider {
                    border-top: 2px dashed #bbb;
                    margin: 20px 0;
                }
                .receipt-footer {
                    text-align: center;
                    margin-top: 30px;
                    color: #888;
                    font-style: italic;
                }
                /* Ẩn index của dataframe */
                [data-testid="stDataFrame"] div:first-child table tbody th {
                    display: none;
                }
                [data-testid="stDataFrame"] div:first-child table thead th:first-child {
                    display: none;
                }
            </style>
        """, unsafe_allow_html=True)

        # Bắt đầu nội dung hóa đơn bên trong khung
        st.markdown('<div class="receipt-container">', unsafe_allow_html=True)
        
        # Tiêu đề hóa đơn
        st.markdown("""
            <div class="receipt-header">
                <h1>🧾 OFFICIAL RECEIPT</h1>
                <p><strong>Gemini Internship Restaurant</strong></p>
                <p>123 AI Boulevard, Tech City</p>
            </div>
            <div class="receipt-divider"></div>
        """, unsafe_allow_html=True)
        
        # Chuẩn bị dữ liệu cho bảng
        receipt_df = pd.DataFrame(st.session_state.cart)
        # Tính giá (nếu món mới thì giá là 0)
        receipt_df['Price'] = receipt_df['Item'].apply(lambda x: MENU_DATABASE.get(x, 0.0))
        receipt_df['Subtotal'] = receipt_df['Price'] * receipt_df['Qty']
        
        # Hiển thị bảng chi tiết đơn hàng
        st.dataframe(
            receipt_df[['Item', 'Qty', 'Price', 'Subtotal']],
            hide_index=True, # Ẩn cột số thứ tự
            use_container_width=True, # Mở rộng bảng ra toàn bộ chiều ngang
            column_config={
                "Item": st.column_config.TextColumn("Item Name"),
                "Qty": st.column_config.NumberColumn("Quantity", format="%d"),
                "Price": st.column_config.NumberColumn("Unit Price", format="$%.2f"),
                "Subtotal": st.column_config.NumberColumn("Subtotal", format="$%.2f"),
            }
        )
        
        st.markdown('<div class="receipt-divider"></div>', unsafe_allow_html=True)
        
        # Tính và hiển thị tổng tiền
        total_val = receipt_df['Subtotal'].sum()
        
        # Sử dụng st.metric để hiển thị tổng tiền lớn và đẹp
        st.metric(label="TOTAL PAID", value=f"${total_val:.2f}")
        
        # Lời cảm ơn cuối hóa đơn
        st.markdown("""
            <div class="receipt-footer">
                <p>Thank you for dining with us!</p>
                <p>Please come again.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True) # Kết thúc khung hóa đơn

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Nút quay lại màn hình Order
        if st.button("🔄 Start New Order", type="primary", use_container_width=True):
            reset_system()