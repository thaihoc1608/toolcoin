import ccxt
import pandas as pd
import os
import time
import warnings
from datetime import datetime

# --- CẤU HÌNH ---
SYMBOL = 'BTC/USDT'
EXCEL_FILE = 'btc_realtime_reversals.xlsx'
# Độ nhạy để xác nhận đảo chiều (0.01% = 0.0001).
# Giảm số này xuống (ví dụ 0.00005) nếu muốn nhạy hơn nữa (nhưng sẽ nhiễu hơn).
THRESHOLD = 0.0001 

warnings.simplefilter(action='ignore', category=FutureWarning)
exchange = ccxt.binance({'enableRateLimit': True})

def init_excel_file():
    if not os.path.exists(EXCEL_FILE):
        df = pd.DataFrame(columns=['Thời gian', 'Đồng tiền', 'Giá lúc đảo', 'Loại đảo chiều', 'Biến động từ đáy/đỉnh'])
        try:
            df.to_excel(EXCEL_FILE, index=False, engine='openpyxl')
        except: pass

def log_to_excel(timestamp, symbol, price, direction, change_val):
    """Ghi ngay lập tức khi phát hiện."""
    try:
        df_current = pd.read_excel(EXCEL_FILE, engine='openpyxl')
        new_row = pd.DataFrame([{
            'Thời gian': timestamp,
            'Đồng tiền': symbol,
            'Giá lúc đảo': price,
            'Loại đảo chiều': direction,
            'Biến động từ đáy/đỉnh': change_val
        }])
        pd.concat([df_current, new_row], ignore_index=True).to_excel(EXCEL_FILE, index=False, engine='openpyxl')
    except PermissionError:
        print(f" [CẢNH BÁO] Không ghi được file Excel do đang mở! (Vẫn tiếp tục theo dõi...)")

def get_current_price():
    try:
        ticker = exchange.fetch_ticker(SYMBOL)
        return ticker['last']
    except:
        return None

# --- CHƯƠNG TRÌNH CHÍNH ---
if __name__ == '__main__':
    print(f"--- BOT BẮT ĐẢO CHIỀU NGAY LẬP TỨC ({SYMBOL}) ---")
    print(f"--- Độ nhạy: {THRESHOLD*100}% ---")
    init_excel_file()
    
    # Khởi tạo trạng thái ban đầu
    current_trend = 'UNKNOWN' # Đang chưa biết xu hướng
    extreme_price = get_current_price() # Giá đỉnh nhất hoặc đáy nhất tạm thời
    
    if not extreme_price:
        print("Lỗi không lấy được giá khởi điểm. Thoát.")
        exit()

    print(f" [BẮT ĐẦU] Giá hiện tại: {extreme_price}. Đang chờ biến động đầu tiên...")

    while True:
        try:
            time.sleep(1) # Kiểm tra giá mỗi 1 giây (Real-time)
            now_price = get_current_price()
            if not now_price: continue
            
            now_str = datetime.now().strftime('%H:%M:%S')

            # --- LOGIC XÁC ĐỊNH XU HƯỚNG ĐẦU TIÊN ---
            if current_trend == 'UNKNOWN':
                if now_price > extreme_price * (1 + THRESHOLD):
                    current_trend = 'UP'
                    extreme_price = now_price
                    print(f"[{now_str}] ➤ Bắt đầu xu hướng TĂNG (Giá: {now_price})")
                elif now_price < extreme_price * (1 - THRESHOLD):
                    current_trend = 'DOWN'
                    extreme_price = now_price
                    print(f"[{now_str}] ➤ Bắt đầu xu hướng GIẢM (Giá: {now_price})")
                continue

            # --- LOGIC BẮT ĐẢO CHIỀU THỜI GIAN THỰC ---
            if current_trend == 'DOWN':
                # Nếu giá vẫn giảm tiếp -> Cập nhật đáy mới
                if now_price < extreme_price:
                    extreme_price = now_price
                    # print(f"Creating new LOW: {extreme_price}", end='\r') # Bỏ comment nếu muốn theo dõi chi tiết
                
                # Nếu giá bật tăng vượt ngưỡng -> BÁO ĐẢO CHIỀU TĂNG NGAY!
                elif now_price > extreme_price * (1 + THRESHOLD):
                    change = now_price - extreme_price
                    print(f"\n[{now_str}] 🚀 ĐẢO CHIỀU TĂNG! (Giá: {now_price} | Từ đáy: {extreme_price})")
                    log_to_excel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), SYMBOL, now_price, 'TĂNG (UP)', f"+{change:.2f}$")
                    # Đổi xu hướng, bây giờ đi tìm đỉnh
                    current_trend = 'UP'
                    extreme_price = now_price

            elif current_trend == 'UP':
                # Nếu giá vẫn tăng tiếp -> Cập nhật đỉnh mới
                if now_price > extreme_price:
                    extreme_price = now_price
                    # print(f"Creating new HIGH: {extreme_price}", end='\r')
                
                # Nếu giá tụt giảm quá ngưỡng -> BÁO ĐẢO CHIỀU GIẢM NGAY!
                elif now_price < extreme_price * (1 - THRESHOLD):
                    change = extreme_price - now_price
                    print(f"\n[{now_str}] 🔻 ĐẢO CHIỀU GIẢM! (Giá: {now_price} | Từ đỉnh: {extreme_price})")
                    log_to_excel(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), SYMBOL, now_price, 'GIẢM (DOWN)', f"-{change:.2f}$")
                    # Đổi xu hướng, bây giờ đi tìm đáy
                    current_trend = 'DOWN'
                    extreme_price = now_price
            
            # In giá hiện tại để biết bot vẫn chạy (ghi đè dòng cũ cho gọn)
            print(f"[{now_str}] Đang {current_trend} | Giá: {now_price} | Đỉnh/Đáy tạm thời: {extreme_price}  ", end='\r')

        except KeyboardInterrupt:
            print("\nĐã dừng bot.")
            break
        except Exception as e:
            print(f"Lỗi: {e}")
            time.sleep(2)