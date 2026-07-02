import pandas as pd

df = pd.read_excel('laptop_rtx3050_cellphones.xlsx')
with open('debug_excel_output.txt', 'w', encoding='utf-8') as f:
    f.write("Total products: " + str(len(df)) + "\n")
    for idx, row in df.head(3).iterrows():
        f.write(f"\n[{idx}] {row['Tên Sản Phẩm']}\n")
        f.write(f"Khuyến mãi: {row['Khuyến Mãi']}\n")
        f.write(f"Giá: {row['Giá Hiện Tại']}\n")
        f.write(f"Cấu hình: {row['Cấu Hình Chi Tiết']}\n")
