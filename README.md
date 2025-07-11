.\.venv\Scripts\Activate.ps1

xóa bảng alembic_version trong postgresql
alembic revision --autogenerate -m "update role enum in user table"
alembic upgrade head


fastapi dev app/main.py

không commit tk mk db lên

model -> schemas -> /endpoint -> api.py


FE
apiService -> model -> request -> response


#91C8E4 -> xanh nhạt
#749BC2 -> xanh trung bình
#4682A9 -> xanh đậm

<!-- cài thêm thư viện -->
pip install aiosmtplib

finish() chỉ đóng Activity hiện tại và quay về Activity trước đó trong stack. Ví dụ:
Activity Stack: [MainActivity] -> [LoginActivity] -> [ForgotPasswordActivity]
                                                            ↑ finish() ở đây
Kết quả:       [MainActivity] -> [LoginActivity] 
                                        ↑ quay về đây