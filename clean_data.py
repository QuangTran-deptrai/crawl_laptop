import pandas as pd
import numpy as np
import re
import os
import sys
import glob
from sqlalchemy import create_engine

# Fix lỗi mã hóa font / emoji trên Windows console (cp1252 / cp1258)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ==========================================================
# CẤU HÌNH DATABASE
# ==========================================================
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "123456")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "laptop_db")


# ==========================================================
# CÁC HÀM XỬ LÝ LÀM SẠCH VÀ BÓC TÁCH THÔNG SỐ (PARSERS)
# ==========================================================

def clean_price(val):
    """Chuẩn hóa giá tiền về dạng số nguyên (VND)"""
    if pd.isna(val):
        return None
    # Nếu đã là int hoặc float thì ép về int ngay, tránh lỗi .0 bị hiểu nhầm thành thêm số 0
    if isinstance(val, (int, float, np.integer, np.floating)):
        try:
            return int(val)
        except:
            return None
            
    val_str = str(val).strip()
    # Xóa đuôi .0 nếu chuỗi float
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
        
    digits = re.sub(r'[^\d]', '', val_str)
    if digits:
        try:
            return int(digits)
        except:
            return None
    return None


def extract_brand(title):
    """Trích xuất Hãng sản xuất laptop từ tên sản phẩm"""
    title_upper = str(title).upper()
    brands = [
        ('APPLE', ['MACBOOK', 'APPLE']),
        ('ASUS', ['ASUS']),
        ('ACER', ['ACER']),
        ('DELL', ['DELL']),
        ('HP', ['HP', 'HEWLETT']),
        ('LENOVO', ['LENOVO', 'THINKPAD']),
        ('MSI', ['MSI']),
        ('GIGABYTE', ['GIGABYTE', 'AORUS']),
        ('LG', ['LG', 'GRAM']),
        ('HUAWEI', ['HUAWEI', 'MATEBOOK']),
        ('COLORFUL', ['COLORFUL']),
        ('VAIO', ['VAIO']),
        ('MICROSOFT', ['SURFACE', 'MICROSOFT']),
        ('MASSTEL', ['MASSTEL'])
    ]
    for brand, keywords in brands:
        for kw in keywords:
            if re.search(r'\b' + kw + r'\b', title_upper):
                return brand
    return "KHÁC"


def extract_series(title, brand):
    """Trích xuất Dòng máy (Series/Model Line)"""
    title_clean = str(title)
    series_dict = {
        'ASUS': ['ZenBook Pro', 'ZenBook', 'Zenbook', 'Vivobook Pro', 'Vivobook S', 'Vivobook Flip', 'Vivobook', 'VivoBook', 'ROG Strix', 'ROG Zephyrus', 'ROG Flow', 'ROG', 'TUF Gaming', 'TUF', 'ExpertBook', 'ProArt'],
        'ACER': ['Predator Helios', 'Predator', 'Nitro V', 'Nitro 5', 'Nitro 16', 'Nitro', 'Aspire 7', 'Aspire 5', 'Aspire 3', 'Aspire Lite', 'Aspire', 'Swift Go', 'Swift X', 'Swift', 'TravelMate'],
        'LENOVO': ['Legion Pro', 'Legion Slim', 'Legion', 'LOQ', 'ThinkPad X1', 'ThinkPad P', 'ThinkPad T', 'ThinkPad E', 'ThinkPad L', 'ThinkPad', 'ThinkBook', 'IdeaPad Slim', 'IdeaPad Gaming', 'IdeaPad', 'Yoga Slim', 'Yoga Pro', 'Yoga'],
        'DELL': ['Alienware', 'XPS', 'Precision', 'Latitude', 'Vostro', 'Inspiron', 'Gaming G15', 'Gaming G16', 'G15', 'G16'],
        'HP': ['Omen', 'Victus', 'Spectre', 'Envy', 'Pavilion Plus', 'Pavilion Aero', 'Pavilion', 'ProBook', 'EliteBook', 'HP 15s', 'HP 14s', 'HP 240', 'HP 245'],
        'MSI': ['Titan', 'Raider', 'Stealth', 'Vector', 'Crosshair', 'Katana', 'Sword', 'Cyborg', 'Pulse', 'Thin', 'Bravo', 'Modern', 'Prestige', 'Summit'],
        'APPLE': ['MacBook Pro 16', 'MacBook Pro 14', 'MacBook Pro 13', 'MacBook Pro', 'MacBook Air 15', 'MacBook Air 13', 'MacBook Air'],
        'LG': ['Gram Style', 'Gram Pro', 'Gram SuperSlim', 'Gram', 'Ultra']
    }
    
    if brand in series_dict:
        for s in series_dict[brand]:
            if re.search(r'\b' + re.escape(s) + r'\b', title_clean, re.I):
                return s
    return "Tiêu chuẩn"


