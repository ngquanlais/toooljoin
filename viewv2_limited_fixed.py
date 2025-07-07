import time
import os
import json
import socket
import random
from colorama import init, Fore, Back, Style
import keyboard
import requests
from requests.exceptions import ConnectTimeout, RequestException
from datetime import datetime, timedelta

# Khởi tạo colorama
init()

# Thông tin Telegram
TELEGRAM_BOT_TOKEN = '7842057434:AAG61EPGHd0CN7HYJDBEyPweAT4T5Z3-AVM'
TELEGRAM_CHAT_ID = '6992813263'

# File để lưu thông tin tài khoản, đăng nhập tự động, last_update_id và thông báo bảo trì
ACCOUNTS_FILE = 'accounts.json'
LAST_LOGIN_FILE = 'last_login.txt'
LAST_UPDATE_FILE = 'last_update_id.txt'
MAINTENANCE_FILE = 'maintenance.json'

# Số lần thử lại tối đa khi gặp lỗi kết nối
MAX_RETRIES = 3
# Thời gian chờ tối đa cho mỗi yêu cầu HTTP (giây)
REQUEST_TIMEOUT = 10
# ID của update cuối cùng đã xử lý (để tránh lặp lại)
last_update_id = -1

# Hàm đọc last_update_id từ file
def load_last_update_id():
    global last_update_id
    if os.path.exists(LAST_UPDATE_FILE):
        with open(LAST_UPDATE_FILE, 'r') as f:
            try:
                last_update_id = int(f.read().strip())
            except ValueError:
                last_update_id = -1
    else:
        last_update_id = -1

# Hàm lưu last_update_id vào file
def save_last_update_id():
    with open(LAST_UPDATE_FILE, 'w') as f:
        f.write(str(last_update_id))

# Hàm đọc thông báo bảo trì từ file
def load_maintenance():
    if os.path.exists(MAINTENANCE_FILE):
        with open(MAINTENANCE_FILE, 'r') as f:
            return json.load(f)
    return {}

# Hàm lưu thông báo bảo trì vào file
def save_maintenance(maintenance_data):
    with open(MAINTENANCE_FILE, 'w') as f:
        json.dump(maintenance_data, f, indent=4)

# Hàm hiển thị thông báo bảo trì
def display_maintenance():
    maintenance_data = load_maintenance()
    if maintenance_data.get('message'):
        clear_screen()
        draw_border(Fore.YELLOW)
        print(f"{Fore.YELLOW}{Style.BRIGHT}  THÔNG BÁO BẢO TRÌ  {Style.RESET_ALL}".center(68))
        draw_border(Fore.YELLOW)
        print(f"{Fore.YELLOW}{Style.BRIGHT}  {maintenance_data['message']}{Style.RESET_ALL}".center(68))
        draw_bottom_border(Fore.YELLOW)
        input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")

# Hàm đọc tài khoản từ file JSON
def load_accounts():
    global accounts
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            accounts = json.load(f)
        for username in accounts:
            if 'allowed_tiktok' not in accounts[username]:
                accounts[username]['allowed_tiktok'] = False
            if 'view_count' not in accounts[username]:
                accounts[username]['view_count'] = 0
            if 'last_limit_reset' not in accounts[username]:
                accounts[username]['last_limit_reset'] = datetime.now().isoformat()
        save_accounts()
    else:
        accounts = {}

# Hàm lưu tài khoản vào file JSON
def save_accounts():
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# Hàm xóa tài khoản
def delete_account(username):
    load_accounts()
    if username in accounts:
        del accounts[username]
        save_accounts()
        print(f"{Fore.GREEN}{Style.BRIGHT}  Tài khoản {username} đã được xóa thành công!{Style.RESET_ALL}".center(68))
        send_to_telegram(f"Tài khoản *{username}* đã bị xóa khỏi hệ thống!", include_ip=True)
    else:
        print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Tài khoản {username} không tồn tại!{Style.RESET_ALL}".center(68))
        send_to_telegram(f"Lỗi: Tài khoản *{username}* không tồn tại!", include_ip=True)

