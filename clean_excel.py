import pandas as pd

def clean_excel():
    file_all = 'laptop_rtx3050_all.xlsx'
    
    try:
        # Đọc tất cả các sheet
        xls = pd.ExcelFile(file_all, engine='openpyxl')
        sheets = {sheet_name: pd.read_excel(xls, sheet_name=sheet_name) for sheet_name in xls.sheet_names}
        
        with pd.ExcelWriter(file_all, engine='openpyxl') as writer:
            for sheet_name, df in sheets.items():
                # 1. Bỏ cột "Giảm Giá"
                if 'Giảm Giá' in df.columns:
                    df = df.drop(columns=['Giảm Giá'])
                
                # 2. Bỏ chữ "đ", "₫", "Đ" trong các cột giá
                for col in ['Giá Hiện Tại', 'Giá Gốc']:
                    if col in df.columns:
                        # Đảm bảo xử lý dạng string
                        df[col] = df[col].astype(str).str.replace('₫', '', regex=False) \
                                                     .str.replace('đ', '', regex=False) \
                                                     .str.replace('Đ', '', regex=False) \
                                                     .str.strip()
                        # Thay 'nan' (do Pandas chuyển từ NaN) thành trống
                        df[col] = df[col].replace('nan', '')

                # Ghi đè vào sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Cleaned sheet: {sheet_name}")
                
        print(f"Successfully updated '{file_all}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    clean_excel()