def extract_category(title, series, gpu_type):
    """Phân loại phân khúc / nhu cầu sử dụng"""
    text = f"{title} {series}".upper()
    if gpu_type == "Card rời" or any(k in text for k in ['GAMING', 'ROG', 'TUF', 'LOQ', 'LEGION', 'NITRO', 'PREDATOR', 'KATANA', 'CYBORG', 'SWORD', 'VICTUS', 'OMEN', 'ALIENWARE', 'BRAVO']):
        return "Gaming"
    if any(k in text for k in ['WORKSTATION', 'PRECISION', 'PROART', 'STUDIO', 'CREATOR']):
        return "Đồ họa / Kỹ thuật"
    if any(k in text for k in ['THINKPAD', 'LATITUDE', 'ELITEBOOK', 'EXPERTBOOK', 'PROBOOK', 'VOSTRO']):
        return "Doanh nhân / Bền bỉ"
    return "Học tập / Văn phòng"


def extract_cpu(title, specs):
    """Trích xuất Hãng CPU, Dòng CPU và Model CPU chi tiết"""
    text = f"{specs} | {title}".upper()
    cpu_hang = "Khác"
    cpu_dong = "Khác"
    cpu_model = ""
    
    # 1. Hãng CPU
    if 'APPLE' in text or re.search(r'\bM[1-4]\b', text):
        cpu_hang = 'Apple'
    elif 'AMD' in text or 'RYZEN' in text:
        cpu_hang = 'AMD'
    elif 'INTEL' in text or 'CORE' in text or 'CELERON' in text or 'PENTIUM' in text:
        cpu_hang = 'Intel'
        
    # 2. Dòng & Model
    # Apple Silicon
    apple_match = re.search(r'\b(M[1-4])\s*(PRO|MAX|ULTRA)?\b', text)
    if apple_match:
        cpu_hang = 'Apple'
        m_ver = apple_match.group(1)
        m_tier = apple_match.group(2)
        cpu_dong = f"{m_ver} {m_tier}".strip() if m_tier else m_ver
        cpu_model = cpu_dong
        return cpu_hang, cpu_dong, cpu_model
        
    # Intel Core Ultra
    ultra_match = re.search(r'ULTRA\s*([3579])', text)
    if ultra_match:
        cpu_hang = 'Intel'
        cpu_dong = f"Core Ultra {ultra_match.group(1)}"
        # Tìm model đuôi dạng 125H, 155H, 228V, 255H...
        model_m = re.search(r'(?:ULTRA\s*[3579][^\n|]*?)(?:[-–—\s]+)?([0-9]{3,4}[A-Z]{0,2})\b', text)
        if model_m and model_m.group(1) not in ['3', '5', '7', '9']:
            cpu_model = model_m.group(1)
        else:
            # Tìm trong ngoặc đơn ở title
            title_m = re.search(r'\b(?:ULTRA\s*[3579][\s\-]+)?([0-9]{3,4}[A-Z]{1,2})\b', title.upper())
            if title_m:
                cpu_model = title_m.group(1)
        return cpu_hang, cpu_dong, cpu_model

    # Intel Core i (e.g. i5-13420H, i7 13620H, i9-14900HX)
    core_match = re.search(r'\bI([3579])[\s\-]+([0-9]{4,5}[A-Z]{0,2})\b', text)
    if core_match:
        cpu_hang = 'Intel'
        cpu_dong = f"Core i{core_match.group(1)}"
        cpu_model = core_match.group(2)
        return cpu_hang, cpu_dong, cpu_model
        
    # Intel Core (Series 1: Core 3 100U, Core 5 120U, Core 7 150U)
    core_gen1_match = re.search(r'\bCORE\s*([357])[\s\-]+([0-9]{3,4}[A-Z]{0,2})\b', text)
    if core_gen1_match:
        cpu_hang = 'Intel'
        cpu_dong = f"Core {core_gen1_match.group(1)}"
        cpu_model = core_gen1_match.group(2)
        return cpu_hang, cpu_dong, cpu_model

    # AMD Ryzen
    ryzen_match = re.search(r'RYZEN\s*(?:AI\s*)?([3579])', text)
    if ryzen_match:
        cpu_hang = 'AMD'
        prefix = "Ryzen AI" if 'RYZEN AI' in text else "Ryzen"
        cpu_dong = f"{prefix} {ryzen_match.group(1)}"
        model_m = re.search(r'RYZEN\s*(?:AI\s*)?[3579][^\n|]*?([0-9]{3,4}[A-Z]{0,2})\b', text)
        if model_m:
            cpu_model = model_m.group(1)
        return cpu_hang, cpu_dong, cpu_model

    return cpu_hang, cpu_dong, cpu_model