# Hàm lưu thông tin đăng nhập tự động
def save_login(username):
    with open(LAST_LOGIN_FILE, 'w') as f:
        f.write(username)

# Hàm đọc thông tin đăng nhập tự động
def load_login():
    if os.path.exists(LAST_LOGIN_FILE):
        with open(LAST_LOGIN_FILE, 'r') as f:
            username = f.read().strip()
            if username in accounts:
                return username
    return None

# Hàm xóa thông tin đăng nhập tự động (đăng xuất)
def clear_login():
    if os.path.exists(LAST_LOGIN_FILE):
        os.remove(LAST_LOGIN_FILE)

# Hàm lấy địa chỉ IP cục bộ
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        return f"Không thể lấy IP: {str(e)}"

# Hàm gửi tin nhắn qua Telegram với retry
def send_to_telegram(message, include_ip=False, reply_markup=None):
    ip = get_local_ip() if include_ip else None
    full_message = f"{message}\nIP máy: {ip}" if include_ip and ip else message
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': full_message,
                'parse_mode': 'Markdown'
            }
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            response = requests.post(url, data=data, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200:
                print(f"{Fore.RED}Lỗi Telegram (Thử {attempt + 1}/{MAX_RETRIES}): {response.text}{Style.RESET_ALL}")
                if attempt == MAX_RETRIES - 1:
                    print(f"{Fore.RED}Không thể gửi tin nhắn Telegram sau {MAX_RETRIES} lần thử!{Style.RESET_ALL}")
                    return
            time.sleep(0.5)
            return
        except ConnectTimeout:
            print(f"{Fore.RED}Lỗi: Hết thời gian kết nối đến Telegram (Thử {attempt + 1}/{MAX_RETRIES}){Style.RESET_ALL}")
            if attempt == MAX_RETRIES - 1:
                print(f"{Fore.RED}Không thể kết nối đến Telegram sau {MAX_RETRIES} lần thử!{Style.RESET_ALL}")
        except RequestException as e:
            print(f"{Fore.RED}Lỗi gửi tin nhắn Telegram (Thử {attempt + 1}/{MAX_RETRIES}): {e}{Style.RESET_ALL}")
            if attempt == MAX_RETRIES - 1:
                print(f"{Fore.RED}Không thể gửi tin nhắn Telegram sau {MAX_RETRIES} lần thử!{Style.RESET_ALL}")
        time.sleep(2)

# Hàm kiểm tra tin nhắn Telegram với retry
def check_telegram_confirmation():
    global last_update_id
    for attempt in range(MAX_RETRIES):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url, timeout=REQUEST_TIMEOUT).json()
            if not response.get('ok') or not response.get('result'):
                return None
            
            updates = response['result']
            if not updates:
                return None
            
            for update in updates:
                update_id = update['update_id']
                last_update_id = max(last_update_id, update_id)
                save_last_update_id()
                
                # Xử lý callback từ inline keyboard
                if 'callback_query' in update:
                    callback = update['callback_query']
                    chat_id = str(callback['message']['chat']['id'])
                    if chat_id != TELEGRAM_CHAT_ID:
                        send_to_telegram("Lỗi: Bạn không có quyền sử dụng lệnh này!", include_ip=True)
                        continue
                    
                    username = callback['data'].split(':')[1]
                    action = callback['data'].split(':')[0]
                    
                    print(f"{Fore.CYAN}Đã nhận callback Telegram: {action} cho {username}{Style.RESET_ALL}")
                    
                    if action == "confirm":
                        if username in accounts:
                            accounts[username]['allowed_tiktok'] = True
                            save_accounts()
                            send_to_telegram(f"Tài khoản *{username}* đã được xác nhận quyền buff view trên TikTok!", include_ip=True)
                            return username, True
                        else:
                            send_to_telegram(f"Lỗi: Tài khoản *{username}* không tồn tại!", include_ip=True)
                    
                    elif action == "deny":
                        if username in accounts:
                            delete_account(username)
                            return username, None
                        else:
                            send_to_telegram(f"Lỗi: Tài khoản *{username}* không tồn tại!", include_ip=True)
                
                # Xử lý lệnh setmaintenance (nếu có)
                if 'message' in update and 'text' in update['message']:
                    if str(update['message']['chat']['id']) != TELEGRAM_CHAT_ID:
                        send_to_telegram("Lỗi: Bạn không có quyền sử dụng lệnh này!", include_ip=True)
                        continue
                    
                    text = update['message']['text'].strip()
                    if text.startswith('setmaintenance'):
                        parts = text.split(maxsplit=1)
                        if len(parts) == 2:
                            maintenance_message = parts[1].strip()
                            maintenance_data = {'message': maintenance_message}
                            save_maintenance(maintenance_data)
                            send_to_telegram(f"Thông báo bảo trì đã được đặt: *{maintenance_message}*", include_ip=True)
                        else:
                            maintenance_data = {}
                            save_maintenance(maintenance_data)
                            send_to_telegram("Thông báo bảo trì đã được xóa!", include_ip=True)
                        return None
            
            return None
        except ConnectTimeout:
            print(f"{Fore.RED}Lỗi: Hết thời gian kết nối đến Telegram (Thử {attempt + 1}/{MAX_RETRIES}){Style.RESET_ALL}")
            if attempt == MAX_RETRIES - 1:
                print(f"{Fore.RED}Không thể kết nối đến Telegram sau {MAX_RETRIES} lần thử!{Style.RESET_ALL}")
                send_to_telegram(f"Lỗi hệ thống: Không thể kết nối đến Telegram sau {MAX_RETRIES} lần thử (ConnectTimeout)", include_ip=True)
                return None
        except RequestException as e:
            print(f"{Fore.RED}Lỗi kiểm tra Telegram (Thử {attempt + 1}/{MAX_RETRIES}): {e}{Style.RESET_ALL}")
            if attempt == MAX_RETRIES - 1:
                print(f"{Fore.RED}Không thể kiểm tra Telegram sau {MAX_RETRIES} lần thử!{Style.RESET_ALL}")
                send_to_telegram(f"Lỗi hệ thống: Không thể kiểm tra Telegram sau {MAX_RETRIES} lần thử ({str(e)})", include_ip=True)
                return None
        time.sleep(2)

