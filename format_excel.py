import pandas as pd
import numpy as np

def format_excel_numbers():
    file_all = 'laptop_rtx3050_all.xlsx'
    
    try:
        # Đọc tất cả các sheet
        xls = pd.ExcelFile(file_all, engine='openpyxl')
        sheets = {sheet_name: pd.read_excel(xls, sheet_name=sheet_name) for sheet_name in xls.sheet_names}
        
        with pd.ExcelWriter(file_all, engine='openpyxl') as writer:
            for sheet_name, df in sheets.items():
                
                # 1. Chuyển đổi chuỗi thành số nguyên chuẩn
                for col in ['Giá Hiện Tại', 'Giá Gốc']:
                    if col in df.columns:
                        def to_number(x):
                            try:
                                # Xóa dấu chấm/phẩy phân cách hàng nghìn cũ
                                val = str(x).replace('.', '').replace(',', '').strip()
                                if not val or val.lower() == 'nan':
                                    return np.nan
                                return float(val)
                            except:
                                return np.nan
                        
                        df[col] = df[col].apply(to_number)

                # Ghi dữ liệu vào sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # 2. Định dạng cột tiền tệ hiển thị dấu phẩy trong Excel
                worksheet = writer.sheets[sheet_name]
                for col_idx, col_name in enumerate(df.columns, 1):
                    if col_name in ['Giá Hiện Tại', 'Giá Gốc']:
                        for row_idx in range(2, len(df) + 2):
                            cell = worksheet.cell(row=row_idx, column=col_idx)
                            # Định dạng number có dấu phẩy ngăn cách hàng nghìn (#,##0)
                            cell.number_format = '#,##0'
                            
                print(f"Formatted sheet: {sheet_name}")
                
        print(f"Successfully formatted numbers in '{file_all}'")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    format_excel_numbers()