def extract_ram(title, specs):
    """Trích xuất Dung lượng RAM (GB), Chuẩn RAM và Khả năng nâng cấp"""
    text = f"{specs} | {title}".upper()
    ram_gb = None
    ram_loai = "DDR4/DDR5"
    ram_nang_cap = "Nâng cấp được"
    
    # 1. Tìm RAM: 16 GB trong specs
    ram_spec_match = re.search(r'(?:RAM|BỘ NHỚ)[:\s]*([0-9]{1,2})\s*GB', text)
    if ram_spec_match:
        ram_gb = int(ram_spec_match.group(1))
    else:
        # Tìm /16GB/ trong title
        title_ram = re.search(r'[/_\-\s]([48]|16|24|32|64)GB[/_\-\s]', text)
        if title_ram:
            ram_gb = int(title_ram.group(1))
        else:
            any_gb = re.search(r'\b([48]|16|24|32|64)\s*GB\b', text)
            if any_gb:
                ram_gb = int(any_gb.group(1))
                
    # Chuẩn RAM
    for l in ['LPDDR5X', 'LPDDR5', 'DDR5', 'LPDDR4X', 'DDR4']:
        if l in text:
            ram_loai = l
            break
            
    # Khả năng nâng cấp
    if any(k in text for k in ['ONBOARD', 'ON-BOARD', 'ON BOARD', 'HÀN CHẾT', 'KHÔNG HỖ TRỢ NÂNG CẤP', 'KHÔNG NÂNG CẤP']):
        ram_nang_cap = "Onboard"
        
    return ram_gb or 16, ram_loai, ram_nang_cap


def extract_storage(title, specs):
    """Trích xuất Loại ổ cứng (SSD/HDD) và Dung lượng (GB)"""
    text = f"{specs} | {title}".upper()
    o_cung_loai = "SSD"
    o_cung_gb = 512
    
    # Lấy vùng ổ cứng riêng biệt để tránh ăn vào 'tối đa 2TB'
    storage_match = re.search(r'(?:Ổ CỨNG|LƯU TRỮ|STORAGE)[:\s]*([^\n|]+)', text)
    if storage_match:
        storage_section = storage_match.group(1)
        storage_section = re.split(r'TỐI ĐA|NÂNG CẤP|LẮP THANH|THÁO RA', storage_section)[0]
    else:
        storage_section = text
        
    tb_match = re.search(r'\b([1-4])\s*TB\b', storage_section)
    if tb_match:
        o_cung_gb = int(tb_match.group(1)) * 1024
    else:
        gb_match = re.search(r'\b(128|256|512)\s*GB\b', storage_section)
        if gb_match:
            o_cung_gb = int(gb_match.group(1))
        else:
            title_match = re.search(r'[/_\-\s](128GB|256GB|512GB|1TB|2TB)[/_\-\s]', text)
            if title_match:
                val = title_match.group(1)
                if 'TB' in val:
                    o_cung_gb = int(val.replace('TB', '')) * 1024
                else:
                    o_cung_gb = int(val.replace('GB', ''))
                    
    return o_cung_loai, o_cung_gb