# Hàm tạo tài khoản
def create_account():
    clear_screen()
    draw_border()
    print(f"{Fore.GREEN}{Style.BRIGHT}  ✨ TẠO TÀI KHOẢN MỚI ✨  {Style.RESET_ALL}".center(68))
    draw_border()
    while True:
        username = input(f"{Fore.GREEN}{Style.BRIGHT}  Tên người dùng: {Style.RESET_ALL}").strip()
        if not username:
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Tên người dùng không được để trống!{Style.RESET_ALL}".center(68))
            continue
        if username in accounts:
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Tên người dùng đã tồn tại!{Style.RESET_ALL}".center(68))
            continue
        password = input(f"{Fore.GREEN}{Style.BRIGHT}  Mật khẩu: {Style.RESET_ALL}")
        if not password:
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Mật khẩu không được để trống!{Style.RESET_ALL}".center(68))
            continue
        accounts[username] = {
            'password': password,
            'allowed_tiktok': False,
            'view_count': 0,
            'last_reset': datetime.now().strftime('%Y-%m-%d')
        }
        save_accounts()
        # Gửi thông báo với inline keyboard
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "Có", "callback_data": f"confirm:{username}"},
                    {"text": "Không", "callback_data": f"deny:{username}"}
                ]
            ]
        }
        send_to_telegram(
            f"Tài khoản mới được tạo!\nTên: *{username}*\nMật khẩu: [Ẩn]\nVui lòng xác nhận bằng cách nhấn nút bên dưới.",
            include_ip=True,
            reply_markup=reply_markup
        )
        print(f"{Fore.GREEN}{Style.BRIGHT}  Tài khoản {username} đã được tạo!{Style.RESET_ALL}".center(68))
        print(f"{Fore.YELLOW}{Style.BRIGHT}  Đang chờ quản trị viên xác nhận qua Telegram...{Style.RESET_ALL}".center(68))
        print(f"{Fore.CYAN}{Style.BRIGHT}  (Nhấn 'Có' hoặc 'Không' trên Telegram){Style.RESET_ALL}".center(68))
        draw_bottom_border()
        save_login(username)
        return username

