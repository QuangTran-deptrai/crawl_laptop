import pandas as pd
import os
import glob

def merge_chunks():
    # Các trang web cần gộp
    stores = ["fptshop", "phongvu", "tgdd", "cellphones", "gearvn"]
    
    for store in stores:
        print(f"=== Đang gộp dữ liệu cho {store.upper()} ===")
        # Tìm tất cả file chunk của store này
        pattern = f"laptop_{store}_chunk_*.xlsx"
        chunk_files = glob.glob(pattern)
        
        if not chunk_files:
            print(f"Không tìm thấy file chunk nào cho {store}.")
            continue
            
        print(f"Tìm thấy {len(chunk_files)} mảnh: {chunk_files}")
        
        all_data = []
        for file in chunk_files:
            try:
                df = pd.read_excel(file)
                all_data.append(df)
            except Exception as e:
                print(f"Lỗi đọc file {file}: {e}")
                
        if all_data:
            # Nối tất cả dữ liệu
            merged_df = pd.concat(all_data, ignore_index=True)
            # Xóa dòng trùng lặp (nếu có, dựa vào URL/Link)
            # URL column có thể là 'URL' hoặc 'Link Sản Phẩm'
            if 'URL' in merged_df.columns:
                merged_df = merged_df.drop_duplicates(subset=['URL'])
            elif 'Link Sản Phẩm' in merged_df.columns:
                merged_df = merged_df.drop_duplicates(subset=['Link Sản Phẩm'])
                
            output_file = f"laptop_{store}_all.xlsx"
            merged_df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"✅ Đã gộp thành công {len(merged_df)} laptop vào {output_file}")
            
            # Xóa các file chunk rác
            for file in chunk_files:
                os.remove(file)
            print(f"Đã dọn dẹp {len(chunk_files)} file chunk rác.")
        print("-" * 40)

if __name__ == "__main__":
    merge_chunks()
