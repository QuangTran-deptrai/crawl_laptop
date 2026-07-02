import pandas as pd
import numpy as np
import os

def create_final_excel():
    files = {
        "CellphoneS": "laptop_rtx3050_cellphones.xlsx",
        "FPT Shop": "laptop_rtx3050_fptshop.xlsx",
        "GearVN": "laptop_rtx3050_gearvn.xlsx",
        "Phong Vu": "laptop_rtx3050_phongvu.xlsx",
        "The Gioi Di Dong": "laptop_rtx3050_tgdd.xlsx"
    }
    
    output_file = "laptop_rtx3050_all.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        for sheet_name, file_name in files.items():
            if os.path.exists(file_name):
                df = pd.read_excel(file_name)
                
                # 1. Bỏ cột Giảm Giá
                if 'Giảm Giá' in df.columns:
                    df = df.drop(columns=['Giảm Giá'])
                
                # 2. Làm sạch và format cột giá
                for col in ['Giá Hiện Tại', 'Giá Gốc']:
                    if col in df.columns:
                        def to_number(x):
                            if pd.isna(x):
                                return np.nan
                            
                            # Nếu đã là số nguyên/thực, trả về luôn để tránh lỗi thêm số 0
                            if isinstance(x, (int, float)):
                                return float(x)
                                
                            val = str(x).strip()
                            # Loại bỏ đơn vị tiền tệ
                            for char in ['₫', 'đ', 'Đ', '*']:
                                val = val.replace(char, '')
                            val = val.strip()
                            
                            # Vì tiền tệ Việt Nam (VND) ở đây không có số thập phân lẻ 
                            # nên tất cả dấu '.' và ',' đều là phân cách hàng nghìn.
                            val = val.replace('.', '').replace(',', '')
                            
                            if not val or val.lower() == 'nan':
                                return np.nan
                            try:
                                return float(val)
                            except:
                                return np.nan
                                
                        df[col] = df[col].apply(to_number)
                
                # Ghi vào excel
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Format hiển thị
                worksheet = writer.sheets[sheet_name]
                for col_idx, col_name in enumerate(df.columns, 1):
                    if col_name in ['Giá Hiện Tại', 'Giá Gốc']:
                        for row_idx in range(2, len(df) + 2):
                            cell = worksheet.cell(row=row_idx, column=col_idx)
                            cell.number_format = '#,##0'
                            
                print(f"Processed: {sheet_name}")
            else:
                print(f"File not found: {file_name}")
                
    print(f"\nDone! Completely regenerated '{output_file}' with correct numbers.")

if __name__ == "__main__":
    create_final_excel()
