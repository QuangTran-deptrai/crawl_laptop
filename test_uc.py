import undetected_chromedriver as uc

if __name__ == "__main__":
    print("Khởi tạo undetected_chromedriver...")
    options = uc.ChromeOptions()
    # Rất quan trọng khi chạy trên server Linux/Github Actions
    options.add_argument('--no-sandbox') 
    options.add_argument('--disable-dev-shm-usage')
    
    # Xử lý lỗi lệch version giữa Chrome cài sẵn trên server và ChromeDriver tải về
    try:
        driver = uc.Chrome(options=options)
    except Exception as e:
        error_msg = str(e)
        if "This version of ChromeDriver only supports Chrome version" in error_msg:
            import re
            match = re.search(r"Current browser version is (\d+)", error_msg)
            if match:
                version = int(match.group(1))
                print(f"-> Đã phát hiện Chrome version {version}. Đang thử lại với version_main={version}...")
                
                # BẮT BUỘC TẠO LẠI OPTIONS VÌ UC KHÔNG CHO PHÉP TÁI SỬ DỤNG
                options2 = uc.ChromeOptions()
                options2.add_argument('--no-sandbox') 
                options2.add_argument('--disable-dev-shm-usage')
                
                driver = uc.Chrome(options=options2, version_main=version)
            else:
                raise e
        else:
            raise e
            
    try:
        print("Mở Chrome thành công! Đang truy cập trang web...")
        driver.get("https://phongvu.vn")
        print("Tiêu đề trang Phong Vũ:", driver.title)
    except Exception as e:
        print("Lỗi:", e)
    finally:
        if 'driver' in locals():
            driver.quit()
        print("Hoàn tất test xvfb.")