# Hàm đăng nhập
def login():
    clear_screen()
    draw_border()
    print(f"{Fore.GREEN}{Style.BRIGHT}  ✨ ĐĂNG NHẬP ✨  {Style.RESET_ALL}".center(68))
    draw_border()
    while True:
        username = input(f"{Fore.GREEN}{Style.BRIGHT}  Tên người dùng: {Style.RESET_ALL}").strip()
        if username not in accounts:
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Tên người dùng không tồn tại!{Style.RESET_ALL}".center(68))
            continue
        password = input(f"{Fore.GREEN}{Style.BRIGHT}  Mật khẩu: {Style.RESET_ALL}")
        if accounts[username]['password'] != password:
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Mật khẩu không đúng!{Style.RESET_ALL}".center(68))
            continue
        if not accounts[username].get('allowed_tiktok'):
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Tài khoản chưa được cấp phép buff view TikTok! Vui lòng chờ xác nhận qua Telegram.{Style.RESET_ALL}".center(68))
            return None
        print(f"{Fore.GREEN}{Style.BRIGHT}  Đăng nhập thành công!{Style.RESET_ALL}".center(68))
        draw_bottom_border()
        save_login(username)
        send_to_telegram(f"Tài khoản *{username}* đã đăng nhập thành công!", include_ip=True)
        return username

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_border(color=Fore.CYAN):
    print(f"{color}{Style.BRIGHT}╔{'═' * 68}╗{Style.RESET_ALL}")

def draw_bottom_border(color=Fore.CYAN):
    print(f"{color}{Style.BRIGHT}╚{'═' * 68}╝{Style.RESET_ALL}")

def blink_text(text, delay=0.5):
    clear_screen()
    draw_border()
    print(f"{Fore.GREEN}{Style.BRIGHT}{text.center(68)}{Style.RESET_ALL}")
    draw_bottom_border()
    time.sleep(delay)

def get_target_link():
    clear_screen()
    draw_border()
    print(f"{Fore.GREEN}{Style.BRIGHT}  ✨ TIKTOK BOOSTER ✨  {Style.RESET_ALL}".center(68))
    draw_border()
    print(f"{Fore.CYAN}{Style.BRIGHT}  Nhập link video TikTok:{Style.RESET_ALL}".center(68))
    target = input(f"{Fore.GREEN}{Style.BRIGHT}  URL: {Style.RESET_ALL}")
    while not target or "tiktok.com" not in target:
        print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Cần link TikTok hợp lệ! Nhập lại:{Style.RESET_ALL}".center(68))
        target = input(f"{Fore.GREEN}{Style.BRIGHT}  URL: {Style.RESET_ALL}")
    send_to_telegram(f"New TikTok link submitted!\nURL: *{target}*\nFunction: Tăng View", include_ip=True)
    return target

