# -*- coding: utf-8 -*-
import json
import pandas as pd
import math
import random
from datetime import datetime, timedelta
import unicodedata

# ==================== UTILITY FUNCTIONS ====================

def calculate_distance(lat1, lon1, lat2, lon2):
    """Tính khoảng cách giữa 2 điểm GPS (km)"""
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return R * c

def estimate_travel_time(distance_km):
    """Ước tính thời gian di chuyển (phút)"""
    avg_speed = 25
    return int((distance_km / avg_speed) * 60)

def normalize_text(text):
    """Chuẩn hóa text để tìm kiếm"""
    if not text or not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore').decode('utf-8')
    return text

def clean_value(value):
    """Chuyển đổi các giá trị NaN/None thành giá trị hợp lệ"""
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return 0
        return value
    return value

def is_open_now(opening_hours_str, check_time=None, min_hours_before_close=2, place_name=None):
    """
    Kiểm tra quán có đang mở cửa không VÀ còn đủ thời gian hoạt động
    
    Args:
        opening_hours_str: Chuỗi giờ mở cửa từ CSV (VD: "Mở cửa vào 4:30 · Đóng cửa vào 12:00")
        check_time: Thời gian cần kiểm tra (HH:MM hoặc time object)
        min_hours_before_close: Số giờ tối thiểu trước khi đóng cửa (mặc định 2 giờ)
        place_name: Tên quán (dùng để debug)
    
    Returns:
        True nếu quán đang mở và còn đủ thời gian, False nếu không
    """
    # Nếu không có thông tin giờ mở cửa → CHẶN LUÔN
    if not opening_hours_str or pd.isna(opening_hours_str):
        return False
    
    try:
        import re
        
        # Xử lý check_time
        if check_time is None:
            current_time = datetime.now().time()
        elif isinstance(check_time, str):
            current_time = datetime.strptime(check_time, '%H:%M').time()
        else:
            current_time = check_time
        
        # Chuẩn hóa: bỏ dấu, lowercase
        hours_str = normalize_text(str(opening_hours_str))
        
        
        # CHẶN các quán "Không rõ giờ mở cửa"
        if 'khong ro' in hours_str or 'khong biet' in hours_str or 'chua ro' in hours_str:
            return False
        
        # Kiểm tra quán mở 24/7
        if any(keyword in hours_str for keyword in ['always', '24', 'ca ngay', 'mo ca ngay']):
            return True
        
        # Parse giờ mở cửa - hỗ trợ cả "Mở cửa vào" và "Mở cửa lúc"
        open_time = None
        open_match = re.search(r'mo\s*cua\s*(?:vao|luc)?\s*(\d{1,2}):?(\d{2})?', hours_str)
        if open_match:
            hour = int(open_match.group(1))
            minute = int(open_match.group(2)) if open_match.group(2) else 0
            open_time = datetime.strptime(f'{hour:02d}:{minute:02d}', '%H:%M').time()
        
        # Parse giờ đóng cửa
        close_time = None
        close_match = re.search(r'(?:d)?ong\s*cua\s*(?:vao|luc)?\s*(\d{1,2}):?(\d{2})?', hours_str)
        if close_match:
            hour = int(close_match.group(1))
            minute = int(close_match.group(2)) if close_match.group(2) else 0
            close_time = datetime.strptime(f'{hour:02d}:{minute:02d}', '%H:%M').time()
        
        # Nếu không parse được giờ → CHẶN LUÔN (không cho qua như trước)
        if open_time is None or close_time is None:
            return False
        
        # Chuyển đổi tất cả sang phút để dễ so sánh
        current_minutes = current_time.hour * 60 + current_time.minute
        open_minutes = open_time.hour * 60 + open_time.minute
        close_minutes = close_time.hour * 60 + close_time.minute
        
        # Xử lý trường hợp quán mở qua đêm (VD: 22:00 - 02:00)
        if close_minutes < open_minutes:
            # Cộng 24 giờ cho giờ đóng cửa
            close_minutes += 24 * 60
            
            # Nếu giờ check < giờ mở → Coi như sáng hôm sau
            if current_minutes < open_minutes:
                current_minutes += 24 * 60
        
        # Tính thời gian tối thiểu cần có trước khi đóng cửa (đổi từ giờ sang phút)
        min_minutes_before_close = min_hours_before_close * 60
        
        # 3 điều kiện để quán hợp lệ:
        # 1. Đã đến giờ mở cửa
        is_open = (current_minutes >= open_minutes)

        # 2. Chưa đến giờ đóng cửa
        is_before_close = (current_minutes < close_minutes)

        # 3. Còn đủ thời gian hoạt động (ít nhất 2 giờ trước khi đóng)
        has_enough_time = ((close_minutes - current_minutes) >= min_minutes_before_close)

        # 🔥 CHẶN CHẶT: Nếu KHÔNG thỏa mãn cả 3 điều kiện → CHẶN LUÔN
        if not (is_open and is_before_close and has_enough_time):
            return False

        # ✅ Nếu đến đây → CẢ 3 ĐIỀU KIỆN ĐỀU ĐÚNG
        result = True
        
        return result
            
    except Exception as e:
        print(f"⚠️ Lỗi parse giờ: {opening_hours_str} -> {e}")
        # Khi có lỗi → CHẶN LUÔN (không cho qua như trước)
        return False

# ==================== CẬP NHẬT HÀM LỌC - GIỮ NGUYÊN DẤU ====================

def normalize_text_with_accent(text):
    """Chuẩn hóa text NHƯNG GIỮ NGUYÊN DẤU tiếng Việt"""
    if not text or not isinstance(text, str):
        return ""
    text = text.lower().strip()
    # Chỉ chuẩn hóa khoảng trắng, KHÔNG loại bỏ dấu
    text = ' '.join(text.split())
    return text

# ==================== TỪ ĐIỂN CHỦ ĐỀ MỞ RỘNG - CÓ DẤU ĐẦY ĐỦ ====================

THEME_CATEGORIES = {
    'street_food': {
        'name': 'Ẩm thực đường phố',
        'keywords': [
            # Món ăn
            'bánh mì', 'bánh mỳ', 'banh mi',
            'phở', 'pho',
            'bún', 'bún bò', 'bún chả', 'bún riêu', 'bún đậu', 'bún mắm',
            'bún thịt nướng', 'bún ốc',
            'cơm tấm', 'cơm sườn', 'cơm gà', 'cơm chiên',
            'xôi', 'xôi gà', 'xôi thịt',
            'chè', 'chè khúc', 'chè thái',
            'street', 'vỉa hè', 'quán vỉa hè', 'đường phố',
            'hủ tiếu', 'hủ tíu', 'mì quảng',
            'cao lầu', 'bánh xèo', 'bánh căn',
            'gỏi cuốn', 'nem', 'chả giò', 'nem rán',
            'bánh cuốn', 'bánh bèo', 'bánh bột lọc',
            'cháo', 'cháo lòng', 'cháo vịt'
            # KHÔNG CÓ thương hiệu vì tên quán đã có keyword rồi
        ],
        'icon': '🍜'
    },
    'seafood': {
        'name': 'Hải sản',
        'keywords': [
            'hải sản', 'seafood',
            'fish', 'cá',
            'cua', 'ghẹ',
            'tôm', 'shrimp',
            'ốc', 'snail',
            'ngao', 'sò', 'nghêu',
            'mực', 'squid',
            'cá hồi', 'salmon',
            'hàu', 'oyster',
            'tôm hùm', 'lobster',
            'cá thu', 'cá ngừ', 'cá basa',
            'lẩu hải sản', 'nướng hải sản',
            'buffet hải sản'
        ],
        'icon': '🦞'
    },
    'coffee_chill': {
        'name': 'Giải khát',
        'keywords': [
            # Món uống
            'cà phê', 'cafe', 'coffee', 'ca phe',
            'cà phê sữa', 'cà phê đá', 'cà phê phin',
            'cà phê sữa đá', 'cà phê đen',
            'bạc xỉu', 'nâu đá', 'Akafe',
            'espresso', 'cappuccino', 'latte', 'americano',
            'mocha', 'macchiato', 'flat white','tea',
            'trà sữa', 'milk tea',
            'trà đào', 'trà chanh', 'trà atiso',
            'trà sen', 'trà hoa', 'trà ô long',
            'trà xanh', 'trà đen', 'trà gừng',
            'sinh tố', 'smoothie', 'juice',
            'nước ép', 'nước trái cây',
            'soda', 'soda cream', 'limonada',
            'matcha', 'chocolate', 'frappe',
            # Không gian
            'acoustic', 'chill', 'cozy',
            'book cafe', 'quán sách',
            # Thương hiệu KHÔNG có keyword trong tên
            'highlands', 'starbucks',
            'phúc long', 'trung nguyên',
            'gong cha', 'royaltea', 'ding tea',
            'tocotoco', 'koi thé', 'koi the',
            'bobapop', 'alley', 'tiger sugar',
            'passio', 'phindi',
            'angfarm', 'runam',
            'effoc', 'vinacafe'
        ],
        'icon': '☕'
    },
    'luxury_dining': {
        'name': 'Nhà hàng sang trọng',
        'keywords': [
            'nhà hàng', 'restaurant', 'nha hang',
            'fine dining', 'luxury', 'sang trọng', 'sang trong',
            'buffet','resort', 'rooftop',
            'steakhouse', 'bít tết', 'beefsteak', 'bit tet',
            'sky bar', 'lounge',
            'five star', 'cao cấp', 'cao cap',
            # Thương hiệu khách sạn/nhà hàng cao cấp
            'marriott', 'sheraton', 'hilton',
            'intercontinental', 'hyatt', 'sofitel',
            'pullman', 'novotel', 'renaissance',
            'reverie', 'vinpearl',
            'bistro', 'grill', 'prime',
            'dining', 'banquet', 'yen tiec', 'yến tiệc'
        ],
        'icon': '🍽️'
    },
    'asian_fusion': {
        'name': 'Ẩm thực châu Á',
        'keywords': [
            # Nhật - Món ăn
            'sushi', 'ramen', 'nhật bản',
            'japanese', 'tempura', 'takoyaki',
            'udon', 'soba', 'teriyaki',
            'sashimi', 'donburi', 'bento',
            'yakiniku', 'okonomiyaki',
            'katsu', 'tonkatsu', 'gyoza',
            'miso', 'wasabi', 'edamame',
            # Nhật - Thương hiệu KHÔNG có keyword
            'omakase', 'ichiban',
            'tokyo', 'osaka', 'hokkaido',
            'izakaya',
            # Hàn - Món ăn
            'hàn quốc', 'korean',
            'kimchi', 'bibimbap', 'bulgogi',
            'gimbap', 'tteokbokki', 'samgyeopsal',
            'bbq hàn', 'korean bbq',
            'jjigae', 'ramyeon',
            'kimbap', 'japchae', 'galbi',
            # Hàn - Thương hiệu
            'gogi', 'king bbq', 'sumo bbq',
            'seoul', 'busan', 'gangnam',
            # Thái
            'thái', 'thai', 'thailand',
            'tom yum', 'pad thai', 'somtum',
            'tom kha', 'green curry',
            'massaman', 'panang', 'bangkok',
            # Trung
            'trung hoa', 'trung quốc', 'chinese',
            'dimsum', 'dim sum', 'lẩu tứ xuyên',
            'mì vằn thắn', 'hủ tiếu xào',
            'há cảo', 'xíu mại', 'sủi cảo',
            'bắc kinh', 'quảng đông', 'thượng hải',
            'hongkong', 'canton'
        ],
        'icon': '🍱'
    },
    'vegetarian': {
        'name': 'Món chay',
        'keywords': [
            'chay', 'vegetarian', 'vegan',
            'healthy', 'organic', 'sạch',
            'salad', 'rau củ', 'rau sạch',
            'cơm chay', 'bún chay', 'phở chay',
            'đậu hũ', 'tofu',
            'nấm', 'mushroom',
            'chay thanh tịnh', 'an lạc',
            'chay tịnh', 'món chay',
            'thực dưỡng', 'thuần chay',
            # 🔥 THÊM KEYWORDS MỚI 🔥
            'chay zen', 'chay buffet', 'quán chay',
            'ăn chay', 'thực phẩm chay', 'chay healthy',
            'bánh mì chay', 'lẩu chay', 'nướng chay',
            'cà ri chay', 'mì chay', 'hủ tiếu chay'
        ],
        'icon': '🥗'
    },
    'dessert_bakery': {
        'name': 'Tráng miệng',
        'keywords': [
            # Bánh
            'bánh', 'cake', 'bakery',
            'bánh kem', 'bánh sinh nhật',
            'bánh ngọt', 'bánh ngon',
            'bánh mì ngọt', 'croissant', 'tiramisu',
            'macaron', 'cupcake', 'donut',
            'bánh bông lan', 'bánh flan',
            'bánh su kem', 'eclair',
            'mousse', 'cheesecake',
            'bánh tart', 'bánh pie',
            'bánh cookie', 'bánh quy',
            'mochi', 'bánh trung thu',
            # Kem
            'kem', 'ice cream', 'gelato',
            'kem tươi', 'kem que', 'kem ly',
            'kem ý', 'kem trang trí',
            'frosty', 'sundae', 'smoothie bowl',
            # Thương hiệu
            'abc bakery', 'tous les jours',
            'breadtalk', 'givral', 'kinh đô',
            'paris gateaux', 'brodard',
            'baskin robbins', 'swensen',
            'dairy queen'
        ],
        'icon': '🍰'
    },
    'spicy_food': {
        'name': 'Đồ cay',
        'keywords': [
        'cay', 'spicy', 'hot',
        'lẩu cay', 'lau cay', 'hot pot cay', 'hotpot cay',  # 🔥 BỎ "lẩu" đơn thuần
        'lẩu thái', 'lau thai',  # Lẩu Thái thường cay
        'lẩu tứ xuyên', 'lau tu xuyen', 'tứ xuyên', 'tu xuyen',  # Tứ Xuyên = cay
        # 🔥 XÓA: 'lẩu ếch', 'lẩu gà' (không chắc cay)
        'mì cay', 'mi cay', 'mì cay hàn quốc', 'mi cay han quoc',
        'tokbokki', 'tteokbokki',
        'gà cay', 'ga cay', 'gà rán cay', 'ga ran cay',
        'ớt', 'chili',
        'bún bò huế',  # Bún bò Huế thường cay
        'mực xào cay', 'muc xao cay',
        'đồ cay hàn', 'do cay han', 'đồ cay thái', 'do cay thai',
        'kim chi', 'kimchi',
        'sườn cay', 'suon cay',
        'phá lấu', 'pha lau'  # Phá lấu thường cay
        ],
        'icon': '🌶️'
    },
    # 🔥 THÊM KEY MỚI CHO "KHU ẨM THỰC"
    'food_street': {
        'name': 'Khu ẩm thực',
        'keywords': [],  # Không cần keywords vì xét trực tiếp cột mo_ta
        'icon': '🏪'
    },
    
    # 🔥 THÊM LUÔN CHO MICHELIN (nếu chưa có)
    'michelin': {
        'name': 'Michelin',
        'keywords': [],  # Xét trực tiếp cột mo_ta
        'icon': '⭐'
    }
}

# ==================== TỪ ĐIỂN KEYWORD CHO TỪNG BỮA ĂN ====================
MEAL_TYPE_KEYWORDS = {
    'breakfast': [
        # Món Việt sáng
        'phở', 'bún', 'bánh mì', 'cháo', 'xôi', 'hủ tiếu', 'bánh cuốn', 
        'bánh bèo', 'cơm tấm', 'mì quảng',
        # 🔥 THÊM KEYWORDS MÓN CHAY CHO BỮA SÁNG 🔥
        'chay', 'vegetarian', 'vegan', 'healthy', 'rau củ', 'rau sạch',
        'cơm chay', 'bún chay', 'phở chay', 'đậu hũ', 'tofu', 'nấm'
        # 🔥 THÊM KEYWORDS NHÀ HÀNG SANG TRỌNG 🔥
        'nhà hàng', 'restaurant', 'buffet', 'resort', 'fine dining', 'luxury'
    ],
    
    'morning_drink': [
        # Đồ uống
        'cafe', 'coffee', 'cà phê', 'trà', 'tea', 'sinh tố', 'juice', 
        'nước', 'nước ép', 'smoothie', 'sữa', 'milk', 'trà sữa',
        'matcha', 'latte', 'cappuccino', 'espresso',
        # Từ theme coffee_chill
        'highlands', 'starbucks', 'phúc long', 'trung nguyên',
        'gong cha', 'royaltea', 'ding tea', 'tocotoco', 'koi thé',
        'bobapop', 'alley', 'tiger sugar', 'passio', 'phindi'
    ],
    
    'lunch': [
        # Món chính
        'cơm', 'bún', 'mì', 'phở', 'hủ tiếu', 'cơm tấm', 'miến',
        'bánh mì', 'bánh xèo', 'cao lầu', 'mì quảng'
        # 🔥 THÊM KEYWORDS NHÀ HÀNG SANG TRỌNG 🔥
        'nhà hàng', 'restaurant', 'buffet', 'resort', 'fine dining', 'luxury'
    ],
    
    'afternoon_drink': [
        # Đồ uống
        'cafe', 'coffee', 'cà phê', 'trà', 'tea', 'trà sữa', 'milk tea', 
        'sinh tố', 'nước', 'juice', 'smoothie', 'soda',
        'matcha', 'chocolate', 'frappe',
        # Bánh nhẹ
        'bánh', 'cake', 'tiramisu', 'macaron', 'cupcake', 'donut',
        # Từ theme
        'highlands', 'starbucks', 'phúc long', 'trung nguyên',
        'gong cha', 'royaltea', 'tocotoco', 'koi thé', 'passio'
    ],
    
    'dinner': [
        # Món tối đa dạng
        'cơm', 'lẩu', 'nướng', 'hải sản', 'bún', 'mì', 'phở',
        'cơm tấm', 'nem', 'gỏi', 'cháo', 'hotpot', 'bbq',
        'sushi', 'ramen', 'dimsum', 'steak', 'bò', 'gà', 'cá', 'tôm', 'buffet'
        # 🔥 THÊM KEYWORDS NHÀ HÀNG SANG TRỌNG 🔥
        'nhà hàng', 'restaurant', 'buffet', 'resort', 'fine dining', 'luxury'
    ],
    
    'dessert': [
        # Tráng miệng
        'bánh', 'kem', 'chè', 'cake', 'ice cream', 'dessert',
        'bánh ngọt', 'bánh kem', 'tiramisu', 'macaron', 'cupcake',
        'gelato', 'frosty', 'sundae', 'mousse', 'cheesecake',
        'donut', 'cookie', 'brownie', 'tart', 'pie', 'mochi',
        # 🔥 Bakery Tiếng Anh
        'bakery', 'patisserie', 'confectionery', 'pastry'
    ],
    
    # 🔥 CHO KHOẢNG THỜI GIAN NGẮN
    'meal': [
        # Bữa chính đa dạng
        'cơm', 'bún', 'phở', 'mì', 'hủ tiếu', 'cơm tấm', 'bánh mì',
        'bánh xèo', 'nem', 'gỏi', 'cháo', 'xôi', 'cao lầu',
        # 🔥 THÊM NHÀ HÀNG 🔥
        'nhà hàng', 'restaurant', 'buffet'
    ],
    
    'meal1': [
        # Bữa chính 1
        'cơm', 'bún', 'phở', 'mì', 'hủ tiếu', 'cơm tấm', 'bánh mì',
        'bánh xèo', 'miến', 'cao lầu', 'mì quảng',
        # 🔥 THÊM NHÀ HÀNG 🔥
        'nhà hàng', 'restaurant', 'buffet'
    ],
    
    'meal2': [
        # Bữa phụ nhẹ hơn
        'cơm', 'bún', 'phở', 'mì', 'bánh mì', 'nem', 'gỏi cuốn',
        'bánh xèo', 'bánh', 'xôi', 'chè',
        # 🔥 THÊM NHÀ HÀNG 🔥
        'nhà hàng', 'restaurant'
    ],
    
    'drink': [
        # Đồ uống tổng hợp
        'cafe', 'coffee', 'cà phê', 'trà', 'tea', 'nước', 'sinh tố',
        'juice', 'smoothie', 'trà sữa', 'milk tea', 'soda', 'nước ép',
        'matcha', 'chocolate', 'latte', 'cappuccino',
        # Từ theme
        'highlands', 'starbucks', 'phúc long', 'trung nguyên',
        'gong cha', 'royaltea', 'tocotoco', 'koi thé', 'passio'
    ]
}

# ==================== FIND PLACES WITH ADVANCED FILTERS ====================

def find_places_advanced(user_lat, user_lon, df, filters, excluded_ids=None, top_n=30):
    """Tìm quán với bộ lọc nâng cao - CHỈ LỌC THEO THEME"""
    if excluded_ids is None:
        excluded_ids = set()
    
    results = []
    radius_km = filters.get('radius_km', 5)
    theme = filters.get('theme')
    # 🔥 BỎ: user_tastes = filters.get('tastes', [])

    # XỬ LÝ THEME - CÓ THỂ LÀ STRING HOẶC LIST
    if theme:
        if isinstance(theme, str):
            theme_list = [theme]
        else:
            theme_list = theme if theme else []
    else:
        theme_list = []
    
    skipped_rows = 0
    
    for idx, row in df.iterrows():
        try:
            data_id = clean_value(row.get('data_id', ''))
            
            if data_id in excluded_ids:
                continue
            
            # Parse tọa độ
            lat_str = str(row.get('lat', '')).strip().strip('"').strip()
            lon_str = str(row.get('lon', '')).strip().strip('"').strip()
            
            if not lat_str or not lon_str or lat_str == 'nan' or lon_str == 'nan':
                continue
                
            place_lat = float(lat_str)
            place_lon = float(lon_str)
            
            distance = calculate_distance(user_lat, user_lon, place_lat, place_lon)
            
            # Lọc bán kính
            if distance > radius_km:
                continue
            
            # Lọc giờ mở cửa
            gio_mo_cua = row.get('gio_mo_cua', '')
            check_time_str = filters.get('meal_time')
            ten_quan = str(row.get('ten_quan', ''))
            name_normalized = normalize_text_with_accent(ten_quan)  # ← THÊM DÒNG NÀY

            if check_time_str:
                if not is_open_now(gio_mo_cua, check_time=check_time_str, min_hours_before_close=2, place_name=ten_quan):
                    continue
            else:
                if not is_open_now(gio_mo_cua, min_hours_before_close=2, place_name=ten_quan):
                    continue
            
            # LỌC THEO THEME
            if theme:
                match_found = False
                
                for single_theme in theme_list:
                    if single_theme == 'food_street':
                        mo_ta = str(row.get('mo_ta', '')).strip().lower()
                        # 🔥 SỬA: So sánh linh hoạt hơn, bỏ dấu tiếng Việt
                        mo_ta_no_accent = normalize_text(mo_ta)  # Bỏ dấu
                        if 'khu' in mo_ta and 'am thuc' in mo_ta_no_accent:
                            match_found = True
                            break
                    
                    elif single_theme == 'michelin':
                        mo_ta = str(row.get('mo_ta', '')).strip()
                        
                        # 🔥 THÊM LOG DEBUG
                        if mo_ta.lower() == 'michelin':
                            print(f"✅ [MICHELIN MATCH] {row.get('ten_quan')} | Giờ: {row.get('gio_mo_cua')} | Check time: {filters.get('meal_time')}")
                            match_found = True
                            break
                    
                    else:
                        # Xử lý theme bình thường
                        theme_keywords = THEME_CATEGORIES[single_theme]['keywords']
                        
                        for keyword in theme_keywords:
                            keyword_normalized = normalize_text_with_accent(keyword)
                            
                            search_text = ' ' + name_normalized + ' '
                            search_keyword = ' ' + keyword_normalized + ' '
                            
                            if search_keyword in search_text:
                                match_found = True
                                break
                        
                        if match_found:
                            break
                        
                        # XÉT cột khau_vi cho spicy_food & dessert_bakery
                        if not match_found and single_theme in ['spicy_food', 'dessert_bakery']:
                            khau_vi = str(row.get('khau_vi', '')).strip().lower()
                            
                            if khau_vi:
                                if single_theme == 'spicy_food' and 'cay' in khau_vi:
                                    match_found = True
                                    break
                                elif single_theme == 'dessert_bakery' and 'ngọt' in khau_vi:
                                    match_found = True
                                    break
                
                if not match_found:
                    continue

            # 🔥 THÊM ĐOẠN NÀY NGAY SAU PHẦN LỌC THEME (sau dòng "if not match_found: continue")
            # 🔥 LỌC QUÁN NƯỚC - CHỈ CHO PHÉP KHI CÓ THEME coffee_chill
            if theme and 'coffee_chill' not in theme_list:
                # Danh sách keyword QUÁN NƯỚC cần loại bỏ
                drink_keywords = [
                    'cafe', 'coffee', 'ca phe', 'cà phê',
                    'trà', 'tea', 'trà sữa', 'milk tea',
                    'sinh tố', 'smoothie', 'juice', 'nước ép',
                    'highlands', 'starbucks', 'phúc long', 'trung nguyên',
                    'gong cha', 'royaltea', 'ding tea', 'tocotoco', 
                    'koi thé', 'koi the', 'bobapop', 'alley', 
                    'tiger sugar', 'passio', 'phindi'
                ]
                
                # Kiểm tra tên quán có chứa keyword quán nước không
                is_drink_place = False
                for drink_kw in drink_keywords:
                    drink_kw_normalized = normalize_text_with_accent(drink_kw)
                    if drink_kw_normalized in name_normalized:
                        is_drink_place = True
                        break
                
                # Nếu là quán nước → BỎ QUA
                if is_drink_place:
                    continue

            # 🔥 Lọc BÁNH MÌ KHỎI THEME dessert_bakery
            if theme and 'dessert_bakery' in theme_list:
                # Bỏ dấu để kiểm tra
                name_for_check = normalize_text(str(row.get('ten_quan', '')))
                # Loại bỏ tất cả biến thể của bánh mì
                banh_mi_variants = ['banhmi', 'banh mi', 'banhmy', 'banh my']
                if any(variant in name_for_check for variant in banh_mi_variants):
                    continue
            
            # THÊM VÀO RESULTS (phần code cũ giữ nguyên)
            results.append({
                'ten_quan': clean_value(row.get('ten_quan', '')),
                'dia_chi': clean_value(row.get('dia_chi', '')),
                'so_dien_thoai': clean_value(row.get('so_dien_thoai', '')),
                'rating': float(clean_value(row.get('rating', 0))) if pd.notna(row.get('rating')) else 0,
                'gio_mo_cua': clean_value(row.get('gio_mo_cua', '')),
                'lat': place_lat,
                'lon': place_lon,
                'distance': distance,
                'data_id': data_id,
                'hinh_anh': clean_value(row.get('hinh_anh', '')),
                'gia_trung_binh': clean_value(row.get('gia_trung_binh', '')),
                'thuc_don': clean_value(row.get('thuc_don', '')),
                'khau_vi': clean_value(row.get('khau_vi', ''))
            })
            
        except Exception as e:
            skipped_rows += 1
            continue
    
    # Sắp xếp: Khoảng cách → Rating
    results.sort(key=lambda x: (x['distance'], -x['rating']))
    return results[:top_n]

# ==================== MEAL TO THEME MAPPING ====================

MEAL_THEME_MAP = {
    # BUỔI SÁNG - Ưu tiên đồ ăn sáng Việt Nam
    'breakfast': {
        'preferred': ['street_food'],  # Ưu tiên phở, bánh mì, bún
        'fallback': ['asian_fusion', 'luxury_dining']
    },
    
    # ĐỒ UỐNG SÁNG - Cafe/trà
    'morning_drink': {
        'preferred': ['coffee_chill'],
        'fallback': ['dessert_bakery']
    },
    
    # BỮA TRƯA - Cơm/bún/mì
    'lunch': {
        'preferred': ['street_food'],
        'fallback': ['asian_fusion', 'seafood', 'spicy_food', 'luxury_dining']
    },
    
    # ĐỒ UỐNG CHIỀU - Cafe/trà sữa
    'afternoon_drink': {
        'preferred': ['coffee_chill', 'dessert_bakery'],
        'fallback': ['coffee_chill']
    },
    
    # BỮA TỐI - Đa dạng hơn
    'dinner': {
        'preferred': ['seafood', 'asian_fusion', 'spicy_food', 'luxury_dining'],
        'fallback': ['street_food']
    },
    
    # TRÁNG MIỆNG - Bánh/kem
    'dessert': {
        'preferred': ['dessert_bakery', 'coffee_chill'],
        'fallback': ['street_food']
    },
    
    # BỮA PHỤ (cho plan ngắn)
    'meal': {
        'preferred': ['street_food'],
        'fallback': ['asian_fusion']
    },
    'meal1': {
        'preferred': ['street_food'],
        'fallback': ['asian_fusion']
    },
    'meal2': {
        'preferred': ['street_food', 'asian_fusion'],
        'fallback': ['coffee_chill']
    },
    'drink': {
        'preferred': ['coffee_chill'],
        'fallback': ['dessert_bakery']
    }
}

def get_theme_for_meal(meal_key, user_selected_themes):
    """
    Chọn theme phù hợp cho từng bữa ăn
    
    Logic:
    1. Nếu user CHỌN theme → DÙNG theme ưu tiên phù hợp với bữa
    2. 🔥 FOOD_STREET / MICHELIN → TÌMẦN BÌNH THƯỜNG (không dùng theme đặc biệt cho bữa chính)
    3. Nếu KHÔNG → dùng theme mặc định theo bữa
    
    ⚠️ HÀM NÀY CHỈ DÙNG CHO 3 BỮA CHÍNH - KHÔNG ẢNH HƯỞNG ĐẾN CARD GỢI Ý
    """
    # ⚡ DANH SÁCH THEME KHÔNG PHÙ HỢP CHO TỪNG BỮA
    MEAL_RESTRICTIONS = {
        'dessert': ['michelin', 'food_street', 'luxury_dining', 'seafood', 'spicy_food'],
        'morning_drink': ['michelin', 'food_street', 'luxury_dining', 'seafood', 'asian_fusion', 'spicy_food', 'vegetarian'],
        'afternoon_drink': ['michelin', 'food_street', 'luxury_dining', 'seafood', 'asian_fusion', 'spicy_food', 'vegetarian'],
        'drink': ['michelin', 'food_street', 'luxury_dining', 'seafood', 'asian_fusion', 'spicy_food', 'vegetarian']
    }
    
    # 🔥 NẾU USER ĐÃ CHỌN THEME
    if user_selected_themes:
        # 🔥 ✅ XỬ LÝ ĐẶC BIỆT: CHỈ CHỌN DUY NHẤT food_street HOẶC michelin
        if len(user_selected_themes) == 1:
            if user_selected_themes[0] in ['food_street', 'michelin']:
                # ✅ TRẢ VỀ ĐÚNG THEME ĐẶC BIỆT
                return user_selected_themes[0]
        
        # 🔥🔥🔥 TẠO BẢN SAO ĐỂ KHÔNG GHI ĐÈ user_selected_themes GỐC 🔥🔥🔥
        themes_for_meal = user_selected_themes.copy()
        
        # 🔥🔥🔥 Xử lý cho NHIỀU THEME (có food_street/michelin + theme khác) 🔥🔥🔥
        if 'food_street' in themes_for_meal or 'michelin' in themes_for_meal:
            # Loại bỏ food_street VÀ michelin ra khỏi danh sách BỮA CHÍNH
            themes_without_special = [t for t in themes_for_meal if t not in ['food_street', 'michelin']]
            
            if themes_without_special:
                # Có theme khác → Dùng theme khác CHO BỮA NÀY
                themes_for_meal = themes_without_special
            else:
                # 🔥 CHỈ CÓ MỘT MÌNH food_street/michelin (nhưng đã xử lý ở trên rồi)
                meal_map = MEAL_THEME_MAP.get(meal_key, {'preferred': ['street_food'], 'fallback': []})
                return meal_map['preferred'][0]
        
        # Lọc bỏ theme không phù hợp với bữa này
        restricted = MEAL_RESTRICTIONS.get(meal_key, [])
        suitable_themes = [t for t in themes_for_meal if t not in restricted]
        
        # 🔥 XÁC ĐỊNH LOẠI BỮA ĂN
        is_main_meal = meal_key in ['breakfast', 'lunch', 'dinner', 'meal', 'meal1', 'meal2']
        is_drink = meal_key in ['morning_drink', 'afternoon_drink', 'drink']
        is_dessert = meal_key == 'dessert'
        
        # ⚡ Nếu LÀ BỮA ĂN CHÍNH → 🔥🔥 LOẠI BỎ COFFEE_CHILL VÀ DESSERT_BAKERY 🔥🔥
        if is_main_meal:
            food_themes = ['street_food', 'asian_fusion', 'seafood', 'spicy_food', 'luxury_dining', 'vegetarian']
            
            # 🔥 CHỈ LẤY THEME ĂN, LOẠI BỎ COFFEE/DESSERT
            suitable_food_themes = [t for t in suitable_themes if t in food_themes]
            
            if suitable_food_themes:
                # ✅ CÓ THEME ĂN → DÙNG THEME ĐẦU TIÊN
                return suitable_food_themes[0]
            else:
                # ❌ KHÔNG CÓ THEME ĂN → DÙNG MẶC ĐỊNH
                meal_map = MEAL_THEME_MAP.get(meal_key, {'preferred': ['street_food'], 'fallback': []})
                return meal_map['preferred'][0]
        
        # ⚡ Nếu LÀ BỮA DRINK → ưu tiên coffee_chill
        elif is_drink:
            if 'coffee_chill' in suitable_themes:
                return 'coffee_chill'
            elif 'dessert_bakery' in suitable_themes:
                return 'dessert_bakery'
            elif suitable_themes:
                return suitable_themes[0]
            else:
                return 'coffee_chill'
        
        # ⚡ Nếu LÀ TRÁNG MIỆNG → ưu tiên dessert_bakery
        elif is_dessert:
            # 🔥🔥 ƯU TIÊN THỨ TỰ MỚI - LOẠI BỎ LUXURY_DINING 🔥🔥
            if 'dessert_bakery' in suitable_themes:
                return 'dessert_bakery'
            elif 'street_food' in suitable_themes:
                return 'street_food'
            elif 'asian_fusion' in suitable_themes:
                return 'asian_fusion'
            elif 'coffee_chill' in suitable_themes:
                return 'coffee_chill'
            elif suitable_themes:
                # 🔥 KIỂM TRA THÊM: Nếu theme còn lại là luxury_dining → dùng mặc định
                if suitable_themes[0] == 'luxury_dining':
                    return 'dessert_bakery'  # ✅ FALLBACK về tráng miệng
                return suitable_themes[0]
            else:
                return 'dessert_bakery'
        
        # Fallback: lấy theme đầu tiên
        if suitable_themes:
            return suitable_themes[0]
        else:
            meal_map = MEAL_THEME_MAP.get(meal_key, {'preferred': ['street_food'], 'fallback': []})
            return meal_map['preferred'][0]
    
    # 🔥 Nếu USER KHÔNG CHỌN THEME → Tự động chọn theo bữa
    meal_map = MEAL_THEME_MAP.get(meal_key, {'preferred': ['street_food'], 'fallback': []})
    return meal_map['preferred'][0]

# ==================== GENERATE SMART PLAN ====================

