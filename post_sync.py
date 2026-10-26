import os
import glob
import subprocess
import sys
import shutil
import httpx

def get_git_executable():
    """Tự động tìm kiếm đường dẫn git.exe chuẩn xác trên Windows/Linux"""
    # 1. Nếu git đã có sẵn trong PATH
    if shutil.which("git"):
        return "git"

    # 2. Danh sách các đường dẫn cài đặt Git phổ biến trên Windows
    candidates = [
        r"C:\Program Files\Git\cmd\git.exe",
        r"C:\Program Files\Git\bin\git.exe",
        r"C:\Program Files (x86)\Git\cmd\git.exe",
        r"C:\Program Files (x86)\Git\bin\git.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Git\cmd\git.exe"),
        r"C:\Users\PSD\actions-runner\externals\git\cmd\git.exe",
        r"C:\Users\PSD\actions-runner\externals\git\bin\git.exe",
    ]
    
    # 3. Quét động thư mục actions-runner nếu đang chạy trên GitHub Runner
    runner_externals = glob.glob(r"C:\Users\*\actions-runner\externals\git\cmd\git.exe")
    candidates.extend(runner_externals)
    
    # 4. Quét tương đối từ thư mục runner workspace
    ws = os.getenv("GITHUB_WORKSPACE", os.getcwd())
    relative_git = os.path.abspath(os.path.join(ws, "..", "..", "..", "externals", "git", "cmd", "git.exe"))
    candidates.append(relative_git)

    for p in candidates:
        if os.path.isfile(p):
            git_dir = os.path.dirname(p)
            print(f"🔧 Đã tìm thấy Git tại: {p}. Bổ sung vào PATH...")
            os.environ["PATH"] = git_dir + os.pathsep + os.environ.get("PATH", "")
            return f'"{p}"'
            
    print("⚠️ Không tìm thấy đường dẫn Git cụ thể, giữ mặc định 'git'")
    return "git"

GIT_CMD = get_git_executable()

def run_command(cmd, ignore_error=True):
    """Thực thi câu lệnh hệ thống an toàn trên cả Windows và Linux"""
    # Tự động thay thế tiền tố 'git ' bằng đường dẫn Git thực tế nếu có
    if cmd.startswith("git "):
        cmd = f"{GIT_CMD} " + cmd[4:]
        
    print(f"👉 Chạy lệnh: {cmd}")
    res = subprocess.run(cmd, shell=True, text=True, encoding='utf-8', errors='replace', capture_output=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr and res.returncode != 0:
        print(f"⚠️ Cảnh báo/Lỗi: {res.stderr.strip()}")
    if not ignore_error and res.returncode != 0:
        sys.exit(res.returncode)
    return res.returncode

def ensure_git_repo():
    """Đảm bảo thư mục làm việc là một Git repo hợp lệ và tránh lỗi safe.directory"""
    token = os.getenv("GH_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")

    # 1. Tránh lỗi 'dubious ownership' của Git trên Windows
    run_command("git config --global --add safe.directory *")

    # 2. Nếu chưa có thư mục .git (do checkout dạng zip/archive khi chưa có git trong PATH)
    if not os.path.exists(".git"):
        print("⚠️ Không tìm thấy thư mục .git! Đang tự động khởi tạo lại Git repository...")
        run_command("git init")
        run_command('git config --local user.email "github-actions[bot]@users.noreply.github.com"')
        run_command('git config --local user.name "github-actions[bot]"')
        
        if repo and token:
            remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
            run_command(f"git remote add origin {remote_url}")
            run_command("git fetch origin main")
            run_command("git reset --soft origin/main")
            print("✅ Đã kết nối lại Git repository với origin/main thành công!")
        elif repo:
            run_command(f"git remote add origin https://github.com/{repo}.git")
    else:
        # Nếu đã có .git, cấu hình remote URL kèm token để push mượt mà
        if repo and token:
            remote_url = f"https://x-access-token:{token}@github.com/{repo}.git"
            run_command(f"git remote set-url origin {remote_url}")

def git_has_changes():
    """Kiểm tra xem có thay đổi nào cần commit hay không"""
    cmd = f"{GIT_CMD} diff --quiet && {GIT_CMD} diff --staged --quiet"
    res = subprocess.run(cmd, shell=True, capture_output=True)
    return res.returncode != 0

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
    
    # 1. Đảm bảo Git repo hợp lệ
    ensure_git_repo()
    
    # 2. Cấu hình thông tin Git
    run_command('git config --local user.email "github-actions[bot]@users.noreply.github.com"')
    run_command('git config --local user.name "github-actions[bot]"')
    
    # 3. Kiểm tra số lần Retry
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

            # Gộp ngay các kênh đã cào xong (không còn pending) để file _all.xlsx
            # của kênh đó được cập nhật luôn, không phải chờ kênh lỗi retry xong.
            all_stores = ["fptshop", "phongvu", "tgdd", "cellphones", "gearvn", "xgear"]
            pending_stores = {os.path.basename(p).split("_pending")[0] for p in pending_files}
            done_stores = [s for s in all_stores if s not in pending_stores]
            print(f"   Kênh còn pending: {sorted(pending_stores)} | Kênh đã xong, gộp ngay: {done_stores}")
            if done_stores:
                run_command(f'"{sys.executable}" chunk_merger.py --stores {",".join(done_stores)}')

            run_command("git add -A *.xlsx")
            run_command("git add -A *_pending*.txt")
            run_command(f"git add {retry_file}")
            
            # Commit nếu có thay đổi
            if git_has_changes():
                run_command(f'git commit -m "Auto-update: Cập nhật kênh đã xong, lưu trạng thái dang dở (Retry lần {count}) [skip ci]"')
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

    # 4. Gộp các mảnh Excel
    print("\n📦 BƯỚC 1: GỘP MẢNH EXCEL (chunk_merger.py)...")
    run_command(f'"{sys.executable}" chunk_merger.py')

    # 5. Đẩy lên Google Sheets
    print("\n📊 BƯỚC 2: ĐẨY LÊN GOOGLE SHEETS & BÁO CÁO TELEGRAM (sync_excel_to_sheets.py)...")
    run_command(f'"{sys.executable}" sync_excel_to_sheets.py')

    # 6. Đẩy vào PostgreSQL (bảng raw_laptop_data)
    print("\n💾 BƯỚC 3: ĐẨY VÀO POSTGRESQL (import_db.py)...")
    run_command(f'"{sys.executable}" import_db.py')

    # 7. Làm sạch và bóc tách thông số vào PostgreSQL (bảng clean_laptop_data)
    print("\n🧹 BƯỚC 4: LÀM SẠCH VÀ CHUẨN HÓA DỮ LIỆU (clean_data.py)...")
    run_command(f'"{sys.executable}" clean_data.py')

    # 8. Commit toàn bộ file Excel đã gộp lên GitHub
    print("\n☁️ BƯỚC 5: COMMIT VÀ ĐẨY LÊN GITHUB REPOSITORY...")
    run_command("git add laptop_*_all.xlsx laptop_clean_snapshot.xlsx retry_count.txt")
    if git_has_changes():
        run_command('git commit -m "Auto-update: Hoàn thành cào và cập nhật dữ liệu mới [skip ci]"')
        run_command("git pull --rebase -X theirs")
        run_command("git push")
        print("✅ Đã push các file dữ liệu mới lên GitHub thành công!")
    else:
        print("ℹ️ Không có thay đổi mới cần commit.")

    print("\n✨ HOÀN TẤT TOÀN BỘ QUY TRÌNH!")

if __name__ == "__main__":
    main()