def get_target_quantity(username):
    clear_screen()
    draw_border()
    print(f"{Fore.GREEN}{Style.BRIGHT}  ✨ TIKTOK BOOSTER ✨  {Style.RESET_ALL}".center(68))
    draw_border()
    print(f"{Fore.CYAN}{Style.BRIGHT}  Nhập số lượng View cần tăng:{Style.RESET_ALL}".center(68))
    target = input(f"{Fore.GREEN}{Style.BRIGHT}  Số lượng: {Style.RESET_ALL}")
    while not target.isdigit() or int(target) <= 0:
        print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Số lượng phải là số nguyên dương! Nhập lại:{Style.RESET_ALL}".center(68))
        target = input(f"{Fore.GREEN}{Style.BRIGHT}  Số lượng: {Style.RESET_ALL}")
    view_count = int(target)
    remaining_views = 30000 - accounts[username]['view_count']
    if remaining_views <= 0:
        print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Bạn đã dùng hết 30.000 view trong 6 tiếng gần nhất!{Style.RESET_ALL}".center(68))
        return None
    if view_count > remaining_views:
        print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Chỉ còn {remaining_views:,} view khả dụng trong 6 tiếng này!{Style.RESET_ALL}".center(68))
        return None
    return view_count


def check_daily_limit(username):
    now = datetime.now()
    reset_time = datetime.fromisoformat(accounts[username].get('last_limit_reset', now.isoformat()))
    elapsed = now - reset_time

    if elapsed >= timedelta(hours=6):
        accounts[username]['view_count'] = 0
        accounts[username]['last_limit_reset'] = now.isoformat()
        save_accounts()
        return True

    return accounts[username]['view_count'] < 3000000000000000000
    if accounts[username]['last_reset'] != current_date:
        accounts[username]['view_count'] = 0
        accounts[username]['last_reset'] = current_date
        save_accounts()
    return accounts[username]['view_count'] < DAILY_VIEW_LIMIT

def display_main_menu(username):
    clear_screen()
    draw_border()
    print(f"{Fore.GREEN}{Style.BRIGHT}  ✨ TIKTOK BOOSTER ✨  {Style.RESET_ALL}".center(68))
    draw_border()
    if username:
        print(f"{Fore.CYAN}{Style.BRIGHT}  Tài khoản hiện tại: {username}{Style.RESET_ALL}".center(68))
        print(f"{Fore.CYAN}{Style.BRIGHT}  1. Buff view TikTok{Style.RESET_ALL}".center(68))
    else:
        print(f"{Fore.CYAN}{Style.BRIGHT}  Chưa đăng nhập{Style.RESET_ALL}".center(68))
        print(f"{Fore.CYAN}{Style.BRIGHT}  1. Đăng nhập{Style.RESET_ALL}".center(68))
    print(f"{Fore.BLUE}{Style.BRIGHT}  2. Tạo tài khoản mới{Style.RESET_ALL}".center(68))
    print(f"{Fore.YELLOW}{Style.BRIGHT}  3. Đăng xuất{Style.RESET_ALL}".center(68))
    draw_bottom_border()