def generate_meal_schedule(time_start_str, time_end_str, user_selected_themes):
    """
    Generate meal schedule dựa trên KHUNG GIỜ thực tế
    Hỗ trợ khung giờ qua đêm (vd: 7:00 → 6:00 sáng hôm sau)
    """
    time_start = datetime.strptime(time_start_str, '%H:%M')
    time_end = datetime.strptime(time_end_str, '%H:%M')
    
    # 🔥 NẾU GIỜ KẾT THÚC < GIỜ BẮT ĐẦU → COI LÀ NGÀY HÔM SAU
    if time_end <= time_start:
        time_end = time_end + timedelta(days=1)
    
    start_hour = time_start.hour + time_start.minute / 60.0
    end_hour = time_end.hour + time_end.minute / 60.0
    
    # 🔥 NẾU QUA ĐÊM → CỘNG 24 GIỜ CHO end_hour
    if time_end.day > time_start.day:
        end_hour += 24
    
    # 🔥 KIỂM TRA CÓ CHỌN THEME KHÔNG
    has_selected_themes = user_selected_themes and len(user_selected_themes) > 0
    
    if has_selected_themes:
        has_coffee_chill = 'coffee_chill' in user_selected_themes
        dessert_themes = {'street_food', 'asian_fusion', 'dessert_bakery', 'coffee_chill'}
        has_dessert_theme = any(theme in dessert_themes for theme in user_selected_themes)
    else:
        has_coffee_chill = True
        has_dessert_theme = True
    
    plan = {}
    
    # 🔥 HÀM HELPER: TÍNH GIỜ VÀ FORMAT
    def format_time(hour_float):
        """Chuyển số giờ (có thể > 24) thành HH:MM"""
        hour_float = hour_float % 24  # Quay vòng 24 giờ
        return f'{int(hour_float):02d}:{int((hour_float % 1) * 60):02d}'
    
    def is_in_range(target_hour, range_start, range_end):
        """Kiểm tra giờ có nằm trong khoảng không (hỗ trợ qua đêm)"""
        # Nếu target_hour < start_hour → coi như ngày hôm sau
        if target_hour < start_hour:
            target_hour += 24
        return range_start <= target_hour < range_end and start_hour <= target_hour < end_hour
    
    # 🔥 KHUNG GIỜ BỮA SÁNG (6:00 - 10:00)
    breakfast_time = max(start_hour, 7)
    if breakfast_time < start_hour:
        breakfast_time += 24
    if is_in_range(breakfast_time, 7, 10):
        plan['breakfast'] = {
            'time': format_time(breakfast_time),
            'title': 'Bữa sáng',
            'categories': ['pho', 'banh mi', 'bun'],
            'icon': '🍳'
        }
    
    # 🔥 ĐỒ UỐNG BUỔI SÁNG (9:30 - 11:30)
    if has_coffee_chill:
        morning_drink_time = max(start_hour + 1.5, 9.5)
        if morning_drink_time < start_hour:
            morning_drink_time += 24
        if is_in_range(morning_drink_time, 9.5, 11.5):
            if 'breakfast' not in plan or (morning_drink_time - start_hour >= 1.5):
                plan['morning_drink'] = {
                    'time': format_time(morning_drink_time),
                    'title': 'Giải khát buổi sáng',
                    'categories': ['tra sua', 'cafe', 'coffee'],
                    'icon': '🧋'
                }
    
    # 🔥 BỮA TRƯA (11:00 - 14:00)
    lunch_time = max(start_hour, 11.5)
    if lunch_time < start_hour:
        lunch_time += 24
    if 'breakfast' in plan:
        breakfast_hour = float(plan['breakfast']['time'].split(':')[0]) + float(plan['breakfast']['time'].split(':')[1]) / 60
        if breakfast_hour < start_hour:
            breakfast_hour += 24
        lunch_time = max(lunch_time, breakfast_hour + 3)
    
    if is_in_range(lunch_time, 11, 14):
        plan['lunch'] = {
            'time': format_time(lunch_time),
            'title': 'Bữa trưa',
            'categories': ['com tam', 'mi', 'bun'],
            'icon': '🍚'
        }
    
    # 🔥 ĐỒ UỐNG BUỔI CHIỀU (14:00 - 17:00)
    if has_coffee_chill:
        afternoon_drink_time = max(start_hour, 14.5)
        if afternoon_drink_time < start_hour:
            afternoon_drink_time += 24
        if 'lunch' in plan:
            lunch_hour = float(plan['lunch']['time'].split(':')[0]) + float(plan['lunch']['time'].split(':')[1]) / 60
            if lunch_hour < start_hour:
                lunch_hour += 24
            afternoon_drink_time = max(afternoon_drink_time, lunch_hour + 1.5)
        
        if is_in_range(afternoon_drink_time, 14, 17):
            plan['afternoon_drink'] = {
                'time': format_time(afternoon_drink_time),
                'title': 'Giải khát buổi chiều',
                'categories': ['tra sua', 'cafe', 'coffee'],
                'icon': '☕'
            }
    
    # 🔥 BỮA TỐI (17:00 - 21:00)
    dinner_time = max(start_hour, 18)
    if dinner_time < start_hour:
        dinner_time += 24
    if 'lunch' in plan:
        lunch_hour = float(plan['lunch']['time'].split(':')[0]) + float(plan['lunch']['time'].split(':')[1]) / 60
        if lunch_hour < start_hour:
            lunch_hour += 24
        dinner_time = max(dinner_time, lunch_hour + 4)
    elif 'breakfast' in plan:
        breakfast_hour = float(plan['breakfast']['time'].split(':')[0]) + float(plan['breakfast']['time'].split(':')[1]) / 60
        if breakfast_hour < start_hour:
            breakfast_hour += 24
        dinner_time = max(dinner_time, breakfast_hour + 6)
    
    if is_in_range(dinner_time, 17, 21):
        plan['dinner'] = {
            'time': format_time(dinner_time),
            'title': 'Bữa tối',
            'categories': ['com tam', 'mi cay', 'pho'],
            'icon': '🍽️'
        }
    
    # 🔥 TRÁNG MIỆNG (19:00 - 23:00)
    if has_dessert_theme:
        dessert_time = max(start_hour, 20)
        if dessert_time < start_hour:
            dessert_time += 24
        if 'dinner' in plan:
            dinner_hour = float(plan['dinner']['time'].split(':')[0]) + float(plan['dinner']['time'].split(':')[1]) / 60
            if dinner_hour < start_hour:
                dinner_hour += 24
            dessert_time = max(dessert_time, dinner_hour + 1.5)
        
        if is_in_range(dessert_time, 19, 24):  # 🔥 Đến 24h (0h)
            plan['dessert'] = {
                'time': format_time(dessert_time),
                'title': 'Tráng miệng',
                'categories': ['banh kem', 'kem', 'tra sua'],
                'icon': '🍰'
            }
    
    # 🔥 NẾU KHÔNG CÓ BỮA NÀO → TẠO BỮA MẶC ĐỊNH
    if len(plan) == 0:
        plan['meal'] = {
            'time': time_start_str,
            'title': 'Bữa ăn',
            'categories': ['pho', 'com tam', 'bun'],
            'icon': '🍜'
        }
        
        duration_hours = (time_end - time_start).seconds / 3600
        if has_coffee_chill and duration_hours >= 1.5:
            drink_time = time_start + timedelta(hours=duration_hours * 0.7)
            plan['drink'] = {
                'time': drink_time.strftime('%H:%M'),
                'title': 'Giải khát',
                'categories': ['tra sua', 'cafe'],
                'icon': '☕'
            }
    
    return plan

# ==================== ĐIỀU CHỈNH MEAL SCHEDULE DỰA TRÊN THEME ====================

def filter_meal_schedule_by_themes(plan, user_selected_themes):
    """
    🔥 LỌC VÀ ĐIỀU CHỈNH LỊCH TRÌNH DỰA TRÊN THEME USER CHỌN
    
    Logic:
    1. CHỈ chọn coffee_chill → CHỈ GIỮ 2 buổi nước (morning_drink, afternoon_drink)
    2. CHỈ chọn dessert_bakery → CHỈ GIỮ 1 buổi tráng miệng (dessert)
    3. Chọn CẢ coffee_chill + dessert_bakery (KHÔNG có theme ăn khác)
       → GIỮ 2 buổi nước + 1 tráng miệng
    4. Chọn coffee_chill/dessert_bakery + theme ăn khác 
       → GIỮ NGUYÊN (3 bữa ăn + 2 nước + 1 tráng miệng)
    5. Chọn theme ăn (street_food, asian_fusion, v.v.) 
       → GIỮ NGUYÊN
    6. KHÔNG chọn theme → GIỮ NGUYÊN
    
    Args:
        plan: Dict lịch trình từ generate_meal_schedule()
        user_selected_themes: List theme user đã chọn
    
    Returns:
        Dict lịch trình đã lọc
    """
    # ❌ KHÔNG có theme → GIỮ NGUYÊN
    if not user_selected_themes or len(user_selected_themes) == 0:
        return plan
    
    # 🔥 ĐỊNH NGHĨA THEME "ĂN"
    food_themes = {
        'street_food', 'asian_fusion', 'seafood', 'spicy_food', 
        'luxury_dining', 'vegetarian', 'michelin', 'food_street'
    }
    
    # 🔥 KIỂM TRA USER CÓ CHỌN THEME ĂN KHÔNG
    has_food_theme = any(theme in food_themes for theme in user_selected_themes)
    has_coffee = 'coffee_chill' in user_selected_themes
    has_dessert = 'dessert_bakery' in user_selected_themes
    
    # ✅ TRƯỜNG HỢP 1: CÓ THEME ĂN → GIỮ NGUYÊN
    if has_food_theme:
        return plan
    
    # ✅ TRƯỜNG HỢP 2: CHỈ CÓ COFFEE_CHILL
    if has_coffee and not has_dessert:
        filtered_plan = {}
        
        # CHỈ GIỮ CÁC BỮA NƯỚC
        drink_keys = ['morning_drink', 'afternoon_drink', 'drink']
        
        for key in drink_keys:
            if key in plan:
                filtered_plan[key] = plan[key]
        
        # ✅ NẾU KHÔNG CÓ BỮA NÀO → TẠO 2 BUỔI NƯỚC MẶC ĐỊNH
        if len(filtered_plan) == 0:
            filtered_plan['morning_drink'] = {
                'time': '09:30',
                'title': 'Giải khát buổi sáng',
                'categories': ['tra sua', 'cafe', 'coffee'],
                'icon': '🧋'
            }
            filtered_plan['afternoon_drink'] = {
                'time': '14:30',
                'title': 'Giải khát buổi chiều',
                'categories': ['tra sua', 'cafe', 'coffee'],
                'icon': '☕'
            }
        
        # Nếu chỉ có 1 buổi nước → Thêm 1 buổi nữa
        elif len(filtered_plan) == 1:
            existing_key = list(filtered_plan.keys())[0]
            existing_time = filtered_plan[existing_key]['time']
            
            # Tính thời gian buổi thứ 2 (cách 3 tiếng)
            from datetime import datetime, timedelta
            time_obj = datetime.strptime(existing_time, '%H:%M')
            new_time_obj = time_obj + timedelta(hours=3)
            new_time = new_time_obj.strftime('%H:%M')
            
            # Thêm buổi nước thứ 2
            if existing_key == 'morning_drink':
                filtered_plan['afternoon_drink'] = {
                    'time': new_time,
                    'title': 'Giải khát buổi chiều',
                    'categories': ['tra sua', 'cafe', 'coffee'],
                    'icon': '☕'
                }
            else:
                filtered_plan['morning_drink'] = {
                    'time': new_time,
                    'title': 'Giải khát buổi sáng',
                    'categories': ['tra sua', 'cafe', 'coffee'],
                    'icon': '🧋'
                }
        
        # 🔥🔥 QUAN TRỌNG: Cập nhật _order theo đúng thứ tự thời gian 🔥🔥
        filtered_plan['_order'] = sorted(
            [k for k in filtered_plan.keys() if k != '_order'],
            key=lambda k: filtered_plan[k]['time']
        )
        
        print(f"✅ Filter coffee_chill: {list(filtered_plan.keys())}")
        return filtered_plan
    
    # ✅ TRƯỜNG HỢP 3: CHỈ CÓ DESSERT_BAKERY
    if has_dessert and not has_coffee:
        filtered_plan = {}
        
        # CHỈ GIỮ BỮA TRÁNG MIỆNG
        if 'dessert' in plan:
            filtered_plan['dessert'] = plan['dessert']
        else:
            # ✅ TẠO TRÁNG MIỆNG MẶC ĐỊNH
            filtered_plan['dessert'] = {
                'time': '20:00',
                'title': 'Tráng miệng',
                'categories': ['banh kem', 'kem', 'tra sua'],
                'icon': '🍰'
            }
        
        filtered_plan['_order'] = ['dessert']
        print(f"✅ Filter dessert_bakery: {list(filtered_plan.keys())}")
        return filtered_plan
    
    # ✅ TRƯỜNG HỢP 4: CẢ COFFEE + DESSERT (KHÔNG CÓ THEME ĂN)
    if has_coffee and has_dessert:
        filtered_plan = {}
        
        # GIỮ 2 BUỔI NƯỚC
        drink_keys = ['morning_drink', 'afternoon_drink', 'drink']
        drink_count = 0
        
        for key in drink_keys:
            if key in plan and drink_count < 2:
                filtered_plan[key] = plan[key]
                drink_count += 1
        
        # ✅ NẾU KHÔNG ĐỦ 2 BUỔI NƯỚC → TẠO THÊM
        if drink_count == 0:
            filtered_plan['morning_drink'] = {
                'time': '09:30',
                'title': 'Giải khát buổi sáng',
                'categories': ['tra sua', 'cafe', 'coffee'],
                'icon': '🧋'
            }
            filtered_plan['afternoon_drink'] = {
                'time': '14:30',
                'title': 'Giải khát buổi chiều',
                'categories': ['tra sua', 'cafe', 'coffee'],
                'icon': '☕'
            }
            drink_count = 2
        elif drink_count == 1:
            existing_key = [k for k in drink_keys if k in filtered_plan][0]
            existing_time = filtered_plan[existing_key]['time']
            
            from datetime import datetime, timedelta
            time_obj = datetime.strptime(existing_time, '%H:%M')
            new_time_obj = time_obj + timedelta(hours=3)
            new_time = new_time_obj.strftime('%H:%M')
            
            if existing_key == 'morning_drink':
                filtered_plan['afternoon_drink'] = {
                    'time': new_time,
                    'title': 'Giải khát buổi chiều',
                    'categories': ['tra sua', 'cafe', 'coffee'],
                    'icon': '☕'
                }
            else:
                filtered_plan['morning_drink'] = {
                    'time': new_time,
                    'title': 'Giải khát buổi sáng',
                    'categories': ['tra sua', 'cafe', 'coffee'],
                    'icon': '🧋'
                }
            drink_count = 2
        
        # GIỮ 1 TRÁNG MIỆNG
        if 'dessert' in plan:
            filtered_plan['dessert'] = plan['dessert']
        else:
            # Tính thời gian tráng miệng (sau buổi nước cuối 2 tiếng)
            last_drink_time = max([filtered_plan[k]['time'] for k in filtered_plan.keys() if k != '_order'])
            from datetime import datetime, timedelta
            time_obj = datetime.strptime(last_drink_time, '%H:%M')
            dessert_time_obj = time_obj + timedelta(hours=2)
            dessert_time = dessert_time_obj.strftime('%H:%M')
            
            filtered_plan['dessert'] = {
                'time': dessert_time,
                'title': 'Tráng miệng',
                'categories': ['banh kem', 'kem', 'tra sua'],
                'icon': '🍰'
            }
        
        # 🔥🔥 Cập nhật _order theo đúng thứ tự thời gian 🔥🔥
        filtered_plan['_order'] = sorted(
            [k for k in filtered_plan.keys() if k != '_order'],
            key=lambda k: filtered_plan[k]['time']
        )
        
        print(f"✅ Filter coffee + dessert: {list(filtered_plan.keys())}")
        return filtered_plan
    
    # ✅ MẶC ĐỊNH: GIỮ NGUYÊN
    return plan

def generate_food_plan(user_lat, user_lon, csv_file='Data_with_flavor.csv', theme=None, user_tastes=None, start_time='07:00', end_time='21:00', radius_km=None):
    """Tạo kế hoạch ăn uống thông minh"""
    
    if radius_km is None or radius_km <= 0:
        return {
            'error': True,
            'message': 'Vui lòng chọn bán kính tìm kiếm'
        }
    
    df = pd.read_csv(csv_file)
    
    # 🔥 PARSE USER THEMES TRƯỚC
    user_selected_themes = []
    if theme:
        if isinstance(theme, str):
            user_selected_themes = [t.strip() for t in theme.split(',')]
        elif isinstance(theme, list):
            user_selected_themes = theme
    
    # 🔥 TẠO MEAL SCHEDULE
    plan = generate_meal_schedule(start_time, end_time, user_selected_themes)
    
    # 🔥🔥🔥 LỌC LỊCH TRÌNH DỰA TRÊN THEME 🔥🔥🔥
    plan = filter_meal_schedule_by_themes(plan, user_selected_themes)
    
    # 🔥🔥 THÊM DÒNG DEBUG 🔥🔥
    print(f"🔍 Plan sau filter: {list(plan.keys())}")
    
    current_lat, current_lon = user_lat, user_lon
    used_place_ids = set()
    
    places_found = 0
    keys_to_remove = []
    
    for key, meal in plan.items():
        # 🔥🔥 BỎ QUA KEY _order 🔥🔥
        if key == '_order':
            continue
            
        # 🔥 CHỌN THEME PHÙ HỢP CHO TỪNG BỮA
        meal_theme = get_theme_for_meal(key, user_selected_themes)
        
        print(f"🔍 Tìm quán cho {key} với theme {meal_theme}")
        
        filters = {
            'theme': meal_theme,
            'tastes': user_tastes if user_tastes else [],
            'radius_km': radius_km,
            'meal_time': meal['time']
        }
        
        places = find_places_advanced(
            current_lat, current_lon, df, 
            filters, excluded_ids=used_place_ids, top_n=20
        )
        
        # 🔥 LỌC ĐẶC BIỆT: Loại bánh mì khỏi bữa tráng miệng
        if key == 'dessert' and places:
            filtered_places = []
            for p in places:
                name_lower = normalize_text(p['ten_quan'])  # Dùng normalize_text (BỎ DẤU)
                # Loại bỏ tất cả quán có "banh mi" hoặc "banhmi"
                if 'banhmi' not in name_lower and 'banh mi' not in name_lower:
                    filtered_places.append(p)
            places = filtered_places
        
        # 🔥 Lọc CHẶT THEO KEYWORD - NHƯNG BỎ QUA CHO THEME ĐẶC BIỆT
        if places and key in MEAL_TYPE_KEYWORDS:
            # ⚡ KIỂM TRA XEM CÓ PHẢI THEME ĐẶC BIỆT KHÔNG
            skip_keyword_filter = False
            
            if meal_theme in ['food_street', 'michelin', 'luxury_dining']:
                skip_keyword_filter = True
                print(f"⚡ Theme đặc biệt '{meal_theme}' - BỎ QUA lọc keyword")
            
            # ⚡ CHỈ LỌC NẾU KHÔNG PHẢI THEME ĐẶC BIỆT
            if not skip_keyword_filter:
                meal_keywords = MEAL_TYPE_KEYWORDS[key]
                filtered_places = []
                
                for place in places:
                    name_normalized = normalize_text_with_accent(place['ten_quan'])
                    
                    for kw in meal_keywords:
                        kw_normalized = normalize_text_with_accent(kw)
                        search_text = ' ' + name_normalized + ' '
                        search_keyword = ' ' + kw_normalized + ' '
                        
                        if search_keyword in search_text:
                            filtered_places.append(place)
                            break
                
                places = filtered_places
                print(f"✅ Đã lọc keyword cho theme '{meal_theme}', còn {len(places)} quán")
            else:
                print(f"⚡ Giữ nguyên {len(places)} quán cho theme '{meal_theme}'")
        
        if places:
            places_found += 1
            weights = [1.0 / (i + 1) for i in range(len(places))]
            best_place = random.choices(places, weights=weights, k=1)[0]
            
            used_place_ids.add(best_place['data_id'])
            
            travel_time = estimate_travel_time(best_place['distance'])
            arrive_time = datetime.strptime(meal['time'], '%H:%M')
            suggest_leave = (arrive_time - timedelta(minutes=travel_time)).strftime('%H:%M')
            
            meal['place'] = {
                'ten_quan': best_place['ten_quan'],
                'dia_chi': best_place['dia_chi'],
                'rating': best_place['rating'],
                'lat': best_place['lat'],
                'lon': best_place['lon'],
                'distance': round(best_place['distance'], 2),
                'travel_time': travel_time,
                'suggest_leave': suggest_leave,
                'data_id': best_place['data_id'],
                'hinh_anh': best_place['hinh_anh'],
                'gia_trung_binh': best_place['gia_trung_binh'],
                'khau_vi': best_place['khau_vi'],
                'gio_mo_cua': best_place['gio_mo_cua'] 
            }
            
            current_lat = best_place['lat']
            current_lon = best_place['lon']
        else:
            # 🔥 KHÔNG CÓ QUÁN PHÙ HỢP → ĐÁNH DẤU XÓA
            print(f"⚠️ Không tìm được quán phù hợp cho {{key}} ({{meal['title']}}), bỏ bữa này")
            keys_to_remove.append(key)  # 🔥 THÊM VÀO LIST THAY VÌ XÓA NGAY
    
    # 🔥 XÓA CÁC BỮA KHÔNG TÌM ĐƯỢC QUÁN SAU KHI DUYỆT XONG
    for key in keys_to_remove:
        del plan[key]
    
    if places_found == 0:
        return {
            'error': True,
            'message': f'Không tìm thấy quán nào trong bán kính {{radius_km}} km'
        }
    
    return plan

# ==================== HTML INTERFACE ====================

