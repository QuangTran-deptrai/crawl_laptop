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
            
            # Gộp quà tặng vào khuyến mãi nếu có
            if 'quà_tặng_/_ghi_chú' in df.columns:
                if 'khuyến_mãi' in df.columns:
                    df['khuyến_mãi'] = df['khuyến_mãi'].fillna('').astype(str) + ' | ' + df['quà_tặng_/_ghi_chú'].fillna('').astype(str)
                    df['khuyến_mãi'] = df['khuyến_mãi'].str.strip(' |')
                else:
                    df['khuyến_mãi'] = df['quà_tặng_/_ghi_chú']
                df = df.drop(columns=['quà_tặng_/_ghi_chú'])
            
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
        'url': 'link_san_pham',
        'ngày_giờ_crawl': 'ngay_gio_crawl',
        'ngày_thu_thập': 'ngay_gio_crawl'
    }
    
    final_df = final_df.rename(columns=column_mapping)
    final_df = final_df.loc[:, ~final_df.columns.duplicated()]

    def clean_price(val):
        if pd.isna(val):
            return None
        if isinstance(val, (int, float)):
            return int(val)
        val_str = str(val).strip()
        digits = re.sub(r'[^\d]', '', val_str)
        return int(digits) if digits else None

    if 'gia_hien_tai' in final_df.columns:
        final_df['gia_hien_tai'] = final_df['gia_hien_tai'].apply(clean_price)
    if 'gia_goc' in final_df.columns:
        final_df['gia_goc'] = final_df['gia_goc'].apply(clean_price)

    # Đảm bảo cột ngày giờ crawl luôn có giá trị (nếu rỗng thì lấy thời điểm hiện tại)
    if 'ngay_gio_crawl' not in final_df.columns:
        final_df['ngay_gio_crawl'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    else:
        final_df['ngay_gio_crawl'] = final_df['ngay_gio_crawl'].fillna(pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'))

    # 3. Kết nối PostgreSQL và Ghi dữ liệu
    try:
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        # Thay đổi user/password cho phù hợp với Máy B của bạn
        DB_USER = "postgres"
        DB_PASS = "123456" # <--- THAY ĐỔI MẬT KHẨU CỦA BẠN
        DB_HOST = "localhost"
        DB_PORT = "5432"
        DB_NAME = "laptop_db"

        # Tự động tạo database nếu chưa có
        try:
            init_conn = psycopg2.connect(dbname="postgres", user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
            init_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = init_conn.cursor()
            cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
            if not cur.fetchone():
                print(f"🛠️ Đang tự động tạo mới database '{DB_NAME}'...")
                cur.execute(f'CREATE DATABASE "{DB_NAME}"')
                print(f"✅ Đã tạo database '{DB_NAME}' thành công!")
            cur.close()
            init_conn.close()
        except Exception as err:
            print(f"⚠️ Kiểm tra database: {err}")

        # Chuỗi kết nối SQLAlchemy
        engine = create_engine(f'postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}')
        
        # Chỉ giữ lại các cột thực tế có trong bảng raw_laptop_data trong Database để tránh lỗi UndefinedColumn
        try:
            existing_cols = pd.read_sql("SELECT * FROM raw_laptop_data LIMIT 0", engine).columns.tolist()
            final_df = final_df[[c for c in final_df.columns if c in existing_cols]]
        except Exception as e_col:
            print(f"ℹ️ Không lấy được schema bảng: {e_col}")

        print(f" Đang ghi {len(final_df)} dòng vào database {DB_NAME}...")
        final_df.to_sql('raw_laptop_data', engine, if_exists='append', index=False, chunksize=1000)
        print("✅ Ghi dữ liệu thành công vào PostgreSQL!")
        
    except Exception as e:
        print(f"❌ Lỗi khi ghi vào Database: {e}")

if __name__ == "__main__":
    import_to_postgres()
