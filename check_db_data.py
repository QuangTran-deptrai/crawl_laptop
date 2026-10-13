import sys
import os
import argparse
import pandas as pd
from sqlalchemy import create_engine, text

# Fix font / emoji trên Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

def check_database(db_host="localhost", db_port="5432", db_name="laptop_db", 
                   db_user="postgres", db_pass="123456"):
    print("=" * 65)
    print(f"🔍 KIỂM TRA DỮ LIỆU TRONG DATABASE: {db_name} ({db_host}:{db_port})")
    print("=" * 65)

    conn_str = f'postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}'
    try:
        engine = create_engine(conn_str)
        with engine.connect() as conn:
            # 1. Kiểm tra danh sách các bảng đang có
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [row[0] for row in conn.execute(tables_query).fetchall()]
            print(f"📋 Các bảng hiện có trong database: {tables}")

            if not tables:
                print("⚠️ Database rỗng, chưa có bảng nào được tạo.")
                return

            # 2. Kiểm tra bảng raw_laptop_data
            if 'raw_laptop_data' in tables:
                print("\n" + "-" * 60)
                print("🗄️ BẢNG 1: raw_laptop_data (Dữ liệu thô)")
                print("-" * 60)
                count_raw = conn.execute(text("SELECT COUNT(*) FROM raw_laptop_data")).scalar()
                print(f"👉 Tổng số dòng: {count_raw:,} sản phẩm")

                # Thống kê theo nguồn
                store_stats = conn.execute(text("""
                    SELECT nguon, COUNT(*) as so_luong,
                           COUNT(gia_hien_tai) as co_gia
                    FROM raw_laptop_data 
                    GROUP BY nguon 
                    ORDER BY so_luong DESC;
                """)).fetchall()
                print("   Phân bổ theo từng nguồn:")
                for s in store_stats:
                    print(f"   - {s[0]}: {s[1]:,} máy (có giá: {s[2]:,} máy)")

            # 3. Kiểm tra bảng clean_laptop_data
            if 'clean_laptop_data' in tables:
                print("\n" + "-" * 60)
                print("✨ BẢNG 2: clean_laptop_data (Dữ liệu đã làm sạch & bóc tách)")
                print("-" * 60)
                count_clean = conn.execute(text("SELECT COUNT(*) FROM clean_laptop_data")).scalar()
                print(f"👉 Tổng số dòng: {count_clean:,} sản phẩm")

                # Thống kê theo Hãng
                brand_stats = conn.execute(text("""
                    SELECT hang, COUNT(*) as so_luong 
                    FROM clean_laptop_data 
                    GROUP BY hang 
                    ORDER BY so_luong DESC 
                    LIMIT 6;
                """)).fetchall()
                print("\n   Top Hãng sản xuất:")
                for b in brand_stats:
                    print(f"   - {b[0]}: {b[1]:,} máy")

                # Thống kê theo Phân khúc / Nhu cầu
                cat_stats = conn.execute(text("""
                    SELECT nhu_cau, COUNT(*) as so_luong 
                    FROM clean_laptop_data 
                    GROUP BY nhu_cau 
                    ORDER BY so_luong DESC;
                """)).fetchall()
                print("\n   Phân bổ theo Nhu cầu sử dụng:")
                for c in cat_stats:
                    print(f"   - {c[0]}: {c[1]:,} máy")

                # Thống kê giá bán
                price_stats = conn.execute(text("""
                    SELECT MIN(gia_hien_tai), AVG(gia_hien_tai), MAX(gia_hien_tai)
                    FROM clean_laptop_data
                    WHERE gia_hien_tai IS NOT NULL AND gia_hien_tai > 0;
                """)).fetchone()
                if price_stats and price_stats[0]:
                    print(f"\n   Giá bán thấp nhất : {int(price_stats[0]):,} VNĐ")
                    print(f"   Giá bán trung bình: {int(price_stats[1]):,} VNĐ")
                    print(f"   Giá bán cao nhất  : {int(price_stats[2]):,} VNĐ")

                # Xem thử 2 dòng mẫu
                print("\n   Mẫu 2 sản phẩm cấu hình đã bóc tách:")
                sample_df = pd.read_sql("""
                    SELECT nguon, hang, dong_may, cpu_hang, cpu_dong, ram_gb, gpu_ten, gia_hien_tai
                    FROM clean_laptop_data
                    LIMIT 2;
                """, conn)
                print(sample_df.to_string(index=False))

            print("\n" + "=" * 65)
            print("🎉 KIỂM TRA HOÀN TẤT! DỮ LIỆU ĐÃ SẴN SÀNG.")
            print("=" * 65)

    except Exception as e:
        print(f"\n❌ LỖI KẾT NỐI DATABASE: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kiểm tra dữ liệu trong database PostgreSQL")
    parser.add_argument("--host", default="localhost", help="Địa chỉ host PostgreSQL")
    parser.add_argument("--port", default="5432", help="Cổng kết nối")
    parser.add_argument("--user", default="postgres", help="Tên user")
    parser.add_argument("--password", default="123456", help="Mật khẩu")
    parser.add_argument("--db", default="laptop_db", help="Tên database")

    args = parser.parse_args()
    check_database(
        db_host=args.host,
        db_port=args.port,
        db_name=args.db,
        db_user=args.user,
        db_pass=args.password
    )
