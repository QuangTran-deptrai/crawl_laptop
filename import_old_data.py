import pandas as pd
import numpy as np
import os
import sys
import argparse
from sqlalchemy import create_engine
import re

# Fix lỗi mã hóa font / emoji trên Windows console (cp1252 / cp1258)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Import bộ xử lý làm sạch từ clean_data nếu muốn tạo luôn bảng sạch
try:
    from clean_data import clean_dataframe
except ImportError:
    clean_dataframe = None

def clean_price(val):
    if pd.isna(val):
        return None
    if isinstance(val, (int, float, np.integer, np.floating)):
        try:
            return int(val)
        except:
            return None
    val_str = str(val).strip()
    if val_str.endswith('.0'):
        val_str = val_str[:-2]
    digits = re.sub(r'[^\d]', '', val_str)
    if digits:
        try:
            return int(digits)
        except:
            return None
    return None

def import_old_data(excel_path="data laptop.xlsx", db_host="localhost", db_port="5432", 
                    db_name="laptop_db", db_user="postgres", db_pass="123456", 
                    auto_clean=True):
    if not os.path.exists(excel_path):
        print(f"❌ Không tìm thấy file: {excel_path}")
        return

    print("=" * 60)
    print(f"📂 Đang đọc dữ liệu lịch sử từ file: {excel_path}")
    print(f"🎯 Mục tiêu: PostgreSQL tại {db_host}:{db_port}/{db_name}")
    print("=" * 60)

    xls = pd.ExcelFile(excel_path)
    all_dfs = []

    column_mapping = {
        'tên_sản_phẩm': 'ten_san_pham',
        'cấu_hình_chi_tiết': 'cau_hinh_chi_tiet',
        'giá_hiện_tại': 'gia_hien_tai',
        'giá_gốc': 'gia_goc',
        'giảm_giá': 'giam_gia',
        'khuyến_mãi': 'khuyen_mai',
        'quà_tặng_/_ghi_chú': 'khuyen_mai',
        'link_sản_phẩm': 'link_san_pham',
        'url': 'link_san_pham',
        'ngày_cập_nhật_(sitemap)': 'ngay_cap_nhat_sitemap',
        'ngày_giờ_crawl': 'ngay_gio_crawl',
        'ngày_thu_thập': 'ngay_gio_crawl'
    }

    target_cols = [
        'nguon', 'ten_san_pham', 'cau_hinh_chi_tiet', 
        'gia_hien_tai', 'gia_goc', 'giam_gia', 'khuyen_mai', 
        'link_san_pham', 'ngay_gio_crawl'
    ]

    for sheet in xls.sheet_names:
        # Bỏ qua sheet tính toán Power Query cũ
        if sheet.lower() in ['dataclean', 'sheet1', 'summary']:
            continue
            
        print(f" Đang đọc sheet '{sheet}'...")
        df = xls.parse(sheet)
        if df.empty:
            continue

        # Chuẩn hóa tên cột
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
        
        # Xử lý gộp cột 'quà_tặng_/_ghi_chú' vào 'khuyến_mãi' để tránh trùng lặp cột khi đổi tên
        if 'quà_tặng_/_ghi_chú' in df.columns:
            if 'khuyến_mãi' in df.columns:
                df['khuyến_mãi'] = df['khuyến_mãi'].fillna('').astype(str) + ' | ' + df['quà_tặng_/_ghi_chú'].fillna('').astype(str)
                df['khuyến_mãi'] = df['khuyến_mãi'].str.strip(' |')
            else:
                df['khuyến_mãi'] = df['quà_tặng_/_ghi_chú']
            df = df.drop(columns=['quà_tặng_/_ghi_chú'])

        df = df.rename(columns=column_mapping)
        # Loại bỏ bất kỳ cột trùng tên nào còn sót lại
        df = df.loc[:, ~df.columns.duplicated()]
        
        # Gán nguồn
        df['nguon'] = sheet.upper()

        # Làm sạch giá
        if 'gia_hien_tai' in df.columns:
            df['gia_hien_tai'] = df['gia_hien_tai'].apply(clean_price)
        if 'gia_goc' in df.columns:
            df['gia_goc'] = df['gia_goc'].apply(clean_price)

        # Đảm bảo đủ các cột target chuẩn hóa trước khi append
        for col in target_cols:
            if col not in df.columns:
                df[col] = None
        df = df[target_cols]

        all_dfs.append(df)
        print(f"   -> Đã đọc {len(df)} sản phẩm từ {sheet}")

    if not all_dfs:
        print("❌ Không có dữ liệu hợp lệ để import.")
        return

    raw_df = pd.concat(all_dfs, ignore_index=True)

    print(f"\n📊 Tổng cộng {len(raw_df)} dòng dữ liệu thô sẵn sàng đẩy vào database.")

    # Kết nối Database
    conn_str = f'postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    try:
        engine = create_engine(conn_str)
        print(f"🔌 Đang kết nối tới PostgreSQL ({db_host}:{db_port})...")
        
        # 1. Đẩy vào bảng raw_laptop_data
        print(f"💾 Đang nạp vào bảng 'raw_laptop_data'...")
        raw_df.to_sql('raw_laptop_data', engine, if_exists='append', index=False)
        print(f"✅ ĐÃ NẠP THÀNH CÔNG {len(raw_df)} DÒNG VÀO BẢNG raw_laptop_data!")

        # 2. Tự động bóc tách và nạp luôn vào bảng clean_laptop_data nếu auto_clean=True
        if auto_clean and clean_dataframe:
            print("\n🧹 Đang tự động làm sạch và bóc tách thông số (CPU, RAM, GPU, Màn hình)...")
            clean_df = clean_dataframe(raw_df)
            print(f"💾 Đang nạp {len(clean_df)} dòng vào bảng 'clean_laptop_data'...")
            clean_df.to_sql('clean_laptop_data', engine, if_exists='replace', index=False)
            print(f"🎉 ĐÃ CẬP NHẬT THÀNH CÔNG BẢNG clean_laptop_data! Sẵn sàng cho Dashboard!")

    except Exception as e:
        print(f"\n❌ LỖI KẾT NỐI DATABASE: {e}")
        print("\n💡 Gợi ý xử lý:")
        print("1. Nếu chạy từ Máy A tới Máy B (10.3.1.97) bị lỗi timeout/refused:")
        print("   -> Hãy copy file này sang Máy B và chạy: python import_old_data.py --host localhost")
        print("2. Hoặc kiểm tra xem service PostgreSQL trên Máy B đã Start chưa và mật khẩu đúng là 123456 chưa.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import dữ liệu laptop cũ vào PostgreSQL")
    parser.add_argument("--file", default="data laptop.xlsx", help="Đường dẫn file Excel")
    parser.add_argument("--host", default="localhost", help="Địa chỉ host PostgreSQL (localhost hoặc 10.3.1.97)")
    parser.add_argument("--port", default="5432", help="Cổng kết nối PostgreSQL")
    parser.add_argument("--user", default="postgres", help="Tên user")
    parser.add_argument("--password", default="123456", help="Mật khẩu database")
    parser.add_argument("--db", default="laptop_db", help="Tên database")
    parser.add_argument("--no-clean", action="store_true", help="Không tự động làm sạch sau khi import")

    args = parser.parse_args()
    import_old_data(
        excel_path=args.file,
        db_host=args.host,
        db_port=args.port,
        db_name=args.db,
        db_user=args.user,
        db_pass=args.password,
        auto_clean=not args.no_clean
    )
