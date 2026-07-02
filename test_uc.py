import undetected_chromedriver as uc

if __name__ == "__main__":
    print("Khởi tạo undetected_chromedriver...")
    options = uc.ChromeOptions()
    # Rất quan trọng khi chạy trên server Linux/Github Actions
    options.add_argument('--no-sandbox') 
    options.add_argument('--disable-dev-shm-usage')
    
    # LƯU Ý: KHÔNG CÓ --headless ở đây, vì chúng ta đang dùng màn hình ảo xvfb!
    driver = uc.Chrome(options=options)
    
    try:
        print("Mở Chrome thành công! Đang truy cập trang web...")
        driver.get("https://phongvu.vn")
        print("Tiêu đề trang Phong Vũ:", driver.title)
    except Exception as e:
        print("Lỗi:", e)
    finally:
        driver.quit()
        print("Hoàn tất test xvfb.")
