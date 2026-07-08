import os
import json
import httpx
import asyncio
import openpyxl
from dotenv import load_dotenv

load_dotenv()

# Danh sách các file Excel và Tên Sheet tương ứng trên Google Sheets
FILES_TO_SYNC = [
    {"file": "laptop_fptshop_all.xlsx", "sheet_name": "FPTShop"},
    {"file": "laptop_tgdd_all.xlsx", "sheet_name": "TGDĐ"},
    {"file": "laptop_cellphones_all.xlsx", "sheet_name": "CellphoneS"},
    {"file": "laptop_phongvu_all.xlsx", "sheet_name": "PhongVu"},
    {"file": "laptop_gearvn_all.xlsx", "sheet_name": "GearVN"},
]

async def send_telegram_msg(message: str):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Bỏ qua gửi Telegram do thiếu cấu hình.")
        return
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10.0)
    except Exception as e:
        print(f"Lỗi khi gửi Telegram: {e}")

async def upload_existing_data():
    webhook_url = os.getenv("GOOGLE_SHEETS_WEBHOOK_URL")
    if not webhook_url:
        print("Lỗi: Chưa có GOOGLE_SHEETS_WEBHOOK_URL trong file .env")
        await send_telegram_msg("❌ Lỗi: Cào dữ liệu xong nhưng thiếu GOOGLE_SHEETS_WEBHOOK_URL để đẩy lên!")
        return
        
    summary_report = ["<b>📊 BÁO CÁO CRAWL LAPTOP HẰNG NGÀY</b>\n"]
    total_laptops = 0
    
    for item in FILES_TO_SYNC:
        excel_path = item["file"]
        sheet_name = item["sheet_name"]
        
        if not os.path.exists(excel_path):
            print(f"Lỗi: Không tìm thấy file {excel_path}")
            summary_report.append(f"❌ <b>{sheet_name}</b>: Không có file dữ liệu")
            continue
            
        print(f"Đang đọc file {excel_path} để đẩy lên tab '{sheet_name}'...")
        try:
            wb = openpyxl.load_workbook(excel_path, data_only=True)
            sheet = wb.active
            
            rows = []
            # Lấy cả dòng tiêu đề
            for row in sheet.iter_rows(values_only=True):
                cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                if any(cleaned_row):
                    rows.append(cleaned_row)
                    
            if not rows:
                print(f"File {excel_path} trống.")
                summary_report.append(f"⚠️ <b>{sheet_name}</b>: File trống (0 sản phẩm)")
                continue
                
            print(f"Tìm thấy {len(rows) - 1} sản phẩm. Đang đẩy lên Google Sheets...")
            
            # Gửi data KHÔNG kèm header (dòng đầu), chỉ gửi dữ liệu để nối tiếp vào cuối sheet
            payload = {
                "clear": False,
                "sheet_name": sheet_name,
                "rows": rows[1:]  # Bỏ dòng tiêu đề, chỉ gửi dữ liệu
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(webhook_url, json=payload, timeout=60.0)
                if response.status_code in [200, 302]:
                    print(f"Đẩy thành công {sheet_name}!")
                    count = len(rows) - 1
                    total_laptops += count
                    summary_report.append(f"✅ <b>{sheet_name}</b>: {count} sản phẩm")
                else:
                    print(f"Lỗi khi đẩy lên Sheets: HTTP {response.status_code}")
                    summary_report.append(f"❌ <b>{sheet_name}</b>: Lỗi HTTP {response.status_code}")
                    
        except Exception as e:
            print(f"Lỗi kết nối/xử lý file {excel_path}: {e}")
            summary_report.append(f"❌ <b>{sheet_name}</b>: Lỗi Exception - {e}")
            
    summary_report.append(f"\n<b>Tổng cộng: {total_laptops} sản phẩm cập nhật mới!</b>")
    
    # Gửi báo cáo Telegram
    await send_telegram_msg("\n".join(summary_report))
    print("Đã hoàn tất toàn bộ tiến trình đẩy dữ liệu.")

if __name__ == "__main__":
    asyncio.run(upload_existing_data())