def extract_gpu(title, specs):
    """Trích xuất Loại GPU (Card rời/Onboard) và Tên GPU cụ thể"""
    text = f"{specs} | {title}".upper()
    
    # RTX series
    rtx_match = re.search(r'\b(?:GEFORCE\s*)?RTX[™\s]*([2345]0[0-9]{2}(?:\s*TI)?)\b', text)
    if rtx_match:
        return "Card rời", f"RTX {rtx_match.group(1).strip()}"
        
    # GTX series
    gtx_match = re.search(r'\b(?:GEFORCE\s*)?GTX[™\s]*(16[56]0(?:\s*TI)?)\b', text)
    if gtx_match:
        return "Card rời", f"GTX {gtx_match.group(1).strip()}"
        
    # Radeon RX rời
    rx_match = re.search(r'\b(RX\s*[67][0-9]{3}[A-Z]?)\b', text)
    if rx_match:
        return "Card rời", rx_match.group(1).strip()
        
    # MX series
    mx_match = re.search(r'\b(MX\s*[345][50]0)\b', text)
    if mx_match:
        return "Card rời", mx_match.group(1).strip()
        
    # Onboard
    if 'ARC GRAPHICS' in text or 'INTEL ARC' in text:
        return "Onboard", "Intel Arc Graphics"
    if 'IRIS XE' in text:
        return "Onboard", "Intel Iris Xe"
    if 'UHD' in text:
        return "Onboard", "Intel UHD Graphics"
    if 'RADEON' in text:
        return "Onboard", "AMD Radeon Graphics"
    if 'APPLE' in text or re.search(r'\bM[1-4]\b', text):
        return "Onboard", "Apple GPU"
        
    return "Onboard", "Tích hợp"


def extract_screen(title, specs):
    """Trích xuất Kích thước màn hình (inch), Độ phân giải và Tần số quét (Hz)"""
    text = f"{specs} | {title}".upper()
    
    screen_match = re.search(r'(?:MÀN HÌNH|KÍCH THƯỚC MÀN HÌNH|DISPLAY)[:\s]*([^\n|]+)', text)
    screen_section = screen_match.group(1) if screen_match else text
        
    # Kích thước Inch
    inch_match = re.search(r'\b(1[3-7](?:\.[0-9])?)\s*(?:["”]|INCH|INCHES|-INCH)?\b', screen_section)
    if not inch_match:
        inch_match = re.search(r'\b(1[3-7](?:\.[0-9])?)\s*(?:["”]|INCH|INCHES|-INCH)?\b', text)
    man_hinh_inch = float(inch_match.group(1)) if inch_match else 14.0
    
    # Tần số quét (Hz)
    hz_match = re.search(r'\b(60|90|120|144|165|240|300|360)\s*HZ\b', text)
    tan_so_quet = int(hz_match.group(1)) if hz_match else 60
    
    # Độ phân giải
    do_phan_giai = "FHD"
    if any(k in text for k in ['4K', '3840 X 2160', '3840X2160']):
        do_phan_giai = "4K UHD"
    elif any(k in text for k in ['2.8K', '2880 X 1800', '2880X1800', '2880 X 1920']):
        do_phan_giai = "2.8K"
    elif any(k in text for k in ['2.5K', 'WQXGA', '2560 X 1600', '2560X1600']):
        do_phan_giai = "2.5K WQXGA"
    elif any(k in text for k in ['2K', 'QHD', '2560 X 1440', '2560X1440']):
        do_phan_giai = "2K QHD"
    elif any(k in text for k in ['WUXGA', 'FULL HD+', 'FHD+', '1920 X 1200', '1920X1200']):
        do_phan_giai = "FHD+ (16:10)"
    elif any(k in text for k in ['FULL HD', 'FHD', '1920 X 1080', '1920X1080']):
        do_phan_giai = "FHD"
    elif any(k in text for k in ['HD', '1366 X 768']):
        do_phan_giai = "HD"
    else:
        if 'WUXGA' in title.upper():
            do_phan_giai = "FHD+ (16:10)"
        elif 'FHD' in title.upper():
            do_phan_giai = "FHD"
            
    if 'OLED' in text:
        do_phan_giai += " OLED"
        
    return man_hinh_inch, do_phan_giai, tan_so_quet


# ==========================================================
# HÀM XỬ LÝ CHÍNH: TRANSFORM TOÀN BỘ DATAFRAME
# ==========================================================