def social_media_booster():
    send_to_telegram("TikTok Booster started!", include_ip=True)
    
    # Hiển thị thông báo bảo trì khi khởi động
    display_maintenance()
    
    # Kiểm tra xem có thông tin đăng nhập tự động không
    username = load_login()
    if username:
        print(f"{Fore.GREEN}{Style.BRIGHT}  Đã tự động đăng nhập với tài khoản: {username}{Style.RESET_ALL}".center(68))
        send_to_telegram(f"Tự động đăng nhập với tài khoản: *{username}*", include_ip=True)
        time.sleep(2)
    else:
        username = None

    while True:
        for text in ["Khởi động hệ thống...", "Kết nối API...", "Chuẩn bị boost..."]:
            blink_text(text, 0.5)
        
        result = check_telegram_confirmation()
        if result:
            result_username, allowed = result
            if allowed is None:
                print(f"{Fore.YELLOW}Tài khoản {result_username} đã được xóa qua Telegram.{Style.RESET_ALL}".center(68))
                if result_username == username:
                    clear_login()
                    username = None
                input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
                continue
            else:
                print(f"{Fore.YELLOW}Quyền buff TikTok được thêm qua Telegram: {result_username}{Style.RESET_ALL}".center(68))
                input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
        
        display_main_menu(username)
        
        choice = input(f"{Fore.GREEN}{Style.BRIGHT}  Chọn [1-3]: {Style.RESET_ALL}")
        
        if choice == '1':
            if username:
                if not accounts[username]['allowed_tiktok']:
                    clear_screen()
                    draw_border(Fore.RED)
                    print(f"{Fore.RED}{Style.BRIGHT}  Tài khoản không được phép buff view trên TikTok!{Style.RESET_ALL}".center(68))
                    draw_bottom_border()
                    send_to_telegram(f"Tài khoản *{username}* cố gắng buff view trên TikTok nhưng không được phép", include_ip=True)
                    input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
                    continue
                
                if not check_daily_limit(username):
                    clear_screen()
                    draw_border(Fore.RED)
                    print(f"{Fore.RED}{Style.BRIGHT}  Tài khoản đã đạt giới hạn 30,000 view trong 6 tiếng!{Style.RESET_ALL}".center(68))
                    print(f"{Fore.YELLOW}{Style.BRIGHT}  Vui lòng chờ đến ngày mai để tiếp tục.{Style.RESET_ALL}".center(68))
                    draw_bottom_border()
                    send_to_telegram(f"Tài khoản *{username}* đã đạt giới hạn 30,000 view trong 6 tiếng!", include_ip=True)
                    input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
                    continue
                
                target_quantity = get_target_quantity(username)
                if target_quantity is None:
                    input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
                    continue
                target_link = get_target_link()
                
                start_message = f"Starting view boost for TikTok\nUsername: *{username}*\nURL: *{target_link}*\nTarget: {target_quantity:,} Views\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                send_to_telegram(start_message, include_ip=True)
                
                total_views = 0
                line_number = 0
                clear_screen()
                draw_border()
                print(f"{Fore.GREEN}{Style.BRIGHT}  ✨ TIKTOK BOOSTER ✨  {Style.RESET_ALL}".center(68))
                draw_border()
                print(f"{Fore.CYAN}{Style.BRIGHT}  Target: {target_link}{Style.RESET_ALL}")
                print(f"{Fore.RED}{Style.BRIGHT}  Nhấn 'q' để thoát{Style.RESET_ALL}")
                draw_bottom_border()
                start_time = time.time()
                
                while total_views < target_quantity:
                    line_number += 1
                    views = min(random.randint(1, 5), target_quantity - total_views)
                    total_views += views
                    accounts[username]['view_count'] += views
                    save_accounts()
                    
                    current_time_display = time.strftime("%H:%M:%S", time.localtime())
                    time_color = Fore.CYAN
                    func_color = Fore.GREEN
                    increase_color = Fore.MAGENTA
                    total_color = Fore.YELLOW
                    
                    print(f"{time_color}{Style.BRIGHT}[{current_time_display}] {func_color}VIEW{increase_color}(+{views:<2}) {total_color}TỔNG: {total_views:>5,}/{target_quantity:,}{Style.RESET_ALL}")
                    
                    if keyboard.is_pressed('q'):
                        break
                    time.sleep(0.005)
                    
                    if accounts[username]['view_count'] >= DAILY_VIEW_LIMIT:
                        break
                
                elapsed_time = time.time() - start_time
                clear_screen()
                draw_border(Fore.RED)
                print(f"{Fore.RED}{Style.BRIGHT}  ✨ HỆ THỐNG ĐÃ TẮT ✨  {Style.RESET_ALL}".center(68))
                draw_border(Fore.RED)
                print(f"{Fore.CYAN}{Style.BRIGHT}  Target: {target_link}{Style.RESET_ALL}")
                draw_border()
                print(f"{Fore.GREEN}{Style.BRIGHT}  Tổng View: {total_views:,}/{target_quantity:,}{Style.RESET_ALL}".center(68))
                print(f"{Fore.WHITE}{Style.BRIGHT}  Số lần tăng: {line_number:,}{Style.RESET_ALL}".center(68))
                print(f"{Fore.WHITE}{Style.BRIGHT}  Thời gian chạy: {elapsed_time:.2f}s{Style.RESET_ALL}".center(68))
                draw_bottom_border()
                
                final_message = f"View boost completed!\nUsername: *{username}*\nPlatform: TikTok\nURL: *{target_link}*\nTotal Views: {total_views:,}/{target_quantity:,}\nNumber of Updates: {line_number:,}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\nRun Time: {elapsed_time:.2f}s"
                send_to_telegram(final_message, include_ip=True)
                
                input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
            else:
                username = login()
                if username is None:
                    input(f"{Fore.RED}{Style.BRIGHT}  Nhấn Enter để quay lại...{Style.RESET_ALL}")
        
        elif choice == '2':
            username = create_account()
            print(f"{Fore.YELLOW}{Style.BRIGHT}  Nhấn 'q' để hủy hoặc chờ xác nhận...{Style.RESET_ALL}".center(68))
            dots = 0
            while not accounts[username]['allowed_tiktok']:
                clear_screen()
                draw_border()
                print(f"{Fore.YELLOW}{Style.BRIGHT}  Đang chờ xác nhận quyền TikTok cho {username}...{'.' * (dots % 4)}{Style.RESET_ALL}".center(68))
                print(f"{Fore.CYAN}{Style.BRIGHT}  (Nhấn 'Có' hoặc 'Không' trên Telegram){Style.RESET_ALL}".center(68))
                print(f"{Fore.RED}{Style.BRIGHT}  Nhấn 'q' để hủy{Style.RESET_ALL}".center(68))
                draw_bottom_border()
                result = check_telegram_confirmation()
                if result:
                    result_username, allowed = result
                    if allowed is None and result_username == username:
                        print(f"{Fore.RED}{Style.BRIGHT}  Tài khoản {username} đã bị xóa qua Telegram!{Style.RESET_ALL}".center(68))
                        input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để quay lại...{Style.RESET_ALL}")
                        username = None
                        break
                    elif result_username == username and allowed:
                        print(f"{Fore.GREEN}{Style.BRIGHT}  Xác nhận thành công: TikTok{Style.RESET_ALL}".center(68))
                        input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
                        break
                if keyboard.is_pressed('q'):
                    print(f"{Fore.RED}{Style.BRIGHT}  Đã hủy chờ xác nhận!{Style.RESET_ALL}".center(68))
                    send_to_telegram(f"Đã hủy chờ xác nhận cho tài khoản *{username}*", include_ip=True)
                    input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để quay lại...{Style.RESET_ALL}")
                    username = None
                    break
                dots += 1
                time.sleep(2)
        
        elif choice == '3':
            if username:
                print(f"{Fore.YELLOW}{Style.BRIGHT}  Đã đăng xuất tài khoản {username}!{Style.RESET_ALL}".center(68))
                send_to_telegram(f"Tài khoản *{username}* đã đăng xuất!", include_ip=True)
            else:
                print(f"{Fore.YELLOW}{Style.BRIGHT}  Đã đăng xuất!{Style.RESET_ALL}".center(68))
                send_to_telegram("Đã đăng xuất khỏi hệ thống!", include_ip=True)
            clear_login()
            username = None
            input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")
        
        else:
            print(f"{Fore.RED}{Style.BRIGHT}  Lỗi: Chọn 1, 2 hoặc 3!{Style.RESET_ALL}".center(68))
            input(f"{Fore.GREEN}{Style.BRIGHT}  Nhấn Enter để tiếp tục...{Style.RESET_ALL}")

# Khởi tạo accounts và last_update_id
accounts = {}
load_accounts()
load_last_update_id()

if __name__ == "__main__":
    try:
        social_media_booster()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}{Style.BRIGHT} Thoát bằng phím Q{Style.RESET_ALL}")
        send_to_telegram("TikTok Booster stopped by user!", include_ip=True)