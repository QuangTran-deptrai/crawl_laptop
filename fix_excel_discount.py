import pandas as pd

def fix_tgdd_discount():
    # 1. Sửa file laptop_rtx3050_tgdd.xlsx
    file_tgdd = 'laptop_rtx3050_tgdd.xlsx'
    try:
        df = pd.read_excel(file_tgdd)
        
        def calc_discount(row):
            try:
                c_price = float(str(row['Giá Hiện Tại']).replace('₫', '').replace('.', '').replace(',', '').strip())
                o_price = float(str(row['Giá Gốc']).replace('₫', '').replace('.', '').replace(',', '').strip())
                if o_price > 0 and c_price < o_price:
                    return f"-{int(round((o_price - c_price) / o_price * 100))}%"
            except:
                pass
            return ""
            
        df['Giảm Giá'] = df.apply(calc_discount, axis=1)
        df.to_excel(file_tgdd, index=False, engine='openpyxl')
        print(f"Updated discount in {file_tgdd}")
    except Exception as e:
        print(f"Error updating {file_tgdd}: {e}")

    # 2. Sửa lại sheet Thế Giới Di Động trong laptop_rtx3050_all.xlsx
    file_all = 'laptop_rtx3050_all.xlsx'
    try:
        # Load tất cả các sheet
        xls = pd.ExcelFile(file_all, engine='openpyxl')
        sheets = {sheet_name: pd.read_excel(xls, sheet_name=sheet_name) for sheet_name in xls.sheet_names}
        
        if 'The Gioi Di Dong' in sheets:
            sheets['The Gioi Di Dong']['Giảm Giá'] = sheets['The Gioi Di Dong'].apply(calc_discount, axis=1)
            
            # Ghi lại toàn bộ
            with pd.ExcelWriter(file_all, engine='openpyxl') as writer:
                for sheet_name, sheet_df in sheets.items():
                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"Updated discount in sheet The Gioi Di Dong of {file_all}")
    except Exception as e:
        print(f"Error updating {file_all}: {e}")

if __name__ == "__main__":
    fix_tgdd_discount()