def clean_dataframe(df):
    """Áp dụng toàn bộ quy tắc làm sạch lên DataFrame"""
    print(f"🧹 Bắt đầu xử lý {len(df)} dòng dữ liệu...")
    
    # Chuẩn hóa tên cột viết thường và thay khoảng trắng bằng gạch dưới
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    
    # Map mọi biến thể tên cột tiếng Việt có dấu về chuẩn không dấu
    col_map = {
        'giá_hiện_tại': 'gia_hien_tai',
        'giá_gốc': 'gia_goc',
        'giảm_giá': 'giam_gia',
        'tên_sản_phẩm': 'ten_san_pham',
        'cấu_hình_chi_tiết': 'cau_hinh_chi_tiet',
        'khuyến_mãi': 'khuyen_mai',
        'quà_tặng_/_ghi_chú': 'khuyen_mai',
        'link_sản_phẩm': 'link_san_pham',
        'url': 'link_san_pham',
        'ngày_giờ_crawl': 'ngay_gio_crawl',
        'ngày_thu_thập': 'ngay_gio_crawl'
    }
    df = df.rename(columns=col_map)
    
    if 'ten_san_pham' not in df.columns:
        df['ten_san_pham'] = ''
    if 'cau_hinh_chi_tiet' not in df.columns:
        df['cau_hinh_chi_tiet'] = ''
    if 'nguon' not in df.columns:
        df['nguon'] = 'KHAC'
        
    cleaned_rows = []
    
    for idx, row in df.iterrows():
        title = str(row.get('ten_san_pham', '')).strip()
        specs = str(row.get('cau_hinh_chi_tiet', ''))
        if specs.lower() == 'nan':
            specs = ""
            
        nguon = str(row.get('nguon', 'KHAC')).upper()
        link = str(row.get('link_san_pham', row.get('url', '')))
        khuyen_mai = str(row.get('khuyen_mai', row.get('quà_tặng_/_ghi_chú', '')))
        if khuyen_mai.lower() == 'nan':
            khuyen_mai = ""
            
        # Giá tiền
        raw_price = row.get('gia_hien_tai', None)
        raw_orig_price = row.get('gia_goc', None)
        gia_hien_tai = clean_price(raw_price)
        gia_goc = clean_price(raw_orig_price)
        
        # Xử lý ngoại lệ giá gốc < giá hiện tại
        if gia_goc and gia_hien_tai and gia_goc < gia_hien_tai:
            if nguon == 'XGEAR' and gia_goc >= 5_000_000:
                # XGEAR trước đây bị đảo ngược giữa giá gốc và giá bán
                gia_hien_tai, gia_goc = gia_goc, gia_hien_tai
            else:
                # Bắt nhầm giá quà tặng / voucher / giá ưu đãi thanh toán -> bỏ giá gốc
                gia_goc = None

        # % Giảm giá
        phan_tram_giam = 0.0
        if gia_goc and gia_hien_tai and gia_goc > gia_hien_tai:
            phan_tram_giam = round((gia_goc - gia_hien_tai) / gia_goc * 100, 1)
            
        # Bóc tách thông số
        brand = extract_brand(title)
        series = extract_series(title, brand)
        cpu_hang, cpu_dong, cpu_model = extract_cpu(title, specs)
        ram_gb, ram_loai, ram_nang_cap = extract_ram(title, specs)
        o_cung_loai, o_cung_gb = extract_storage(title, specs)
        gpu_loai, gpu_ten = extract_gpu(title, specs)
        man_hinh_inch, do_phan_giai, tan_so_quet = extract_screen(title, specs)
        nhu_cau = extract_category(title, series, gpu_loai)
        
        ngay_crawl = row.get('ngay_gio_crawl', row.get('ngày_thu_thập', ''))
        
        cleaned_rows.append({
            'nguon': nguon,
            'hang': brand,
            'dong_may': series,
            'ten_san_pham': title,
            'nhu_cau': nhu_cau,
            'gia_hien_tai': gia_hien_tai,
            'gia_goc': gia_goc,
            'phan_tram_giam': phan_tram_giam,
            'cpu_hang': cpu_hang,
            'cpu_dong': cpu_dong,
            'cpu_model': cpu_model,
            'ram_gb': ram_gb,
            'ram_loai': ram_loai,
            'ram_nang_cap': ram_nang_cap,
            'o_cung_loai': o_cung_loai,
            'o_cung_gb': o_cung_gb,
            'gpu_loai': gpu_loai,
            'gpu_ten': gpu_ten,
            'man_hinh_inch': man_hinh_inch,
            'do_phan_giai': do_phan_giai,
            'tan_so_quet_hz': tan_so_quet,
            'khuyen_mai': khuyen_mai,
            'link_san_pham': link,
            'ngay_gio_crawl': ngay_crawl
        })
        
    clean_df = pd.DataFrame(cleaned_rows)
    print(f"✅ Đã làm sạch xong {len(clean_df)} dòng dữ liệu!")
    return clean_df


