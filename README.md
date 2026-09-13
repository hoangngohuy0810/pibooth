# Hướng Dẫn Cài Đặt và Sử Dụng Pibooth

**Pibooth** là ứng dụng Photobooth (buồng chụp ảnh tự động) mã nguồn mở viết bằng Python, được thiết kế chuyên biệt cho **Raspberry Pi** và cũng có thể chạy, kiểm thử trực tiếp trên máy tính cá nhân (**Windows / Linux / macOS**).

---

## Mục lục
1. [Tính năng nổi bật](#tính-năng-nổi-bật)
2. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
3. [Cài đặt & Thiết lập](#cài-đặt--thiết-lập)
   - [Cách 1: Chạy trên PC (Windows / Linux / macOS)](#cách-1-chạy-thử-nghiệm--phát-triển-trên-pc-windows--linux--macos)
   - [Cách 2: Cài đặt trên Raspberry Pi](#cách-2-cài-đặt-trên-raspberry-pi-chính-thức)
4. [Cách chạy ứng dụng](#cách-chạy-ứng-dụng)
5. [Hướng dẫn điều khiển](#hướng-dẫn-điều-khiển)
6. [Cấu hình & Tùy biến](#cấu-hình--tùy-biến)
7. [Các công cụ dòng lệnh (CLI Tools)](#các-công-cụ-dòng-lệnh-cli-tools)
8. [Tự động khởi động cùng Raspberry Pi](#tự-động-khởi-động-cùng-raspberry-pi)
9. [Sơ đồ kết nối phần cứng (GPIO)](#sơ-đồ-kết-nối-phần-cứng-gpio)
10. [Các Plugin phổ biến](#các-plugin-phổ-biến)
11. [Xử lý sự cố thường gặp (Troubleshooting)](#xử-lý-sự-cố-thường-gặp-troubleshooting)

---

## Tính năng nổi bật

- 📸 **Chụp từ 1 đến 4 ảnh** và tự động ghép thành một bức ảnh hoàn chỉnh.
- 📷 **Hỗ trợ đa dạng camera**: Raspberry Pi Camera (Picamera2 / libcamera), máy ảnh DSLR (qua gPhoto2) và mọi Webcam USB (qua OpenCV).
- 🔄 **Chế độ Hybrid**: Kết hợp Pi Camera để xem trước mượt mà và DSLR để chụp ảnh chất lượng cao.
- 🎨 **Tùy biến giao diện & bố cục**: Thêm chữ (footer text, ngày giờ, bộ đếm), phông chữ, logo/khung ảnh (overlay), màu nền (background) hoặc template nâng cao.
- 🖨️ **Hỗ trợ máy in**: Tích hợp in ảnh trực tiếp qua máy chủ in CUPS.
- 🔘 **Điều khiển linh hoạt**: Hỗ trợ nút bấm vật lý + đèn LED qua GPIO, bàn phím, chuột hoặc màn hình cảm ứng (touchscreen).
- 🧩 **Hệ thống Plugin mạnh mẽ**: Dễ dàng cài thêm plugin chia sẻ QR code, Google Photos, Dropbox, Telegram, hiệu ứng âm thanh,...

---

## Yêu cầu hệ thống

### Phần mềm
- **Python**: Phiên bản `3.10` trở lên.
- **Hệ điều hành**:
  - Raspberry Pi: Khuyến nghị **Raspberry Pi OS Bookworm (64-bit)** có giao diện Desktop.
  - PC: Windows 10/11, Linux (Ubuntu/Debian), macOS.

### Phần cứng (tùy chọn theo nhu cầu)
- 1 board **Raspberry Pi 3 Model B** trở lên (khuyên dùng Pi 4 hoặc Pi 5).
- 1 camera: Pi Camera v2/v3/HQ, DSLR tương thích gPhoto2, hoặc USB Webcam.
- 2 nút bấm nhả (push button).
- 2 đèn LED + 2 điện trở ~100 Ohm.
- Màn hình (HDMI hoặc màn hình cảm ứng DSI) và máy in ảnh (tùy chọn).

*(Tất cả nút bấm, đèn LED và máy in đều là tùy chọn. Ứng dụng có thể điều khiển hoàn toàn bằng bàn phím/chuột).*

---

## Cài đặt & Thiết lập

### Cách 1: Chạy thử nghiệm / Phát triển trên PC (Windows / Linux / macOS)

Khi chạy trên PC không có cổng GPIO thực, Pibooth sẽ tự động chuyển sang chế độ giả lập GPIO (**GPIO Mock**), bạn có thể dùng chuột/bàn phím và Webcam để thử nghiệm.

1. **Mở terminal** (PowerShell hoặc Command Prompt trên Windows) tại thư mục dự án `pibooth`:
   ```bash
   cd d:\pibooth
   ```

2. **Tạo và kích hoạt môi trường ảo (Virtual Environment)**:
   - **Trên Windows**:
     ```powershell
     python -m venv .venv
     .venv\Scripts\activate
     ```
   - **Trên Linux / macOS**:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```

3. **Cài đặt các thư viện cần thiết**:
   ```bash
   pip install --upgrade pip
   pip install -e .
   ```
   > *Lưu ý:* Nếu bạn có kết nối máy ảnh DSLR hoặc máy in trên Linux, có thể cài đặt thêm các gói mở rộng:
   > ```bash
   > pip install -e ".[dslr,printer]"
   > ```

---

### Cách 2: Cài đặt trên Raspberry Pi (Chính thức)

1. **Cập nhật hệ thống**:
   ```bash
   sudo apt-get update
   sudo apt-get full-upgrade -y
   ```

2. **Cài đặt các thư viện hệ thống cần thiết**:
   ```bash
   # Thư viện đồ họa SDL2 cho pygame:
   sudo apt-get install -y libsdl2-*

   # Thư viện Camera và tối ưu xử lý ảnh:
   sudo apt-get install -y python3-opencv python3-picamera2

   # (Nếu dùng Raspberry Pi 5) Cài thư viện GPIO:
   sudo apt-get install -y python3-lgpio

   # (Tùy chọn) Hỗ trợ máy in CUPS:
   sudo apt-get install -y cups libcups2-dev
   ```

3. **(Tùy chọn) Cài gPhoto2 nếu dùng máy ảnh DSLR**:
   ```bash
   wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/gphoto2-updater.sh
   wget https://raw.githubusercontent.com/gonzalo/gphoto2-updater/master/.env
   chmod +x gphoto2-updater.sh
   sudo ./gphoto2-updater.sh
   ```

4. **Tạo môi trường ảo và cài đặt Pibooth**:
   > **Quan trọng**: Trên Raspberry Pi OS (Bookworm), hãy sử dụng cờ `--system-site-packages` để môi trường ảo có thể nhìn thấy các gói hệ thống như `picamera2`, `opencv` và `gpiozero`.

   ```bash
   python3 -m venv --system-site-packages ~/pibooth-venv
   ~/pibooth-venv/bin/pip install --upgrade pip
   
   # Cài từ mã nguồn hiện tại (chế độ editable):
   cd /path/to/pibooth
   ~/pibooth-venv/bin/pip install -e .[dslr,printer]
   ```

---

## Cách chạy ứng dụng

### Trên Windows / PC:
Bạn có thể chạy bằng script tiện ích đã có sẵn:
```powershell
# Chạy trực tiếp qua file runner:
python run.py
```
Hoặc dùng lệnh console (khi đã kích hoạt virtualenv):
```powershell
pibooth
```

### Trên Raspberry Pi:
```bash
# Nếu dùng môi trường ảo:
~/pibooth-venv/bin/pibooth

# Hoặc kích hoạt môi trường ảo trước:
source ~/pibooth-venv/bin/activate
pibooth
```

### Các tùy chọn dòng lệnh hữu ích:
- `pibooth -v` hoặc `pibooth --verbose`: Bật log chi tiết (hữu ích khi kiểm tra camera và GPIO).
- `pibooth my_config/`: Khởi động ứng dụng với thư mục cấu hình riêng biệt.
- `pibooth --config`: Mở file cấu hình bằng trình soạn thảo mặc định.
- `pibooth --translate`: Mở file dịch ngôn ngữ giao diện để chỉnh sửa.
- `pibooth --reset`: Khôi phục toàn bộ cấu hình về mặc định.
- `pibooth --help`: Xem danh sách tất cả các tham số hỗ trợ.

---

## Hướng dẫn điều khiển

Sau khi giao diện mở lên, bạn có thể tương tác bằng các phương thức sau:

| Thao tác | Phím bàn phím | Nút bấm vật lý GPIO | Cảm ứng (Touchscreen) |
| :--- | :--- | :--- | :--- |
| **Bật/Tắt Toàn màn hình** | `Ctrl + F` | - | - |
| **Chọn số lượng ảnh (Bố cục)** | `Mũi tên TRÁI / PHẢI` | Nút 1 hoặc Nút 2 | Chạm 1 ngón |
| **Chụp ảnh** | `P` hoặc `SPACE` | Nút 1 | Chạm 1 ngón |
| **Duyệt mẫu khung (Template)** | `Mũi tên TRÁI / PHẢI` | Nút 2 | Chạm 2 mép màn hình |
| **Xác nhận mẫu khung** | `ENTER`, `SPACE`, `P` | Nút 1 | Chạm giữa màn hình |
| **Thoát màn hình xem trước ảnh** | `ENTER`, `SPACE`, `P` | Nút 1 hoặc Nút 2 | Chạm vào màn hình |
| **In ảnh / Xuất ảnh** | `Ctrl + E` | Nút 2 | Chạm 1 ngón |
| **Mở / Đóng Menu Cài đặt** | `ESC` | Nhấn giữ đồng thời Nút 1 + Nút 2 | Chạm 4 ngón cùng lúc |
| **Chọn mục trong Menu** | `Mũi tên LÊN / XUỐNG` | Nút 1 | Chạm 1 ngón |
| **Thay đổi giá trị mục** | `Mũi tên TRÁI / PHẢI` | Nút 2 | Chạm 1 ngón |

---

## Cấu hình & Tùy biến

Mặc định, file cấu hình được tạo tại:
- **Linux/Raspberry Pi**: `~/.config/pibooth/pibooth.cfg`
- **Windows**: `C:\Users\<Tên_User>\.config\pibooth\pibooth.cfg`

### Nơi lưu trữ ảnh chụp
- Tất cả ảnh chụp hoàn chỉnh được lưu tại đường dẫn cấu hình trong `[GENERAL][directory]`. Mặc định thường là thư mục `~/Pictures/pibooth`.
- Định dạng tên file: `YYYY-mm-dd-hh-mm-ss_pibooth.jpg`.
- Các ảnh gốc riêng lẻ từng lần bấm máy được lưu trong thư mục con `raw/YYYY-mm-dd-hh-mm-ss`.

### Một số thiết lập quan trọng trong `pibooth.cfg`:
```ini
[GENERAL]
# Ngôn ngữ hiển thị (en, de, fr, es,...)
language = en

# Thư mục lưu ảnh đã chụp
directory = ~/Pictures/pibooth

# Xoay toàn bộ giao diện màn hình (0, 90, 180, 270)
vflip = False
hflip = False

[WINDOW]
# Chạy chế độ toàn màn hình
fullscreen = True

# Xem trước ảnh sau khi chụp
review_picture = True

[CAMERA]
# Độ phân giải ảnh chụp (Chiều rộng, Chiều cao)
resolution = (1920, 1080)

# Thời gian đếm ngược trước mỗi lần chụp (giây)
countdown = 3

[PICTURE]
# Hướng ảnh chụp ghép hoàn chỉnh: auto, landscape (ngang) hoặc portrait (dọc)
orientation = auto

# Chữ hiển thị ở chân bức ảnh ghép
footer_text1 = Tiệc Cưới Hạnh Phúc
footer_text2 = Ngày chụp: {date.day}/{date.month}/{date.year}

# Phông chữ sử dụng (tên font hoặc đường dẫn file .ttf)
text_fonts = ('Amatic-Bold', 'Amatic-Bold')

# Màu chữ dạng RGB
text_colors = ((0, 0, 0), (0, 0, 0))

# Hiệu ứng áp dụng lên từng tấm ảnh: None, film, cartoon, washedout,...
captures_effects = None
```

---

## Các công cụ dòng lệnh (CLI Tools)

Pibooth đi kèm nhiều công cụ dòng lệnh tiện ích:

1. **`pibooth-diag`**: Chẩn đoán phần cứng, kiểm tra kết nối camera, nút GPIO, máy in.
2. **`pibooth-count`**: Xem và quản lý bộ đếm số lượng ảnh đã chụp, đã in hoặc đã bỏ qua.
3. **`pibooth-fonts`**: Liệt kê tất cả các phông chữ hệ thống mà Pibooth có thể sử dụng.
4. **`pibooth-regen`**: Tạo lại (ghép lại) các bức ảnh hoàn chỉnh từ các bức ảnh gốc trong thư mục `raw/` sau khi bạn thay đổi bố cục hoặc text.
5. **`pibooth-printcfg`**: Kiểm tra và cấu hình các thông số máy in.

---

## Tự động khởi động cùng Raspberry Pi

Để Pibooth tự khởi động khi Raspberry Pi bật nguồn lên màn hình desktop:

1. Mở terminal trên Raspberry Pi và tạo thư mục tự khởi động:
   ```bash
   mkdir -p ~/.config/autostart
   ```

2. Tạo file `.desktop`:
   ```bash
   nano ~/.config/autostart/pibooth.desktop
   ```

3. Thêm nội dung sau (điều chỉnh đường dẫn phù hợp với môi trường của bạn):
   ```ini
   [Desktop Entry]
   Type=Application
   Name=Pibooth
   Exec=/home/pi/pibooth-venv/bin/pibooth
   Terminal=false
   ```

4. Lưu lại (`Ctrl + O`, `Enter`, `Ctrl + X`). Pibooth sẽ tự động chạy mỗi khi boot vào màn hình Desktop.

---

## Sơ đồ kết nối phần cứng (GPIO)

Mặc định, Pibooth sử dụng sơ đồ chân vật lý (Physical Pin / Board Pin) trên Raspberry Pi như sau:

- **Nút 1 (Chụp ảnh / Chọn)**: Chân vật lý **11** (GPIO 17) nối qua nút bấm về Ground (**GND - chân 6, 9 hoặc 14**).
- **Nút 2 (Đổi kiểu / In)**: Chân vật lý **13** (GPIO 27) nối qua nút bấm về Ground (**GND**).
- **Đèn LED 1**: Chân vật lý **16** (GPIO 23) nối qua điện trở 100 Ohm đến cực dương LED, cực âm nối **GND**.
- **Đèn LED 2**: Chân vật lý **18** (GPIO 24) nối qua điện trở 100 Ohm đến cực dương LED, cực âm nối **GND**.

> *(Gợi ý)* Để thêm nút bấm tắt/mở nguồn an toàn cho Pi, bạn có thể thêm dòng `dtoverlay=gpio-shutdown` vào file `/boot/config.txt` (hoặc `/boot/firmware/config.txt` trên Bookworm) và nối một nút bấm giữa **chân 5** và **chân 6**.

---

## Các Plugin phổ biến

Pibooth hỗ trợ mở rộng thông qua các plugin PyPI:

- **`pibooth-picture-template`**: Cho phép tạo và chọn các khung hình, template đồ họa tùy biến theo phong cách K-Pop, sự kiện,...
- **`pibooth-qrcode`**: Tạo mã QR ngay trên màn hình để khách quét và tải ảnh về điện thoại.
- **`pibooth-google-photo`**: Tự động tải ảnh chụp lên album Google Photos.
- **`pibooth-dropbox`**: Đồng bộ ảnh lên Dropbox.
- **`pibooth-sound-effects`**: Phát âm thanh vui nhộn khi đếm ngược và chụp ảnh.
- **`pibooth-extra-lights`**: Điều khiển hệ thống đèn flash hoặc đèn LED chiếu sáng trợ sáng.

Cài đặt plugin bằng pip:
```bash
pip install pibooth-qrcode pibooth-picture-template
```

---

## Xử lý sự cố thường gặp (Troubleshooting)

1. **Ứng dụng báo `Starting the photo booth application without physical GPIO, fallback to GPIO mock`**:
   - Đây là điều bình thường khi bạn chạy trên máy tính Windows/Mac.
   - Nếu bạn đang chạy trên **Raspberry Pi 5**, hãy đảm bảo đã cài đặt backend GPIO mới:
     ```bash
     sudo apt-get install python3-lgpio
     ```

2. **Không nhận diện được Camera**:
   - Kiểm tra xem camera đã được bật chưa (`raspi-config` -> Interface Options -> Camera).
   - Chạy lệnh chẩn đoán `pibooth-diag` hoặc kiểm tra log bằng `pibooth -v`.
   - Với Webcam USB, hãy đảm bảo OpenCV đã cài đặt đúng: `python3 -c "import cv2; print(cv2.__version__)"`.

3. **Màn hình hiển thị bị ngược hoặc sai hướng**:
   - Mở file cấu hình `~/.config/pibooth/pibooth.cfg` và điều chỉnh các giá trị `hflip = True/False` hoặc `vflip = True/False` trong mục `[GENERAL]`.

---

## Giấy phép (License)

Dự án này được phát hành theo giấy phép mã nguồn mở **MIT License**.
Tham khảo chi tiết tại file [LICENSE](file:///d:/pibooth/LICENSE).
