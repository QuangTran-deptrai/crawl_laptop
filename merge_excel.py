import pandas as pd
import os

def merge_excel_files():
    # Các file cần merge
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
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                print(f"Merged sheet: {sheet_name} ({len(df)} products)")
            else:
                print(f"Warning: File not found {file_name}")
                
    print(f"\nDone! Data is merged into '{output_file}'")

if __name__ == "__main__":
    merge_excel_files()