# ==========================================================
# PIPELINE CHÍNH: CHẠY QUA DATABASE HOẶC FILE EXCEL
# ==========================================================

def run_cleaning_pipeline(source_file=None):
    """
    Chạy quy trình làm sạch:
    - Nếu source_file được truyền vào: Đọc file Excel và xuất ra file Excel sạch.
    - Mặc định: Kết nối PostgreSQL, đọc raw_laptop_data và lưu vào clean_laptop_data.
    """
    clean_df = None
    
    # TRƯỜNG HỢP 1: CHẠY TRỰC TIẾP TỪ FILE EXCEL (OFFLINE / TEST MODE)
    if source_file and os.path.exists(source_file):
        print(f"📂 Đang đọc dữ liệu từ file Excel: {source_file}")
        xls = pd.ExcelFile(source_file)
        all_dfs = []
        for sheet in xls.sheet_names:
            if sheet.lower() == 'dataclean':
                continue
            df_sheet = xls.parse(sheet)
            df_sheet['nguon'] = sheet.upper()
            all_dfs.append(df_sheet)
            print(f"  - Sheet {sheet}: {len(df_sheet)} dòng")
            
        merged_raw = pd.concat(all_dfs, ignore_index=True)
        clean_df = clean_dataframe(merged_raw)
        
        out_excel = "laptop_clean_data.xlsx"
        clean_df.to_excel(out_excel, index=False)
        print(f"🎉 Đã lưu kết quả làm sạch ra file: {out_excel}")
        return clean_df
        
    # TRƯỜNG HỢP 2: KẾT NỐI POSTGRESQL (PRODUCTION PIPELINE)
    try:
        conn_str = f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
        engine = create_engine(conn_str)
        print(f"🔌 Kết nối tới PostgreSQL ({DB_HOST}:{DB_PORT}/{DB_NAME})...")
        
        # Đọc dữ liệu từ bảng raw
        raw_df = pd.read_sql('SELECT * FROM raw_laptop_data', engine)
        if raw_df.empty:
            print("⚠️ Bảng raw_laptop_data chưa có dữ liệu!")
            return None
            
        print(f"📥 Đã lấy {len(raw_df)} dòng từ bảng raw_laptop_data.")
        clean_df = clean_dataframe(raw_df)
        
        # Lưu vào bảng clean_laptop_data (replace để làm mới bảng báo cáo)
        print("💾 Đang ghi vào bảng clean_laptop_data...")
        clean_df.to_sql('clean_laptop_data', engine, if_exists='replace', index=False)
        print("🎉 GHI THÀNH CÔNG VÀO BẢNG clean_laptop_data TRONG DATABASE!")
        
        # Đồng thời lưu 1 bản snapshot Excel để tiện kiểm tra
        clean_df.to_excel("laptop_clean_snapshot.xlsx", index=False)
        return clean_df
        
    except Exception as e:
        print(f"⚠️ Không thể kết nối Database ({e}). Đang chuyển sang chế độ đọc file Excel cục bộ...")
        if os.path.exists("data laptop.xlsx"):
            return run_cleaning_pipeline("data laptop.xlsx")
        else:
            print("❌ Không tìm thấy file 'data laptop.xlsx' để chạy dự phòng.")
            return None


if __name__ == "__main__":
    # Nếu người dùng truyền tham số file (ví dụ: python clean_data.py "data laptop.xlsx")
    target_file = sys.argv[1] if len(sys.argv) > 1 else None
    run_cleaning_pipeline(target_file)
