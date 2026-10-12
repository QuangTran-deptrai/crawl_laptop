import os
import glob
import subprocess
import sys
import httpx

def run_command(cmd, ignore_error=True):
    """Thực thi câu lệnh hệ thống an toàn trên cả Windows và Linux"""
    print(f"👉 Chạy lệnh: {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"⚠️ Cảnh báo/Lỗi: {res.stderr.strip()}")
    if not ignore_error and res.returncode != 0:
        sys.exit(res.returncode)
    return res.returncode

def trigger_github_workflow():
    """Kích hoạt lại workflow qua gh CLI hoặc trực tiếp qua GitHub REST API"""
    token = os.getenv("GH_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    
    # Cách 1: Thử gọi qua gh CLI nếu có
    res = subprocess.run("gh workflow run daily_scraper.yml", shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        print("✅ Đã kích hoạt lại workflow qua gh CLI!")
        return True
        
    # Cách 2: Gọi trực tiếp GitHub REST API (không cần cài đặt gh CLI)
    if repo and token:
        try:
            url = f"https://api.github.com/repos/{repo}/actions/workflows/daily_scraper.yml/dispatches"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "GitHub-Actions-Runner"
            }
            resp = httpx.post(url, json={"ref": "main"}, headers=headers, timeout=15.0)
            if resp.status_code in [204, 200, 201]:
                print("✅ Đã kích hoạt lại workflow qua GitHub API thành công!")
                return True
            else:
                print(f"⚠️ GitHub API phản hồi HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"⚠️ Lỗi khi gọi GitHub API: {e}")
            
    print("⚠️ Không thể kích hoạt lại workflow tự động.")
    return False

def main():
    print("=" * 60)
    print("🚀 BẮT ĐẦU QUY TRÌNH ĐỒNG BỘ DỮ LIỆU SAU KHI CÀO")
    print("=" * 60)
    
    # 1. Cấu hình thông tin Git
    run_command('git config --local user.email "github-actions[bot]@users.noreply.github.com"')
    run_command('git config --local user.name "github-actions[bot]"')
    
    # 2. Kiểm tra số lần Retry
    retry_file = "retry_count.txt"
    count = 0
    if os.path.exists(retry_file):
        try:
            with open(retry_file, "r", encoding="utf-8") as f:
                content = f.read().strip()
                count = int(content) if content else 0
        except Exception:
            count = 0

    pending_files = glob.glob("*_pending*.txt")
    
    # Nếu còn file pending (cào chưa hết / bị chặn mạng)
    if pending_files:
        print(f"⚠️ Phát hiện {len(pending_files)} file pending: {pending_files}")
        if count >= 3:
            print("⚠️ CẢNH BÁO: Đã Retry 3 lần nhưng vẫn còn pending. Dừng Retry để tránh lặp vô tận!")
            with open(retry_file, "w", encoding="utf-8") as f:
                f.write("0")
        else:
            count += 1
            with open(retry_file, "w", encoding="utf-8") as f:
                f.write(str(count))
            print(f"🔄 Lưu Excel tạm và kích hoạt Retry lần {count}...")
            
            run_command("git add -A *.xlsx")
            run_command("git add -A *_pending*.txt")
            run_command(f"git add {retry_file}")
            
            # Commit nếu có thay đổi
            diff_res = subprocess.run("git diff --quiet && git diff --staged --quiet", shell=True)
            if diff_res.returncode != 0:
                run_command(f'git commit -m "Auto-update: Lưu trạng thái dang dở (Retry lần {count}) [skip ci]"')
                run_command("git pull --rebase")
                run_command("git push")
                
            trigger_github_workflow()
            print("Dừng nhánh này tại đây để chờ lượt chạy mới.")
            sys.exit(0)

    print("🎉 HOÀN THÀNH CÀO DỮ LIỆU! TIẾN HÀNH XỬ LÝ DỮ LIỆU...")
    with open(retry_file, "w", encoding="utf-8") as f:
        f.write("0")
        
    # Xóa sạch pending trên Git và local
    run_command("git rm *_pending*.txt --ignore-unmatch")
    for pf in glob.glob("*_pending*.txt"):
        try:
            os.remove(pf)
        except Exception:
            pass

    # 3. Gộp các mảnh Excel
    print("\n📦 BƯỚC 1: GỘP MẢNH EXCEL (chunk_merger.py)...")
    run_command(f'"{sys.executable}" chunk_merger.py')

    # 4. Đẩy lên Google Sheets
    print("\n📊 BƯỚC 2: ĐẨY LÊN GOOGLE SHEETS & BÁO CÁO TELEGRAM (sync_excel_to_sheets.py)...")
    run_command(f'"{sys.executable}" sync_excel_to_sheets.py')

    # 5. Đẩy vào PostgreSQL (bảng raw_laptop_data)
    print("\n💾 BƯỚC 3: ĐẨY VÀO POSTGRESQL (import_db.py)...")
    run_command(f'"{sys.executable}" import_db.py')

    # 6. Làm sạch và bóc tách thông số vào PostgreSQL (bảng clean_laptop_data)
    print("\n🧹 BƯỚC 4: LÀM SẠCH VÀ CHUẨN HÓA DỮ LIỆU (clean_data.py)...")
    run_command(f'"{sys.executable}" clean_data.py')

    # 7. Commit toàn bộ file Excel đã gộp lên GitHub
    print("\n☁️ BƯỚC 5: COMMIT VÀ ĐẨY LÊN GITHUB REPOSITORY...")
    run_command("git add -A")
    diff_check = subprocess.run("git diff --quiet && git diff --staged --quiet", shell=True)
    if diff_check.returncode != 0:
        run_command('git commit -m "Auto-update: Hoàn thành cào và cập nhật dữ liệu mới [skip ci]"')
        run_command("git pull --rebase")
        run_command("git push")
        print("✅ Đã push các file dữ liệu mới lên GitHub thành công!")
    else:
        print("ℹ️ Không có thay đổi mới cần commit.")

    print("\n✨ HOÀN TẤT TOÀN BỘ QUY TRÌNH!")

if __name__ == "__main__":
    main()
