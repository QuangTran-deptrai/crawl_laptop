import pandas as pd
import glob
import os
from sqlalchemy import create_engine
import psycopg2

def import_to_postgres():
    # 1. Thu thập tất cả các file Excel đã gộp từ chunk_merger.py
    files = glob.glob("laptop_*_all.xlsx")
    if not files:
        print("Không tìm thấy file Excel nào để import vào Database!")
        return

    print(f"Bắt đầu import {len(files)} file vào PostgreSQL...")
    
    # Đọc và gộp tất cả data
    all_data = []
    for file in files:
        # Lấy tên store từ tên file (ví dụ: laptop_tgdd_all.xlsx -> tgdd)
        store_name = file.split('_')[1].upper()
        
        try:
            df = pd.read_excel(file)
            # Chuẩn hóa tên cột để khớp với SQL Table (viết thường, thay khoảng trắng bằng gạch dưới)
            df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
            
            # Đảm bảo có cột 'nguon'
            if 'nguon' not in df.columns:
                df['nguon'] = store_name
                
            all_data.append(df)
            print(f" Đã đọc {len(df)} dòng từ {file}")
        except Exception as e:
            print(f" Lỗi khi đọc file {file}: {e}")
            
    if not all_data:
        return
        
    final_df = pd.concat(all_data, ignore_index=True)
    
    # 2. Xử lý đổi tên cột cho đúng chuẩn Database
    # Map các cột từ Excel sang SQL (dựa theo schema raw_laptop_data)
    column_mapping = {
        'nguon': 'nguon',
        'tên_sản_phẩm': 'ten_san_pham',
        'cấu_hình_chi_tiết': 'cau_hinh_chi_tiet',
        'giá_hiện_tại': 'gia_hien_tai',
        'giá_gốc': 'gia_goc',
        'giảm_giá': 'giam_gia',
        'khuyến_mãi': 'khuyen_mai',
        'link_sản_phẩm': 'link_san_pham',
        'url': 'link_san_pham', # Đề phòng một số web đặt tên là URL
        'ngày_cập_nhật_(sitemap)': 'ngay_cap_nhat_sitemap',
        'ngày_giờ_crawl': 'ngay_gio_crawl'
    }
    
    # Chỉ giữ lại các cột có trong database
    final_df = final_df.rename(columns=column_mapping)
    available_cols = [col for col in final_df.columns if col in column_mapping.values()]
    final_df = final_df[available_cols]

    # 3. Kết nối PostgreSQL và Ghi dữ liệu
    try:
        # Thay đổi user/password cho phù hợp với Máy B của bạn
        DB_USER = "postgres"
        DB_PASS = "123456" # <--- THAY ĐỔI MẬT KHẨU CỦA BẠN
        DB_HOST = "localhost"
        DB_PORT = "5432"
        DB_NAME = "laptop_db"

        # Chuỗi kết nối SQLAlchemy
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
        
        # Cập nhật: Trước khi chèn, có thể bạn muốn xóa data cũ hoặc append data mới.
        # Ở đây dùng 'append' để giữ lịch sử, hoặc 'replace' nếu bạn muốn làm mới mỗi ngày.
        print(f" Đang ghi {len(final_df)} dòng vào database {DB_NAME}...")
        final_df.to_sql('raw_laptop_data', engine, if_exists='append', index=False)
        print("✅ Ghi dữ liệu thành công vào PostgreSQL!")
        
    except Exception as e:
        print(f"❌ Lỗi khi ghi vào Database: {e}")

if __name__ == "__main__":
    import_to_postgres()
