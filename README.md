# BÀI TẬP LỚN TRÍ TUỆ NHÂN TẠO - CARO AI

Dự án xây dựng tác nhân chơi cờ Caro trên bàn cờ $9 \times 9$ sử dụng hai thuật toán đối kháng:

1. **MiniMax kết hợp cắt tỉa Alpha-Beta**.
2. **Monte Carlo Tree Search (MCTS) kết hợp chỉ số UCT**.
3. **Thực nghiệm, khảo sát tham số & vẽ biểu đồ**: Khảo sát tham số khám phá $c \in \{0.5, 1.0, 1.4, 2.0\}$ và số iteration $\in \{100, 300, 500\}$.
4. **Giao diện trực quan (UI)**: Hỗ trợ Người đấu Máy, Máy đấu Máy, thay đổi tham số trực tiếp và hiển thị nhật ký suy luận.

---

## 1. Thiết lập môi trường chung

Dự án sử dụng công cụ **`uv`** để tự động khóa phiên bản Python **3.11.9** và đồng bộ chính xác từng thư viện qua file `uv.lock`.

### Cách 1: Sử dụng `uv` (Khuyên dùng)

#### 🔹 Bước 1: Cài đặt `uv` (Nếu máy bạn chưa có)

Mở Terminal / PowerShell và chạy **1 lệnh duy nhất** tương ứng với hệ điều hành:

- **Trên Windows (PowerShell):**

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

    _(Hoặc nếu máy đã có winget: `winget install --id=astral-sh.uv -e`)_

- **Trên macOS / Linux:**

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

- **Hoặc cài nhanh qua pip (nếu máy đã có sẵn Python bất kỳ):**
    ```bash
    pip install uv
    ```

> Sau khi cài đặt `uv`, hãy tắt và mở lại Terminal / PowerShell để máy nhận diện lệnh `uv`.

#### 🔹 Bước 2: Đồng bộ môi trường

Tại thư mục gốc `Caro_AI`, chạy lệnh:

```bash
uv sync
```

`uv` sẽ **tự động tải bản Python 3.11.9 chính thức về** (nếu máy bạn chưa có), tạo môi trường ảo `.venv` và cài đặt đầy đủ tất cả thư viện theo file `uv.lock`.

#### 🔹 Bước 3: Chạy ứng dụng

- Chạy trực tiếp qua uv:
    ```bash
    uv run python main.py
    ```
- Hoặc kích hoạt môi trường ảo như bình thường:
    - Windows: `.venv\Scripts\activate` rồi gõ `python main.py`
    - macOS/Linux: `source .venv/bin/activate` rồi gõ `python main.py`

---

### Cách 2: Phương án dự phòng (Sử dụng `pip` & `venv`)

Nếu vì lý do gì bạn không cài được `uv`, bạn có thể cài thủ công bằng Python:

1. Đảm bảo máy tính đã cài đặt **Python 3.11.x**.
2. Mở terminal tại thư mục dự án và chạy:
    - **Windows:**
        ```powershell
        python -m venv .venv
        .venv\Scripts\activate
        pip install --upgrade pip
        pip install -r requirements.txt
        ```
    - **macOS / Linux:**
        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        ```

---