def get_food_planner_html():
    """Trả về HTML cho Food Planner - Version 2"""
    return '''
<!-- Leaflet Polyline Offset Plugin -->
<script src="https://cdn.jsdelivr.net/npm/leaflet-polylineoffset@1.1.1/leaflet.polylineoffset.min.js"></script>
<style>
/* ========== FLOATING BUTTON ========== */
.food-planner-btn {
    position: fixed;
    bottom: 230px; /* đặt cao hơn nút 🍜 khoảng 80px */
    right: 30px;
    width: 56px;
    height: 56px;
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    border-radius: 50%;
    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9998;
    transition: all 0.2s ease;
}

.food-planner-btn:hover {
    transform: scale(1.05);
    box-shadow: 0 6px 16px rgba(255, 107, 53, 0.4);
}

.food-planner-btn svg {
    width: 28px;
    height: 28px;
    fill: white;
}

/* ========== ROUTE TOOLTIP ========== */
.route-tooltip {
    background: rgba(0, 0, 0, 0.8) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
}

.route-tooltip::before {
    border-top-color: rgba(0, 0, 0, 0.8) !important;
}

.route-number-marker {
    background: none !important;
    border: none !important;
}

/* ========== SIDE PANEL ========== */
.food-planner-panel {
    position: fixed;
    top: 160px;
    right: -30%;
    width: 30%;
    height: calc(100% - 160px);
    max-height: calc(100vh - 60px);
    background: white;
    z-index: 9999999999999 !important;
    transition: right 0.3s ease;
    display: flex;
    flex-direction: column;
    /* ❌ bỏ overflow-y: auto ở đây */
    overflow: visible; /* ✅ để panel không trở thành scroll container */
}

.food-planner-panel.active {
    right: 0;
}


.panel-header {
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    color: white;
    padding: 18px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    gap: 16px; /* 🔥 THÊM khoảng cách giữa title và nút */
}

.panel-header h2 {
    font-size: 18px;
    font-weight: 600;
    margin: 0;
    flex: 1; /* 🔥 THÊM: cho phép title chiếm không gian còn lại */
}

.header-actions {
    display: flex;
    gap: 8px;
}

.header-btn {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.header-btn:hover {
    background: rgba(255, 255, 255, 0.3);
}

.header-btn svg {
    width: 16px;
    height: 16px;
    fill: white;
}

/* ========== CONTENT AREA ========== */
.panel-content {
    flex: 1;
    position: relative;        /* ✅ thêm dòng này cho chắc */
    overflow-y: auto;          /* ✅ đây mới là thằng scroll chính */
    padding: 20px;
    padding-top: 10px;
}

/* THAY BẰNG */
.tab-content {
    height: auto;
    min-height: 500px; /* Nếu muốn giữ chiều cao tối thiểu */
}

.food-planner-panel .tab-content {
    height: auto !important;
    max-height: none !important;
    min-height: 0 !important;
}

.food-planner-panel .tab-content.active {
    height: auto !important;
    display: block !important;
}

/* 🔥 BẮT BUỘC: bỏ overflow trên tab-content trong panel
   để sticky dùng scroll của .panel-content */
.food-planner-panel .tab-content,
.food-planner-panel .tab-content.active {
    overflow: visible !important;
}
/* ========== NEW FILTERS DESIGN ========== */
.filters-wrapper-new {
    padding: 0;
    margin-bottom: 20px;
}

.filter-section-new {
    background: linear-gradient(135deg, #FFFFFF 0%, #F8F9FA 100%);
    border: 2px solid #E9ECEF;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
    transition: all 0.3s ease;
}

.filter-section-new:hover {
    border-color: #FF6B35;
    box-shadow: 0 6px 24px rgba(255, 107, 53, 0.12);
}

.section-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 2px solid rgba(255, 107, 53, 0.1);
}

.section-icon {
    font-size: 28px;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.section-title {
    font-size: 16px;
    font-weight: 700;
    color: #333;
    margin: 0;
}

/* ❤️ THEME GRID REDESIGN */
.theme-grid-new {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
}

.theme-grid-new .theme-card {
    background: white;
    border: 2px solid #E9ECEF;
    border-radius: 12px;
    padding: 16px 12px;
    cursor: pointer;
    transition: all 0.25s ease;
    text-align: center;
    position: relative;
    overflow: hidden;
}

.theme-grid-new .theme-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, rgba(255, 107, 53, 0.1) 0%, rgba(255, 142, 83, 0.1) 100%);
    opacity: 0;
    transition: opacity 0.3s ease;
}

.theme-grid-new .theme-card:hover {
    border-color: #FF6B35;
    transform: translateY(-4px);
    box-shadow: 0 8px 20px rgba(255, 107, 53, 0.2);
}

.theme-grid-new .theme-card:hover::before {
    opacity: 1;
}

.theme-grid-new .theme-card.selected {
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    border-color: #FF6B35;
    color: white;
    transform: scale(1.05);
    box-shadow: 0 8px 24px rgba(255, 107, 53, 0.4);
}

.theme-grid-new .theme-card.selected::before {
    opacity: 0;
}

.theme-grid-new .theme-icon {
    font-size: 32px;
    margin-bottom: 8px;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
    transition: transform 0.3s ease;
}

.theme-grid-new .theme-card:hover .theme-icon {
    transform: scale(1.2) rotate(5deg);
}

.theme-grid-new .theme-card.selected .theme-icon {
    transform: scale(1.1);
}

.theme-grid-new .theme-name {
    font-size: 13px;
    font-weight: 600;
    line-height: 1.3;
}

/* ⏰ TIME PICKER REDESIGN */
.time-picker-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    background: white;
    padding: 16px;
    border-radius: 12px;
    border: 2px solid #E9ECEF;
}

.time-picker-group {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.time-label {
    font-size: 13px;
    font-weight: 600;
    color: #666;
    text-align: center;
}

.time-input-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%);
    padding: 12px;
    border-radius: 12px;
    border: 2px solid #FFD699;
}

.time-input {
    width: 52px;
    height: 48px;
    padding: 0;
    border: 2px solid #FF6B35;
    border-radius: 10px;
    font-size: 20px;
    font-weight: 700;
    text-align: center;
    background: white;
    color: #FF6B35;
    outline: none;
    transition: all 0.2s ease;
}

.time-input:focus {
    border-color: #FF8E53;
    box-shadow: 0 0 0 4px rgba(255, 107, 53, 0.1);
    transform: scale(1.05);
}

.time-separator {
    font-size: 24px;
    font-weight: 700;
    color: #FF6B35;
}

.time-arrow {
    font-size: 24px;
    color: #FF6B35;
    font-weight: 700;
    flex-shrink: 0;
}

/* 🎯 BUTTON REDESIGN */
.generate-btn-new {
    width: 100%;
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    color: white;
    border: none;
    padding: 18px 24px;
    border-radius: 16px;
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    box-shadow: 0 6px 20px rgba(255, 107, 53, 0.3);
    position: relative;
    overflow: hidden;
}

.generate-btn-new::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    transition: left 0.5s ease;
}

.generate-btn-new:hover::before {
    left: 100%;
}

.generate-btn-new:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(255, 107, 53, 0.4);
}

.generate-btn-new:active {
    transform: translateY(0);
}

.btn-icon {
    font-size: 20px;
}

.btn-text {
    font-size: 16px;
}

.btn-arrow {
    font-size: 20px;
    transition: transform 0.3s ease;
}

.generate-btn-new:hover .btn-arrow {
    transform: translateX(4px);
}

/* 📱 RESPONSIVE */
@media (max-width: 768px) {
    .theme-grid-new {
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
    }
    
    .time-picker-container {
        flex-direction: column;
        gap: 12px;
    }
    
    .time-arrow {
        transform: rotate(90deg);
    }
    
    .time-picker-group {
        width: 100%;
    }
}


/* ========== SAVED PLANS SECTION ========== */
.saved-plans-section {
    background: linear-gradient(135deg, #FFF9F5 0%, #FFF5F0 100%);
    border: 2px solid #FFE5D9;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 4px 16px rgba(255, 107, 53, 0.1);
}

.saved-plans-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    margin-bottom: 15px;
    padding: 10px;
    background: white;
    border-radius: 12px;
    transition: all 0.2s ease;
}

.saved-plans-header:hover {
    background: #FFF5F0;
    transform: translateY(-2px);
}

.saved-plans-header .filter-title {
    font-size: 16px !important;
    font-weight: 700 !important;
    color: #FF6B35 !important;
}

.saved-plans-list {
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease;
}

.saved-plans-list.open {
    max-height: 400px;
    overflow-y: auto;
}

.saved-plan-item {
    background: white;
    border: 2px solid #FFE5D9;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.saved-plan-item:hover {
    border-color: #FF6B35;
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(255, 107, 53, 0.15);
}

.saved-plan-info {
    flex: 1;
}

.saved-plan-name {
    font-weight: 700;
    color: #333;
    font-size: 15px;
    margin-bottom: 6px;
    max-width: 180px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.saved-plan-date {
    font-size: 13px;
    color: #999;
    font-weight: 500;
}

.delete-plan-btn {
    background: #e74c3c;
    color: white;
    border: none;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.delete-plan-btn:hover {
    background: #c0392b;
}

/* ========== STYLE TÊN PLAN KHI EDIT ========== */
.schedule-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* 🔥 Icon emoji - cố định, KHÔNG di chuyển */
.schedule-title > span:first-child {
    flex-shrink: 0;
}

/* 🔥 Container cho text - có overflow */
.schedule-title > span:last-child {
    flex: 1;
    min-width: 0;
    max-width: 280px;
    overflow: hidden;
    position: relative;
}

/* 🔥 Text bên trong - MẶC ĐỊNH KHÔNG chạy */
.schedule-title > span:last-child > span {
    display: inline-block;
    white-space: nowrap;
    animation: none; /* 🔥 Mặc định tắt */
}

/* 🔥 CHỈ CHẠY khi có class "overflow" */
.schedule-title > span:last-child.overflow > span {
    animation: marquee 10s ease-in-out infinite;
}

/* 🔥 Animation chạy qua lại - mượt mà hơn */
@keyframes marquee {
    0% {
        transform: translateX(0);
    }
    40% {
        transform: translateX(calc(-100% + 100px)); /* Chạy sang trái */
    }
    50% {
        transform: translateX(calc(-100% + 100px)); /* Dừng lại lâu hơn */
    }
    60% {
        transform: translateX(calc(-100% + 100px)); /* Dừng tiếp */
    }
    100% {
        transform: translateX(0); /* Chạy về phải */
    }
}

/* ========== KHI Ở CHẾ ĐỘ EDIT - KHUNG VIỀN CAM GRADIENT CỐ ĐỊNH ========== */
.schedule-title > span[contenteditable="true"] {
    border: 3px solid transparent;
    background: linear-gradient(white, white) padding-box,
                linear-gradient(to right, #FF6B35, #FF8E53) border-box;
    border-radius: 8px;
    padding: 6px 10px;
    width: 100%;
    max-width: 180px; /* 🔥 THU NHỎ lại để tránh nút + */
    min-width: 150px;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
    display: block;
    outline: none;
    cursor: text;
    box-sizing: border-box;
    margin-right: 8px; /* 🔥 THÊM khoảng cách với nút bên phải */
}

/* 🔥 TẮT ANIMATION khi đang edit */
.schedule-title > span[contenteditable="true"] > span {
    animation: none !important;
    transform: none !important;
}

/* 🔥 Ẩn scrollbar nhưng vẫn scroll được */
.schedule-title > span[contenteditable="true"]::-webkit-scrollbar {
    height: 3px;
}

.schedule-title > span[contenteditable="true"]::-webkit-scrollbar-thumb {
    background: linear-gradient(to right, #FF6B35, #FF8E53);
    border-radius: 10px;
}

.schedule-title > span[contenteditable="true"]::-webkit-scrollbar-track {
    background: #FFE5D9;
}

/* ========== TIMELINE VERTICAL - REDESIGN ========== */
.timeline-container {
    position: relative;
    padding: 20px 0;
    margin-top: 20px;
}

.timeline-line {
    position: absolute;
    left: 50%;
    top: 0;
    bottom: 0;
    width: 4px;
    background: linear-gradient(to bottom, #FF6B35, #FF8E53);
    transform: translateX(-50%);
    z-index: 0;
}

.meal-item {
    position: relative;
    margin-bottom: 30px;
    padding: 0;
    z-index: 1;
}

.meal-item:last-child {
    margin-bottom: 0;
}

.meal-item.dragging {
    opacity: 0.5;
}

/* ========== TIME MARKER - TRÊN ĐẦU CARD ========== */
.time-marker {
    position: relative;
    text-align: center;
    margin-bottom: 12px;
    z-index: 2;
}

.time-badge {
    display: inline-block;
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    color: white;
    padding: 10px 24px;
    border-radius: 25px;
    font-size: 16px;
    font-weight: 700;
    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
    white-space: nowrap;
    letter-spacing: 0.5px;
    border: 3px solid white;
}

/* ========== TIME DOT - ẨN ĐI ========== */
.time-dot {
    display: none;
}

.meal-card-vertical {
    background: linear-gradient(135deg, #FFF9F5 0%, #FFF5F0 100%);
    border: 2px solid #FFE5D9;
    border-radius: 16px;
    padding: 20px;
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: visible;
    box-shadow: 0 4px 16px rgba(255, 107, 53, 0.1);
    width: 100%;
}

.meal-card-vertical::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 6px;
    height: 100%;
    background: linear-gradient(to bottom, #FF6B35, #FF8E53);
    border-radius: 16px 0 0 16px;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.meal-card-vertical:hover {
    border-color: #FF6B35;
    box-shadow: 0 8px 32px rgba(255, 107, 53, 0.2);
    transform: translateY(-4px);
}

.meal-card-vertical:hover::before {
    opacity: 1;
}

.meal-card-vertical.edit-mode {
    cursor: default;
    background: linear-gradient(135deg, #FAFBFC 0%, #F5F7FA 100%);
}

.meal-card-vertical.empty-slot {
    background: linear-gradient(135deg, #F0F9FF 0%, #E0F2FE 100%);
    border: 2px dashed #4caf50;
    cursor: default;
}

.meal-card-vertical.empty-slot:hover {
    border-color: #45a049;
    background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
    transform: none;
}

/* 🔥 CARD VÀNG GOLD CHO KHU ẨM THỰC & MICHELIN - GIỐNG CARD GỢI Ý */
.meal-card-vertical.gold-card {
    background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%) !important;
    border: 3px dashed #FFB84D !important;
    box-shadow: 
        0 6px 20px rgba(255, 184, 77, 0.25),
        0 2px 8px rgba(255, 184, 77, 0.15) !important;
    position: relative;
    overflow: hidden;
}

/* ✨ HOVER STATE */
.meal-card-vertical.gold-card:hover {
    border-color: #FFA500 !important;
    box-shadow: 
        0 8px 28px rgba(255, 165, 0, 0.35),
        0 4px 12px rgba(255, 184, 77, 0.25) !important;
    transform: translateY(-4px);
}

/* 📝 PHẦN TIÊU ĐỀ */
.meal-card-vertical.gold-card .meal-title-vertical {
    border-bottom: 2px solid rgba(255, 184, 77, 0.2) !important;
}

/* 📦 PHẦN THÔNG TIN QUÁN */
.meal-card-vertical.gold-card .place-info-vertical {
    background: #FFFEF5 !important;
    border: 1px solid rgba(255, 184, 77, 0.2) !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
}

/* 🏷️ TÊN QUÁN */
.meal-card-vertical.gold-card .place-name-vertical {
    color: #FF6B35 !important;
    font-weight: 700 !important;
}

/* 📊 META ITEMS */
.meal-card-vertical.gold-card .meta-item-vertical {
    background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%) !important;
    border: 1px solid #FFD699 !important;
    color: #8B6914 !important;
    font-weight: 600 !important;
}

/* 🔧 EDIT MODE */
.meal-card-vertical.gold-card.edit-mode {
    background: linear-gradient(135deg, #FFF9E6 0%, #FFEFC7 100%) !important;
    border-color: #FFB84D !important;
    border-style: solid !important;
}

/* 🎆 HIỆU ỨNG KHI DRAG/DROP */
.meal-card-vertical.gold-card.just-dropped,
.meal-card-vertical.gold-card.repositioned {
    animation: goldPulse 1.5s ease-in-out;
}

@keyframes goldPulse {
    0%, 100% {
        background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%);
        border-color: #FFB84D;
        box-shadow: 0 0 0 0 rgba(255, 184, 77, 0);
    }
    25% {
        background: linear-gradient(135deg, #FFE5B3 0%, #FFD699 100%);
        border-color: #FFA500;
        box-shadow: 0 0 0 8px rgba(255, 184, 77, 0.3);
    }
    50% {
        background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%);
        border-color: #FFB84D;
        box-shadow: 0 0 0 0 rgba(255, 184, 77, 0);
    }
    75% {
        background: linear-gradient(135deg, #FFE5B3 0%, #FFD699 100%);
        border-color: #FFA500;
        box-shadow: 0 0 0 8px rgba(255, 184, 77, 0.3);
    }
}

/* ========== HIGHLIGHT EFFECT KHI SẮP XẾP LẠI ========== */
@keyframes repositionPulse {
    0%, 100% {
        background: #FFF5F0;
        border-color: #FFE5D9;
        box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
    }
    25% {
        background: #E8F5E9;
        border-color: #4caf50;
        box-shadow: 0 0 0 8px rgba(76, 175, 80, 0.3);
    }
    50% {
        background: #FFF5F0;
        border-color: #FFE5D9;
        box-shadow: 0 0 0 0 rgba(76, 175, 80, 0);
    }
    75% {
        background: #E8F5E9;
        border-color: #4caf50;
        box-shadow: 0 0 0 8px rgba(76, 175, 80, 0.3);
    }
}

/* ========== DRAG & DROP VISUAL FEEDBACK ========== */
.meal-item[draggable="true"] {
    cursor: move;
}

.meal-item[draggable="true"]:active {
    cursor: grabbing;
}

.meal-item.dragging {
    opacity: 0.5;
}

.meal-item.drag-over {
    transform: scale(1.02);
    transition: transform 0.2s ease;
}

.meal-card-vertical.drop-target {
    border: 2px dashed #4caf50 !important;
    background: #E8F5E9 !important;
}

.meal-card-vertical.just-dropped {
    animation: repositionPulse 1.5s ease-in-out;
}

.meal-card-vertical.repositioned {
    animation: repositionPulse 1.5s ease-in-out;
}

/* Icon di chuyển lên/xuống */
.reposition-indicator {
    position: absolute;
    right: 10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 24px;
    animation: slideIndicator 0.8s ease-out;
    pointer-events: none;
    z-index: 100;
}

@keyframes slideIndicator {
    0% {
        opacity: 0;
        transform: translateY(-50%) scale(0.5);
    }
    50% {
        opacity: 1;
        transform: translateY(-50%) scale(1.2);
    }
    100% {
        opacity: 0;
        transform: translateY(-50%) scale(0.8);
    }
}


.meal-title-vertical {
    font-size: 16px;
    font-weight: 700;
    color: #333;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 12px;
    border-bottom: 2px solid rgba(255, 107, 53, 0.1);
}

.meal-title-left {
    display: flex;
    align-items: center;
    gap: 10px;
}

.meal-title-left > span:first-child {
    font-size: 24px;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
}

.meal-title-left {
    display: flex;
    align-items: center;
    gap: 8px;
}

/* ========== MEAL ACTIONS - REDESIGN ========== */
.meal-actions {
    display: none;
    gap: 10px;
    flex-wrap: nowrap; /* ✅ BẮT BUỘC NGANG HÀNG */
    align-items: center; /* ✅ CĂNG GIỮA */
}

.meal-card-vertical.edit-mode .meal-actions {
    display: flex;
}

/* ✅ NÚT CƠ BẢN - TO HƠN, RÕ RÀNG HƠN */
.meal-action-btn {
    background: white;
    border: 2px solid #e9ecef;
    padding: 10px 16px;
    border-radius: 12px;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    font-size: 14px;
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
    position: relative;
    overflow: hidden;
    white-space: nowrap;
    min-height: 44px;
    outline: none; /* ✅ XÓA VIỀN ĐEN */
}

/* ✅ XÓA OUTLINE KHI FOCUS/ACTIVE */
.meal-action-btn:focus,
.meal-action-btn:active {
    outline: none;
}

.meal-action-btn:hover::before {
    opacity: 1;
}

/* ✅ ĐẢM BẢO ICON + TEXT Ở TRÊN */
.meal-action-btn .btn-icon,
.meal-action-btn .btn-text {
    position: relative;
    z-index: 1;
}

.meal-action-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    background: #f8f9fa; /* ✅ THÊM DÒNG NÀY */
    border-color: inherit;
}

.meal-action-btn:active {
    transform: translateY(0);
}

/* ✅ ICON + TEXT TRONG NÚT */
.meal-action-btn .btn-icon {
    font-size: 18px;
    line-height: 1;
    z-index: 1;
}

.meal-action-btn .btn-text {
    font-size: 13px;
    font-weight: 700;
    z-index: 1;
}

/* ========== NÚT XÓA - ĐỎ RÕ RÀNG ========== */
.meal-action-btn.delete-meal {
    background: linear-gradient(135deg, #fee 0%, #fdd 100%);
    border-color: #e74c3c;
    color: #c0392b;
}

.meal-action-btn.delete-meal:hover {
    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
    border-color: #c0392b;
    color: white;
    box-shadow: 0 4px 16px rgba(231, 76, 60, 0.4);
}

/* ========== NÚT CHỌN QUÁN - XANH LÁ NỔI BẬT ========== */
.meal-action-btn.select-meal {
    background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
    border: 2px solid #4caf50;
    color: #2e7d32;
    flex: 1; /* ✅ Chiếm nhiều không gian hơn */
    min-width: 140px; /* ✅ Đủ rộng để hiển thị text */
}

.meal-action-btn.select-meal:hover {
    background: linear-gradient(135deg, #66bb6a 0%, #4caf50 100%);
    border-color: #45a049;
    color: white;
    box-shadow: 0 4px 16px rgba(76, 175, 80, 0.4);
}

/* ✅ TRẠNG THÁI ACTIVE - ĐANG CHỜ CHỌN */
.meal-action-btn.select-meal.active {
    background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
    border-color: #2e7d32;
    color: white;
    animation: selectPulse 1.5s ease-in-out infinite;
    box-shadow: 0 0 0 4px rgba(76, 175, 80, 0.2);
}

@keyframes selectPulse {
    0%, 100% { 
        box-shadow: 0 0 0 4px rgba(76, 175, 80, 0.2);
        transform: scale(1);
    }
    50% { 
        box-shadow: 0 0 0 8px rgba(76, 175, 80, 0.1);
        transform: scale(1.03);
    }
}

/* ✅ RESPONSIVE - MOBILE */
@media (max-width: 768px) {
    .meal-actions {
        width: 100%;
        flex-wrap: nowrap; /* ✅ VẪN NGANG TRÊN MOBILE */
    }
    
    .meal-action-btn {
        flex: 1;
        min-width: 0;
        padding: 8px 10px; /* ✅ THU NHỎ PADDING */
    }
    
    .meal-action-btn.select-meal {
        min-width: 0;
    }
    
    .meal-action-btn .btn-text {
        font-size: 11px; /* ✅ CHỮ NHỎ HƠN */
    }
    
    .meal-action-btn .btn-icon {
        font-size: 16px; /* ✅ ICON NHỎ HƠN */
    }
}

.place-info-vertical {
    background: white;
    border-radius: 12px;
    padding: 16px;
    margin-top: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(255, 107, 53, 0.1);
}

.place-name-vertical {
    font-weight: 700;
    color: #FF6B35;
    margin-bottom: 8px;
    font-size: 15px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.place-name-vertical::before {
    content: '🍽️';
    font-size: 18px;
}

.place-address-vertical {
    color: #666;
    font-size: 13px;
    margin-bottom: 12px;
    line-height: 1.5;
    padding-left: 20px;
    position: relative;
}

.place-name-vertical {
    font-weight: 600;
    color: #FF6B35;
    margin-bottom: 5px;
    font-size: 14px;
}

.place-address-vertical {
    color: #666;
    font-size: 12px;
    margin-bottom: 10px;
    line-height: 1.4;
}

.place-meta-vertical {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 13px;
    margin-bottom: 12px;
}

.meta-item-vertical {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%);
    border-radius: 20px;
    color: #8B6914;
    font-weight: 600;
    border: 1px solid #FFD699;
}

.meta-item-vertical span {
    font-size: 16px;
}

.meta-item-vertical {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #666;
}

.travel-info-vertical {
    background: #FFF5E6;
    border-left: 3px solid #FFB84D;
    padding: 8px 10px;
    margin-top: 10px;
    border-radius: 4px;
    font-size: 12px;
    color: #8B6914;
    line-height: 1.4;
}

.time-input-inline {
    padding: 6px 10px;
    border: 2px solid #FFE5D9;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    outline: none;
    width: 100px;
    text-align: center;
}

.time-input-inline:focus {
    border-color: #FF6B35;
}

.empty-slot-content {
    text-align: center;
    padding: 20px;
    color: #4caf50;
}

.empty-slot-content .icon {
    font-size: 32px;
    margin-bottom: 8px;
}

.empty-slot-content .text {
    font-size: 14px;
    font-weight: 600;
}

/* ========== ACTION BUTTONS ========== */
.action-btn {
    min-width: 52px;
    height: 52px;
    border-radius: 26px;
    border: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 16px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    flex-shrink: 0;
    font-size: 15px;
    font-weight: 700;
    position: relative;
    overflow: hidden;
}

.action-btn::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 0;
    height: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.3);
    transform: translate(-50%, -50%);
    transition: width 0.6s, height 0.6s;
}

.action-btn:hover::before {
    width: 300px;
    height: 300px;
}

.action-btn:hover {
    transform: translateY(-4px) scale(1.05);
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}
/* 🔥 STYLE ĐẶC BIỆT CHO NÚT THOÁT */
.action-btn[onclick*="exitSharedPlanView"]:hover {
    background: linear-gradient(135deg, #c0392b 0%, #e74c3c 100%) !important;
    box-shadow: 0 8px 24px rgba(231, 76, 60, 0.4) !important;
}

.action-btn:active {
    transform: translateY(-2px) scale(1.02);
    transition: all 0.1s;
}

/* 🔥 NÚT EDIT (CAM) */
.action-btn.edit {
    background: linear-gradient(135deg, #FFA500 0%, #FF8C00 100%);
    color: white;
}

.action-btn.edit:hover {
    background: linear-gradient(135deg, #FFB84D 0%, #FFA500 100%);
    box-shadow: 0 8px 24px rgba(255, 165, 0, 0.4);
}

.action-btn.edit.active {
    background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
    animation: editPulse 2s infinite;
}

.action-btn.edit.active:hover {
    background: linear-gradient(135deg, #66bb6a 0%, #4caf50 100%);
    box-shadow: 0 8px 24px rgba(76, 175, 80, 0.4);
}

@keyframes editPulse {
    0%, 100% {
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
    }
    50% {
        box-shadow: 0 4px 20px rgba(76, 175, 80, 0.6);
    }
}

/* 🔥 NÚT LƯU (ĐỎ CAM GRADIENT) */
.action-btn.primary {
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    color: white;
}

.action-btn.primary:hover {
    background: linear-gradient(135deg, #FF8E53 0%, #FFB84D 100%);
    box-shadow: 0 8px 24px rgba(255, 107, 53, 0.4);
}

.action-btn.add {
    background: #4caf50;
    color: white;
}

.action-btn.add:hover {
    background: #45a049;
}

.action-btn svg {
    width: 22px;
    height: 22px;
    fill: white;
    z-index: 1;
    flex-shrink: 0;
}

.btn-label {
    z-index: 1;
    white-space: nowrap;
    color: white;
    font-size: 15px;
    font-weight: 700;
}

/* 🔥 NÚT CHIA SẺ (XANH DƯƠNG) */
.action-btn.share {
    background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
    color: white;
}

.action-btn.share:hover {
    background: linear-gradient(135deg, #42A5F5 0%, #2196F3 100%);
    box-shadow: 0 8px 24px rgba(33, 150, 243, 0.4);
}

/* ========== SCHEDULE HEADER ========== */
.schedule-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    background: white;
    z-index: 100; /* 🔥 TĂNG Z-INDEX */
    padding: 16px 20px;
    border-bottom: 2px solid #FFE5D9;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    margin: 0;
    margin-bottom: 0 !important;
}

/* 🔥 ĐẢM BẢO PANEL CONTENT KHÔNG CÓ PADDING TOP */
.panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 0; /* 🔥 BỎ PADDING TOP */
    padding-bottom: 20px; /* 🔥 CHỈ GIỮ PADDING BOTTOM */
}

/* 🔥 THÊM PADDING CHO NỘI DUNG BÊN TRONG */
.filters-wrapper-new,
.saved-plans-section,
#planResult {
    margin: 20px; /* 🔥 THÊM MARGIN CHO CÁC PHẦN TỬ CON */
}

/* 🔥 TIMELINE CONTAINER KHÔNG CẦN PADDING TOP */
.timeline-container {
    position: relative;
    padding: 0 0 20px 0; /* 🔥 BỎ PADDING TOP */
    margin-top: 0; /* 🔥 BỎ MARGIN TOP */
}

.schedule-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
    max-width: 280px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.action-buttons {
    display: flex;
    flex-direction: row-reverse;
    gap: 10px;
}

/* ========== STYLE INPUT TÊN CARD ========== */
.meal-title-input {
    padding: 4px 8px;
    border: 2px solid #FFE5D9;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    outline: none;
    width: 160px;
    background: white; /* 🔥 THÊM background */
}

.meal-title-input:focus {
    border-color: #FF6B35;
}

.meal-tick-btn:hover {
    transform: scale(1.15);
    opacity: 0.8;
}

/* ========== MOBILE RESPONSIVE ========== */
@media (max-width: 768px) {
    .food-planner-panel {
        width: 100%;
        right: -100%;
    }
    
    .timeline-container {
        padding: 20px 0;
    }
    
    .meal-item {
        padding: 0;
        margin-bottom: 30px;
    }
    
    .time-dot {
        width: 16px;
        height: 16px;
    }
    
    .food-planner-btn {
        right: 20px;
    }
    
    .time-badge {
        padding: 8px 20px;
        font-size: 14px;
    }
}

/* ========== AUTO-SCROLL ZONE INDICATOR ========== */
.panel-content.scrolling-up::before,
.panel-content.scrolling-down::after {
    content: '';
    position: fixed;
    left: 0;
    right: 0;
    height: 200px;
    pointer-events: none;
    z-index: 999;
    animation: scrollZonePulse 1s infinite;
}

.panel-content.scrolling-up::before {
    top: 60px; /* Dưới header */
    background: linear-gradient(to bottom, rgba(76, 175, 80, 0.1), transparent);
}

.panel-content.scrolling-down::after {
    bottom: 0;
    background: linear-gradient(to top, rgba(76, 175, 80, 0.1), transparent);
}

@keyframes scrollZonePulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 0.8; }
}

/* 🔥 CHẶN SCROLL KHI HOVER VÀO INPUT GIỜ/PHÚT */
.time-input-hour:hover,
.time-input-minute:hover {
    overscroll-behavior: contain;
}

/* 🔥 CHẶN SCROLL TOÀN BỘ PANEL KHI FOCUS VÀO INPUT */
.panel-content:has(.time-input-hour:focus),
.panel-content:has(.time-input-minute:focus) {
    overflow: hidden !important;
}

/* ========== TOOLTIP HƯỚNG DẪN ========== */
.meal-action-btn[title]:hover::after {
    content: attr(title);
    position: absolute;
    bottom: calc(100% + 10px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.9);
    color: white;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 500;
    white-space: nowrap;
    z-index: 1000;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    pointer-events: none;
    animation: tooltipFadeIn 0.2s ease-out;
}

.meal-action-btn[title]:hover::before {
    content: '';
    position: absolute;
    bottom: calc(100% + 2px);
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: rgba(0, 0, 0, 0.9);
    z-index: 1000;
    pointer-events: none;
    animation: tooltipFadeIn 0.2s ease-out;
}

@keyframes tooltipFadeIn {
    from {
        opacity: 0;
        transform: translateX(-50%) translateY(5px);
    }
    to {
        opacity: 1;
        transform: translateX(-50%) translateY(0);
    }
}

/* ✅ ẨN TOOLTIP MẶC ĐỊNH CỦA BROWSER */
.meal-action-btn {
    position: relative;
}

/* ========== NÚT ĐÓNG THU THEO PANEL ========== */
.close-panel-btn {
    position: fixed;
    top: 65%;
    right: -48px; /* ✅ MẶC ĐỊNH ẨN NGOÀI MÀN HÌNH */
    transform: translateY(-50%);
    width: 48px;
    height: 100px;
    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
    border: none;
    border-radius: 12px 0 0 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 99999999999;
    box-shadow: none;
    transition: right 0.3s ease, transform 0.3s ease, width 0.3s ease, box-shadow 0.3s ease, background 0.3s ease; /* ✅ CHỈ GIỮ TRANSITION CẦN THIẾT */
    overflow: hidden;
}

.close-panel-btn::before {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
    transition: left 0.6s ease;
}

.close-panel-btn:hover::before {
    left: 100%;
}

/* ✅ KHI PANEL MỞ → NÚT XUẤT HIỆN */
.food-planner-panel.active .close-panel-btn {
    right: 30% !important; /* ✅ LỒI RA BÊN TRÁI PANEL */
    box-shadow: -6px 0 20px rgba(255, 107, 53, 0.4);
}

.close-panel-btn:hover {
    background: linear-gradient(135deg, #FF8E53 0%, #FFB84D 100%);
    box-shadow: -8px 0 28px rgba(255, 107, 53, 0.5);
    transform: translateY(-50%) translateX(20px);
    width: 56px;
}

.close-panel-btn:active {
    transform: translateY(-50%) translateX(4px) scale(0.95);
}

.close-panel-btn .arrow-icon {
    font-size: 28px;
    font-weight: 900;
    color: white;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    animation: arrowPulse 2s ease-in-out infinite;
}

@keyframes arrowPulse {
    0%, 100% {
        transform: translateX(0);
        opacity: 1;
    }
    50% {
        transform: translateX(4px);
        opacity: 0.8;
    }
}

.close-panel-btn:hover .arrow-icon {
    animation: arrowBounce 0.6s ease-in-out infinite;
}

@keyframes arrowBounce {
    0%, 100% {
        transform: translateX(0);
    }
    50% {
        transform: translateX(8px);
    }
}

/* ========== CUSTOM SCROLLBAR CHO PANEL ========== */
.panel-content::-webkit-scrollbar {
    width: 6px;
}

.panel-content::-webkit-scrollbar-track {
    background: transparent; /* Nền thanh cuộn trong suốt */
}

.panel-content::-webkit-scrollbar-thumb {
    /* Màu cam nhạt mờ, phù hợp với theme Food Planner */
    background: rgba(255, 107, 53, 0.3);
    border-radius: 3px;
    transition: background 0.3s ease;
}

.panel-content::-webkit-scrollbar-thumb:hover {
    /* Đậm hơn khi hover */
    background: rgba(255, 107, 53, 0.6);
}
/* ========== RESPONSIVE ========== */
@media (max-width: 768px) {
    .close-panel-btn {
        right: -48px; /* ✅ Mobile: ẨN mặc định */
    }
    
    .food-planner-panel.active ~ .close-panel-btn {
        right: 100%; /* ✅ Mobile: panel = 100% width */
        width: 36px;
        height: 70px;
    }
}
</style>

<!-- Food Planner Button -->
<div class="food-planner-btn" id="foodPlannerBtn" title="Lên kế hoạch ăn uống">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
        <path d="M11 9H9V2H7v7H5V2H3v7c0 2.12 1.66 3.84 3.75 3.97V22h2.5v-9.03C11.34 12.84 13 11.12 13 9V2h-2v7zm5-3v8h2.5v8H21V2c-2.76 0-5 2.24-5 4z"/>
    </svg>
</div>

<!-- Food Planner Panel -->
<div class="food-planner-panel" id="foodPlannerPanel">
    <div class="panel-header">
    <h2 style="font-size: 22px;">
        <span style="font-size: 26px;" data-translate="food_planning_title">📋 Lên kế hoạch ăn uống</span>
    </h2>
</div>
        
        <div class="panel-content">
            <!-- AUTO MODE -->
            <div class="tab-content active" id="autoTab">
                <div class="filters-wrapper-new">
                    <!-- ❤️ BẢNG CHỦ ĐỀ ĐẸP -->
                    <div class="filter-section-new theme-section">
                        <div class="section-header">
                            <span class="section-icon">❤️</span>
                            <h3 class="section-title">Chọn chủ đề yêu thích</h3>
                        </div>
                        <div class="theme-grid-new" id="themeGrid"></div>
                    </div>
                    
                    <!-- ⏰ KHUNG THỜI GIAN ĐẸP -->
                    <div class="filter-section-new time-section">
                        <div class="section-header">
                            <span class="section-icon">⏰</span>
                            <h3 class="section-title">Khoảng thời gian</h3>
                        </div>
                        <div class="time-picker-container">
                            <div class="time-picker-group">
                                <label class="time-label">Từ</label>
                                <div class="time-input-wrapper">
                                    <input type="number" id="startHour" min="0" max="23" value="07" class="time-input">
                                    <span class="time-separator">:</span>
                                    <input type="number" id="startMinute" min="0" max="59" value="00" class="time-input">
                                </div>
                            </div>
                            
                            <div class="time-arrow">→</div>
                            
                            <div class="time-picker-group">
                                <label class="time-label">Đến</label>
                                <div class="time-input-wrapper">
                                    <input type="number" id="endHour" min="0" max="23" value="21" class="time-input">
                                    <span class="time-separator">:</span>
                                    <input type="number" id="endMinute" min="0" max="59" value="00" class="time-input">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- 🎯 NÚT TẠO KẾ HOẠCH ĐẸP -->
                    <button class="generate-btn-new" onclick="generateAutoPlan()">
                        <span class="btn-icon">✨</span>
                        <span class="btn-text">Tạo kế hoạch tự động</span>
                        <span class="btn-arrow">→</span>
                    </button>
                </div>
                
                <!-- Saved Plans Section -->
                <div class="saved-plans-section" id="savedPlansSection" style="display: block;">
                    <div class="saved-plans-header" onclick="toggleSavedPlans()">
                        <div class="filter-title" style="margin: 0; font-size: 16px; font-weight: 700; color: #FF6B35;">
                            <span style="font-size: 20px; margin-right: 8px;">📋</span>
                            Lịch trình đã lưu
                        </div>
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" style="width: 20px; height: 20px; transition: transform 0.3s ease; color: #FF6B35;" id="savedPlansArrow">
                            <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
                        </svg>
                    </div>
                    <div class="saved-plans-list" id="savedPlansList"></div>
                </div>
                
                <div id="planResult"></div>
            </div>  
        </div>
        <!-- ✅ NÚT ĐÓNG ĐẸP HƠN VỚI ICON >> -->
            <button class="close-panel-btn" onclick="closeFoodPlanner()" title="Đóng lịch trình">
                <span class="arrow-icon">»</span>
            </button>
    </div>
</div>

<script>
// ========== GLOBAL STATE ==========
let isPlannerOpen = false;
let selectedThemes = []; // Đổi từ selectedTheme thành selectedThemes (array)
let currentPlan = null;
let currentPlanId = null;
let suggestedFoodStreet = null;
let suggestedMichelin = null; 
let filtersCollapsed = false;
let isEditMode = false;
let draggedElement = null;
let selectedPlaceForReplacement = null;
let waitingForPlaceSelection = null;
let autoScrollInterval = null;
let lastDragY = 0;
let dragDirection = 0;
let lastTargetElement = null;
window.currentPlanName = null;
window.loadedFromSavedPlan = false;

// Themes data
const themes = {
    'street_food': { name: 'Ẩm thực đường phố', icon: '🍜' },
    'seafood': { name: 'Hải sản', icon: '🦞' },
    'coffee_chill': { name: 'Giải khát', icon: '☕' },
    'luxury_dining': { name: 'Nhà hàng sang trọng', icon: '🍽️' },
    'asian_fusion': { name: 'Ẩm thực châu Á', icon: '🍱' },
    'vegetarian': { name: 'Món chay', icon: '🥗' },
    'dessert_bakery': { name: 'Tráng miệng', icon: '🍰' },
    'spicy_food': { name: 'Đồ cay', icon: '🌶️' },
    'food_street': { name: 'Khu ẩm thực', icon: '🏪' },
    'michelin': { name: 'Michelin', icon: '⭐' }
};

// Meal icons
const mealIcons = {
    'breakfast': '🍳',
    'morning_drink': '🧋',
    'lunch': '🍚',
    'afternoon_drink': '☕',
    'dinner': '🍽️',
    'dessert': '🍰',
    'meal': '🍜',
    'meal1': '🍚',
    'meal2': '🥖',
    'drink': '☕'
};

// ========== INITIALIZATION ==========
document.addEventListener('DOMContentLoaded', function() {
    initThemeGrid();
    loadSavedPlans();
});

function initThemeGrid() {
    const grid = document.getElementById('themeGrid');
    if (!grid) return;
    
    // 🔥 XÓA CLASS CŨ
    grid.className = '';
    
    // 🔥 CẤU TRÚC MỚI - CHIA THÀNH 3 SECTIONS
    const sections = [
        {
            title: 'Giải khát & Tráng miệng',
            icon: '🍹',
            themes: ['coffee_chill', 'dessert_bakery'],
            columns: 2
        },
        {
            title: 'Ẩm thực đa dạng',
            icon: '🍽️',
            themes: ['street_food', 'asian_fusion', 'seafood', 'luxury_dining', 'vegetarian', 'spicy_food'],
            columns: 2
        },
        {
            title: 'Địa điểm nổi bật',
            icon: '🏙️',
            themes: ['food_street', 'michelin'],
            columns: 2
        }
    ];
    
    sections.forEach(section => {
        // Tạo section container
        const sectionDiv = document.createElement('div');
        sectionDiv.className = 'theme-section-group';
        sectionDiv.style.marginBottom = '24px';
        
        // Tạo header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'theme-section-header';
        headerDiv.innerHTML = `
            <span style="font-size: 24px; margin-right: 8px;">${section.icon}</span>
            <span style="font-size: 14px; font-weight: 700; color: #333;">${section.title}</span>
        `;
        headerDiv.style.cssText = `
            display: flex;
            align-items: center;
            margin-bottom: 12px;
            padding: 8px 12px;
            background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%);
            border-radius: 12px;
            border: 2px solid #FFD699;
        `;
        
        // Tạo grid cho themes
        const themeGrid = document.createElement('div');
        themeGrid.className = 'theme-grid-new';
        themeGrid.style.gridTemplateColumns = `repeat(${section.columns}, 1fr)`;
        
        section.themes.forEach(key => {
            const theme = themes[key];
            const card = document.createElement('div');
            card.className = 'theme-card';
            card.dataset.theme = key;
            card.innerHTML = `
                <div class="theme-icon">${theme.icon}</div>
                <div class="theme-name">${theme.name}</div>
            `;
            card.onclick = () => selectTheme(key);
            themeGrid.appendChild(card);
        });
        
        sectionDiv.appendChild(headerDiv);
        sectionDiv.appendChild(themeGrid);
        grid.appendChild(sectionDiv);
    });

    // Chọn sẵn 3 theme khi lần đầu mở
    setTimeout(() => {
        const defaultThemes = ['coffee_chill', 'dessert_bakery', 'food_street'];
        
        defaultThemes.forEach(themeKey => {
            if (!selectedThemes.includes(themeKey)) {
                selectedThemes.push(themeKey);
            }
            
            const card = document.querySelector(`[data-theme="${themeKey}"]`);
            if (card) {
                card.classList.add('selected');
            }
        });
    }, 100);
}

// ========== THEME SELECTION ==========
function selectTheme(themeKey) {
    const card = document.querySelector(`[data-theme="${themeKey}"]`);
    
    if (selectedThemes.includes(themeKey)) {
        // Bỏ chọn
        selectedThemes = selectedThemes.filter(t => t !== themeKey);
        if (card) card.classList.remove('selected');
    } else {
        // Thêm vào chọn
        selectedThemes.push(themeKey);
        if (card) card.classList.add('selected');
    }
}

// ========== SAVED PLANS ==========
function displaySavedPlansList(plans) {
    const listDiv = document.getElementById('savedPlansList');

    // ✅ Bắt đầu với nút "Tạo mới"
    let html = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding: 10px; background: #f8f9fa; border-radius: 8px;">
            <span style="font-size: 14px; font-weight: 600; color: #333;">📋 Danh sách lịch trình</span>
            <button onclick="createNewEmptyPlan()" style="background: #4caf50; color: white; border: none; width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 18px; display: flex; align-items: center; justify-content: center; transition: all 0.2s ease;" title="Tạo lịch trình mới">+</button>
        </div>
    `;

    // ✅ Nếu không có plans → chỉ thêm thông báo
    if (!plans || plans.length === 0) {
        html += '<p style="color: #999; font-size: 13px; padding: 15px; text-align: center;">Chưa có kế hoạch nào</p>';
        listDiv.innerHTML = html;
        return;
    }
    
    // 🔥 LỌC TRÙNG LẶP - CHỈ GIỮ 1 PLAN DUY NHẤT
    const uniquePlans = [];
    const seenIds = new Set();
    
    plans.forEach(plan => {
        if (!seenIds.has(plan.id)) {
            seenIds.add(plan.id);
            uniquePlans.push(plan);
        }
    });
    
    console.log('🔍 Original plans:', plans.length, 'Unique plans:', uniquePlans.length);
    
    // ✅ Nếu có plans → thêm từng plan vào html
    uniquePlans.forEach((plan, index) => {
        // 🔥 CODE FIX TIMEZONE
        const rawCreated = plan.created_at || plan.savedAt || null;

        let dateStr = 'Không rõ ngày';
        let timeStr = '';

        if (rawCreated) {
            try {
                let isoString = rawCreated;
                
                if (isoString.includes(' ') && !isoString.includes('T')) {
                    isoString = isoString.replace(' ', 'T');
                }
                
                const parts = isoString.match(/(\d{4})-(\d{2})-(\d{2})[T\s](\d{2}):(\d{2}):(\d{2})?/);
                
                if (!parts) {
                    throw new Error('Invalid date format');
                }
                
                const year = parseInt(parts[1]);
                const month = parseInt(parts[2]) - 1;
                const day = parseInt(parts[3]);
                let hour = parseInt(parts[4]);
                const minute = parseInt(parts[5]);
                const second = parseInt(parts[6] || '0');
                
                hour += 7;
                if (hour >= 24) {
                    hour -= 24;
                }
                
                const date = new Date(year, month, day, hour, minute, second);

                if (!isNaN(date.getTime())) {
                    const dd = String(date.getDate()).padStart(2, '0');
                    const mm = String(date.getMonth() + 1).padStart(2, '0');
                    const yyyy = date.getFullYear();
                    dateStr = `${dd}/${mm}/${yyyy}`;
                    
                    const hh = String(date.getHours()).padStart(2, '0');
                    const min = String(date.getMinutes()).padStart(2, '0');
                    timeStr = `${hh}:${min}`;
                }
            } catch (error) {
                console.error('❌ Lỗi parse datetime:', error, 'Input:', rawCreated);
                dateStr = 'Không rõ ngày';
                timeStr = '';
            }
        }
        
        // 🔥 THÊM BADGE CHO SHARED PLAN
        const sharedBadge = plan.is_shared ? 
            `<span style="font-size: 10px; background: #2196F3; color: white; padding: 2px 6px; border-radius: 8px; margin-left: 6px;">Chia sẻ</span>` 
            : '';

        html += `
            <div class="saved-plan-item" onclick="loadSavedPlans(${plan.id})">
                <div class="saved-plan-info">
                    <div class="saved-plan-name">${plan.name}${sharedBadge}</div>
                    <div class="saved-plan-date">📅 ${dateStr} • ⏰ ${timeStr}</div>
                    ${plan.is_shared ? `<div style="font-size: 11px; color: #2196F3; margin-top: 4px;">👤 ${plan.owner_username}</div>` : ''}
                </div>
                ${!plan.is_shared ? `
                    <button class="delete-plan-btn" onclick="event.stopPropagation(); deleteSavedPlan(${plan.id})" title="Xóa lịch trình">×</button>
                ` : `
                    <button class="delete-plan-btn" onclick="event.stopPropagation(); leaveSharedPlan(${plan.id})" title="Ngừng xem plan này" style="background: #FF9800;">×</button>
                `}
            </div>
        `;
    });

    listDiv.innerHTML = html;
}

// ========== TOGGLE SAVED PLANS - SỬA LẠI ĐƠN GIẢN HƠN ==========
function toggleSavedPlans() {
    const listDiv = document.getElementById('savedPlansList');
    const arrow = document.getElementById('savedPlansArrow');
    
    if (!listDiv || !arrow) {
        console.error('❌ Không tìm thấy savedPlansList hoặc savedPlansArrow');
        return;
    }
    
    // 🔥 TOGGLE CLASS 'open'
    const isOpen = listDiv.classList.contains('open');
    
    if (isOpen) {
        // Đang mở → đóng lại
        listDiv.classList.remove('open');
        arrow.style.transform = 'rotate(0deg)';
        console.log('✅ Đóng saved plans');
    } else {
        // Đang đóng → mở ra
        listDiv.classList.add('open');
        arrow.style.transform = 'rotate(180deg)';
        console.log('✅ Mở saved plans');
        
        // 🔥 ĐÓNG FILTERS nếu đang mở
        const filtersWrapper = document.querySelector('.filters-wrapper-new');
        if (filtersWrapper && !filtersWrapper.classList.contains('collapsed')) {
            const filterHeader = document.querySelector('.section-header');
            if (filterHeader && typeof filterHeader.click === 'function') {
                // Không làm gì - giữ nguyên filters
            }
        }
    }
}

// ========== SAVE PLAN - Lưu vào Database Django ==========
async function savePlan() {
    if (!currentPlan) return;

    // 🔥 KIỂM TRA ĐĂNG NHẬP
    const checkAuth = await fetch('/api/check-auth/');
    const authData = await checkAuth.json();
    
    if (!authData.is_logged_in) {
        alert('⚠️ Bạn cần đăng nhập để lưu lịch trình!');
        window.location.href = '/accounts/login/';
        return;
    }

    // 🔥 LƯU THỨ TỰ VỀ DOM
    const mealItems = document.querySelectorAll('.meal-item');
    const planArray = [];
    
    mealItems.forEach(item => {
        const mealKey = item.dataset.mealKey;
        if (mealKey && currentPlan[mealKey]) {
            // Cập nhật thời gian từ input
            const hourInput = item.querySelector('.time-input-hour[data-meal-key="' + mealKey + '"]');
            const minuteInput = item.querySelector('.time-input-minute[data-meal-key="' + mealKey + '"]');
            
            if (hourInput && minuteInput) {
                const hour = hourInput.value.padStart(2, '0');
                const minute = minuteInput.value.padStart(2, '0');
                currentPlan[mealKey].time = `${hour}:${minute}`;
            }
            
            // Cập nhật TITLE từ input
            const titleInput = item.querySelector('input[onchange*="updateMealTitle"]');
            if (titleInput && titleInput.value) {
                currentPlan[mealKey].title = titleInput.value;
            }
            
            planArray.push({
                key: mealKey,
                data: JSON.parse(JSON.stringify(currentPlan[mealKey]))
            });
        }
    });

    // ✅ KIỂM TRA PLAN CÓ DỮ LIỆU KHÔNG
    if (planArray.length === 0) {
        alert('⚠️ Lịch trình trống! Hãy thêm ít nhất 1 quán trước khi lưu.');
        return;
    }

    currentPlan._order = planArray.map(x => x.key);

    // Xóa quán gợi ý trước khi lưu
    suggestedFoodStreet = null;
    suggestedMichelin = null;

    // 🔥 LẤY TÊN TỪ DOM
    const titleElement = document.querySelector('.schedule-title span[contenteditable]');
    let currentDisplayName = titleElement ? titleElement.textContent.trim() : (window.currentPlanName || '');
    
    // ✅ XỬ LÝ TÊN PLAN
    if (!currentDisplayName || currentDisplayName === 'Lịch trình của bạn') {
        currentDisplayName = prompt('Đặt tên cho kế hoạch:', `Kế hoạch ${new Date().toLocaleDateString('vi-VN')}`);
        if (!currentDisplayName || currentDisplayName.trim() === '') {
            alert('⚠️ Bạn phải đặt tên để lưu lịch trình!');
            return;
        }
        currentDisplayName = currentDisplayName.trim();
    }

    // 🔥 GỌI API DJANGO ĐỂ LƯU
    try {
        const response = await fetch('/api/accounts/food-plan/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                name: currentDisplayName,
                plan_data: planArray
            })
        });

                const result = await response.json();

        if (result.status === 'success') {
            alert('✅ Đã lưu kế hoạch thành công!');
            window.currentPlanName = currentDisplayName;
            
            // ✅ TẮT EDIT MODE SAU KHI LƯU
            if (isEditMode) {
                toggleEditMode();
            }
            
            // 🔥 LẤY ID PLAN VỪA LƯU (NẾU API TRẢ VỀ)
            let newPlanId = null;
            if (result.plan && result.plan.id) {
                newPlanId = result.plan.id;
            } else if (result.plan_id) {
                newPlanId = result.plan_id;
            }

            if (newPlanId) {
                currentPlanId = newPlanId;
            }
            
            // ✅ LOAD LẠI DANH SÁCH + MỞ LUÔN PLAN VỪA LƯU
            if (newPlanId) {
                // forceReload = true để không bị nhánh "click lại cùng planId" đóng plan
                await loadSavedPlans(newPlanId, true);
            } else {
                // fallback: nếu API chưa trả id thì giữ behaviour cũ
                await loadSavedPlans();
            }

        } else {
            alert('❌ Lỗi: ' + result.message);
        }
    } catch (error) {
        console.error('Error saving plan:', error);
        alert('❌ Không thể lưu lịch trình!');
    }
}

// ========== LOAD SAVED PLANS ==========
async function loadSavedPlans(planId, forceReload = false) {
    try {

        // 🧹 ĐÓNG LỊCH TRÌNH NẾU BẤM LẠI CÙNG 1 PLAN ĐANG MỞ
        if (
            !forceReload &&                      // không phải load lại bắt buộc
            typeof planId !== 'undefined' &&
            planId !== null &&
            currentPlanId !== null &&
            String(currentPlanId) === String(planId)
        ) {
            console.log('🧹 Đóng lịch trình hiện tại vì click lại cùng planId:', planId);

            // Reset trạng thái liên quan tới plan
            isViewingSharedPlan = false;
            isSharedPlan = false;
            sharedPlanOwnerId = null;
            sharedPlanOwnerName = '';
            hasEditPermission = false;

            currentPlan = null;
            currentPlanId = null;
            isEditMode = false;
            waitingForPlaceSelection = null;
            window.currentPlanName = null;
            window.loadedFromSavedPlan = false;
            window.originalSharedPlanData = null; // 🔥 MỚI: Xóa original data khi đóng plan

            // Xóa route + clear khu vực lịch trình
            clearRoutes();
            const resultDiv = document.getElementById('planResult');
            if (resultDiv) {
                resultDiv.innerHTML = '';
            }

            // Hiện lại bộ lọc (filters)
            const filtersWrapper = document.querySelector('.filters-wrapper-new');
            if (filtersWrapper) {
                filtersWrapper.style.display = 'block';
            }

            // ⭐ HIỆN LẠI TẤT CẢ MARKER CÁC QUÁN (từ kết quả search trước đó)
            if (
                typeof displayPlaces === 'function' &&
                typeof allPlacesData !== 'undefined' &&
                Array.isArray(allPlacesData) &&
                allPlacesData.length > 0
            ) {
                // false = không zoom lại map, chỉ vẽ marker
                displayPlaces(allPlacesData, false);
            }

            // 👉 Không gọi API nữa, coi như "đóng lịch trình"
            return;
        }

        // 🔥 GỌI API DJANGO - BÂY GIỜ TRẢ VỀ CẢ SHARED PLANS
        const response = await fetch('/api/accounts/food-plan/list/');
        const data = await response.json();
        
        if (data.status !== 'success') {
            console.error('Lỗi load plans:', data.message);
            return;
        }
        
        const savedPlans = data.plans || [];
        
        // ✅ THÊM: GỌI API LẤY SHARED PLANS
        let sharedPlans = [];
        try {
            const sharedResponse = await fetch('/api/accounts/food-plan/shared/');
            const sharedData = await sharedResponse.json();
            if (sharedData.status === 'success') {
                sharedPlans = sharedData.shared_plans || [];
            }
        } catch (error) {
            console.error('Error loading shared plans:', error);
        }
        
        const section = document.getElementById('savedPlansSection');
        
        // ✅ LUÔN HIỂN THỊ SECTION
        section.style.display = 'block';
        
        
        // ✅ GỘP 2 DANH SÁCH
        const allPlans = [...savedPlans, ...sharedPlans];
        
        displaySavedPlansList(allPlans);
        
        // Nếu có planId, load plan đó
       // Nếu có planId, load plan đó
if (planId) {
    const plan = allPlans.find(p => p.id === planId);
    
    if (plan) {
        currentPlan = {};
        
        // 🔥 XỬ LÝ SHARED PLAN
        if (plan.is_shared) {
            isSharedPlan = true;
            isViewingSharedPlan = true;
            sharedPlanOwnerId = plan.owner_id;
            sharedPlanOwnerName = plan.owner_username;
            hasEditPermission = (plan.permission === 'edit');

            // 🔥 MỚI: LƯU BẢN SAO ORIGINAL PLAN
    window.originalSharedPlanData = null; // Reset trước
            
            // 🔥 FIX: THÊM AWAIT ĐỂ ĐỢI PENDING CHECK HOÀN TẤT
            if (hasEditPermission) {
                await checkPendingSuggestion(planId);
                console.log('✅ Đã check pending suggestion sau reload:', hasPendingSuggestion);
            }
        } else {
            isSharedPlan = false;
            isViewingSharedPlan = false; // 🔥 THÊM DÒNG NÀY
            sharedPlanOwnerId = null;
            sharedPlanOwnerName = '';
            hasEditPermission = false;
        }
                
                // 🔥 CHUYỂN ĐỔI TỪ plan_data
            const planData = plan.plan_data;
            if (Array.isArray(planData)) {
                const orderList = [];
                planData.forEach(item => {
                    currentPlan[item.key] = JSON.parse(JSON.stringify(item.data));
                    orderList.push(item.key);
                });
                currentPlan._order = orderList;
            } else {
                Object.assign(currentPlan, planData);
            }

            // 🔥 MỚI: LƯU BẢN SAO ORIGINAL (SAU KHI PARSE)
            if (plan.is_shared && hasEditPermission) {
                window.originalSharedPlanData = JSON.parse(JSON.stringify(currentPlan));
                console.log('💾 Đã lưu original shared plan data');
}

                currentPlanId = planId;
                window.currentPlanName = plan.name;
                window.loadedFromSavedPlan = true;
                isEditMode = false;
                suggestedFoodStreet = null;
                suggestedMichelin = null;
                displayPlanVertical(currentPlan, false);

                // 🔥 THÊM: Tự động check suggestions sau khi load plan
                if (!plan.is_shared) {
                    setTimeout(() => {
                        checkPendingSuggestions(planId);
                    }, 500);
                }

                setTimeout(() => drawRouteOnMap(currentPlan), 500);
                
                const savedPlansList = document.getElementById('savedPlansList');
                const savedPlansArrow = document.getElementById('savedPlansArrow');
                
                if (savedPlansList && savedPlansArrow) {
                    savedPlansList.classList.remove('open');
                    savedPlansArrow.style.transform = 'rotate(0deg)';
                }
                
                if (section) {
                    section.style.display = 'block';
                }
                if (!plan.is_shared) {
                    checkPendingSuggestions(planId);
                }
            }
        }
    } catch (error) {
        console.error('Error loading plans:', error);
    }
}

// ========== HELPER: CONVERT UTC TO LOCAL TIMEZONE ==========
function formatDateTimeWithTimezone(datetimeString) {
    if (!datetimeString) return 'Không rõ ngày';
    
    try {
        // Parse ISO string
        let date;
        
        // Nếu có 'T' thì đã đúng format ISO
        if (datetimeString.includes('T')) {
            date = new Date(datetimeString);
        } else {
            // Nếu format 'YYYY-MM-DD HH:MM:SS' thì thêm 'T'
            const normalized = datetimeString.replace(' ', 'T');
            date = new Date(normalized);
        }
        
        // 🔥 BỎ PHẦN CỘNG 7 GIỜ - CHỈ FORMAT LẠI
        // JavaScript Date tự động convert sang timezone local rồi
        
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        const hour = String(date.getHours()).padStart(2, '0');
        const minute = String(date.getMinutes()).padStart(2, '0');
        const second = String(date.getSeconds()).padStart(2, '0');
        
        return `${hour}:${minute}:${second} ${day}/${month}/${year}`;
        
    } catch (error) {
        console.error('❌ Lỗi format datetime:', error);
        return 'Lỗi định dạng';
    }
}
// ========== DELETE PLAN - Xóa từ Database Django ==========
async function deleteSavedPlan(planId) {
    if (!confirm('Bạn có chắc muốn xóa kế hoạch này?')) return;
    
    try {
        const response = await fetch(`/api/accounts/food-plan/delete/${planId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const result = await response.json();

        if (result.status === 'success') {
            alert('✅ Đã xóa kế hoạch!');
            
            if (currentPlanId === planId) {
                currentPlanId = null;
                currentPlan = null;
                document.getElementById('planResult').innerHTML = '';
                isEditMode = false;
            }
            
            await loadSavedPlans();
        } else {
            alert('❌ Lỗi: ' + result.message);
        }
    } catch (error) {
        console.error('Error deleting plan:', error);
        alert('❌ Không thể xóa lịch trình!');
    }
}
// ========== DELETE PLAN - Xóa từ Database Django ==========
async function deleteSavedPlan(planId) {
    if (!confirm('Bạn có chắc muốn xóa kế hoạch này?')) return;
    
    try {
        const response = await fetch(`/api/accounts/food-plan/delete/${planId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const result = await response.json();

        if (result.status === 'success') {
            alert('✅ Đã xóa kế hoạch!');
            
            if (currentPlanId === planId) {
                currentPlanId = null;
                currentPlan = null;
                document.getElementById('planResult').innerHTML = '';
                isEditMode = false;
            }
            
            await loadSavedPlans();
        } else {
            alert('❌ Lỗi: ' + result.message);
        }
    } catch (error) {
        console.error('Error deleting plan:', error);
        alert('❌ Không thể xóa lịch trình!');
    }
}

// ========== LEAVE SHARED PLAN ==========
async function leaveSharedPlan(planId) {
    if (!confirm('Bạn có chắc muốn ngừng xem lịch trình này? Lịch trình sẽ biến mất khỏi danh sách của bạn')) return;
    
    try {
        const response = await fetch(`/api/accounts/food-plan/leave-shared/${planId}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const result = await response.json();

        if (result.status === 'success') {
            alert('✅ Đã ngừng xem lịch trình!');
            
            if (currentPlanId === planId) {
                currentPlanId = null;
                currentPlan = null;
                document.getElementById('planResult').innerHTML = '';
                isEditMode = false;
                clearRoutes();
            }
            
            await loadSavedPlans();
        } else {
            alert('❌ Lỗi: ' + result.message);
        }
    } catch (error) {
        console.error('Error leaving shared plan:', error);
        alert('❌ Không thể rời khỏi lịch trình!');
    }
}
// ========== TẠO LỊCH TRÌNH TRỐNG MỚI ==========
function createNewEmptyPlan() {
    isViewingSharedPlan = false;
    const now = new Date();
    const dateStr = now.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' });
    const planName = prompt('Đặt tên cho lịch trình:', `Lịch trình ngày ${dateStr}`);
    
    if (!planName) return; // User cancel
    
    const newPlanId = Date.now().toString();
    
    // ✅ TẠO LỊCH TRÌNH TRỐNG VỚI 1 SLOT MẶC ĐỊNH
    currentPlan = {
        'custom_1': {
            time: '07:00',
            title: 'Bữa sáng',
            icon: '🍳',
            place: null
        },
        _order: ['custom_1']
    };
    
    currentPlanId = newPlanId;
    window.currentPlanName = planName;
    window.loadedFromSavedPlan = true;
    isEditMode = true; // ✅ TỰ ĐỘNG BẬT EDIT MODE
    waitingForPlaceSelection = null;
    
    // ✅ HIỂN THỊ LỊCH TRÌNH MỚI
    displayPlanVertical(currentPlan, true);
    
    // ✅ ĐÓNG "LỊCH TRÌNH ĐÃ LƯU" SAU KHI TẠO
    const savedPlansList = document.getElementById('savedPlansList');
    const savedPlansArrow = document.getElementById('savedPlansArrow');
    if (savedPlansList && savedPlansArrow) {
        savedPlansList.classList.remove('open');
        savedPlansArrow.style.transform = 'rotate(0deg)';
    }
    
    // ✅ ĐÓNG FILTERS NẾU ĐANG MỞ
    const filtersWrapper = document.getElementById('filtersWrapper');
    if (filtersWrapper && !filtersWrapper.classList.contains('collapsed')) {
        toggleFilters();
    }
    
    // ✅ SCROLL LÊN TOP
    const panelContent = document.querySelector('.panel-content');
    if (panelContent) {
        panelContent.scrollTop = 0;
    }
}

// ========== EDIT MODE ==========
function toggleEditMode() {
    isEditMode = !isEditMode;
    const editBtn = document.getElementById('editPlanBtn');
    
    if (editBtn) {
        if (isEditMode) {
            editBtn.classList.add('active');
            editBtn.title = 'Thoát chỉnh sửa';
            clearRoutes(); // Xóa đường khi vào edit mode
        } else {
            editBtn.classList.remove('active');
            editBtn.title = 'Chỉnh sửa';
            selectedPlaceForReplacement = null;
            waitingForPlaceSelection = null;
        }
    }
    
    // 🔥 LƯU TITLE TỪ INPUT TRƯỚC KHI RENDER LẠI
    if (isEditMode && currentPlan) {
        const mealItems = document.querySelectorAll('.meal-item');
        mealItems.forEach(item => {
            const mealKey = item.dataset.mealKey;
            if (mealKey && currentPlan[mealKey]) {
                const titleInput = item.querySelector('input[onchange*="updateMealTitle"]');
                if (titleInput && titleInput.value) {
                    currentPlan[mealKey].title = titleInput.value;
                }
            }
        });
    }
    
    if (currentPlan) {
        displayPlanVertical(currentPlan, isEditMode);
    }
}
// ========== OPEN/CLOSE PLANNER ==========
document.addEventListener('DOMContentLoaded', function() {
    console.log('🔍 DOMContentLoaded fired');
    
    const foodPlannerBtn = document.getElementById('foodPlannerBtn');
    
    if (foodPlannerBtn) {
        console.log('✅ Tìm thấy foodPlannerBtn');
        
        foodPlannerBtn.addEventListener('click', function(e) {
            console.log('🔍 Food Planner Button clicked');
            e.preventDefault();
            e.stopPropagation();
            
            if (isPlannerOpen) {
                closeFoodPlanner();
            } else {
                openFoodPlanner();
            }
        });
    } else {
        console.error('❌ Không tìm thấy foodPlannerBtn');
    }
});

function openFoodPlanner() {
    console.log('🚀 Opening Food Planner.');
    
    const panel = document.getElementById('foodPlannerPanel');
    console.log('Panel element:', panel);
    
    if (!panel) {
        console.error('❌ Không tìm thấy foodPlannerPanel');
        return;
    }
    
    panel.classList.add('active');
    isPlannerOpen = true;
    loadSavedPlans();
    
    // 🔥 Nếu đã có currentPlan (và không ở edit mode) thì vẽ lại route + marker theo plan
    setTimeout(() => {
        if (currentPlan && !isEditMode) {
            const hasPlaces = Object.keys(currentPlan)
                .filter(k => k !== '_order')
                .some(k => currentPlan[k] && currentPlan[k].place);
            
            if (hasPlaces) {
                // Vẽ đường đi cho lịch trình
                if (typeof drawRouteOnMap === 'function') {
                    drawRouteOnMap(currentPlan);
                }

                // 🔥 Ẩn marker quán ngoài lịch trình, chỉ giữ quán trong plan
                if (typeof window.showMarkersForPlaceIds === 'function') {
                    window.showMarkersForPlaceIds(currentPlan);
                }
            }
        }
    }, 300);
}


function closeFoodPlanner() {
    const panel = document.getElementById('foodPlannerPanel');
    if (panel) {
        panel.classList.remove('active');
    }

    isPlannerOpen = false;
    isViewingSharedPlan = false;
    window.originalSharedPlanData = null; // 🔥 MỚI: Xóa original data
    // ✅ Cleanup toàn bộ route / drag
    clearRoutes();
    stopAutoScroll();
    disableGlobalDragTracking();
    
    // ✅ Reset drag state
    draggedElement = null;
    window.draggedElement = null;
    lastTargetElement = null;
    lastDragY = 0;

    // ✅ Reset trạng thái chọn quán cho bữa ăn (nếu đang chờ)
    waitingForPlaceSelection = null;
    selectedPlaceForReplacement = null;
    
    // 🔥 ẨN NÚT X KHI ĐÓNG PANEL
    const exitBtn = document.getElementById('exitSharedPlanBtn');
    if (exitBtn) {
        exitBtn.style.display = 'none';
    }

    // 🔥 KHI ĐÓNG FOOD PLANNER → HIỆN LẠI TẤT CẢ MARKER QUÁN BÌNH THƯỜNG
    try {
        // Ưu tiên dùng data search đang có (allPlacesData)
        if (typeof displayPlaces === 'function' &&
            Array.isArray(window.allPlacesData) &&
            window.allPlacesData.length > 0) {

            // false = không đổi zoom, chỉ vẽ lại marker
            displayPlaces(window.allPlacesData, false);
        } else if (typeof loadMarkersInViewport === 'function' && window.map) {
            // Fallback: nếu chưa có allPlacesData thì bật lại lazy-load + load marker
            window.map.on('moveend', loadMarkersInViewport);
            loadMarkersInViewport();
        }
    } catch (e) {
        console.error('❌ Lỗi khi restore marker sau khi đóng Food Planner:', e);
    }
}


// ========== GET SELECTED FLAVORS ==========
function getSelectedFlavors() {
    const selectedFlavors = [];
    const flavorInput = document.getElementById('flavor');
    
    if (flavorInput && flavorInput.value.trim()) {
        const flavors = flavorInput.value.trim().toLowerCase().split(',');
        flavors.forEach(flavor => {
            const normalized = flavor.trim();
            if (normalized) {
                selectedFlavors.push(normalized);
            }
        });
    }
    
    return selectedFlavors;
}
// ========== RANDOM LẠI QUÁN GỢI Ý ==========
async function randomSuggestedPlace(themeType) {
    try {
        let userLat, userLon;
        
        if (window.currentUserCoords) {
            userLat = window.currentUserCoords.lat;
            userLon = window.currentUserCoords.lon;
        } else {
            return null;
        }
        
        const radiusInput = document.getElementById('radius');
        const radius = radiusInput?.value || window.currentRadius || '10';
        
        // 🔥 GIỜ THOẢI MÁI - RANDOM TỪ 0-23 GIỜ
        const randomHour = Math.floor(Math.random() * 24);
        const randomMinute = Math.floor(Math.random() * 60);
        const searchTime = `${randomHour.toString().padStart(2, '0')}:${randomMinute.toString().padStart(2, '0')}`;
        
        const randomSeed = Date.now();
        const url = `/api/food-plan?lat=${userLat}&lon=${userLon}&random=${randomSeed}&start_time=${searchTime}&end_time=${searchTime}&radius_km=${radius}&theme=${themeType}`;
        
        const response = await fetch(url);
        if (!response.ok) return null;
        
        const data = await response.json();
        if (data.error || !data) return null;
        
        for (const key in data) {
            if (key !== '_order' && data[key] && data[key].place) {
                return data[key].place;
            }
        }
        
        return null;
    } catch (error) {
        console.error(`Lỗi random ${themeType}:`, error);
        return null;
    }
}

// 🔥 HÀM CẬP NHẬT TRỰC TIẾP CARD GỢI Ý (KHÔNG RENDER LẠI TOÀN BỘ)
function updateSuggestedCard(themeType, place) {
    // 🔥 TÌM CARD BẰNG TITLE CỤ THỂ (an toàn hơn icon)
    const titleToFind = themeType === 'food_street' ? 'Khu ẩm thực đêm' : 'Nhà hàng Michelin';
    
    let targetCard = null;
    
    // Tìm tất cả các div có "Gợi ý cho bạn"
    const allSuggestionCards = document.querySelectorAll('#planResult > div');
    
    allSuggestionCards.forEach(card => {
        // 🔥 KIỂM TRA CẢ "Gợi ý" VÀ TITLE CỤ THỂ
        const cardHTML = card.innerHTML;
        if (cardHTML.includes('Gợi ý cho bạn') && cardHTML.includes(titleToFind)) {
            targetCard = card;
            console.log(`✅ Tìm thấy card ${themeType}:`, titleToFind);
        }
    });
    
    if (!targetCard) {
        console.error(`❌ Không tìm thấy card ${themeType}`);
        return;
    }
    
    // Format giờ mở cửa (giữ nguyên code cũ)
    const gioMoCua = place.gio_mo_cua || '';
    let displayTime = '';
    
    if (!gioMoCua || gioMoCua.trim() === '') {
        displayTime = 'Không rõ thời gian';
    } else {
        const gioNormalized = gioMoCua.toLowerCase();
        
        if (gioNormalized.includes('always') || gioNormalized.includes('24') || 
            gioNormalized.includes('cả ngày') || gioNormalized.includes('mở cả ngày') ||
            gioNormalized.includes('ca ngay') || gioNormalized.includes('mo ca ngay')) {
            displayTime = 'Mở cả ngày';
        } else if (gioNormalized.includes('mở') || gioNormalized.includes('đóng') ||
                gioNormalized.includes('ong') || gioNormalized.includes('mo cua') || 
                gioNormalized.includes('dong cua') || gioNormalized.includes('mo') || 
                gioNormalized.includes('dong')) {
            displayTime = gioMoCua;
        } else {
            displayTime = 'Không rõ thời gian';
        }
    }
    
    // 🔥 THÊM ICON VÀO BIẾN
    const cardIcon = themeType === 'food_street' ? '🪔' : '⭐';
    const cardTitle = themeType === 'food_street' ? 'Khu ẩm thực đêm' : 'Nhà hàng Michelin';
    
    // Tạo HTML mới cho card (giữ nguyên phần còn lại)
    const newHTML = `
        <div style="margin-top: 40px; padding: 0 20px;">
            <div style="
                background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%);
                border: 3px dashed #FFB84D;
                border-radius: 20px;
                padding: 20px;
                position: relative;
                box-shadow: 0 6px 20px rgba(255, 184, 77, 0.25);
                max-width: 100%;
            ">
                
                <!-- TAG Gợi ý -->
                <div style="
                    position: absolute;
                    top: -12px;
                    left: 20px;
                    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                    color: white;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 700;
                    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                    display: flex;
                    align-items: center;
                    gap: 6px;
                ">
                    <span style="font-size: 16px;">✨</span>
                    <span>Gợi ý cho bạn</span>
                </div>
                
                <!-- HEADER -->
                <div style="margin-top: 10px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">${cardIcon}</span>
                    <div>
                        <div style="font-size: 16px; font-weight: 700; color: #6B5410; margin-bottom: 4px;">
                            ${cardTitle}
                        </div>
                        <div style="font-size: 13px; color: #8B6914; font-weight: 500;">
                            🕐 ${displayTime}
                        </div>
                    </div>
                </div>
                
                <!-- NỘI DUNG -->
                <div style="
                    background: white;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                    border: 1px solid rgba(255, 184, 77, 0.2);
                    cursor: pointer;
                    transition: all 0.3s ease;
                " onclick="flyToPlace(${place.lat}, ${place.lon}, '${place.data_id}', '${place.ten_quan.replace(/'/g, "\\'")}')"
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0, 0, 0, 0.1)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0, 0, 0, 0.04)';">
                    <div style="font-weight: 700; color: #FF6B35; margin-bottom: 8px; font-size: 15px; display: flex; align-items: center; gap: 6px;">
                        <span>🍽️</span>
                        <span>${place.ten_quan}</span>
                    </div>
                    <div style="color: #666; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
                        📍 ${place.dia_chi}
                    </div>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px;">
                        <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%); border-radius: 20px; color: #8B6914; font-weight: 600; border: 1px solid #FFD699;">
                            <span style="font-size: 16px;">⭐</span>
                            <strong>${place.rating ? parseFloat(place.rating).toFixed(1) : 'N/A'}</strong>
                        </div>
                        ${place.gia_trung_binh && !['$', '$$', '$$$', '$$$$'].includes(place.gia_trung_binh.trim()) ? `
                            <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%); border-radius: 20px; color: #8B6914; font-weight: 600; border: 1px solid #FFD699;">
                                <span style="font-size: 16px;">💰</span>
                                <strong>${place.gia_trung_binh}</strong>
                            </div>
                        ` : ''}
                    </div>
                    ${place.khau_vi ? `
                        <div style="margin-top: 12px; padding: 8px 12px; background: #FFF5E6; border-left: 3px solid #FFB84D; border-radius: 6px; font-size: 12px; color: #8B6914;">
                            👅 Khẩu vị: ${place.khau_vi}
                        </div>
                    ` : ''}
                </div>
                
                <!-- 2 NÚT -->
                <div style="margin-top: 16px; display: flex; gap: 12px; justify-content: center;">
                    <button onclick="event.stopPropagation(); random${themeType === 'food_street' ? 'FoodStreet' : 'Michelin'}();" style="
                        flex: 1;
                        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(76, 175, 80, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(76, 175, 80, 0.3)';">
                        <span style="font-size: 18px;">🔄</span>
                        <span>Đổi quán khác</span>
                    </button>
                    
                    <button onclick="event.stopPropagation(); addSuggestedToSchedule(suggested${themeType === 'food_street' ? 'FoodStreet' : 'Michelin'}, '${themeType}');" style="
                        flex: 1;
                        background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 107, 53, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 107, 53, 0.3)';">
                        <span style="font-size: 18px;">➕</span>
                        <span>Thêm vào lịch</span>
                    </button>
                </div>
                
                <!-- FOOTER -->
                <div style="margin-top: 16px; text-align: center; font-size: 13px; color: #8B6914; font-weight: 600;">
                    👆 Nhấn vào card để xem trên bản đồ
                </div>
            </div>
        </div>
    `;
    
    // ✅ THAY THẾ HTML CŨ BẰNG HTML MỚI
    targetCard.outerHTML = newHTML;
    
    console.log(`✅ Đã update card ${themeType}:`, place.ten_quan);
}

// 🔥 HÀM RANDOM LẠI KHU ẨM THỰC
async function randomFoodStreet() {
    const btn = event.target.closest('button');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span style="font-size: 18px;">⏳</span> Đang tìm...';
    }
    
    const newPlace = await randomSuggestedPlace('food_street');
    
    if (newPlace) {
        suggestedFoodStreet = newPlace;
        
        // ✅ CHỈ CẬP NHẬT CARD GỢI Ý - KHÔNG RENDER LẠI TOÀN BỘ
        updateSuggestedCard('food_street', newPlace);
    } else {
        alert('⚠️ Không tìm thấy khu ẩm thực khác trong bán kính này');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span style="font-size: 18px;">🔄</span> Đổi quán khác';
        }
    }
}

// 🔥 HÀM RANDOM LẠI MICHELIN
async function randomMichelin() {
    const btn = event.target.closest('button');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span style="font-size: 18px;">⏳</span> Đang tìm...';
    }
    
    // 🔥 RETRY 3 LẦN VỚI GIỜ 18:30
    let newPlace = null;
    for (let attempt = 0; attempt < 3; attempt++) {
        try {
            let userLat, userLon;
            
            if (window.currentUserCoords) {
                userLat = window.currentUserCoords.lat;
                userLon = window.currentUserCoords.lon;
            } else {
                break;
            }
            
            const radiusInput = document.getElementById('radius');
            const radius = radiusInput?.value || window.currentRadius || '10';
            
            const searchTime = '18:30';  // 🔥 CỐ ĐỊNH 18:30
            const randomSeed = Date.now() + attempt * 1000;
            const url = `/api/food-plan?lat=${userLat}&lon=${userLon}&random=${randomSeed}&start_time=${searchTime}&end_time=${searchTime}&radius_km=${radius}&theme=michelin`;
            
            const response = await fetch(url);
            if (!response.ok) continue;
            
            const data = await response.json();
            if (data.error || !data) continue;
            
            for (const key in data) {
                if (key !== '_order' && data[key] && data[key].place) {
                    newPlace = data[key].place;
                    break;
                }
            }
            
            if (newPlace) break;
        } catch (error) {
            console.error('Lỗi retry Michelin:', error);
        }
    }
    
    if (newPlace) {
        suggestedMichelin = newPlace;
        updateSuggestedCard('michelin', newPlace);
    } else {
        alert('⚠️ Không tìm thấy nhà hàng Michelin khác');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<span style="font-size: 18px;">🔄</span> Đổi quán khác';
        }
    }
}

// 🔥 HÀM THÊM QUÁN GỢI Ý VÀO LỊCH TRÌNH
function addSuggestedToSchedule(suggestedPlace, themeType) {
    if (!suggestedPlace) return;
    
    if (!currentPlan) {
        currentPlan = {};
    }
    
    // Tạo key mới
    const newKey = 'custom_' + Date.now();
    
    // Tính thời gian mới (sau quán cuối 1 tiếng)
    const lastMealTime = getLastMealTime();
    const newTime = addMinutesToTime(lastMealTime, 60);
    
    // Tính khoảng cách từ vị trí trước đó
    let prevLat, prevLon;
    if (window.currentUserCoords) {
        prevLat = window.currentUserCoords.lat;
        prevLon = window.currentUserCoords.lon;
    }
    
    // Tìm quán trước đó (nếu có)
    const allKeys = Object.keys(currentPlan)
        .filter(k => k !== '_order')
        .sort((a, b) => {
            const timeA = currentPlan[a]?.time || '00:00';
            const timeB = currentPlan[b]?.time || '00:00';
            return timeA.localeCompare(timeB);
        });
    
    for (let i = allKeys.length - 1; i >= 0; i--) {
        const prevMeal = currentPlan[allKeys[i]];
        if (prevMeal && prevMeal.place) {
            prevLat = prevMeal.place.lat;
            prevLon = prevMeal.place.lon;
            break;
        }
    }
    
    const distance = calculateDistanceJS(prevLat, prevLon, suggestedPlace.lat, suggestedPlace.lon);
    const travelTime = Math.round((distance / 25) * 60);
    
    const arriveTime = new Date(`2000-01-01 ${newTime}`);
    const suggestLeave = new Date(arriveTime.getTime() - travelTime * 60000);
    const suggestLeaveStr = suggestLeave.toTimeString().substring(0, 5);
    
    // Tạo meal mới
    currentPlan[newKey] = {
        time: newTime,
        title: themeType === 'food_street' ? 'Khu ẩm thực' : 'Nhà hàng Michelin',
        icon: themeType === 'food_street' ? '🪔' : '⭐',
        place: {
            ten_quan: suggestedPlace.ten_quan,
            dia_chi: suggestedPlace.dia_chi,
            rating: parseFloat(suggestedPlace.rating) || 0,
            lat: suggestedPlace.lat,
            lon: suggestedPlace.lon,
            distance: Math.round(distance * 100) / 100,
            travel_time: travelTime,
            suggest_leave: suggestLeaveStr,
            data_id: suggestedPlace.data_id,
            hinh_anh: suggestedPlace.hinh_anh || '',
            gia_trung_binh: suggestedPlace.gia_trung_binh || '',
            khau_vi: suggestedPlace.khau_vi || '',
            gio_mo_cua: suggestedPlace.gio_mo_cua || ''
        }
    };
    
    if (!currentPlan._order) {
        currentPlan._order = [];
    }
    currentPlan._order.push(newKey);
    
    // Render lại
    displayPlanVertical(currentPlan, isEditMode);
    
    // Scroll đến quán vừa thêm
    setTimeout(() => {
        const addedItem = document.querySelector(`[data-meal-key="${newKey}"]`);
        if (addedItem) {
            addedItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            const card = addedItem.querySelector('.meal-card-vertical');
            if (card) {
                card.style.border = '3px solid #4caf50';
                card.style.boxShadow = '0 0 20px rgba(76, 175, 80, 0.5)';
                
                setTimeout(() => {
                    card.style.border = '';
                    card.style.boxShadow = '';
                }, 2000);
            }
        }
    }, 100);
    
    alert('✅ Đã thêm quán vào lịch trình!');
}

// ========== TÌM KHU ẨM THỰC GỢI Ý (18:00 - 02:00) ==========
async function findSuggestedFoodStreet() {
    try {
        let userLat, userLon;
        
        if (window.currentUserCoords) {
            userLat = window.currentUserCoords.lat;
            userLon = window.currentUserCoords.lon;
        } else {
            return null;
        }
        
        const radiusInput = document.getElementById('radius');
        const radius = radiusInput?.value || window.currentRadius || '10';
        
        
        const randomHour = Math.floor(Math.random() * 9) + 18; // 18-26 (26 = 2h sÃ¡ng)
        const actualHour = randomHour >= 24 ? randomHour - 24 : randomHour;
        const randomMinute = Math.floor(Math.random() * 60);
        const searchTime = `${actualHour.toString().padStart(2, '0')}:${randomMinute.toString().padStart(2, '0')}`;
        
        const randomSeed = Date.now();
        const url = `/api/food-plan?lat=${userLat}&lon=${userLon}&random=${randomSeed}&start_time=${searchTime}&end_time=${searchTime}&radius_km=${radius}&theme=food_street`;
        
        const response = await fetch(url);
        if (!response.ok) return null;
        
        const data = await response.json();
        if (data.error || !data) return null;
        
        
        for (const key in data) {
            if (key !== '_order' && data[key] && data[key].place) {
                return data[key].place;
            }
        }
        
        return null;
    } catch (error) {
        console.error('Lỗi tìm khu ẩm thực gợi ý:', error);
        return null;
    }
}

// Tìm quán Michelin (17:00 - 00:00)
async function findSuggestedMichelin() {
    try {
        let userLat, userLon;
        
        if (window.currentUserCoords) {
            userLat = window.currentUserCoords.lat;
            userLon = window.currentUserCoords.lon;
        } else {
            return null;
        }
        
        const radiusInput = document.getElementById('radius');
        const radius = radiusInput?.value || window.currentRadius || '10';
        const searchTime = '18:30';
        const randomSeed = Date.now();
        
        const url = `/api/food-plan?lat=${userLat}&lon=${userLon}&random=${randomSeed}&start_time=${searchTime}&end_time=${searchTime}&radius_km=${radius}&theme=michelin`;
        
        const response = await fetch(url);
        if (!response.ok) return null;
        
        const data = await response.json();
        if (data.error) return null;
        
        // Tìm quán trong response
        for (const key in data) {
            if (key !== '_order' && data[key]?.place) {
                return data[key].place;
            }
        }
        
        return null;
        
    } catch (error) {
        console.error('Error finding Michelin restaurant:', error);
        return null;
    }
}

// ========== AUTO MODE: GENERATE PLAN ==========
async function generateAutoPlan() {
isViewingSharedPlan = false;
    const resultDiv = document.getElementById('planResult');

    window.loadedFromSavedPlan = false;

    // 🔁 Reset ID & tên lịch khi tạo lịch mới
    currentPlanId = null;           // không còn gắn với plan đã lưu
    window.currentPlanName = null;  // để header dùng lại "Lịch trình của bạn"

    // ✅ THÊM 2 DÒNG NÀY
    suggestedFoodStreet = null;
    suggestedMichelin = null;
    
    resultDiv.innerHTML = `
        <div class="loading-planner">
            <div class="loading-spinner"></div>
            <p>Đang tạo kế hoạch...</p>
        </div>
    `;
    
    try {
        let userLat, userLon;
        
        if (window.currentUserCoords && window.currentUserCoords.lat && window.currentUserCoords.lon) {
            userLat = window.currentUserCoords.lat;
            userLon = window.currentUserCoords.lon;
        } else if (navigator.geolocation) {
            const position = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject);
            });
            userLat = position.coords.latitude;
            userLon = position.coords.longitude;
            window.currentUserCoords = { lat: userLat, lon: userLon };
        } else {
            throw new Error('Trình duyệt không hỗ trợ GPS');
        }
        
        const startHour = document.getElementById('startHour').value.padStart(2, '0');
        const startMinute = document.getElementById('startMinute').value.padStart(2, '0');
        const startTime = `${startHour}:${startMinute}`;

        const endHour = document.getElementById('endHour').value.padStart(2, '0');
        const endMinute = document.getElementById('endMinute').value.padStart(2, '0');
        const endTime = `${endHour}:${endMinute}`;
        
        // 🔥 ĐỌC TỪ HIDDEN INPUT TRƯỚC, SAU ĐÓ MỚI DÙNG window.currentRadius
        const radiusInput = document.getElementById('radius');
        const radius = radiusInput?.value || window.currentRadius || '10';

        // 🔥 CẬP NHẬT LẠI window.currentRadius
        window.currentRadius = radius;

        console.log('🔍 Bán kính đang dùng:', radius + ' km');

        const selectedFlavors = getSelectedFlavors();
        const tastesParam = selectedFlavors.join(',');
        
        const randomSeed = Date.now();
        let url = `/api/food-plan?lat=${userLat}&lon=${userLon}&random=${randomSeed}&start_time=${startTime}&end_time=${endTime}&radius_km=${radius}`;
        
        if (selectedThemes.length > 0) {
            url += `&theme=${selectedThemes.join(',')}`;
        }
        
        if (tastesParam) {
            url += `&tastes=${tastesParam}`;
        }
        
        const response = await fetch(url);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.message || 'Không thể tạo kế hoạch');
        }
        
        const data = await response.json();

        // 🔥 LOG DEBUG - KIỂM TRA DATA TỪ API
        console.log('🔍 [API Response] Full data:', data);
        Object.keys(data).forEach(key => {
            if (key !== '_order' && data[key] && data[key].place) {
                console.log(`📍 [${key}] ${data[key].place.ten_quan}`);
                console.log(`   gio_mo_cua:`, data[key].place.gio_mo_cua);
            }
        });
        
        if (data.error) {
            resultDiv.innerHTML = `
                <div class="error-message">
                    <h3>😔 ${data.message || 'Không tìm thấy quán'}</h3>
                    <p>Hãy thử tăng bán kính tìm kiếm hoặc thay đổi bộ lọc</p>
                </div>
            `;
            return;
        }
        
        currentPlan = data;
        isEditMode = false;

        console.log('🔍 [Generate] Selected themes:', selectedThemes);
        console.log('🔍 [Generate] BEFORE fetch - suggestedMichelin:', suggestedMichelin);

        // 🔥 TÌM FOOD STREET TRƯỚC
        if (selectedThemes.includes('food_street')) {
            console.log('🔍 Đang fetch Food Street...');
            suggestedFoodStreet = await findSuggestedFoodStreet();
            console.log('📍 After fetch Food Street:', suggestedFoodStreet?.ten_quan || 'NULL');
        }

        // 🔥 SAU ĐÓ TÌM MICHELIN
        if (selectedThemes.includes('michelin')) {
            console.log('🔍 Đang fetch Michelin...');
            suggestedMichelin = await findSuggestedMichelin();
            console.log('📍 After fetch Michelin:', suggestedMichelin?.ten_quan || 'NULL');
        }

        // 🔥 RENDER 1 LẦN DUY NHẤT SAU KHI CẢ 2 XONG
        console.log('🎨 [Final] Render với:', {
            foodStreet: suggestedFoodStreet?.ten_quan || 'null',
            michelin: suggestedMichelin?.ten_quan || 'null',
            selectedThemes: selectedThemes
        });

        displayPlanVertical(currentPlan, false);
        
    } catch (error) {
        console.error('Error:', error);
        resultDiv.innerHTML = `
            <div class="error-message">
                <h3>⚠️ Không thể tạo kế hoạch</h3>
                <p>${error.message === 'User denied Geolocation' 
                    ? 'Vui lòng bật GPS và thử lại' 
                    : 'Đã có lỗi xảy ra. Vui lòng thử lại sau.'}</p>
            </div>
        `;
    }
}

// ========== TÍNH TỔNG KINH PHÍ ==========
function calculateTotalBudget(plan) {
    let total = 0;
    let unknownCount = 0;
    let hasOverPrice = false;
    
    Object.keys(plan).forEach(key => {
        if (key === '_order') return;
        
        const meal = plan[key];
        if (!meal || !meal.place || !meal.place.gia_trung_binh) {
            unknownCount++;
            return;
        }
        
        const priceStr = meal.place.gia_trung_binh.trim();
        
        // 🔥 XỬ LÝ "Trên X.XXX.XXX ₫"
        if (priceStr.includes('Trên')) {
            hasOverPrice = true;
            const match = priceStr.match(/[\d\.]+/);
            if (match) {
                const value = parseInt(match[0].replace(/\./g, ''));
                total += value;
            }
            return;
        }
        
        // 🔥 XỬ LÝ KHOẢNG GIÁ: "100-200 N ₫" hoặc "1-100.000 ₫"
        const parts = priceStr.split('-');
        if (parts.length === 2) {
            let maxPart = parts[1].trim();
            
            // 🔥 CHUẨN HÓA: Thay thế TẤT CẢ khoảng trắng (bao gồm \xa0) thành khoảng trắng thường
            maxPart = maxPart.replace(/\s+/g, ' ');
            
            // 🔥 KIỂM TRA CÓ CHỮ "N" (không phân biệt khoảng trắng)
            const hasN = /N\s*₫/i.test(maxPart) || /\s+N\s+/i.test(maxPart);
            
            // Xóa TẤT CẢ ký tự không phải số hoặc dấu chấm
            maxPart = maxPart.replace(/[^\d\.]/g, '');
            
            // Xóa dấu chấm phân cách hàng nghìn
            maxPart = maxPart.replace(/\./g, '');
            
            let max = parseInt(maxPart);
            
            // 🔥 NẾU CÓ CHỮ "N" → NHÂN 1000
            if (!isNaN(max) && max > 0) {
                if (hasN) {
                    max = max * 1000;
                }
                total += max;
            } else {
                unknownCount++;
            }
        } else {
            unknownCount++;
        }
    });
    
    return {
        total: total,
        unknown: unknownCount,
        hasOverPrice: hasOverPrice
    };
}

function formatMoney(value) {
    if (value >= 1000000) {
        return (value / 1000000).toFixed(1).replace('.0', '') + ' triệu ₫';
    } else if (value >= 1000) {
        return (value / 1000).toFixed(0) + '.000 ₫';
    } else {
        return value + ' ₫';
    }
}
// ========== SHARE PLAN LOGIC ==========
let isSharedPlan = false;
let sharedPlanOwnerId = null;
let hasEditPermission = false;
let sharedPlanOwnerName = ''; // ✅ THÊM DÒNG NÀY
let isViewingSharedPlan = false; // 🔥 BIẾN MỚI - theo dõi có đang xem shared plan không
window.originalSharedPlanData = null; // 🔥 MỚI: Lưu bản gốc của shared plan
// 🔥 THÊM BIẾN MỚI - LƯU TRẠNG THÁI CÁC THAY ĐỔI TẠM THỜI
let pendingApprovals = {}; // { suggestionId: { approvedChanges: [], rejectedChanges: [] } }
let hasPendingSuggestion = false; // 🔥 THÊM: Theo dõi có suggestion pending không

// ========== SO SÁNH 2 PLAN DATA ==========
function comparePlanData(plan1, plan2) {
    // Bỏ qua _order khi so sánh
    const keys1 = Object.keys(plan1).filter(k => k !== '_order').sort();
    const keys2 = Object.keys(plan2).filter(k => k !== '_order').sort();
    
    // Kiểm tra số lượng keys
    if (keys1.length !== keys2.length) {
        console.log('🔍 [COMPARE] Khác số lượng keys:', keys1.length, 'vs', keys2.length);
        return false;
    }
    
    // Kiểm tra xem keys có giống nhau không
    if (JSON.stringify(keys1) !== JSON.stringify(keys2)) {
        console.log('🔍 [COMPARE] Khác danh sách keys');
        return false;
    }
    
    // So sánh từng key
    for (const key of keys1) {
        const meal1 = plan1[key];
        const meal2 = plan2[key];
        
        // So sánh time
        if (meal1.time !== meal2.time) {
            console.log(`🔍 [COMPARE] Key ${key} - Khác time:`, meal1.time, 'vs', meal2.time);
            return false;
        }
        
        // So sánh title
        if (meal1.title !== meal2.title) {
            console.log(`🔍 [COMPARE] Key ${key} - Khác title:`, meal1.title, 'vs', meal2.title);
            return false;
        }
        
        // So sánh icon
        if (meal1.icon !== meal2.icon) {
            console.log(`🔍 [COMPARE] Key ${key} - Khác icon:`, meal1.icon, 'vs', meal2.icon);
            return false;
        }
        
        // So sánh place
        const place1 = meal1.place;
        const place2 = meal2.place;
        
        // Nếu 1 cái có place, 1 cái không có
        if ((place1 && !place2) || (!place1 && place2)) {
            console.log(`🔍 [COMPARE] Key ${key} - Khác place existence`);
            return false;
        }
        
        // Nếu cả 2 đều có place, so sánh data_id
        if (place1 && place2) {
            if (place1.data_id !== place2.data_id) {
                console.log(`🔍 [COMPARE] Key ${key} - Khác place:`, place1.data_id, 'vs', place2.data_id);
                return false;
            }
        }
    }
    
    console.log('✅ [COMPARE] Plan giống nhau hoàn toàn');
    return true;
}

async function sharePlan() {
    if (!currentPlan || !currentPlanId) {
        alert('⚠️ Chưa có lịch trình để chia sẻ');
        return;
    }
    
    try {
        // Lấy danh sách bạn bè
        const response = await fetch('/api/accounts/my-friends/');
        const data = await response.json();
        
        if (!data.friends || data.friends.length === 0) {
            alert('Bạn chưa có bạn bè nào để chia sẻ');
            return;
        }
        
        // Tạo modal chọn bạn bè
        const friendsList = data.friends.map(friend => `
            <label style="display: flex; align-items: center; gap: 8px; padding: 8px; cursor: pointer;">
                <input type="checkbox" value="${friend.id}" class="friend-checkbox">
                <span>${friend.username}</span>
            </label>
        `).join('');
        
        const modalHTML = `
            <div id="shareModal" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 99999; display: flex; align-items: center; justify-content: center;">
                <div style="background: white; padding: 30px; border-radius: 16px; max-width: 400px; width: 90%;">
                    <h3 style="margin-top: 0;">📤 Chia sẻ lịch trình</h3>
                    <p style="color: #666; font-size: 14px;">Chọn bạn bè bạn muốn chia sẻ:</p>
                    
                    <div style="max-height: 300px; overflow-y: auto; border: 1px solid #ddd; border-radius: 8px; padding: 10px; margin: 15px 0;">
                        ${friendsList}
                    </div>
                    
                    <div style="display: flex; gap: 10px; margin-top: 20px;">
                        <button onclick="confirmShare()" style="flex: 1; padding: 12px; background: #FF6B35; color: white; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">Chia sẻ</button>
                        <button onclick="closeShareModal()" style="flex: 1; padding: 12px; background: #ccc; color: #333; border: none; border-radius: 8px; cursor: pointer; font-weight: 600;">Hủy</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
    } catch (error) {
        console.error('Error loading friends:', error);
        alert('Không thể tải danh sách bạn bè');
    }
}

function closeShareModal() {
    const modal = document.getElementById('shareModal');
    if (modal) modal.remove();
}

async function confirmShare() {
    const checkedBoxes = document.querySelectorAll('.friend-checkbox:checked');
    const friend_ids = Array.from(checkedBoxes).map(cb => parseInt(cb.value));
    
    if (friend_ids.length === 0) {
        alert('Vui lòng chọn ít nhất 1 bạn bè');
        return;
    }
    
    try {
        const response = await fetch(`/api/accounts/food-plan/share/${currentPlanId}/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                friend_ids: friend_ids,
                permission: 'edit'
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✅ ' + result.message);
            closeShareModal();
        } else {
            alert('❌ ' + result.message);
        }
        
    } catch (error) {
        console.error('Error sharing plan:', error);
        alert('Không thể chia sẻ lịch trình');
    }
}

// ========== LOAD SHARED PLANS ==========
async function loadSharedPlans() {
    try {
        const response = await fetch('/api/accounts/food-plan/shared/');
        const data = await response.json();
        
        if (data.status === 'success' && data.shared_plans.length > 0) {
            // Thêm vào saved plans list
            displaySavedPlansList(data.shared_plans, true); // true = là shared plans
        }
    } catch (error) {
        console.error('Error loading shared plans:', error);
    }
}

// ========== AUTO MODE: DISPLAY VERTICAL TIMELINE ==========
function displayPlanVertical(plan, editMode = false) {
    const resultDiv = document.getElementById('planResult');
    
    if (!plan || Object.keys(plan).length === 0) {
        resultDiv.innerHTML = `
            <div class="error-message">
                <h3>😔 Không tìm thấy quán</h3>
                <p>Không có quán nào phù hợp trong khu vực của bạn</p>
            </div>
        `;
        clearRoutes();
        return;
    }

    // 🔥 KIỂM TRA TRƯỜNG HỢP ĐÃ XÓA HẾT QUÁN TRONG EDIT MODE
    const allKeys = Object.keys(plan).filter(k => k !== '_order');
    if (allKeys.length === 0 && editMode) {
        resultDiv.innerHTML = `
            <div class="error-message">
                <h3>🗑️ Đã xóa hết lịch trình</h3>
                <p>Bạn đã xóa tất cả các quán trong lịch trình này</p>
                <button onclick="toggleEditMode(); generateAutoPlan();" 
                    style="margin-top: 15px; padding: 10px 20px; background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 14px; font-weight: 600;">
                    ✨ Tạo lại lịch trình
                </button>
            </div>
        `;
        clearRoutes();
        return;
    }

    // 🔥 TÍNH TỔNG KINH PHÍ
    const budget = calculateTotalBudget(plan);
    
    // 🔥 ẨN/HIỆN FILTERS DựA vào trạng thái xem shared plan
const filtersWrapper = document.querySelector('.filters-wrapper-new');
if (filtersWrapper) {
    if (isViewingSharedPlan) {
        filtersWrapper.style.display = 'none'; // Ẩn khi xem shared plan
    } else {
        filtersWrapper.style.display = 'block'; // Hiện khi không xem shared plan
    }
}

   let html = `
<div class="schedule-header">
    <div>
        <h3 class="schedule-title">
            <span style="margin-right: 8px;">📅</span>
            <span ${!isSharedPlan && editMode ? 'contenteditable="true" class="editable" onblur="updateAutoPlanName(this.textContent)"' : ''}><span>${window.currentPlanName || 'Lịch trình của bạn'}</span></span>
        </h3>
        ${isSharedPlan ? `
            <p style="font-size: 12px; color: #666; margin: 5px 0 0 0;">
                Được chia sẻ bởi <strong>${sharedPlanOwnerName}</strong>
            </p>
        ` : ''}
    </div>
    <div class="action-buttons" id="actionButtons">
  
    
   ${isSharedPlan ? `
    ${hasEditPermission ? `
        <button class="action-btn edit ${editMode ? 'active' : ''}" id="editPlanBtn" onclick="toggleEditMode()" title="${editMode ? 'Thoát chỉnh sửa' : 'Chỉnh sửa'}">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
            </svg>
            <span class="btn-label">${editMode ? 'Xong' : 'Sửa'}</span>
        </button>
        
        <button class="action-btn" onclick="viewMySuggestions(${currentPlanId})" 
            style="background: linear-gradient(135deg, #9C27B0 0%, #BA68C8 100%);" 
            title="Xem đề xuất của tôi">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
            </svg>
            <span class="btn-label">Đề xuất của tôi</span>
        </button>
        
        <button class="action-btn primary" onclick="submitSuggestion()" title="Gửi đề xuất" ${hasPendingSuggestion ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
            </svg>
            <span class="btn-label">${hasPendingSuggestion ? 'Đang chờ duyệt' : 'Gửi đề xuất'}</span>
        </button>
        ${hasPendingSuggestion ? `
            <div style="
                position: absolute;
                top: -8px;
                right: -8px;
                background: #FF9800;
                color: white;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                font-weight: 700;
                box-shadow: 0 2px 8px rgba(255, 152, 0, 0.4);
            ">⏳</div>
        ` : ''}
    ` : ''}
` : `
    <button class="action-btn" onclick="openSuggestionsPanel()" id="suggestionsBtn" title="Xem đề xuất chỉnh sửa" style="display: none; background: linear-gradient(135deg, #9C27B0 0%, #BA68C8 100%);">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"/>
        </svg>
        <span class="btn-label">Đề xuất (<span id="suggestionCount">0</span>)</span>
    </button>
    
    <button class="action-btn edit ${editMode ? 'active' : ''}" id="editPlanBtn" onclick="toggleEditMode()" title="${editMode ? 'Thoát chỉnh sửa' : 'Chỉnh sửa'}">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
        </svg>
        <span class="btn-label">${editMode ? 'Xong' : 'Sửa'}</span>
    </button>
    
    <button class="action-btn primary" onclick="savePlan()" title="Lưu kế hoạch">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M17 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/>
        </svg>
        <span class="btn-label">Lưu</span>
    </button>
    
    <button class="action-btn share" onclick="sharePlan()" title="Chia sẻ kế hoạch">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
            <path d="M15 8l4.39 4.39a1 1 0 010 1.42L15 18.2v-3.1c-4.38.04-7.43 1.4-9.88 4.3.94-4.67 3.78-8.36 9.88-8.4V8z"/>
        </svg>
        <span class="btn-label">Chia sẻ</span>
    </button>
`}
    </div>
</div>
  <div class="timeline-container"><div class="timeline-line"></div>
`;
    

  
    
    const mealOrder = ['breakfast', 'morning_drink', 'lunch', 'afternoon_drink', 'dinner', 'dessert', 'meal', 'meal1', 'drink', 'meal2'];
    let hasPlaces = false;
    
    // 🔥 ƯU TIÊN THỨ TỰ ĐÃ KÉO THẢ (_order), CHỈ SORT KHI CHƯA CÓ _order
    let allMealKeys;

    if (plan._order && plan._order.length > 0) {
        // ✅ Nếu có _order (đã kéo thả) → GIỮ NGUYÊN thứ tự
        allMealKeys = plan._order.filter(k => plan[k] && plan[k].time);
    } else {
        // ✅ Nếu chưa có _order → Sắp xếp theo thời gian
        allMealKeys = Object.keys(plan)
            .filter(k => k !== '_order' && plan[k] && plan[k].time)
            .sort((a, b) => {
                const timeA = plan[a].time || '00:00';
                const timeB = plan[b].time || '00:00';
                return timeA.localeCompare(timeB);
            });
        
        // 🔥 LƯU vào _order để lần sau không bị sort lại
        plan._order = allMealKeys;
    }
    
    for (const key of allMealKeys) {
        const meal = plan[key];
        if (!meal) continue;
        
        const icon = meal.icon || mealIcons[key] || '🍽️';
        
        // Kiểm tra nếu là slot trống (chưa có place)
        if (!meal.place) {
            const isWaitingForSelection = waitingForPlaceSelection === key;
            
            html += `
                <div class="meal-item" draggable="${editMode}" data-meal-key="${key}">
                    <div class="time-marker">
                        ${editMode ? 
                            `<div style="display: inline-flex; gap: 5px; align-items: center; justify-content: center; background: white; padding: 6px 12px; border-radius: 25px; box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);">
                                <input type="number" min="0" max="23" value="${meal.time.split(':')[0]}" 
                                    class="time-input-hour" data-meal-key="${key}"
                                    style="width: 60px; padding: 8px 6px; border: 2px solid #FFE5D9; border-radius: 8px; font-size: 16px; text-align: center; font-weight: 700; background: white; line-height: 1;">
                                <span style="font-weight: bold; color: #FF6B35; font-size: 18px;">:</span>
                                <input type="number" min="0" max="59" value="${meal.time.split(':')[1]}" 
                                    class="time-input-minute" data-meal-key="${key}"
                                    style="width: 60px; padding: 8px 6px; border: 2px solid #FFE5D9; border-radius: 8px; font-size: 16px; text-align: center; font-weight: 700; background: white; line-height: 1;">
                            </div>` :
                            `<div class="time-badge">⏰ ${meal.time}</div>`
                        }
                    </div>
                    <div class="time-dot"></div>
                    <div class="meal-card-vertical empty-slot ${editMode ? 'edit-mode' : ''}">
                        <div class="meal-title-vertical">
                            <div class="meal-title-left">
                                ${editMode ? `
                                    <select onchange="updateMealIcon('${key}', this.value)" style="border: none; background: transparent; font-size: 22px; cursor: pointer; outline: none; padding: 0;" onclick="event.stopPropagation();">
                                        ${iconOptions.map(ico => `<option value="${ico}" ${ico === icon ? 'selected' : ''}>${ico}</option>`).join('')}
                                    </select>
                                ` : `<span style="font-size: 22px;">${icon}</span>`}
                                ${editMode 
                                    ? `<input type="text" value="${meal.title}" onchange="updateMealTitle('${key}', this.value)" 
                                        class="time-input-inline" onclick="event.stopPropagation();" placeholder="Nhập tên bữa ăn">`
                                    : `<span>${meal.title}</span>`
                                }
                            </div>
                            ${editMode ? `
                            <div class="meal-actions">
                                <button class="meal-action-btn select-meal ${isWaitingForSelection ? 'active' : ''}" 
                                        onclick="selectPlaceForMeal('${key}')" title="${isWaitingForSelection ? 'Đang chờ bạn chọn quán trên bản đồ...' : 'Nhấn để chọn quán ăn từ bản đồ'}">
                                    <span class="btn-icon">${isWaitingForSelection ? '⏳' : '✏️'}</span>
                                    <span class="btn-text">${isWaitingForSelection ? 'Đang chọn...' : 'Chọn quán'}</span>
                                </button>
                                <button class="meal-action-btn delete-meal" onclick="deleteMealSlot('${key}')" title="Xóa bữa ăn này">
                                    <span class="btn-icon">🗑️</span>
                                    <span class="btn-text">Xóa</span>
                                </button>
                            </div>
                            ` : ''}
                        </div>
                        <div class="empty-slot-content">
                            <div class="icon">🏪</div>
                            <div class="text">${isWaitingForSelection ? 'Đang chờ chọn quán...' : 'Chưa có quán'}</div>
                            ${!editMode ? '<div style="font-size: 12px; margin-top: 8px; color: #999;">Bật chế độ chỉnh sửa để thêm quán</div>' : ''}
                        </div>
                    </div>
                </div>
            `;
            continue;
        }
        
        hasPlaces = true;
        const place = meal.place;
        
        // ✅ CODE MỚI - TRUYỀN THÊM data_id VÀ ten_quan
        const cardClickEvent = `onclick="flyToPlace(${place.lat}, ${place.lon}, '${place.data_id}', '${place.ten_quan.replace(/'/g, "\\'")}')"`;
        const cardCursor = 'cursor: pointer;'; // ✅ LUÔN HIỆN CON TRỎ TAY
        
        const isWaitingForSelection = waitingForPlaceSelection === key;
        
        html += `
            <div class="meal-item" draggable="${editMode}" data-meal-key="${key}">
                <div class="time-marker">
                    ${editMode ? 
                        `<div style="display: inline-flex; gap: 5px; align-items: center; justify-content: center; background: white; padding: 6px 12px; border-radius: 25px; box-shadow: 0 4px 12px rgba(255, 107, 53, 0.2);">
                            <input type="number" min="0" max="23" value="${meal.time.split(':')[0]}" 
                                class="time-input-hour" data-meal-key="${key}"
                                style="width: 60px; padding: 8px 6px; border: 2px solid #FFE5D9; border-radius: 8px; font-size: 16px; text-align: center; font-weight: 700; background: white; line-height: 1;">
                            <span style="font-weight: bold; color: #FF6B35; font-size: 18px;">:</span>
                            <input type="number" min="0" max="59" value="${meal.time.split(':')[1]}" 
                                class="time-input-minute" data-meal-key="${key}"
                                style="width: 60px; padding: 8px 6px; border: 2px solid #FFE5D9; border-radius: 8px; font-size: 16px; text-align: center; font-weight: 700; background: white; line-height: 1;">
                        </div>` :
                        `<div class="time-badge">⏰ ${meal.time}</div>`
                    }
                </div>
                <div class="time-dot"></div>
                <div class="meal-card-vertical ${editMode ? 'edit-mode' : ''} ${(() => {
                    // 🔥 KIỂM TRA NHIỀU NGUỒN: mo_ta, title, icon
                    const moTa = (place.mo_ta || '').toLowerCase();
                    const title = (meal.title || '').toLowerCase();
                    const icon = meal.icon || '';
                    
                    // Kiểm tra từ MÔ TẢ (mo_ta)
                    const isKhuAmThucFromMoTa = moTa.includes('khu') && moTa.includes('am thuc');
                    const isMichelinFromMoTa = moTa === 'michelin';
                    
                    // Kiểm tra từ TITLE của meal
                    const isKhuAmThucFromTitle = title.includes('khu') && title.includes('ẩm thực');
                    const isMichelinFromTitle = title.includes('michelin');
                    
                    // Kiểm tra từ ICON
                    const isKhuAmThucFromIcon = icon === '🪔';
                    const isMichelinFromIcon = icon === '⭐';
                    
                    // TRẢ VỀ CLASS
                    const isGold = isKhuAmThucFromMoTa || isMichelinFromMoTa || 
                                isKhuAmThucFromTitle || isMichelinFromTitle ||
                                isKhuAmThucFromIcon || isMichelinFromIcon;
                    
                    return isGold ? 'gold-card' : '';
                })()}" ${cardClickEvent} style="${cardCursor}">
                    <div class="meal-title-vertical">
                        <div class="meal-title-left">
                            ${editMode ? `
                                <select onchange="updateMealIcon('${key}', this.value)" style="border: none; background: transparent; font-size: 22px; cursor: pointer; outline: none; padding: 0;" onclick="event.stopPropagation();">
                                    ${iconOptions.map(ico => `<option value="${ico}" ${ico === icon ? 'selected' : ''}>${ico}</option>`).join('')}
                                </select>
                            ` : `<span style="font-size: 22px;">${icon}</span>`}
                            <div style="display: flex; flex-direction: column; gap: 2px;">
                                ${editMode ? 
                                    `<input type="text" value="${meal.title}" onchange="updateMealTitle('${key}', this.value)" 
                                        class="time-input-inline" onclick="event.stopPropagation();" placeholder="Nhập tên bữa ăn">`
                                    : `<span>${meal.title}</span>`
                                }
                                ${(() => {
                                    const gioMoCua = place.gio_mo_cua || '';
                                    let displayTime = '';
                                    
                                    if (!gioMoCua || gioMoCua.trim() === '') {
                                        displayTime = 'Không rõ thời gian';
                                    } else {
                                        const gioNormalized = gioMoCua.toLowerCase();
                                        
                                        if (gioNormalized.includes('always') || gioNormalized.includes('24') || 
                                            gioNormalized.includes('cả ngày') || gioNormalized.includes('mở cả ngày') ||
                                            gioNormalized.includes('ca ngay') || gioNormalized.includes('mo ca ngay')) {
                                            displayTime = 'Mở cả ngày';
                                        } else if (gioNormalized.includes('mở') || gioNormalized.includes('đóng') ||
                                                gioNormalized.includes('ong') || gioNormalized.includes('mo cua') || 
                                                gioNormalized.includes('dong cua') || gioNormalized.includes('mo') || 
                                                gioNormalized.includes('dong')) {
                                            displayTime = gioMoCua;
                                        } else {
                                            displayTime = 'Không rõ thời gian';
                                        }
                                    }
                                    
                                    return `<div style="font-size: 11px; color: #8B6914; font-weight: 500;">
                                        🕐 ${displayTime}
                                    </div>`;
                                })()}
                            </div>
                        </div>
                        ${editMode ? `
                        <div class="meal-actions">
                            <button class="meal-action-btn select-meal ${isWaitingForSelection ? 'active' : ''}" 
                                    onclick="event.stopPropagation(); selectPlaceForMeal('${key}')" title="${isWaitingForSelection ? 'Đang chờ bạn chọn quán khác trên bản đồ...' : 'Nhấn để đổi sang quán khác'}">
                                <span class="btn-icon">${isWaitingForSelection ? '⏳' : '✏️'}</span>
                                <span class="btn-text">${isWaitingForSelection ? 'Đang đổi...' : 'Đổi quán'}</span>
                            </button>
                            <button class="meal-action-btn delete-meal" onclick="event.stopPropagation(); deleteMealSlot('${key}')" title="Xóa bữa ăn này">
                                <span class="btn-icon">🗑️</span>
                                <span class="btn-text">Xóa</span>
                            </button>
                        </div>
                        ` : ''}
                    </div>
                    <div class="place-info-vertical">
                        <div class="place-name-vertical">${place.ten_quan}</div>
                        <div class="place-address-vertical">📍 ${place.dia_chi}</div>
                        <div class="place-meta-vertical">
                            <div class="meta-item-vertical">
                                <span>⭐</span>
                                <strong>${place.rating ? parseFloat(place.rating).toFixed(1) : 'N/A'}</strong>
                            </div>
                            ${place.gia_trung_binh && !['$', '$$', '$$$', '$$$$'].includes(place.gia_trung_binh.trim()) ? `
                                <div class="meta-item-vertical">
                                    <span>💰</span>
                                    <strong>${place.gia_trung_binh}</strong>
                                </div>
                            ` : ''}
                        </div>
                        ${place.khau_vi ? `
                            <div style="margin-top: 8px; padding: 6px 10px; background: #FFF5E6; border-left: 3px solid #FFB84D; border-radius: 6px; font-size: 12px; color: #8B6914;">
                                👅 Khẩu vị: ${place.khau_vi}
                            </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    html += '</div>'; // Đóng timeline-container

    // 🔥 NÚT THÊM/XÓA (CHỈ KHI EDIT MODE)
    if (editMode) {
        html += `
            <div style="margin-top: 30px; padding: 20px; text-align: center; display: flex; justify-content: center; align-items: center; gap: 30px;">
                <!-- NÚT THÊM QUÁN MỚI -->
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <button onclick="addNewMealSlot()" style="
                        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                        color: white;
                        border: none;
                        width: 56px;
                        height: 56px;
                        border-radius: 50%;
                        cursor: pointer;
                        font-size: 28px;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
                        transition: all 0.2s ease;
                    " onmouseover="this.style.transform='scale(1.1)'; this.style.boxShadow='0 6px 16px rgba(76, 175, 80, 0.4)';" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(76, 175, 80, 0.3)';" title="Thêm quán mới">
                        +
                    </button>
                    <div style="margin-top: 10px; font-size: 14px; color: #4caf50; font-weight: 600;">
                        Thêm quán mới
                    </div>
                </div>
                
                <!-- NÚT LÀM TRỐNG -->
                <div style="display: flex; flex-direction: column; align-items: center;">
                    <button onclick="deleteAllMeals()" style="
                        background: linear-gradient(135deg, #FF6B35 0%, #FFB84D 100%);
                        color: white;
                        border: none;
                        width: 56px;
                        height: 56px;
                        border-radius: 50%;
                        cursor: pointer;
                        font-size: 28px;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                        transition: all 0.2s ease;
                    " onmouseover="this.style.transform='scale(1.1)'; this.style.boxShadow='0 6px 16px rgba(255, 107, 53, 0.4)';" onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 4px 12px rgba(255, 107, 53, 0.3)';" title="Làm trống lịch trình">
                        📋
                    </button>
                    <div style="margin-top: 10px; font-size: 14px; color: #FF6B35; font-weight: 600;">
                        Làm trống
                    </div>
                </div>
            </div>
        `;
    }

    // 📍 Bán Kính Tìm Kiếm - CHỈ HIỆN KHI TẠO MỚI
    if (!window.loadedFromSavedPlan) {
        html += `
        <div style="
            background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%);
            border: 2px solid #FFB84D;
            border-radius: 16px;
            padding: 16px 20px;
            margin: 24px 20px 16px 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 4px 12px rgba(255, 184, 77, 0.2);
        ">
            <div style="display: flex; align-items: center; gap: 12px;">
                <span style="font-size: 28px;">📍</span>
                <div>
                    <div style="font-size: 13px; color: #8B6914; font-weight: 600; margin-bottom: 4px;">
                        Bán kính tìm kiếm
                        <span style="
                            display: inline-block;
                            background: rgba(255, 107, 53, 0.15);
                            color: #FF6B35;
                            padding: 2px 8px;
                            border-radius: 12px;
                            font-size: 11px;
                            font-weight: 700;
                            margin-left: 8px;
                            border: 1px solid rgba(255, 107, 53, 0.3);
                        ">Thay đổi bán kính<br>ở thanh lọc bán kính</span>
                    </div>
                    <div style="font-size: 20px; font-weight: 700; color: #6B5410;">
                        ${window.currentRadius || '10'} km
                    </div>
                </div>
            </div>
            <div style="
                background: rgba(255, 184, 77, 0.2);
                padding: 10px 16px;
                border-radius: 10px;
                font-size: 12px;
                color: #8B6914;
                font-weight: 600;
                text-align: center;
                line-height: 1.5;
                min-width: 140px;
            ">
                ℹ️ Bán kính mặc định: 10km
            </div>
        </div>
        `;
    }
    // 💰 Tổng Kinh Phí
    html += `
    <div style="
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border: 2px solid #4caf50;
        border-radius: 16px;
        padding: 16px 20px;
        margin: 16px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.2);
    ">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="font-size: 28px;">💰</span>
            <div>
                <div style="font-size: 13px; color: #2e7d32; font-weight: 600; margin-bottom: 4px;">Tổng kinh phí dự kiến</div>
                <div style="font-size: 20px; font-weight: 700; color: #1b5e20;">
                    ${budget.hasOverPrice ? 'Trên ' : ''}${formatMoney(budget.total)}
                    ${budget.unknown > 0 ? `<span style="font-size: 13px; font-weight: 500; color: #666; margin-left: 8px;">(Không tính ${budget.unknown} quán)</span>` : ''}
                </div>
            </div>
        </div>
    </div>
    `;

// 🔥 CARD GỢI Ý MICHELIN (17:00 - 00:00)
console.log('🔍 [displayPlanVertical] Check Michelin:', {
    suggestedMichelin: suggestedMichelin,
    tenQuan: suggestedMichelin?.ten_quan,
    selectedThemes: selectedThemes,
    hasMichelinTheme: selectedThemes.includes('michelin')
});

const shouldShowMichelinSuggestion = suggestedMichelin && 
                                      selectedThemes.includes('michelin');

console.log('🎯 shouldShowMichelinSuggestion:', shouldShowMichelinSuggestion);

if (shouldShowMichelinSuggestion) {
    console.log('✅ RENDER Michelin card:', suggestedMichelin.ten_quan);
    html += `
        <div style="margin-top: 40px; padding: 0 20px;">
            <div style="
                background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%);
                border: 3px dashed #FFB84D;
                border-radius: 20px;
                padding: 20px;
                position: relative;
                box-shadow: 0 6px 20px rgba(255, 184, 77, 0.25);
                max-width: 100%;
            ">
                
                <!-- ✅ TAG Gợi ý cho bạn -->
                <div style="
                    position: absolute;
                    top: -12px;
                    left: 20px;
                    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                    color: white;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 700;
                    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                    display: flex;
                    align-items: center;
                    gap: 6px;
                ">
                    <span style="font-size: 16px;">✨</span>
                    <span>Gợi ý cho bạn</span>
                </div>
                
                <!-- HEADER -->
                <div style="margin-top: 10px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">⭐</span>
                    <div>
                        <div style="font-size: 16px; font-weight: 700; color: #6B5410; margin-bottom: 4px;">
                            Nhà hàng Michelin
                        </div>
                        ${(() => {
                            const gioMoCua = suggestedMichelin.gio_mo_cua || '';
                            let displayTime = '';
                            
                            if (!gioMoCua || gioMoCua.trim() === '') {
                                displayTime = 'Không rõ thời gian';
                            } else {
                                const gioNormalized = gioMoCua.toLowerCase();
                                
                                if (gioNormalized.includes('always') || gioNormalized.includes('24') || 
                                    gioNormalized.includes('cả ngày') || gioNormalized.includes('mở cả ngày') ||
                                    gioNormalized.includes('ca ngay') || gioNormalized.includes('mo ca ngay')) {
                                    displayTime = 'Mở cả ngày';
                                } else if (gioNormalized.includes('mở') || gioNormalized.includes('đóng') ||
                                        gioNormalized.includes('ong') || gioNormalized.includes('mo cua') || 
                                        gioNormalized.includes('dong cua') || gioNormalized.includes('mo') || 
                                        gioNormalized.includes('dong')) {
                                    displayTime = gioMoCua;
                                } else {
                                    displayTime = 'Không rõ thời gian';
                                }
                            }
                            
                            return `<div style="font-size: 13px; color: #8B6914; font-weight: 500;">
                                🕐 ${displayTime}
                            </div>`;
                        })()}
                    </div>
                </div>
                
                <!-- NỘI DUNG -->
                <div style="
                    background: white;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                    border: 1px solid rgba(255, 184, 77, 0.2);
                    cursor: pointer;
                    transition: all 0.3s ease;
                " onclick="flyToPlace(${suggestedMichelin.lat}, ${suggestedMichelin.lon}, '${suggestedMichelin.data_id}', '${suggestedMichelin.ten_quan.replace(/'/g, "\\'")}')"
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0, 0, 0, 0.1)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0, 0, 0, 0.04)';">
                    <div style="font-weight: 700; color: #FF6B35; margin-bottom: 8px; font-size: 15px; display: flex; align-items: center; gap: 6px;">
                        <span>🍽️</span>
                        <span>${suggestedMichelin.ten_quan}</span>
                    </div>
                    <div style="color: #666; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
                        📍 ${suggestedMichelin.dia_chi}
                    </div>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px;">
                        <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%); border-radius: 20px; color: #8B6914; font-weight: 600; border: 1px solid #FFD699;">
                            <span style="font-size: 16px;">⭐</span>
                            <strong>${suggestedMichelin.rating ? parseFloat(suggestedMichelin.rating).toFixed(1) : 'N/A'}</strong>
                        </div>
                        ${suggestedMichelin.gia_trung_binh && !['$', '$$', '$$$', '$$$$'].includes(suggestedMichelin.gia_trung_binh.trim()) ? `
                            <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%); border-radius: 20px; color: #8B6914; font-weight: 600; border: 1px solid #FFD699;">
                                <span style="font-size: 16px;">💰</span>
                                <strong>${suggestedMichelin.gia_trung_binh}</strong>
                            </div>
                        ` : ''}
                    </div>
                    ${suggestedMichelin.khau_vi ? `
                        <div style="margin-top: 12px; padding: 8px 12px; background: #FFF5E6; border-left: 3px solid #FFB84D; border-radius: 6px; font-size: 12px; color: #8B6914;">
                            👅 Khẩu vị: ${suggestedMichelin.khau_vi}
                        </div>
                    ` : ''}
                </div>
                
                <!-- 🔥 2 NÚT MỚI -->
                <div style="margin-top: 16px; display: flex; gap: 12px; justify-content: center;">
                    <button onclick="event.stopPropagation(); randomMichelin();" style="
                        flex: 1;
                        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(76, 175, 80, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(76, 175, 80, 0.3)';">
                        <span style="font-size: 18px;">🔄</span>
                        <span>Đổi quán khác</span>
                    </button>
                    
                    <button onclick="event.stopPropagation(); addSuggestedToSchedule(suggestedMichelin, 'michelin');" style="
                        flex: 1;
                        background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 107, 53, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 107, 53, 0.3)';">
                        <span style="font-size: 18px;">➕</span>
                        <span>Thêm vào lịch</span>
                    </button>
                </div>
                
                <!-- FOOTER -->
                <div style="margin-top: 16px; text-align: center; font-size: 13px; color: #8B6914; font-weight: 600;">
                    👆 Nhấn vào card để xem trên bản đồ
                </div>
            </div>
        </div>
    `;
}

// 🔥 CARD GỢI Ý KHU ẨM THỰC (GIỮ NGUYÊN - CÓ TAG "GỢI Ý")
const shouldShowFoodStreetSuggestion = suggestedFoodStreet && 
                                        selectedThemes.includes('food_street');

if (shouldShowFoodStreetSuggestion) {
    html += `
        <div style="margin-top: 40px; padding: 0 20px;">
            <div style="
                background: linear-gradient(135deg, #FFF9E6 0%, #FFE5B3 100%);
                border: 3px dashed #FFB84D;
                border-radius: 20px;
                padding: 20px;
                position: relative;
                box-shadow: 0 6px 20px rgba(255, 184, 77, 0.25);
                max-width: 100%;
            ">
                
                <!-- TAG Gợi ý -->
                <div style="
                    position: absolute;
                    top: -12px;
                    left: 20px;
                    background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                    color: white;
                    padding: 6px 16px;
                    border-radius: 20px;
                    font-size: 13px;
                    font-weight: 700;
                    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                    display: flex;
                    align-items: center;
                    gap: 6px;
                ">
                    <span style="font-size: 16px;">✨</span>
                    <span>Gợi ý cho bạn</span>
                </div>
                
                <!-- HEADER -->
                <div style="margin-top: 10px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;">
                    <span style="font-size: 32px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));">🪔</span>
                    <div>
                        <div style="font-size: 16px; font-weight: 700; color: #6B5410; margin-bottom: 4px;">
                            Khu ẩm thực đêm
                        </div>
                        ${(() => {
                            const gioMoCua = suggestedFoodStreet.gio_mo_cua || '';
                            let displayTime = '';
                            
                            if (!gioMoCua || gioMoCua.trim() === '') {
                                displayTime = 'Không rõ thời gian';
                            } else {
                                const gioNormalized = gioMoCua.toLowerCase();
                                
                                if (gioNormalized.includes('always') || gioNormalized.includes('24') || 
                                    gioNormalized.includes('cả ngày') || gioNormalized.includes('mở cả ngày') ||
                                    gioNormalized.includes('ca ngay') || gioNormalized.includes('mo ca ngay')) {
                                    displayTime = 'Mở cả ngày';
                                } else if (gioNormalized.includes('mở') || gioNormalized.includes('đóng') ||
                                        gioNormalized.includes('ong') || gioNormalized.includes('mo cua') || 
                                        gioNormalized.includes('dong cua') || gioNormalized.includes('mo') || 
                                        gioNormalized.includes('dong')) {
                                    displayTime = gioMoCua;
                                } else {
                                    displayTime = 'Không rõ thời gian';
                                }
                            }
                            
                            return `<div style="font-size: 13px; color: #8B6914; font-weight: 500;">
                                🕐 ${displayTime}
                            </div>`;
                        })()}
                    </div>
                </div>
                
                <!-- NỘI DUNG -->
                <div style="
                    background: white;
                    border-radius: 12px;
                    padding: 16px;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
                    border: 1px solid rgba(255, 184, 77, 0.2);
                    cursor: pointer;
                    transition: all 0.3s ease;
                " onclick="flyToPlace(${suggestedFoodStreet.lat}, ${suggestedFoodStreet.lon}, '${suggestedFoodStreet.data_id}', '${suggestedFoodStreet.ten_quan.replace(/'/g, "\\'")}')"
                onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 16px rgba(0, 0, 0, 0.1)';"
                onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 8px rgba(0, 0, 0, 0.04)';">
                    <div style="font-weight: 700; color: #FF6B35; margin-bottom: 8px; font-size: 15px; display: flex; align-items: center; gap: 6px;">
                        <span>🍽️</span>
                        <span>${suggestedFoodStreet.ten_quan}</span>
                    </div>
                    <div style="color: #666; font-size: 13px; margin-bottom: 12px; line-height: 1.5;">
                        📍 ${suggestedFoodStreet.dia_chi}
                    </div>
                    <div style="display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px;">
                        <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%); border-radius: 20px; color: #8B6914; font-weight: 600; border: 1px solid #FFD699;">
                            <span style="font-size: 16px;">⭐</span>
                            <strong>${suggestedFoodStreet.rating ? parseFloat(suggestedFoodStreet.rating).toFixed(1) : 'N/A'}</strong>
                        </div>
                        ${suggestedFoodStreet.gia_trung_binh && !['$', '$$', '$$$', '$$$$'].includes(suggestedFoodStreet.gia_trung_binh.trim()) ? `
                            <div style="display: flex; align-items: center; gap: 6px; padding: 6px 12px; background: linear-gradient(135deg, #FFF5E6 0%, #FFE5CC 100%); border-radius: 20px; color: #8B6914; font-weight: 600; border: 1px solid #FFD699;">
                                <span style="font-size: 16px;">💰</span>
                                <strong>${suggestedFoodStreet.gia_trung_binh}</strong>
                            </div>
                        ` : ''}
                    </div>
                    ${suggestedFoodStreet.khau_vi ? `
                        <div style="margin-top: 12px; padding: 8px 12px; background: #FFF5E6; border-left: 3px solid #FFB84D; border-radius: 6px; font-size: 12px; color: #8B6914;">
                            👅 Khẩu vị: ${suggestedFoodStreet.khau_vi}
                        </div>
                    ` : ''}
                </div>
                
                <!-- 🔥 2 NÚT MỚI -->
                <div style="margin-top: 16px; display: flex; gap: 12px; justify-content: center;">
                    <button onclick="event.stopPropagation(); randomFoodStreet();" style="
                        flex: 1;
                        background: linear-gradient(135deg, #4caf50 0%, #45a049 100%);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(76, 175, 80, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(76, 175, 80, 0.3)';">
                        <span style="font-size: 18px;">🔄</span>
                        <span>Đổi quán khác</span>
                    </button>
                    
                    <button onclick="event.stopPropagation(); addSuggestedToSchedule(suggestedFoodStreet, 'food_street');" style="
                        flex: 1;
                        background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                        color: white;
                        border: none;
                        padding: 12px 20px;
                        border-radius: 12px;
                        font-size: 14px;
                        font-weight: 700;
                        cursor: pointer;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        gap: 8px;
                        box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3);
                        transition: all 0.3s ease;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 107, 53, 0.4)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 107, 53, 0.3)';">
                        <span style="font-size: 18px;">➕</span>
                        <span>Thêm vào lịch</span>
                    </button>
                </div>
                
                <!-- FOOTER -->
                <div style="margin-top: 16px; text-align: center; font-size: 13px; color: #8B6914; font-weight: 600;">
                    👆 Nhấn vào card để xem trên bản đồ
                </div>
            </div>
        </div>
    `;
}

    if (!hasPlaces && !editMode) {
        resultDiv.innerHTML = `
            <div class="error-message">
                <h3>😔 Không tìm thấy quán</h3>
                <p>Không có quán nào phù hợp trong khu vực của bạn</p>
            </div>
        `;
        clearRoutes();
        return;
    }

    resultDiv.innerHTML = html;

    const actionBtns = document.getElementById('actionButtons');
    if (actionBtns) {
        actionBtns.classList.add('visible');
    }

    // 🔥 THÊM ĐOẠN CODE MỚI Ở ĐÂY
    const exitBtn = document.getElementById('exitSharedPlanBtn');
    if (exitBtn) {
        if (isViewingSharedPlan) {
            console.log('✅ Hiện nút X vì đang xem shared plan');
            exitBtn.style.display = 'flex';
        } else {
            console.log('❌ Ẩn nút X vì không xem shared plan');
            exitBtn.style.display = 'none';
        }
    }

    if (editMode) {
        setupDragAndDrop();
        setTimeout(() => setupEditModeTimeInputs(), 100);
    }
    
    // 🔥 VẼ ĐƯỜNG ĐI KHI HIỂN THỊ KẾ HOẠCH
    if (!editMode && hasPlaces) {
        setTimeout(() => drawRouteOnMap(plan), 500);
    } else {
        clearRoutes();
    }

    // 🔥 ẨN TẤT CẢ MARKER KHÁC, CHỈ GIỮ MARKER CỦA QUÁN TRONG LỊCH TRÌNH
    if (hasPlaces && window.showMarkersForPlaceIds) {
        window.showMarkersForPlaceIds(plan);
    }

    // 🔥 KIỂM TRA text có dài hơn khung không
    setTimeout(() => {
        const titleContainer = document.querySelector('.schedule-title > span:last-child');
        if (titleContainer && !titleContainer.hasAttribute('contenteditable')) {
            const textSpan = titleContainer.querySelector('span');
            if (textSpan && textSpan.scrollWidth > titleContainer.clientWidth) {
                titleContainer.classList.add('overflow'); // 🔥 Thêm class để bật animation
            } else {
                titleContainer.classList.remove('overflow');
            }
        }
    }, 100);
}

// ========== ADD NEW MEAL SLOT ==========
function addNewMealSlot() {
    if (!currentPlan) {
        currentPlan = {};
    }
    
    const newKey = 'custom_' + Date.now();
    const lastMealTime = getLastMealTime();
    const newTime = addMinutesToTime(lastMealTime, 60);
    
    currentPlan[newKey] = {
        time: newTime,
        title: 'Bữa mới',
        icon: '🍽️',
        place: null
    };

    if (!currentPlan._order) {
        currentPlan._order = [];
    }
    currentPlan._order.push(newKey);
    
    waitingForPlaceSelection = newKey;
    displayPlanVertical(currentPlan, isEditMode);
    
    // 🔥 THÊM ĐOẠN NÀY - HIỆN TẤT CẢ QUÁN KHI TẠO CARD MỚI
    setTimeout(() => {
        // Ưu tiên dùng data tìm kiếm hiện tại
        if (typeof displayPlaces === 'function' &&
            Array.isArray(window.allPlacesData) &&
            window.allPlacesData.length > 0) {
            
            // false = không đổi zoom, chỉ vẽ lại marker
            displayPlaces(window.allPlacesData, false);
            console.log('✅ Đã hiện lại tất cả quán sau khi tạo card mới');
        } else if (typeof loadMarkersInViewport === 'function' && window.map) {
            // Fallback: nếu chưa có allPlacesData thì bật lại lazy-load
            window.map.on('moveend', loadMarkersInViewport);
            loadMarkersInViewport();
            console.log('✅ Đã bật lại lazy-load marker sau khi tạo card mới');
        }
    }, 100);
    
    // 🔥 THÊM: Kích hoạt refresh sidebar
    if (typeof window.refreshCurrentSidebar === 'function') {
        setTimeout(() => {
            console.log('🔄 Refresh sidebar sau khi thêm quán mới');
            window.refreshCurrentSidebar();
        }, 100);
    }
    
    // Scroll to bottom
    setTimeout(() => {
        const timeline = document.querySelector('.timeline-container');
        if (timeline) {
            timeline.scrollIntoView({ behavior: 'smooth', block: 'end' });
        }
    }, 200);
}

function getLastMealTime() {
    let latestTime = '07:00';
    for (const key in currentPlan) {
        if (currentPlan[key] && currentPlan[key].time) {
            if (currentPlan[key].time > latestTime) {
                latestTime = currentPlan[key].time;
            }
        }
    }
    return latestTime;
}

function addMinutesToTime(timeStr, minutes) {
    const [hours, mins] = timeStr.split(':').map(Number);
    const totalMins = hours * 60 + mins + minutes;
    const newHours = Math.floor(totalMins / 60) % 24;
    const newMins = totalMins % 60;
    return `${String(newHours).padStart(2, '0')}:${String(newMins).padStart(2, '0')}`;
}

// ========== KIỂM TRA 2 ĐOẠN ĐƯỜNG CÓ TRÙNG KHÔNG ==========
function checkRouteOverlap(coords1, coords2, threshold = 0.0001) {
    // Giảm threshold để chính xác hơn
    let overlapCount = 0;
    const sampleStep = Math.max(1, Math.floor(coords1.length / 20)); // Lấy mẫu để tăng tốc
    
    for (let i = 0; i < coords1.length; i += sampleStep) {
        const point1 = coords1[i];
        
        for (let j = 0; j < coords2.length; j += sampleStep) {
            const point2 = coords2[j];
            
            const distance = Math.sqrt(
                Math.pow(point1[0] - point2[0], 2) + 
                Math.pow(point1[1] - point2[1], 2)
            );
            
            if (distance < threshold) {
                overlapCount++;
                break;
            }
        }
    }
    
    // Chỉ cần 15% điểm trùng là đủ
    const minOverlapPoints = Math.ceil(coords1.length / sampleStep * 0.15);
    return overlapCount >= minOverlapPoints;
}

// ========== DRAW ROUTE ON MAP ==========
let routeLayers = [];
let currentRouteAbortController = null;

function clearRoutes() {
    // 🔥 HỦY TẤT CẢ REQUESTS ĐANG CHẠY
    if (currentRouteAbortController) {
        currentRouteAbortController.abort();
        currentRouteAbortController = null;
        console.log('⚠️ Đã hủy tất cả requests vẽ đường cũ');
    }

    if (typeof map !== 'undefined' && routeLayers.length > 0) {
        routeLayers.forEach(layer => {
            map.removeLayer(layer);
        });
        routeLayers = [];
    }
}

function getRouteColor(index, total) {
    const colors = [
        '#FF6B35', // Cam
        '#FFA500', // Cam sáng
        '#32CD32', // Xanh lá
        '#00CED1', // Xanh da trời
        '#1E90FF', // Xanh dương
        '#FF1493', // Hồng đậm
        '#9370DB'  // Tím
    ];
    
    if (total <= 1) return colors[0];
    
    const colorIndex = Math.min(
        Math.floor((index / (total - 1)) * (colors.length - 1)),
        colors.length - 1
    );
    
    return colors[colorIndex];
}

// ========== HÀM DỊCH CHUYỂN POLYLINE THEO MÉT (CỐ ĐỊNH) ==========
function offsetPolylineByMeters(coords, offsetMeters) {
    const offsetCoords = [];
    
    for (let i = 0; i < coords.length; i++) {
        const lat = coords[i][0];
        const lon = coords[i][1];
        
        // Tính vector hướng đi (tangent)
        let tangentLat, tangentLon;
        
        if (i === 0) {
            tangentLat = coords[i + 1][0] - lat;
            tangentLon = coords[i + 1][1] - lon;
        } else if (i === coords.length - 1) {
            tangentLat = lat - coords[i - 1][0];
            tangentLon = lon - coords[i - 1][1];
        } else {
            tangentLat = coords[i + 1][0] - coords[i - 1][0];
            tangentLon = coords[i + 1][1] - coords[i - 1][1];
        }
        
        // Chuẩn hóa vector hướng đi
        const tangentLength = Math.sqrt(tangentLat * tangentLat + tangentLon * tangentLon);
        if (tangentLength > 0) {
            tangentLat /= tangentLength;
            tangentLon /= tangentLength;
        }
        
        // 🔥 Vector vuông góc BÊN PHẢI của hướng đi (xoay 90° theo chiều kim đồng hồ)
        const perpLat = tangentLon;  // Swap và đổi dấu để xoay đúng
        const perpLon = -tangentLat;
        
        // 🔥 TÍNH OFFSET BẰNG MÉT (không phụ thuộc zoom)
        const metersPerDegreeLat = 111320;
        const metersPerDegreeLon = 111320 * Math.cos(lat * Math.PI / 180);
        
        const offsetLat = (offsetMeters / metersPerDegreeLat) * perpLat;
        const offsetLon = (offsetMeters / metersPerDegreeLon) * perpLon;
        
        offsetCoords.push([lat + offsetLat, lon + offsetLon]);
    }
    
    return offsetCoords;
}

function drawRouteOnMap(plan) {
    if (typeof map === 'undefined' || typeof L === 'undefined') {
        console.log('Map chưa sẵn sàng');
        return;
    }
    
    // 🔥 HỦY REQUESTS CŨ VÀ TẠO MỚI
    clearRoutes(); // Xóa routes cũ + hủy requests cũ
    currentRouteAbortController = new AbortController();
    const signal = currentRouteAbortController.signal;
    
    const drawnSegments = [];
    const waypoints = [];
    
    // Thêm vị trí user
    if (window.currentUserCoords) {
        waypoints.push({
            lat: window.currentUserCoords.lat,
            lon: window.currentUserCoords.lon,
            name: 'Vị trí của bạn',
            isUser: true
        });
    }
    
    // Lấy tất cả meal keys và sắp xếp theo thời gian
    const allMealKeys = Object.keys(plan)
        .filter(k => k !== '_order' && plan[k] && plan[k].time && plan[k].place)
        .sort((a, b) => {
            const timeA = plan[a].time || '00:00';
            const timeB = plan[b].time || '00:00';
            return timeA.localeCompare(timeB);
        });
    
    // Thêm các quán theo thứ tự
    allMealKeys.forEach(key => {
        const meal = plan[key];
        if (meal && meal.place) {
            waypoints.push({
                lat: meal.place.lat,
                lon: meal.place.lon,
                name: meal.place.ten_quan,
                time: meal.time,
                isUser: false
            });
        }
    });
    
    if (waypoints.length < 2) {
        console.log('Không đủ điểm để vẽ đường');
        return;
    }
    
    const totalRoutes = waypoints.length - 1;
    
    // 🔥 PATTERN VÀ WEIGHT ĐỒNG NHẤT CHO TẤT CẢ CÁC ĐƯỜNG
    const routeWeight = 6;
    const routeDash = null; // Đường liền
    
    async function drawSingleRoute(startPoint, endPoint, index) {
        try {
            // 🔥 MAPBOX URL
            const MAPBOX_TOKEN = 'pk.eyJ1IjoidHRraGFuZzI0MTEiLCJhIjoiY21qMWVpeGJnMDZqejNlcHdkYnQybHdhbCJ9.V0_GUI2CBTtEhkrnajG3Ug'; // Token demo, bạn nên lấy token riêng tại mapbox.com
            
            const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${startPoint.lon},${startPoint.lat};${endPoint.lon},${endPoint.lat}?geometries=geojson&overview=full&access_token=${MAPBOX_TOKEN}`;
            
            const response = await fetch(url, { signal });
            const data = await response.json();
            
            // 🔥 MapBox format: data.routes[0].geometry.coordinates
            if (data.routes && data.routes[0] && data.routes[0].geometry) {
                const route = data.routes[0];
                
                // MapBox trả: coordinates = [[lon, lat], [lon, lat]]
                const coords = route.geometry.coordinates.map(coord => [coord[1], coord[0]]);
                
                const color = getRouteColor(index, totalRoutes);
                
                // 🔥 KIỂM TRA TRÙNG VÀ TÍNH OFFSET
                let offsetPixels = 0;
                
                for (let i = 0; i < drawnSegments.length; i++) {
                    if (checkRouteOverlap(coords, drawnSegments[i].coords)) {
                        const overlapCount = drawnSegments.filter(seg => 
                            checkRouteOverlap(coords, seg.coords)
                        ).length;
                        
                        offsetPixels = (overlapCount % 2 === 0) ? 8 : -8;
                        console.log(`⚠️ Đường ${index} trùng ${overlapCount} đường, offset = ${offsetPixels}px`);
                        break;
                    }
                }
                
                drawnSegments.push({ coords: coords, index: index });
                
                // VẼ VIỀN TRẮNG
                const outlinePolyline = L.polyline(coords, {
                    color: '#FFFFFF',
                    weight: routeWeight + 3,
                    opacity: 0.9,
                    smoothFactor: 1
                }).addTo(map);
                
                routeLayers.push(outlinePolyline);
                
                // VẼ ĐƯỜNG MÀU CHÍNH
                const mainPolyline = L.polyline(coords, {
                    color: color,
                    weight: routeWeight,
                    opacity: 1,
                    smoothFactor: 1,
                    dashArray: null
                }).addTo(map);
                
                // ÁP DỤNG OFFSET
                if (offsetPixels !== 0) {
                    if (typeof outlinePolyline.setOffset === 'function') {
                        outlinePolyline.setOffset(offsetPixels);
                    }
                    if (typeof mainPolyline.setOffset === 'function') {
                        mainPolyline.setOffset(offsetPixels);
                    }
                }
                
                const tooltipText = index === 0 
                    ? `🚗 Khởi hành → ${endPoint.name}`
                    : `${index}. ${startPoint.name} → ${endPoint.name}`;
                
                mainPolyline.bindTooltip(tooltipText, {
                    permanent: false,
                    direction: 'center',
                    className: 'route-tooltip'
                });
                
                routeLayers.push(mainPolyline);
                
                // ĐÁNH SỐ QUÁN
                if (!startPoint.isUser) {
                    const numberMarker = L.marker([startPoint.lat, startPoint.lon], {
                        icon: L.divIcon({
                            className: 'route-number-marker',
                            html: `<div style="
                                background: ${color};
                                color: white;
                                width: 40px;
                                height: 40px;
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: bold;
                                font-size: 18px;
                                border: 4px solid white;
                                box-shadow: 0 3px 10px rgba(0,0,0,0.4);
                                z-index: 1000;
                            ">${index}</div>`,
                            iconSize: [40, 40],
                            iconAnchor: [20, 20]
                        }),
                        zIndexOffset: 1000
                    }).addTo(map);
                    
                    routeLayers.push(numberMarker);
                }
                
                // ĐÁNH SỐ QUÁN CUỐI
                if (index === totalRoutes - 1 && !endPoint.isUser) {
                    const lastColor = getRouteColor(totalRoutes - 1, totalRoutes);
                    const lastNumberMarker = L.marker([endPoint.lat, endPoint.lon], {
                        icon: L.divIcon({
                            className: 'route-number-marker',
                            html: `<div style="
                                background: ${lastColor};
                                color: white;
                                width: 40px;
                                height: 40px;
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                font-weight: bold;
                                font-size: 18px;
                                border: 4px solid white;
                                box-shadow: 0 3px 10px rgba(0,0,0,0.4);
                                z-index: 1000;
                            ">${totalRoutes}</div>`,
                            iconSize: [40, 40],
                            iconAnchor: [20, 20]
                        }),
                        zIndexOffset: 1000
                    }).addTo(map);
                    
                    routeLayers.push(lastNumberMarker);
                }
                
            } else {
                // 🔥 LOG ĐỂ DEBUG
                console.log('❌ MapBox response:', data);
                console.log('Không tìm thấy route, dùng đường thẳng');
                
                const color = getRouteColor(index, totalRoutes);
                
                const outlineLine = L.polyline(
                    [[startPoint.lat, startPoint.lon], [endPoint.lat, endPoint.lon]],
                    { color: '#FFFFFF', weight: routeWeight + 3, opacity: 0.9 }
                ).addTo(map);
                routeLayers.push(outlineLine);

                const mainStraightLine = L.polyline(
                    [[startPoint.lat, startPoint.lon], [endPoint.lat, endPoint.lon]],
                    { color: color, weight: routeWeight, opacity: 1 }
                ).addTo(map);
                routeLayers.push(mainStraightLine);
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log(`⚠️ Request vẽ đường ${index} đã bị hủy`);
                return;
            }
        
            console.error('❌ Lỗi vẽ route:', error);
            const color = getRouteColor(index, totalRoutes);
            
            const outlineLine = L.polyline(
                [[startPoint.lat, startPoint.lon], [endPoint.lat, endPoint.lon]],
                { color: '#FFFFFF', weight: routeWeight + 3, opacity: 0.9 }
            ).addTo(map);
            routeLayers.push(outlineLine);

            const mainStraightLine = L.polyline(
                [[startPoint.lat, startPoint.lon], [endPoint.lat, endPoint.lon]],
                { color: color, weight: routeWeight, opacity: 1 }
            ).addTo(map);
            routeLayers.push(mainStraightLine);
        }
    }
    
    // Vẽ từng đoạn route
    (async function drawAllRoutes() {
        try {
            for (let i = 0; i < waypoints.length - 1; i++) {
                // 🔥 KIỂM TRA NẾU ĐÃ BỊ HỦY THÌ DỪNG NGAY
                if (signal.aborted) {
                    console.log('⚠️ Đã dừng vẽ tất cả routes do bị hủy');
                    return;
                }
                
                await drawSingleRoute(waypoints[i], waypoints[i + 1], i);
            }
            
            // 🔥 CHỈ FIT BOUNDS NẾU CHƯA BỊ HỦY
            if (!signal.aborted) {
                const bounds = L.latLngBounds(waypoints.map(w => [w.lat, w.lon]));
                map.fitBounds(bounds, { padding: [50, 50] });
                
                console.log(`✅ Đã vẽ ${waypoints.length - 1} đoạn đường`);
            }
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Lỗi trong drawAllRoutes:', error);
            }
        }
    })();
}

// ========== DELETE MEAL SLOT ==========
function deleteMealSlot(mealKey) {
    if (!currentPlan) return;
    
    if (confirm('Bạn có chắc muốn xóa bữa ăn này?')) {
        delete currentPlan[mealKey];
        
        // Reset waiting state nếu đang chờ chọn quán cho slot này
        if (waitingForPlaceSelection === mealKey) {
            waitingForPlaceSelection = null;
        }
        
        displayPlanVertical(currentPlan, isEditMode);
    }
}

// ========== SELECT PLACE FOR MEAL ==========
function selectPlaceForMeal(mealKey) {
    // Xem trước đó có đang chờ chọn quán cho meal này không
    const wasWaiting = (waitingForPlaceSelection === mealKey);

    if (wasWaiting) {
        // Nhấn lại lần nữa -> hủy chế độ đổi quán
        waitingForPlaceSelection = null;
        selectedPlaceForReplacement = null;
    } else {
        // Bắt đầu chế độ đổi quán cho meal này
        waitingForPlaceSelection = mealKey;
    }

    // Render lại timeline (vẫn giữ logic hide marker theo lịch trình)
    displayPlanVertical(currentPlan, isEditMode);

    // 🔥 Nếu VỪA BẮT ĐẦU chế độ "Đổi quán" -> hiện TẤT CẢ marker quán
    if (!wasWaiting && waitingForPlaceSelection === mealKey) {
        // Ưu tiên dùng data tìm kiếm hiện tại
        if (typeof displayPlaces === 'function' &&
            Array.isArray(window.allPlacesData) &&
            window.allPlacesData.length > 0) {

            // Không đổi zoom, chỉ vẽ lại toàn bộ marker từ allPlacesData
            displayPlaces(window.allPlacesData, false);
        } else if (typeof loadMarkersInViewport === 'function' && window.map) {
            // Fallback: nếu chưa có allPlacesData thì bật lại lazy-load
            window.map.on('moveend', loadMarkersInViewport);
            loadMarkersInViewport();
        }
    }

    // Giữ nguyên phần refreshCurrentSidebar như cũ
    console.log('🔍 Kiểm tra refreshCurrentSidebar:', typeof window.refreshCurrentSidebar);
    
    if (typeof window.refreshCurrentSidebar === 'function') {
        setTimeout(() => {
            console.log('🔄 Gọi refreshCurrentSidebar');
            window.refreshCurrentSidebar();
        }, 100);
    } else {
        console.error('❌ refreshCurrentSidebar không tồn tại!');
    }
}

// ========== REPLACE PLACE IN MEAL ==========
function replacePlaceInMeal(newPlace) {
    // 🔥 KIỂM TRA ĐẦY ĐỦ
    if (!waitingForPlaceSelection) {
        console.error("❌ Không có slot nào đang chờ chọn quán");
        return false;
    }
    
    if (!currentPlan) {
        console.error("❌ currentPlan không tồn tại");
        return false;
    }
    
    const mealKey = waitingForPlaceSelection;
    
    // 🔥 KIỂM TRA MEAL KEY CÓ TỒN TẠI KHÔNG
    if (!currentPlan[mealKey]) {
        console.error("❌ Meal key không tồn tại trong plan:", mealKey);
        return false;
    }
    
    // ✅ Tính khoảng cách từ vị trí trước đó
    let prevLat, prevLon;
    if (window.currentUserCoords) {
        prevLat = window.currentUserCoords.lat;
        prevLon = window.currentUserCoords.lon;
    }
    
    // Tìm quán trước đó (nếu có)
    const allKeys = Object.keys(currentPlan)
        .filter(k => k !== '_order')
        .sort((a, b) => {
            const timeA = currentPlan[a]?.time || '00:00';
            const timeB = currentPlan[b]?.time || '00:00';
            return timeA.localeCompare(timeB);
        });
    
    const currentIndex = allKeys.indexOf(mealKey);
    
    for (let i = currentIndex - 1; i >= 0; i--) {
        const prevMeal = currentPlan[allKeys[i]];
        if (prevMeal && prevMeal.place) {
            prevLat = prevMeal.place.lat;
            prevLon = prevMeal.place.lon;
            break;
        }
    }
    
    const distance = calculateDistanceJS(prevLat, prevLon, newPlace.lat, newPlace.lon);
    const travelTime = Math.round((distance / 25) * 60);
    
    const mealTime = currentPlan[mealKey].time;
    const arriveTime = new Date(`2000-01-01 ${mealTime}`);
    const suggestLeave = new Date(arriveTime.getTime() - travelTime * 60000);
    const suggestLeaveStr = suggestLeave.toTimeString().substring(0, 5);
    
    // ✅ CẬP NHẬT QUÁN
    currentPlan[mealKey].place = {
        ten_quan: newPlace.ten_quan,
        dia_chi: newPlace.dia_chi,
        rating: parseFloat(newPlace.rating) || 0,
        lat: newPlace.lat,
        lon: newPlace.lon,
        distance: Math.round(distance * 100) / 100,
        travel_time: travelTime,
        suggest_leave: suggestLeaveStr,
        data_id: newPlace.data_id,
        hinh_anh: newPlace.hinh_anh || '',
        gia_trung_binh: newPlace.gia_trung_binh || '',
        khau_vi: newPlace.khau_vi || '',
        gio_mo_cua: newPlace.gio_mo_cua || ''
    };
    
    console.log("✅ Đã cập nhật quán cho mealKey:", mealKey, currentPlan[mealKey]);
    
    // ✅ RESET waiting state
    waitingForPlaceSelection = null;
    
    // ✅ RENDER LẠI NGAY LẬP TỨC
    displayPlanVertical(currentPlan, isEditMode);
    
    // ✅ SCROLL ĐẾN QUÁN VỪA THÊM
    setTimeout(() => {
        const addedItem = document.querySelector(`[data-meal-key="${mealKey}"]`);
        if (addedItem) {
            addedItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // ✅ HIGHLIGHT CARD VỪA THÊM
            const card = addedItem.querySelector('.meal-card-vertical');
            if (card) {
                card.style.border = '3px solid #4caf50';
                card.style.boxShadow = '0 0 20px rgba(76, 175, 80, 0.5)';
                
                setTimeout(() => {
                    card.style.border = '';
                    card.style.boxShadow = '';
                }, 2000);
            }
        }
    }, 100);
    
    return true; // 🔥 RETURN TRUE KHI THÀNH CÔNG
}

function calculateDistanceJS(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon/2) * Math.sin(dLon/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

// ========== DRAG AND DROP ==========
function setupDragAndDrop() {
    const mealItems = document.querySelectorAll('.meal-item[draggable="true"]');
    
    mealItems.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
        item.addEventListener('dragover', handleDragOverItem);  // 🔥 ĐỔI TỪ dragenter
    });
    
    const container = document.querySelector('.timeline-container');
    if (container) {
        container.addEventListener('dragover', handleDragOver);
        container.addEventListener('drop', handleDrop);  // 🔥 THÊM DROP
    }
}

function handleDragStart(e) {
    draggedElement = this;
    window.draggedElement = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
    
    lastTargetElement = null;
    enableGlobalDragTracking(); // ✅ Bật tracking
    startAutoScroll();
}

function handleDragEnd(e) {
    if (draggedElement) {
        draggedElement.classList.remove('dragging');
    }
    
    document.querySelectorAll('.meal-card-vertical.drop-target').forEach(card => {
        card.classList.remove('drop-target');
    });
    
    draggedElement = null;
    window.draggedElement = null;
    lastDragY = 0;
    lastTargetElement = null;
    
    stopAutoScroll();
    disableGlobalDragTracking(); // ✅ Tắt tracking
}

// ========== DRAG OVER ITEM - HIGHLIGHT VỊ TRÍ MUỐN ĐỔI ==========
function handleDragOverItem(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    
    if (!draggedElement || draggedElement === this) return;
    
    e.dataTransfer.dropEffect = 'move';
    
    // 🔥 XÓA highlight cũ
    document.querySelectorAll('.meal-card-vertical.drop-target').forEach(card => {
        card.classList.remove('drop-target');
    });
    
    // 🔥 HIGHLIGHT card đích
    const targetCard = this.querySelector('.meal-card-vertical');
    if (targetCard) {
        targetCard.classList.add('drop-target');
    }
    
    lastTargetElement = this;
    lastDragY = e.clientY;
    return false;
}

// ========== DRAG ENTER - ĐỘI VỊ TRÍ NGAY LẬP TỨC KHI CHẠM ==========
function handleDragEnter(e) {
    if (!draggedElement || draggedElement === this) return;
    
    const draggedKey = draggedElement.dataset.mealKey;
    const targetKey = this.dataset.mealKey;
    
    // 🔥 CHỈ ĐỔI 1 LẦN - TRÁNH ĐỔI LẶP LẠI
    if (lastTargetElement !== this) {
        lastTargetElement = this;
        
        // ✅ ĐỔI VỊ TRÍ TRONG DOM
        if (draggedElement.parentNode === this.parentNode) {
            const temp = draggedElement.innerHTML;
            draggedElement.innerHTML = this.innerHTML;
            this.innerHTML = temp;
            
            // ✅ ĐỔI ATTRIBUTE
            const tempKey = draggedElement.dataset.mealKey;
            draggedElement.dataset.mealKey = this.dataset.mealKey;
            this.dataset.mealKey = tempKey;
        }
        
        // ✅ ĐỔI DỮ LIỆU TRONG currentPlan
        if (currentPlan && draggedKey && targetKey) {
            const temp = currentPlan[draggedKey];
            currentPlan[draggedKey] = currentPlan[targetKey];
            currentPlan[targetKey] = temp;
        }
    }
}

// ✨ AUTO-SCROLL TOÀN BỘ PANEL - CỰC NHANH VÀ MƯỢT
function startAutoScroll() {
    if (autoScrollInterval) return;
    
    let frameCount = 0;
    
    autoScrollInterval = setInterval(() => {
        if (!draggedElement) {
            stopAutoScroll();
            return;
        }
        
        // ✅ Giảm tần suất xuống 30fps thay vì 60fps
        frameCount++;
        if (frameCount % 2 !== 0) return;
        
        const container = document.querySelector('.panel-content');
        if (!container) return;
        
        const rect = container.getBoundingClientRect();
        
        // 🔥 DÙNG lastDragY CẬP NHẬT LIÊN TỤC
        if (lastDragY === 0) return;
        
        // 🔥 VÙNG KÍCH HOẠT RỘNG HƠN - 200px thay vì 150px
        const topEdge = rect.top + 200;      // Vùng trên
        const bottomEdge = rect.bottom - 200; // Vùng dưới
        
        let scrollSpeed = 0;
        
       // CUỘN LÊNNN
        if (lastDragY < topEdge) {
            const distance = topEdge - lastDragY;
            const ratio = Math.min(1, distance / 200);
            scrollSpeed = -(15 + ratio * 50);
            container.scrollTop += scrollSpeed;
            container.classList.add('scrolling-up'); // 🔥 THÊM
            container.classList.remove('scrolling-down');
        }
        // CUỘN XUỐNG
        else if (lastDragY > bottomEdge) {
            const distance = lastDragY - bottomEdge;
            const ratio = Math.min(1, distance / 200);
            scrollSpeed = (15 + ratio * 50);
            container.scrollTop += scrollSpeed;
            container.classList.add('scrolling-down'); // 🔥 THÊM
            container.classList.remove('scrolling-up');
        } else {
            // 🔥 XÓA CLASS KHI KHÔNG SCROLL
            container.classList.remove('scrolling-up', 'scrolling-down');
        }
        
    }, 16); // 60fps - mượt
}

function stopAutoScroll() {
    if (autoScrollInterval) {
        clearInterval(autoScrollInterval);
        autoScrollInterval = null;
    }

    // ✅ Cleanup visual indicators
    const container = document.querySelector('.panel-content');
    if (container) {
        container.classList.remove('scrolling-up', 'scrolling-down');
    }
}

// ✨ THEO DÕI CHUỘT TRÊN TOÀN BỘ DOCUMENT
let globalDragListener = null;

function enableGlobalDragTracking() {
    if (globalDragListener) return;
    
    globalDragListener = (e) => {
        if (draggedElement) {
            lastDragY = e.clientY;
        }
    };
    
    document.addEventListener('dragover', globalDragListener, { passive: true });
}

function disableGlobalDragTracking() {
    if (globalDragListener) {
        document.removeEventListener('dragover', globalDragListener);
        globalDragListener = null;
    }
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    
    // 🔥 CẬP NHẬT LiÊN TỤC VỊ TRÍ Y TOÀN CẦU
    lastDragY = e.clientY;
    
    if (!draggedElement) return;
    
    e.dataTransfer.dropEffect = 'move';
    
    // Tìm phần tử nằm sau vị trí hiện tại
    const afterElement = getDragAfterElement(
        document.querySelector('.timeline-container'),
        e.clientY
    );
    
    if (afterElement == null) {
        document.querySelector('.timeline-container').appendChild(draggedElement);
    } else {
        document.querySelector('.timeline-container').insertBefore(draggedElement, afterElement);
    }
    
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    if (!draggedElement || !lastTargetElement) return;
    
    if (draggedElement === lastTargetElement) return;
    
    const draggedKey = draggedElement.dataset.mealKey;
    const targetKey = lastTargetElement.dataset.mealKey;
    
    // ✅ Cập nhật dữ liệu TRƯỚC khi đổi
    const draggedTitleInput = draggedElement.querySelector('.meal-title-input, input[onchange*="updateMealTitle"]');
    const draggedHourInput = draggedElement.querySelector('.time-input-hour[data-meal-key="' + draggedKey + '"]');
    const draggedMinuteInput = draggedElement.querySelector('.time-input-minute[data-meal-key="' + draggedKey + '"]');
    
    if (draggedTitleInput && draggedKey && currentPlan[draggedKey]) {
        currentPlan[draggedKey].title = draggedTitleInput.value;
    }
    if (draggedHourInput && draggedMinuteInput && draggedKey && currentPlan[draggedKey]) {
        const hour = draggedHourInput.value.padStart(2, '0');
        const minute = draggedMinuteInput.value.padStart(2, '0');
        currentPlan[draggedKey].time = `${hour}:${minute}`;
    }
    
    const targetTitleInput = lastTargetElement.querySelector('.meal-title-input, input[onchange*="updateMealTitle"]');
    const targetHourInput = lastTargetElement.querySelector('.time-input-hour[data-meal-key="' + targetKey + '"]');
    const targetMinuteInput = lastTargetElement.querySelector('.time-input-minute[data-meal-key="' + targetKey + '"]');
    
    if (targetTitleInput && targetKey && currentPlan[targetKey]) {
        currentPlan[targetKey].title = targetTitleInput.value;
    }
    if (targetHourInput && targetMinuteInput && targetKey && currentPlan[targetKey]) {
        const hour = targetHourInput.value.padStart(2, '0');
        const minute = targetMinuteInput.value.padStart(2, '0');
        currentPlan[targetKey].time = `${hour}:${minute}`;
    }
    
    // ✅ SWAP dữ liệu
    if (currentPlan && draggedKey && targetKey) {
        const temp = currentPlan[draggedKey];
        currentPlan[draggedKey] = currentPlan[targetKey];
        currentPlan[targetKey] = temp;
    }
    
    // 🔥 LƯU VỊ TRÍ CŨ để biết quán nào bị di chuyển
    const allMealItems = document.querySelectorAll('.meal-item[data-meal-key]');
    const oldOrder = Array.from(allMealItems).map(item => item.dataset.mealKey);
    const draggedOldIndex = oldOrder.indexOf(draggedKey);
    const targetOldIndex = oldOrder.indexOf(targetKey);
    
    // Cập nhật thứ tự mới
    const newOrder = [...oldOrder];
    [newOrder[draggedOldIndex], newOrder[targetOldIndex]] = [newOrder[targetOldIndex], newOrder[draggedOldIndex]];
    
    if (!currentPlan._order) {
        currentPlan._order = [];
    }
    currentPlan._order = newOrder;
    
    // ✅ RENDER lại
    displayPlanVertical(currentPlan, isEditMode);
    
    // 🔥 THÊM HIỆU ỨNG CHO CẢ 2 QUÁN BỊ HOÁN ĐỔI
    setTimeout(() => {
        // Quán được kéo
        const draggedCard = document.querySelector(`[data-meal-key="${draggedKey}"] .meal-card-vertical`);
        if (draggedCard) {
            draggedCard.classList.add('just-dropped');
            
            // Thêm icon mũi tên
            const draggedNewIndex = newOrder.indexOf(draggedKey);
            const direction = draggedNewIndex < draggedOldIndex ? '⬆️' : '⬇️';
            const indicator1 = document.createElement('div');
            indicator1.className = 'reposition-indicator';
            indicator1.textContent = direction;
            draggedCard.style.position = 'relative';
            draggedCard.appendChild(indicator1);
            
            // Scroll đến quán được kéo
            const draggedItem = document.querySelector(`[data-meal-key="${draggedKey}"]`);
            if (draggedItem) {
                draggedItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            
            // Xóa sau 1.5s
            setTimeout(() => {
                draggedCard.classList.remove('just-dropped');
                if (indicator1.parentNode) {
                    indicator1.remove();
                }
            }, 1500);
        }
        
        // Quán đích (bị đẩy)
        const targetCard = document.querySelector(`[data-meal-key="${targetKey}"] .meal-card-vertical`);
        if (targetCard) {
            targetCard.classList.add('just-dropped');
            
            // Thêm icon mũi tên (ngược hướng với quán kéo)
            const targetNewIndex = newOrder.indexOf(targetKey);
            const direction = targetNewIndex < targetOldIndex ? '⬆️' : '⬇️';
            const indicator2 = document.createElement('div');
            indicator2.className = 'reposition-indicator';
            indicator2.textContent = direction;
            targetCard.style.position = 'relative';
            targetCard.appendChild(indicator2);
            
            // Xóa sau 1.5s
            setTimeout(() => {
                targetCard.classList.remove('just-dropped');
                if (indicator2.parentNode) {
                    indicator2.remove();
                }
            }, 1500);
        }
    }, 100);
    
    return false;
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.meal-item:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// ========== UPDATE MEAL TIME ==========
function updateMealTime(mealKey, newTime) {
    if (currentPlan && currentPlan[mealKey]) {
        currentPlan[mealKey].time = newTime;
        
        // 🔥 CẬP NHẬT TITLE TỪ INPUT (nếu có)
        const mealCard = document.querySelector(`[data-meal-key="${mealKey}"]`);
        if (mealCard) {
            const titleInput = mealCard.querySelector('input[onchange*="updateMealTitle"]');
            if (titleInput && titleInput.value) {
                currentPlan[mealKey].title = titleInput.value;
            }
        }
    }
}

// ========== UPDATE MEAL TITLE ==========
function updateMealTitle(mealKey, newTitle) {
    if (currentPlan && currentPlan[mealKey]) {
        currentPlan[mealKey].title = newTitle;
    }
}

// ========== UPDATE MEAL ICON ==========
function updateMealIcon(mealKey, newIcon) {
    if (currentPlan && currentPlan[mealKey]) {
        currentPlan[mealKey].icon = newIcon;
        displayPlanVertical(currentPlan, isEditMode);
    }
}

// ========== ICON OPTIONS ==========
const iconOptions = ['🍳', '🥐', '🍜', '🍚', '🍛', '🍝', '🍕', '🍔', '🌮', '🥗', '🍱', '🍤', '🍣', '🦞', '☕', '🧋', '🍵', '🥤', '🍰', '🍨', '🧁', '🍩', '🍪', '🍽️'];

function updateAutoPlanName(newName) {
    const cleanName = (newName || '').trim() || 'Kế hoạch';

    // Tên không đổi thì thôi
    if (window.currentPlanName === cleanName) return;

    // Cập nhật lại tên hiện tại đang dùng trong UI / khi bấm "Lưu"
    window.currentPlanName = cleanName;
}

function flyToPlace(lat, lon, placeId, placeName) {
     // ✅ GỌI HÀM RIÊNG TỪ script.js
    if (typeof window.flyToPlaceFromPlanner === 'function') {
        window.flyToPlaceFromPlanner(lat, lon, placeId, placeName);
    } else {
        console.error('❌ Hàm flyToPlaceFromPlanner chưa được load từ script.js');
        alert('Có lỗi khi mở quán. Vui lòng thử lại!');
    }
}

// ========== EXPOSE FUNCTIONS TO WINDOW ==========
window.foodPlannerState = {
    isEditMode: () => {
        return isEditMode;
    },
    isWaitingForPlaceSelection: () => {
        return waitingForPlaceSelection !== null;
    },
    selectPlace: (place) => {
        if (waitingForPlaceSelection) {
            // AUTO MODE
            const success = replacePlaceInMeal(place);
            return success;
        }
        return false;
    }
};

// ========== EVENT LISTENERS ==========
document.getElementById('foodPlannerPanel')?.addEventListener('click', function(e) {
    if (e.target === this) {
        closeFoodPlanner();
    }
});

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && isPlannerOpen) {
        closeFoodPlanner();
    }
});
// ========== LOAD POLYLINE OFFSET PLUGIN ==========
(function() {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/leaflet-polylineoffset@1.1.1/leaflet.polylineoffset.min.js';
    script.onload = function() {
        console.log('✅ Leaflet PolylineOffset loaded');
    };
    script.onerror = function() {
        console.error('❌ Failed to load PolylineOffset plugin');
    };
    document.head.appendChild(script);
})();
// ========== CYCLIC TIME INPUT ==========
document.addEventListener('DOMContentLoaded', function() {
    function setupCyclicInput(id, maxValue) {
        const input = document.getElementById(id);
        if (!input) return;
        
        let lastValue = parseInt(input.value) || 0;
        
        // 🔥 CHO PHÉP XÓA TỰ DO KHI FOCUS
        input.addEventListener('focus', function() {
            this.select(); // Select all để dễ gõ đè
        });
        
        // 🔥 CHỈ FORMAT KHI BLUR (CLICK RA NGOÀI)
        input.addEventListener('blur', function() {
            if (this.value === '' || this.value === null || this.value.trim() === '') {
                this.value = '00';
                lastValue = 0;
                return;
            }
            
            let val = parseInt(this.value);
            
            if (isNaN(val)) {
                this.value = '00';
                lastValue = 0;
                return;
            }
            
            if (val > maxValue) val = maxValue;
            if (val < 0) val = 0;
            
            this.value = val.toString().padStart(2, '0');
            lastValue = val;
        });
        
        // 🔥 XỬ LÝ PHÍM MŨI TÊN + CHO PHÉP BACKSPACE/DELETE
        input.addEventListener('keydown', function(e) {
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                let val = parseInt(this.value) || 0;
                val = val >= maxValue ? 0 : val + 1;
                this.value = val.toString().padStart(2, '0');
                lastValue = val;
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                let val = parseInt(this.value) || 0;
                val = val <= 0 ? maxValue : val - 1;
                this.value = val.toString().padStart(2, '0');
                lastValue = val;
            }
            // 🔥 CHO PHÉP XÓA BẰNG BACKSPACE/DELETE - KHÔNG BLOCK
            // else if (e.key === 'Backspace' || e.key === 'Delete') {
            //     // Không làm gì, cho phép xóa tự nhiên
            // }
        });
        
        // 🔥 SCROLL CHUỘT
        input.addEventListener('wheel', function(e) {
            e.preventDefault();
            let val = parseInt(this.value) || 0;
            
            if (e.deltaY < 0) {
                val = val >= maxValue ? 0 : val + 1;
            } else {
                val = val <= 0 ? maxValue : val - 1;
            }
            
            this.value = val.toString().padStart(2, '0');
            lastValue = val;
        }, { passive: false });
    }
    
    // Áp dụng cho tất cả input
    setupCyclicInput('startHour', 23);
    setupCyclicInput('endHour', 23);
    setupCyclicInput('startMinute', 59);
    setupCyclicInput('endMinute', 59);
});
// ========== SETUP CYCLIC TIME INPUTS FOR EDIT MODE ==========
function setupEditModeTimeInputs() {
    document.querySelectorAll('.time-input-hour, .time-input-minute').forEach(input => {
        const isHour = input.classList.contains('time-input-hour');
        const maxValue = isHour ? 23 : 59;
        
        // Xử lý wheel scroll
        let scrollTimeout = null;
        // ✅ Debounce để giảm tần suất update
        let wheelTimeout = null;

        input.addEventListener('wheel', function(e) {
            e.preventDefault();
            
            // ✅ Debounce - chỉ update sau 50ms
            clearTimeout(wheelTimeout);
            
            let val = parseInt(this.value) || 0;
            
            if (e.deltaY < 0) {
                val = val >= maxValue ? 0 : val + 1;
            } else {
                val = val <= 0 ? maxValue : val - 1;
            }
            
            this.value = val.toString().padStart(2, '0');
            
            // ✅ Chỉ update sau khi dừng scroll
            wheelTimeout = setTimeout(() => {
                updateTimeFromInputs(this);
            }, 50);
            
        }, { passive: false }); // ✅ Bỏ capture: true
        
        // Xử lý arrow keys
        input.addEventListener('keydown', function(e) {
            let val = parseInt(this.value) || 0;
            
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                val = val >= maxValue ? 0 : val + 1;
                this.value = val.toString().padStart(2, '0');
                updateTimeFromInputs(this);
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                val = val <= 0 ? maxValue : val - 1;
                this.value = val.toString().padStart(2, '0');
                updateTimeFromInputs(this);
            }
        });
        
        // Xử lý blur để format
        input.addEventListener('blur', function() {
            let val = parseInt(this.value) || 0;
            if (val > maxValue) val = maxValue;
            if (val < 0) val = 0;
            this.value = val.toString().padStart(2, '0');
            updateTimeFromInputs(this);
        });
        
        // Xử lý change
        input.addEventListener('change', function() {
            let val = parseInt(this.value) || 0;
            if (val > maxValue) val = 0;
            if (val < 0) val = maxValue;
            this.value = val.toString().padStart(2, '0');
            updateTimeFromInputs(this);
        });
    });
}

function updateTimeFromInputs(input) {
    const mealKey = input.dataset.mealKey;
    const parent = input.closest('.meal-item');
    if (!parent) return;
    
    const hourInput = parent.querySelector('.time-input-hour[data-meal-key="' + mealKey + '"]');
    const minuteInput = parent.querySelector('.time-input-minute[data-meal-key="' + mealKey + '"]');
    
    if (hourInput && minuteInput) {
        const hour = hourInput.value.padStart(2, '0');
        const minute = minuteInput.value.padStart(2, '0');
        const newTime = `${hour}:${minute}`;
        
        if (currentPlan && currentPlan[mealKey]) {
            // 🔥 LƯU VỊ TRÍ CŨ trước khi sort
            const oldOrder = currentPlan._order ? [...currentPlan._order] : 
                Object.keys(currentPlan)
                    .filter(k => k !== '_order' && currentPlan[k] && currentPlan[k].time)
                    .sort((a, b) => currentPlan[a].time.localeCompare(currentPlan[b].time));
            
            const oldIndex = oldOrder.indexOf(mealKey);
            
            // Cập nhật thời gian
            currentPlan[mealKey].time = newTime;
            
            // Cập nhật title nếu có
            const titleInput = parent.querySelector('input[onchange*="updateMealTitle"]');
            if (titleInput && titleInput.value) {
                currentPlan[mealKey].title = titleInput.value;
            }
            
            // 🔥 SORT lại theo thời gian
            const newOrder = Object.keys(currentPlan)
                .filter(k => k !== '_order' && currentPlan[k] && currentPlan[k].time)
                .sort((a, b) => {
                    const timeA = currentPlan[a].time || '00:00';
                    const timeB = currentPlan[b].time || '00:00';
                    return timeA.localeCompare(timeB);
                });
            
            const newIndex = newOrder.indexOf(mealKey);
            
            currentPlan._order = newOrder;
            
            // ✅ RENDER lại
            displayPlanVertical(currentPlan, isEditMode);
            
            // 🔥 HIGHLIGHT card vừa di chuyển + HIỂN THỊ ICON
            setTimeout(() => {
                const movedCard = document.querySelector(`[data-meal-key="${mealKey}"] .meal-card-vertical`);
                if (movedCard && oldIndex !== newIndex) {
                    // Thêm class animation
                    movedCard.classList.add('repositioned');
                    
                    // Thêm icon mũi tên
                    const direction = newIndex < oldIndex ? '⬆️' : '⬇️';
                    const indicator = document.createElement('div');
                    indicator.className = 'reposition-indicator';
                    indicator.textContent = direction;
                    movedCard.style.position = 'relative';
                    movedCard.appendChild(indicator);
                    
                    // Scroll đến vị trí mới
                    const mealItem = document.querySelector(`[data-meal-key="${mealKey}"]`);
                    if (mealItem) {
                        mealItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    
                    // Xóa animation và icon sau 1.5s
                    setTimeout(() => {
                        movedCard.classList.remove('repositioned');
                        if (indicator.parentNode) {
                            indicator.remove();
                        }
                    }, 1500);
                }
            }, 100);
        }
    }
}
// ========== CẬP NHẬT BÁN KÍNH KHI CHỌN ==========
document.addEventListener('DOMContentLoaded', function() {
    const radiusInputs = document.querySelectorAll('input[name="radius"]');
    
    radiusInputs.forEach(input => {
        input.addEventListener('change', function() {
            const radiusValue = this.value || '10'; // Mặc định 10km nếu chọn "Bán kính mặc định"
            
            // 🔥 CẬP NHẬT BIẾN TOÀN CỤC
            window.currentRadius = radiusValue;
            
            // 🔥 CẬP NHẬT HIDDEN INPUT
            const hiddenInput = document.getElementById('radius');
            if (hiddenInput) {
                hiddenInput.value = radiusValue;
            }
            
            console.log('✅ Đã cập nhật bán kính:', radiusValue + ' km');
        });
    });
    
    // 🔥 ĐẶT GIÁ TRỊ BAN ĐẦU
    const checkedRadius = document.querySelector('input[name="radius"]:checked');
    if (checkedRadius) {
        window.currentRadius = checkedRadius.value || '10';
        const hiddenInput = document.getElementById('radius');
        if (hiddenInput) {
            hiddenInput.value = window.currentRadius;
        }
    }
});

// ========== DELETE ALL MEALS ==========
function deleteAllMeals() {
    if (!currentPlan) return;
    
    const mealCount = Object.keys(currentPlan).filter(k => k !== '_order').length;
    
    if (mealCount === 0) {
        alert('⚠️ Lịch trình đã trống rồi!');
        return;
    }
    
    if (!confirm(`🗑️ Bạn có chắc muốn xóa tất cả ${mealCount} quán trong lịch trình?`)) {
        return;
    }
    
    // Xóa tất cả keys trừ _order
    Object.keys(currentPlan).forEach(key => {
        if (key !== '_order') {
            delete currentPlan[key];
        }
    });
    
    // Reset _order
    currentPlan._order = [];
    
    // Reset waiting state
    waitingForPlaceSelection = null;
    
    // Render lại
    displayPlanVertical(currentPlan, isEditMode);
    
    alert('✅ Đã xóa tất cả quán!');
}
// ========== CHECK PENDING SUGGESTION ==========
async function checkPendingSuggestion(planId) {
    try {
        console.log('🔍 Checking pending suggestion for plan:', planId);
        
        const response = await fetch(`/api/accounts/food-plan/check-pending/${planId}/`);
        const data = await response.json();
        
        console.log('📥 Response from API:', data);
        
        if (data.status === 'success') {
            hasPendingSuggestion = data.has_pending;
            
            console.log('✅ hasPendingSuggestion updated to:', hasPendingSuggestion);
            
            // Cập nhật UI nút "Gửi đề xuất"
            updateSubmitSuggestionButton();
        }
    } catch (error) {
        console.error('❌ Error checking pending suggestion:', error);
    }
}

function updateSubmitSuggestionButton() {
    const submitBtn = document.querySelector('button[onclick*="submitSuggestion"]');
    
    if (!submitBtn) return;
    
    if (hasPendingSuggestion) {
        // Disable button và đổi style
        submitBtn.disabled = true;
        submitBtn.style.opacity = '0.5';
        submitBtn.style.cursor = 'not-allowed';
        submitBtn.title = 'Bạn đã có 1 đề xuất đang chờ duyệt';
        
        // Đổi text
        const btnLabel = submitBtn.querySelector('.btn-label');
        if (btnLabel) {
            btnLabel.textContent = 'Đang chờ duyệt';
        }
    } else {
        // Enable button
        submitBtn.disabled = false;
        submitBtn.style.opacity = '1';
        submitBtn.style.cursor = 'pointer';
        submitBtn.title = 'Gửi đề xuất';
        
        // Đổi text về ban đầu
        const btnLabel = submitBtn.querySelector('.btn-label');
        if (btnLabel) {
            btnLabel.textContent = 'Gửi đề xuất';
        }
    }
}
async function submitSuggestion() {
    if (!currentPlan || !currentPlanId) {
        alert('⚠️ Không có thay đổi để gửi');
        return;
    }
    
    // 🔥 THÊM: Kiểm tra pending
    if (hasPendingSuggestion) {
        alert('⚠️ Bạn đã có 1 đề xuất đang chờ duyệt. Vui lòng đợi chủ sở hữu xử lý trước khi gửi đề xuất mới.');
        return;
    }
    
    // 🔥 MỚI: KIỂM TRA CÓ THAY ĐỔI THỰC SỰ KHÔNG
    if (window.originalSharedPlanData) {
        // Lưu dữ liệu từ input trước khi so sánh
        const mealItems = document.querySelectorAll('.meal-item');
        mealItems.forEach(item => {
            const mealKey = item.dataset.mealKey;
            if (mealKey && currentPlan[mealKey]) {
                // Lưu title
                const titleInput = item.querySelector('input[onchange*="updateMealTitle"]');
                if (titleInput && titleInput.value) {
                    currentPlan[mealKey].title = titleInput.value;
                }
                
                // Lưu time
                const hourInput = item.querySelector('.time-input-hour');
                const minuteInput = item.querySelector('.time-input-minute');
                if (hourInput && minuteInput) {
                    const hour = hourInput.value.padStart(2, '0');
                    const minute = minuteInput.value.padStart(2, '0');
                    currentPlan[mealKey].time = `${hour}:${minute}`;
                }
            }
        });
        
        // So sánh với bản gốc
        const hasChanges = !comparePlanData(currentPlan, window.originalSharedPlanData);
        
        if (!hasChanges) {
            alert('⚠️ Bạn chưa thực hiện thay đổi nào so với lịch trình gốc!');
            return;
        }
        
        console.log('✅ Phát hiện có thay đổi, cho phép gửi đề xuất');
    }
    
    const message = prompt('Nhập lời nhắn kèm theo đề xuất (tùy chọn):');
    if (message === null) return; // User clicked Cancel
    
    try {
        // 🔥 LƯU DỮ LIỆU TỪ INPUT TRƯỚC KHI GỬI
        const mealItems = document.querySelectorAll('.meal-item');
        mealItems.forEach(item => {
            const mealKey = item.dataset.mealKey;
            if (mealKey && currentPlan[mealKey]) {
                // Lưu title
                const titleInput = item.querySelector('input[onchange*="updateMealTitle"]');
                if (titleInput && titleInput.value) {
                    currentPlan[mealKey].title = titleInput.value;
                }
                
                // Lưu time
                const hourInput = item.querySelector('.time-input-hour');
                const minuteInput = item.querySelector('.time-input-minute');
                if (hourInput && minuteInput) {
                    const hour = hourInput.value.padStart(2, '0');
                    const minute = minuteInput.value.padStart(2, '0');
                    currentPlan[mealKey].time = `${hour}:${minute}`;
                }
            }
        });
        
        // 🔥 CHUẨN BỊ DỮ LIỆU GỬI ĐI
        const planArray = [];
        const orderKeys = currentPlan._order || Object.keys(currentPlan).filter(k => k !== '_order');
        
        orderKeys.forEach(key => {
            if (currentPlan[key]) {
                planArray.push({
                    key: key,
                    data: JSON.parse(JSON.stringify(currentPlan[key]))
                });
            }
        });
        
        const response = await fetch(`/api/accounts/food-plan/suggest/${currentPlanId}/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                suggested_data: planArray,
                message: message || ''
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            alert('✅ Đã gửi đề xuất chỉnh sửa! Chờ chủ sở hữu phê duyệt.');
            
            // 🔥 THÊM: Đánh dấu đã có pending
            hasPendingSuggestion = true;
            updateSubmitSuggestionButton();
            
            // Tắt edit mode
            if (isEditMode) {
                toggleEditMode();
            }
        } else {
            alert('❌ ' + result.message);
        }
        
    } catch (error) {
        console.error('Error submitting suggestion:', error);
        alert('Không thể gửi đề xuất');
    }
}
// ========== CHECK PENDING SUGGESTIONS ==========
async function checkPendingSuggestions(planId) {
    try {
        const response = await fetch(`/api/accounts/food-plan/suggestions/${planId}/`);
        const data = await response.json();
        
        const suggestionsBtn = document.getElementById('suggestionsBtn');
        const suggestionCount = document.getElementById('suggestionCount');
        
        if (!suggestionsBtn || !suggestionCount) return;
        
        // 🔥 LỌC CHỈ LẤY PENDING
        const pendingSuggestions = data.suggestions ? 
            data.suggestions.filter(s => s.status === 'pending') : [];
        
        if (pendingSuggestions.length > 0) {
            suggestionsBtn.style.display = 'flex';
            suggestionCount.textContent = pendingSuggestions.length;
        } else {
            suggestionsBtn.style.display = 'none';
            suggestionCount.textContent = '0';
        }
        
    } catch (error) {
        console.error('Error checking suggestions:', error);
    }
}

// ========== OPEN SUGGESTIONS PANEL ==========
async function openSuggestionsPanel() {
    if (!currentPlanId) {
        alert('⚠️ Không có lịch trình đang mở');
        return;
    }
    
    try {
        const response = await fetch(`/api/accounts/food-plan/suggestions/${currentPlanId}/`);
        const data = await response.json();
        
        if (data.status !== 'success' || !data.suggestions || data.suggestions.length === 0) {
            alert('ℹ️ Không có đề xuất nào');
            return;
        }
        
        // 🔥 LỌC CHỈ LẤY PENDING
        const suggestions = data.suggestions.filter(s => s.status === 'pending');
        
        if (suggestions.length === 0) {
            alert('ℹ️ Không còn đề xuất pending nào');
            return;
        }
        

   // Tạo HTML cho danh sách đề xuất
const suggestionsHTML = suggestions.map((sug, index) => {
    const statusBg = sug.status === 'pending' ? '#FFF3E0' : sug.status === 'accepted' ? '#E8F5E9' : '#FFEBEE';
    const statusColor = sug.status === 'pending' ? '#F57C00' : sug.status === 'accepted' ? '#2E7D32' : '#C62828';
    const statusText = sug.status === 'pending' ? '⏳ Chờ duyệt' : sug.status === 'accepted' ? '✅ Đã chấp nhận' : '❌ Đã từ chối';
    const borderColor = sug.status === 'pending' ? '#FF9800' : sug.status === 'accepted' ? '#4CAF50' : '#F44336';
    
    return `
        <div style="
            background: white;
            border: 2px solid ${borderColor};
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 16px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        ">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                <div>
                    <div style="font-weight: 700; color: #333; font-size: 15px; margin-bottom: 8px;">
                        👤 ${sug.suggested_by_username}
                    </div>
                    <div style="font-size: 13px; color: #666;">
                        📅 ${new Date(sug.created_at).toLocaleString('vi-VN')}
                    </div>
                </div>
                <span style="
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 600;
                    background: ${statusBg};
                    color: ${statusColor};
                ">
                    ${statusText}
                </span>
            </div>
            
            ${sug.message ? `
                <div style="
                    background: #F5F5F5;
                    border-left: 3px solid #FF6B35;
                    padding: 10px 12px;
                    border-radius: 6px;
                    margin-bottom: 12px;
                    font-size: 13px;
                    color: #555;
                ">
                    💬 ${sug.message}
                </div>
            ` : ''}
            
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button onclick="viewSuggestionComparison(${sug.id})" style="
                    flex: 1;
                    background: linear-gradient(135deg, #2196F3 0%, #64B5F6 100%);
                    color: white;
                    border: none;
                    padding: 10px;
                    border-radius: 8px;
                    font-size: 13px;
                    font-weight: 600;
                    cursor: pointer;
                ">
                    👁️ Xem chi tiết
                </button>
                
                ${sug.status === 'pending' ? `
                    <button onclick="approveSuggestion(${sug.id})" style="
                        flex: 1;
                        background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
                        color: white;
                        border: none;
                        padding: 10px;
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                        cursor: pointer;
                    ">
                        ✅ Chấp nhận
                    </button>
                    
                    <button onclick="rejectSuggestion(${sug.id})" style="
                        flex: 1;
                        background: linear-gradient(135deg, #F44336 0%, #E57373 100%);
                        color: white;
                        border: none;
                        padding: 10px;
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                        cursor: pointer;
                    ">
                        ❌ Từ chối
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}).join('');
        
        // Tạo modal
        const modalHTML = `
            <div id="suggestionsModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.6);
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s ease;
            ">
                <div style="
                    background: linear-gradient(135deg, #F5F5F5 0%, #EEEEEE 100%);
                    padding: 24px;
                    border-radius: 16px;
                    max-width: 600px;
                    width: 90%;
                    max-height: 80vh;
                    overflow-y: auto;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="margin: 0; color: #333; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 28px;">📝</span>
                            <span>Đề xuất chỉnh sửa (${suggestions.length})</span>
                        </h3>
                        <button onclick="closeSuggestionsModal()" style="
                            background: #F44336;
                            color: white;
                            border: none;
                            width: 36px;
                            height: 36px;
                            border-radius: 50%;
                            cursor: pointer;
                            font-size: 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        ">×</button>
                    </div>
                    
                    ${suggestionsHTML}
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
    } catch (error) {
        console.error('Error loading suggestions:', error);
        alert('Không thể tải đề xuất');
    }
}

function closeSuggestionsModal() {
    const modal = document.getElementById('suggestionsModal');
    if (modal) modal.remove();
}

// ========== VIEW SUGGESTION COMPARISON ==========
async function viewSuggestionComparison(suggestionId) {
    try {
        const response = await fetch(`/api/accounts/food-plan/suggestion-detail/${suggestionId}/`);
        const data = await response.json();
        
        if (data.status !== 'success') {
            alert('❌ ' + data.message);
            return;
        }
        
        const suggestion = data.suggestion;
        const currentData = suggestion.current_data;
        const suggestedData = suggestion.suggested_data;
        
        // 🔥 PHÂN TÍCH THAY ĐỔI
        const changes = analyzeChanges(currentData, suggestedData);
        
        // Tạo modal với layout mới
        const comparisonHTML = `
            <div id="comparisonModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.7);
                z-index: 100000;
                display: flex;
                align-items: center;
                justify-content: center;
            ">
                <div style="
                    background: white;
                    padding: 30px;
                    border-radius: 16px;
                    max-width: 900px;
                    width: 95%;
                    max-height: 85vh;
                    overflow-y: auto;
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="margin: 0;">🔍 So sánh thay đổi</h3>
                        <button onclick="closeComparisonModal()" style="
                            background: #F44336;
                            color: white;
                            border: none;
                            width: 36px;
                            height: 36px;
                            border-radius: 50%;
                            cursor: pointer;
                            font-size: 20px;
                        ">×</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <!-- Cột trái: Lịch trình hiện tại -->
                        <div>
                            <h4 style="
                                background: linear-gradient(135deg, #FF6B35 0%, #FF8E53 100%);
                                color: white;
                                padding: 12px;
                                border-radius: 8px;
                                margin: 0 0 16px 0;
                            ">📅 Lịch trình hiện tại</h4>
                            ${renderPlanPreview(currentData)}
                        </div>
                        
                        <!-- Cột phải: Đề xuất thay đổi -->
                        <div>
                            <h4 style="
                                background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
                                color: white;
                                padding: 12px;
                                border-radius: 8px;
                                margin: 0 0 16px 0;
                            ">✨ Đề xuất thay đổi</h4>
                            ${renderChangesWithActions(changes, suggestionId)}
                        </div>
                    </div>
                    
                    ${suggestion.status === 'pending' && changes.length > 0 ? `
                        <div style="display: flex; gap: 12px; margin-top: 24px;">
                            <button onclick="approveAllChanges(${suggestionId})" style="
                                flex: 1;
                                background: linear-gradient(135deg, #4CAF50 0%, #66BB6A 100%);
                                color: white;
                                border: none;
                                padding: 14px;
                                border-radius: 10px;
                                font-size: 15px;
                                font-weight: 700;
                                cursor: pointer;
                            ">✅ Lưu thay đổi</button>
                            
                            <button onclick="rejectSuggestion(${suggestionId})" style="
                                flex: 1;
                                background: linear-gradient(135deg, #F44336 0%, #E57373 100%);
                                color: white;
                                border: none;
                                padding: 14px;
                                border-radius: 10px;
                                font-size: 15px;
                                font-weight: 700;
                                cursor: pointer;
                            ">❌ Từ chối toàn bộ đề xuất</button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', comparisonHTML);
        
    } catch (error) {
        console.error('Error loading comparison:', error);
        alert('Không thể tải chi tiết');
    }
}

// ========== ANALYZE CHANGES ==========
function analyzeChanges(currentData, suggestedData) {
    const changes = [];
    
    // Tạo map để dễ so sánh
    const currentMap = {};
    const suggestedMap = {};
    
    currentData.forEach(item => {
        currentMap[item.key] = item.data;
    });
    
    suggestedData.forEach(item => {
        suggestedMap[item.key] = item.data;
    });
    
    // 1. Tìm quán BỊ XÓA (có trong current nhưng không có trong suggested)
    currentData.forEach(item => {
        if (!suggestedMap[item.key]) {
            changes.push({
                type: 'removed',
                key: item.key,
                data: item.data
            });
        }
    });
    
    // 2. Tìm quán MỚI THÊM (có trong suggested nhưng không có trong current)
    suggestedData.forEach(item => {
        if (!currentMap[item.key]) {
            changes.push({
                type: 'added',
                key: item.key,
                data: item.data
            });
        }
    });
    
    // 3. Tìm quán BỊ THAY ĐỔI (cùng key nhưng khác place hoặc time/title)
    suggestedData.forEach(item => {
        if (currentMap[item.key]) {
            const current = currentMap[item.key];
            const suggested = item.data;
            
            // So sánh place
            const placeChanged = 
                current.place?.data_id !== suggested.place?.data_id;
            
            // So sánh time hoặc title
            const detailsChanged = 
                current.time !== suggested.time || 
                current.title !== suggested.title ||
                current.icon !== suggested.icon;
            
            if (placeChanged || detailsChanged) {
                changes.push({
                    type: 'modified',
                    key: item.key,
                    oldData: current,
                    newData: suggested
                });
            }
        }
    });
    
    return changes;
}
// ========== RENDER CHANGES WITH ACTION BUTTONS ==========
function renderChangesWithActions(changes, suggestionId) {
    if (changes.length === 0) {
        return '<p style="color: #999; text-align: center; padding: 20px;">Không có thay đổi nào</p>';
    }
    
    // 🔥 LẤY TRẠNG THÁI ĐÃ LƯU
    const pending = pendingApprovals[suggestionId] || { approvedChanges: [], rejectedChanges: [] };
    
    return changes.map((change, index) => {
        // 🔥 KIỂM TRA ĐÃ APPROVE/REJECT CHƯA
        const isApproved = pending.approvedChanges.some(c => c.changeKey === change.key);
        const isRejected = pending.rejectedChanges.some(c => c.changeKey === change.key);
        
        if (change.type === 'added') {
            // Quán mới thêm
            const meal = change.data;
            const place = meal.place;
            
            // 🔥 THÊM STYLE FADE NẾU ĐÃ CHỌN
            let containerStyle = `
                background: #E8F5E9;
                border: 2px solid #4CAF50;
                border-radius: 10px;
                padding: 12px;
                margin-bottom: 12px;
                position: relative;
            `;
            
            if (isApproved || isRejected) {
                containerStyle += `opacity: 0.5; pointer-events: none;`;
            }
            
            // 🔥 BADGE HIỆN TRẠNG THÁI
            const badgeHTML = isApproved ? `
                <div class="approval-badge" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #4CAF50;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
                    z-index: 10;
                ">✅ Đã đánh dấu chấp nhận</div>
            ` : isRejected ? `
                <div class="approval-badge" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #F44336;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4);
                    z-index: 10;
                ">❌ Đã đánh dấu từ chối</div>
            ` : '';
            
            return `
                <div id="change-${index}" style="${containerStyle}">
                    ${badgeHTML}
                    <div style="
                        position: absolute;
                        top: 8px;
                        left: 8px;
                        background: #4CAF50;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 700;
                    ">➕ THÊM MỚI</div>
                    
                    <div style="margin-top: 30px;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                            <span style="font-size: 20px;">${meal.icon || '🍽️'}</span>
                            <div style="flex: 1;">
                                <div style="font-weight: 700; color: #333; font-size: 14px;">
                                    ⏰ ${meal.time} - ${meal.title}
                                </div>
                                ${place ? `
                                    <div style="font-size: 12px; color: #666; margin-top: 4px;">
                                        🏪 ${place.ten_quan}
                                    </div>
                                    <div style="font-size: 11px; color: #999; margin-top: 2px;">
                                        📍 ${place.dia_chi}
                                    </div>
                                ` : '<div style="font-size: 12px; color: #999;">Chưa có quán</div>'}
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 8px; margin-top: 12px; border-top: 1px solid #C8E6C9; padding-top: 12px;">
                            <button onclick="approveChange(${suggestionId}, ${index}, 'added', '${change.key}')" style="
                                flex: 1;
                                background: #4CAF50;
                                color: white;
                                border: none;
                                padding: 8px;
                                border-radius: 6px;
                                font-size: 12px;
                                font-weight: 600;
                                cursor: pointer;
                            ">✅ Chấp nhận</button>
                            
                            <button onclick="rejectChange(${suggestionId}, ${index}, 'added', '${change.key}')" style="
                                flex: 1;
                                background: #F44336;
                                color: white;
                                border: none;
                                padding: 8px;
                                border-radius: 6px;
                                font-size: 12px;
                                font-weight: 600;
                                cursor: pointer;
                            ">❌ Từ chối</button>
                        </div>
                    </div>
                </div>
            `;
            
        } else if (change.type === 'removed') {
            // Quán bị xóa
            const meal = change.data;
            const place = meal.place;
            
            // 🔥 THÊM STYLE FADE NẾU ĐÃ CHỌN
            let containerStyle = `
                background: #FFEBEE;
                border: 2px solid #F44336;
                border-radius: 10px;
                padding: 12px;
                margin-bottom: 12px;
                position: relative;
                opacity: 0.8;
            `;
            
            if (isApproved || isRejected) {
                containerStyle = containerStyle.replace('opacity: 0.8;', 'opacity: 0.5; pointer-events: none;');
            }
            
            // 🔥 BADGE HIỆN TRẠNG THÁI
            const badgeHTML = isApproved ? `
                <div class="approval-badge" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #4CAF50;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
                    z-index: 10;
                ">✅ Đã đánh dấu chấp nhận</div>
            ` : isRejected ? `
                <div class="approval-badge" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #F44336;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4);
                    z-index: 10;
                ">❌ Đã đánh dấu từ chối</div>
            ` : '';
            
            return `
                <div id="change-${index}" style="${containerStyle}">
                    ${badgeHTML}
                    <div style="
                        position: absolute;
                        top: 8px;
                        left: 8px;
                        background: #F44336;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 700;
                    ">🗑️ XÓA BỎ</div>
                    
                    <div style="margin-top: 30px;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                            <span style="font-size: 20px;">${meal.icon || '🍽️'}</span>
                            <div style="flex: 1;">
                                <div style="font-weight: 700; color: #333; font-size: 14px; text-decoration: line-through;">
                                    ⏰ ${meal.time} - ${meal.title}
                                </div>
                                ${place ? `
                                    <div style="font-size: 12px; color: #666; margin-top: 4px; text-decoration: line-through;">
                                        🏪 ${place.ten_quan}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 8px; margin-top: 12px; border-top: 1px solid #FFCDD2; padding-top: 12px;">
                            <button onclick="approveChange(${suggestionId}, ${index}, 'removed', '${change.key}')" style="
                                flex: 1;
                                background: #4CAF50;
                                color: white;
                                border: none;
                                padding: 8px;
                                border-radius: 6px;
                                font-size: 12px;
                                font-weight: 600;
                                cursor: pointer;
                            ">✅ Đồng ý xóa</button>
                            
                            <button onclick="rejectChange(${suggestionId}, ${index}, 'removed', '${change.key}')" style="
                                flex: 1;
                                background: #F44336;
                                color: white;
                                border: none;
                                padding: 8px;
                                border-radius: 6px;
                                font-size: 12px;
                                font-weight: 600;
                                cursor: pointer;
                            ">❌ Giữ lại</button>
                        </div>
                    </div>
                </div>
            `;
            
        } else if (change.type === 'modified') {
            // Quán bị thay đổi
            const oldMeal = change.oldData;
            const newMeal = change.newData;
            
            // 🔥 THÊM STYLE FADE NẾU ĐÃ CHỌN
            let containerStyle = `
                background: #FFF3E0;
                border: 2px solid #FF9800;
                border-radius: 10px;
                padding: 12px;
                margin-bottom: 12px;
                position: relative;
            `;
            
            if (isApproved || isRejected) {
                containerStyle += `opacity: 0.5; pointer-events: none;`;
            }
            
            // 🔥 BADGE HIỆN TRẠNG THÁI
            const badgeHTML = isApproved ? `
                <div class="approval-badge" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #4CAF50;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
                    z-index: 10;
                ">✅ Đã đánh dấu chấp nhận</div>
            ` : isRejected ? `
                <div class="approval-badge" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    background: #F44336;
                    color: white;
                    padding: 12px 24px;
                    border-radius: 20px;
                    font-weight: 700;
                    font-size: 14px;
                    box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4);
                    z-index: 10;
                ">❌ Đã đánh dấu từ chối</div>
            ` : '';
            
            return `
                <div id="change-${index}" style="${containerStyle}">
                    ${badgeHTML}
                    <div style="
                        position: absolute;
                        top: 8px;
                        left: 8px;
                        background: #FF9800;
                        color: white;
                        padding: 4px 8px;
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: 700;
                    ">✏️ THAY ĐỔI</div>
                    
                    <div style="margin-top: 30px;">
                        <div style="font-size: 11px; color: #E65100; font-weight: 600; margin-bottom: 8px;">Trước:</div>
                        <div style="background: rgba(255,255,255,0.5); padding: 8px; border-radius: 6px; margin-bottom: 8px; opacity: 0.7;">
                            <div style="font-size: 12px; color: #666;">
                                <span style="font-size: 16px;">${oldMeal.icon || '🍽️'}</span>
                                ⏰ ${oldMeal.time} - ${oldMeal.title}
                            </div>
                            ${oldMeal.place ? `
                                <div style="font-size: 11px; color: #999; margin-top: 4px;">
                                    🏪 ${oldMeal.place.ten_quan}
                                </div>
                            ` : ''}
                        </div>
                        
                        <div style="text-align: center; margin: 8px 0;">
                            <span style="font-size: 20px;">⬇️</span>
                        </div>
                        
                        <div style="font-size: 11px; color: #E65100; font-weight: 600; margin-bottom: 8px;">Sau:</div>
                        <div style="background: rgba(255,255,255,0.8); padding: 8px; border-radius: 6px; border: 1px solid #FFB74D;">
                            <div style="font-size: 12px; color: #333; font-weight: 600;">
                                <span style="font-size: 16px;">${newMeal.icon || '🍽️'}</span>
                                ⏰ ${newMeal.time} - ${newMeal.title}
                            </div>
                            ${newMeal.place ? `
                                <div style="font-size: 11px; color: #666; margin-top: 4px;">
                                    🏪 ${newMeal.place.ten_quan}
                                </div>
                            ` : ''}
                        </div>
                        
                        <div style="display: flex; gap: 8px; margin-top: 12px; border-top: 1px solid #FFE0B2; padding-top: 12px;">
                            <button onclick="approveChange(${suggestionId}, ${index}, 'modified', '${change.key}')" style="
                                flex: 1;
                                background: #4CAF50;
                                color: white;
                                border: none;
                                padding: 8px;
                                border-radius: 6px;
                                font-size: 12px;
                                font-weight: 600;
                                cursor: pointer;
                            ">✅ Chấp nhận</button>
                            
                            <button onclick="rejectChange(${suggestionId}, ${index}, 'modified', '${change.key}')" style="
                                flex: 1;
                                background: #F44336;
                                color: white;
                                border: none;
                                padding: 8px;
                                border-radius: 6px;
                                font-size: 12px;
                                font-weight: 600;
                                cursor: pointer;
                            ">❌ Từ chối</button>
                        </div>
                    </div>
                </div>
            `;
        }
    }).join('');
}

function renderPlanPreview(planData) {
    if (!planData || planData.length === 0) {
        return '<p style="color: #999; text-align: center;">Không có dữ liệu</p>';
    }
    
    return planData.map((item, index) => {
        const meal = item.data;
        const place = meal.place;
        
        return `
            <div style="
                background: #F9F9F9;
                border: 2px solid #E0E0E0;
                border-radius: 10px;
                padding: 12px;
                margin-bottom: 12px;
            ">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 20px;">${meal.icon || '🍽️'}</span>
                    <div>
                        <div style="font-weight: 700; color: #333; font-size: 14px;">
                            ⏰ ${meal.time} - ${meal.title}
                        </div>
                        ${place ? `
                            <div style="font-size: 12px; color: #666; margin-top: 4px;">
                                🏪 ${place.ten_quan}
                            </div>
                        ` : '<div style="font-size: 12px; color: #999;">Chưa có quán</div>'}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function closeComparisonModal() {
    const modal = document.getElementById('comparisonModal');
    if (modal) modal.remove();
}

async function approveSuggestion(suggestionId) {
    if (!confirm('✅ Xác nhận chấp nhận đề xuất này?')) return;
    
    try {
        const response = await fetch(`/api/accounts/food-plan/suggestion-approve/${suggestionId}/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // 🔥 HIỂN THỊ THÔNG BÁO VỀ SỐ ĐỀ XUẤT BỊ TỪ CHỐI
            let alertMsg = '✅ Đã chấp nhận đề xuất!';
            if (result.rejected_count && result.rejected_count > 0) {
                alertMsg += `\n\n🔄 Đã tự động từ chối ${result.rejected_count} đề xuất khác.`;
            }
            alert(alertMsg);
            
            // Đóng tất cả modal
            closeComparisonModal();
            closeSuggestionsModal();
            
            // 🔥 CẬP NHẬT SỐ LƯỢNG ĐỀ XUẤT PENDING
            if (currentPlanId) {
                await checkPendingSuggestions(currentPlanId);
                await loadSavedPlans(currentPlanId);
            }
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error approving suggestion:', error);
        alert('Không thể chấp nhận đề xuất');
    }
}
async function rejectSuggestion(suggestionId) {
    if (!confirm('❌ Xác nhận từ chối TOÀN BỘ đề xuất này?')) return;
    
    try {
        const response = await fetch(`/api/accounts/food-plan/suggestion-reject/${suggestionId}/`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            // 🔥 XÓA TRẠNG THÁI TẠM
            delete pendingApprovals[suggestionId];
            
            alert('✅ Đã từ chối toàn bộ đề xuất!');
            
            closeComparisonModal();
            closeSuggestionsModal();
            
            if (currentPlanId) {
                await checkPendingSuggestions(currentPlanId);
            }
            // 🔥 THÊM: Reset pending status nếu đang xem shared plan
            if (isViewingSharedPlan && hasEditPermission) {
                hasPendingSuggestion = false;
                updateSubmitSuggestionButton();
            }
        } else {
            alert('❌ ' + result.message);
        }
    } catch (error) {
        console.error('Error rejecting suggestion:', error);
        alert('Không thể từ chối đề xuất');
    }
}

// ========== EXIT SHARED PLAN VIEW ==========
function exitSharedPlanView() {
    if (!confirm('Bạn có chắc muốn thoát chế độ xem shared plan?')) return;
    
    // Reset tất cả trạng thái
    isViewingSharedPlan = false;
    isSharedPlan = false;
    sharedPlanOwnerId = null;
    sharedPlanOwnerName = '';
    hasEditPermission = false;
    currentPlan = null;
    currentPlanId = null;
    isEditMode = false;
    waitingForPlaceSelection = null;
    
    // Xóa routes trên map
    clearRoutes();
    
    // Clear nội dung
    const resultDiv = document.getElementById('planResult');
    if (resultDiv) {
        resultDiv.innerHTML = '';
    }
    
    // Hiện lại filters
    const filtersWrapper = document.querySelector('.filters-wrapper-new');
    if (filtersWrapper) {
        filtersWrapper.style.display = 'block';
    }
    
    // 🔥 ẨN NÚT X KHI THOÁT CHẾ ĐỘ XEM
    const exitBtn = document.getElementById('exitSharedPlanBtn');
    if (exitBtn) {
        exitBtn.style.display = 'none';
    }
    
    // Reload danh sách plans
    loadSavedPlans();
    
    console.log('✅ Đã thoát chế độ xem shared plan');
}
// ========== APPROVE SINGLE CHANGE - CHỈ LƯU TRẠNG THÁI TẠM ==========
async function approveChange(suggestionId, changeIndex, changeType, changeKey) {
    if (!confirm('✅ Xác nhận chấp nhận thay đổi này?')) return;
    
    // 🔥 KHỞI TẠO NẾU CHƯA CÓ
    if (!pendingApprovals[suggestionId]) {
        pendingApprovals[suggestionId] = {
            approvedChanges: [],
            rejectedChanges: []
        };
    }
    
    // 🔥 LƯU VÀO DANH SÁCH TẠM
    const changeInfo = { changeIndex, changeType, changeKey };
    
    // Xóa khỏi rejected nếu có
    pendingApprovals[suggestionId].rejectedChanges = 
        pendingApprovals[suggestionId].rejectedChanges.filter(c => c.changeKey !== changeKey);
    
    // Thêm vào approved (nếu chưa có)
    if (!pendingApprovals[suggestionId].approvedChanges.some(c => c.changeKey === changeKey)) {
        pendingApprovals[suggestionId].approvedChanges.push(changeInfo);
    }
    
    console.log('✅ Đã lưu trạng thái tạm:', pendingApprovals[suggestionId]);
    
    // 🔥 CẬP NHẬT UI - HIỆN BADGE
    const changeEl = document.getElementById(`change-${changeIndex}`);
    if (changeEl) {
        changeEl.style.opacity = '0.5';
        changeEl.style.pointerEvents = 'none';
        
        // Xóa badge cũ nếu có
        const oldBadge = changeEl.querySelector('.approval-badge');
        if (oldBadge) oldBadge.remove();
        
        const badge = document.createElement('div');
        badge.className = 'approval-badge';
        badge.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #4CAF50;
            color: white;
            padding: 12px 24px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
            z-index: 10;
        `;
        badge.textContent = '✅ Đã đánh dấu chấp nhận';
        changeEl.style.position = 'relative';
        changeEl.appendChild(badge);
    }
    
    // 🔥 KHÔNG CÓ ALERT NỮA
}

// ========== REJECT SINGLE CHANGE - CHỈ LƯU TRẠNG THÁI TẠM ==========
async function rejectChange(suggestionId, changeIndex, changeType, changeKey) {
    if (!confirm('❌ Xác nhận từ chối thay đổi này?')) return;
    
    // 🔥 KHỞI TẠO NẾU CHƯA CÓ
    if (!pendingApprovals[suggestionId]) {
        pendingApprovals[suggestionId] = {
            approvedChanges: [],
            rejectedChanges: []
        };
    }
    
    // 🔥 LƯU VÀO DANH SÁCH TẠM
    const changeInfo = { changeIndex, changeType, changeKey };
    
    // Xóa khỏi approved nếu có
    pendingApprovals[suggestionId].approvedChanges = 
        pendingApprovals[suggestionId].approvedChanges.filter(c => c.changeKey !== changeKey);
    
    // Thêm vào rejected (nếu chưa có)
    if (!pendingApprovals[suggestionId].rejectedChanges.some(c => c.changeKey === changeKey)) {
        pendingApprovals[suggestionId].rejectedChanges.push(changeInfo);
    }
    
    console.log('❌ Đã lưu trạng thái từ chối:', pendingApprovals[suggestionId]);
    
    // 🔥 CẬP NHẬT UI
    const changeEl = document.getElementById(`change-${changeIndex}`);
    if (changeEl) {
        changeEl.style.opacity = '0.5';
        changeEl.style.pointerEvents = 'none';
        
        const oldBadge = changeEl.querySelector('.approval-badge');
        if (oldBadge) oldBadge.remove();
        
        const badge = document.createElement('div');
        badge.className = 'approval-badge';
        badge.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: #F44336;
            color: white;
            padding: 12px 24px;
            border-radius: 20px;
            font-weight: 700;
            font-size: 14px;
            box-shadow: 0 4px 12px rgba(244, 67, 54, 0.4);
            z-index: 10;
        `;
        badge.textContent = '❌ Đã đánh dấu từ chối';
        changeEl.style.position = 'relative';
        changeEl.appendChild(badge);
    }
}

async function approveAllChanges(suggestionId) {
    const pending = pendingApprovals[suggestionId];
    
    // 🔥 BƯỚC 1: Lấy tổng số thay đổi từ suggestion
    let totalChanges = 0;
    try {
        const response = await fetch(`/api/accounts/food-plan/suggestion-detail/${suggestionId}/`);
        const data = await response.json();
        
        if (data.status !== 'success') {
            alert('❌ ' + data.message);
            return;
        }
        
        const suggestion = data.suggestion;
        const changes = analyzeChanges(suggestion.current_data, suggestion.suggested_data);
        totalChanges = changes.length;
        
        // 🔥 CASE 1: Không đánh dấu gì cả → Chấp nhận TẤT CẢ
        if (!pending || (!pending.approvedChanges.length && !pending.rejectedChanges.length)) {
            if (!confirm(`Bạn chưa xử lý bất kỳ thay đổi nào.\n\n✅ Xác nhận chấp nhận TẤT CẢ ${totalChanges} thay đổi?`)) {
                return;
            }
            
            // Tự động chấp nhận tất cả
            if (!pendingApprovals[suggestionId]) {
                pendingApprovals[suggestionId] = {
                    approvedChanges: [],
                    rejectedChanges: []
                };
            }
            
            changes.forEach((change, index) => {
                pendingApprovals[suggestionId].approvedChanges.push({
                    changeIndex: index,
                    changeType: change.type,
                    changeKey: change.key
                });
            });
            
            console.log('✅ Đã tự động chấp nhận tất cả thay đổi:', pendingApprovals[suggestionId]);
        }
        // 🔥 CASE 2: Đã đánh dấu một vài cái → KIỂM TRA có xử lý hết chưa
        else {
            const approvedCount = pending.approvedChanges.length;
            const rejectedCount = pending.rejectedChanges.length;
            const processedCount = approvedCount + rejectedCount;
            
            // Nếu chưa xử lý hết → BẮT BUỘC phải xử lý hết
            if (processedCount < totalChanges) {
                const remainingCount = totalChanges - processedCount;
                alert(`⚠️ Bạn còn ${remainingCount} thay đổi chưa xử lý!\n\n` +
                      `📊 Tổng: ${totalChanges} thay đổi\n` +
                      `✅ Đã chấp nhận: ${approvedCount}\n` +
                      `❌ Đã từ chối: ${rejectedCount}\n\n` +
                      `Vui lòng xử lý HẾT các thay đổi còn lại trước khi lưu.`);
                return;
            }
            
               // 🔥 CASE ĐẶC BIỆT: Nếu TẤT CẢ đều bị từ chối → Gọi API reject toàn bộ suggestion
            if (approvedCount === 0 && rejectedCount === totalChanges) {
                if (!confirm(`⚠️ Bạn đã từ chối TẤT CẢ ${totalChanges} thay đổi.\n\nXác nhận từ chối toàn bộ đề xuất này?`)) {
                    return;
                }
                
                // Gọi API reject suggestion
                try {
                    const response = await fetch(`/api/accounts/food-plan/suggestion-reject/${suggestionId}/`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'}
                    });
                    
                    const result = await response.json();
                    
                    if (result.status === 'success') {
                        alert('✅ Đã từ chối toàn bộ đề xuất!');
                        
                        // Xóa trạng thái tạm
                        delete pendingApprovals[suggestionId];
                        
                        // Đóng modal
                        closeComparisonModal();
                        closeSuggestionsModal();
                        
                        // Reload
                        if (currentPlanId) {
                            await checkPendingSuggestions(currentPlanId);
                        }
                        
                        // Reset pending status nếu đang xem shared plan
                        if (isViewingSharedPlan && hasEditPermission) {
                            hasPendingSuggestion = false;
                            updateSubmitSuggestionButton();
                        }
                    } else {
                        alert('❌ ' + result.message);
                    }
                    
                } catch (error) {
                    console.error('Error rejecting suggestion:', error);
                    alert('Không thể từ chối đề xuất');
                }
                
                return; // Dừng hàm, không chạy tiếp phần approve
            }
            
            // Xác nhận cuối cùng
            const confirmMsg = `📊 Tổng kết:\n✅ Chấp nhận: ${approvedCount} thay đổi\n❌ Từ chối: ${rejectedCount} thay đổi\n\nXác nhận áp dụng các thay đổi đã chọn?`;
            
            if (!confirm(confirmMsg)) return;
        }
        
    } catch (error) {
        console.error('Error loading suggestion:', error);
        alert('⚠️ Không thể tải thông tin đề xuất');
        return;
    }
    
    // 🔥 PHẦN CODE GỬI API VẪN GIỮ NGUYÊN
    const approvedCount = pendingApprovals[suggestionId].approvedChanges.length;
    const rejectedCount = pendingApprovals[suggestionId].rejectedChanges.length;
    
    try {
        const response = await fetch('/api/accounts/food-plan/approve-all-changes/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                suggestion_id: suggestionId,
                approved_changes: pendingApprovals[suggestionId].approvedChanges
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            let alertMsg = `✅ Đã áp dụng ${result.applied_count} thay đổi!`;
            if (result.rejected_count && result.rejected_count > 0) {
                alertMsg += `\n\n🔄 Đã tự động từ chối ${result.rejected_count} đề xuất khác.`;
            }
            alert(alertMsg);
            
            delete pendingApprovals[suggestionId];
            
            closeComparisonModal();
            closeSuggestionsModal();
            
            if (currentPlanId) {
                await checkPendingSuggestions(currentPlanId);
                await loadSavedPlans(currentPlanId, true);
            }
            if (isViewingSharedPlan && hasEditPermission) {
                hasPendingSuggestion = false;
                updateSubmitSuggestionButton();
            }
        } else {
            alert('❌ ' + result.message);
        }
        
    } catch (error) {
        console.error('Error approving all changes:', error);
        alert('Không thể áp dụng thay đổi');
    }
}

// ========== VIEW MY SUGGESTIONS ==========
async function viewMySuggestions(planId) {
    // 🔥 KIỂM TRA NẾU MODAL ĐÃ TỒN TẠI → KHÔNG MỞ THÊM
    if (document.getElementById('mySuggestionsModal')) {
        console.log('⚠️ Modal đã mở rồi, không mở thêm');
        return;
    }
    
    if (!planId) {
        alert('⚠️ Không có lịch trình đang mở');
        return;
    }
    
    try {
        const response = await fetch(`/api/accounts/food-plan/my-suggestions/${planId}/`);
        const data = await response.json();
        
        if (data.status !== 'success') {
            alert('❌ ' + data.message);
            return;
        }
        
        const suggestions = data.suggestions || [];
        
        if (suggestions.length === 0) {
            alert('ℹ️ Bạn chưa gửi đề xuất nào cho lịch trình này');
            return;
        }
        
        // Tạo HTML hiển thị
        const suggestionsHTML = suggestions.map((sug, index) => {
            const statusBg = sug.status === 'pending' ? '#FFF3E0' : 
                           sug.status === 'accepted' ? '#E8F5E9' : '#FFEBEE';
            const statusColor = sug.status === 'pending' ? '#F57C00' : 
                              sug.status === 'accepted' ? '#2E7D32' : '#C62828';
            const statusIcon = sug.status === 'pending' ? '⏳' : 
                             sug.status === 'accepted' ? '✅' : '❌';
            const statusText = sug.status === 'pending' ? 'Chờ duyệt' : 
                             sug.status === 'accepted' ? 'Đã chấp nhận' : 'Đã từ chối';
            
            // 🔥 SỬA: Dùng hàm formatDateTimeWithTimezone
            const createdAtFormatted = formatDateTimeWithTimezone(sug.created_at);
            const reviewedAtFormatted = sug.reviewed_at ? 
                formatDateTimeWithTimezone(sug.reviewed_at) : null;
            
            return `
                <div style="
                    background: white;
                    border: 2px solid ${sug.status === 'pending' ? '#FF9800' : sug.status === 'accepted' ? '#4CAF50' : '#F44336'};
                    border-radius: 12px;
                    padding: 16px;
                    margin-bottom: 16px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
                        <div>
                            <div style="font-weight: 700; color: #333; font-size: 15px; margin-bottom: 8px;">
                                📝 Đề xuất #${suggestions.length - index}
                            </div>
                            <div style="font-size: 13px; color: #666;">
                                📅 ${createdAtFormatted}
                            </div>
                            ${reviewedAtFormatted ? `
                                <div style="font-size: 13px; color: #666; margin-top: 4px;">
                                    🕐 Xét duyệt: ${reviewedAtFormatted}
                                </div>
                            ` : ''}
                        </div>
                        <span style="
                            padding: 6px 14px;
                            border-radius: 12px;
                            font-size: 13px;
                            font-weight: 700;
                            background: ${statusBg};
                            color: ${statusColor};
                        ">
                            ${statusIcon} ${statusText}
                        </span>
                    </div>
                    
                    ${sug.message ? `
                        <div style="
                            background: #F5F5F5;
                            border-left: 3px solid #FF6B35;
                            padding: 10px 12px;
                            border-radius: 6px;
                            margin-bottom: 12px;
                            font-size: 13px;
                            color: #555;
                        ">
                            💬 ${sug.message}
                        </div>
                    ` : ''}
                    
                    ${sug.status === 'accepted' ? `
                        <div style="
                            background: #E8F5E9;
                            border: 1px solid #4CAF50;
                            padding: 10px;
                            border-radius: 8px;
                            font-size: 13px;
                            color: #2E7D32;
                            font-weight: 600;
                        ">
                            ✨ Đề xuất của bạn đã được chấp nhận và áp dụng vào lịch trình!
                        </div>
                    ` : ''}
                    
                    ${sug.status === 'rejected' ? `
                        <div style="
                            background: #FFEBEE;
                            border: 1px solid #F44336;
                            padding: 10px;
                            border-radius: 8px;
                            font-size: 13px;
                            color: #C62828;
                            font-weight: 600;
                        ">
                            😔 Đề xuất của bạn đã bị từ chối
                        </div>
                    ` : ''}
                    
                    ${sug.status === 'pending' ? `
                        <div style="
                            background: #FFF3E0;
                            border: 1px solid #FF9800;
                            padding: 10px;
                            border-radius: 8px;
                            font-size: 13px;
                            color: #F57C00;
                            font-weight: 600;
                        ">
                            ⏳ Đang chờ chủ sở hữu xem xét...
                        </div>
                    ` : ''}
                </div>
            `;
        }).join('');
        
        // Tạo modal
        const modalHTML = `
            <div id="mySuggestionsModal" style="
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.6);
                z-index: 99999;
                display: flex;
                align-items: center;
                justify-content: center;
                animation: fadeIn 0.3s ease;
            ">
                <div style="
                    background: linear-gradient(135deg, #F5F5F5 0%, #EEEEEE 100%);
                    padding: 24px;
                    border-radius: 16px;
                    max-width: 600px;
                    width: 90%;
                    max-height: 80vh;
                    overflow-y: auto;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                        <h3 style="margin: 0; color: #333; display: flex; align-items: center; gap: 10px;">
                            <span style="font-size: 28px;">📋</span>
                            <span>Đề xuất của tôi (${suggestions.length})</span>
                        </h3>
                        <button onclick="closeMySuggestionsModal()" style="
                            background: #F44336;
                            color: white;
                            border: none;
                            width: 36px;
                            height: 36px;
                            border-radius: 50%;
                            cursor: pointer;
                            font-size: 20px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                        ">×</button>
                    </div>
                    
                    ${suggestionsHTML}
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
    } catch (error) {
        console.error('Error loading my suggestions:', error);
        alert('Không thể tải đề xuất của bạn');
    }
}

function closeMySuggestionsModal() {
    const modal = document.getElementById('mySuggestionsModal');
    if (modal) modal.remove();
}
</script>
'''