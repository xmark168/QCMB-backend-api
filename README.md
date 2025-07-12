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


OkHttp: xem log

<!-- ///// -->
Không dựa vào findViewById để phân biệt view type vì có thể bị nhầm lẫn
Sử dụng instanceof để kiểm tra kiểu thực tế của object

// ❌ LOGIC SAI: Cả 2 layout đều có R.id.tvItemName
    if (itemView.findViewById(R.id.tvItemName) != null) {
        // Đây được cho là header
        isHeader = true;
        headerTitle = (TextView) itemView;  // 💥 CRASH HERE!
        // Khi itemView là LinearLayout từ item_store.xml
        // nhưng cố cast thành TextView
    } else {
        // Đây được cho là item  
        isHeader = false;
        // ... init các view khác
    }


 // ✅ LOGIC ĐÚNG: Kiểm tra kiểu thực tế của itemView
    if (itemView instanceof TextView) {
        // itemView thực sự là TextView → Header
        isHeader = true;
        headerTitle = (TextView) itemView;  // ✅ An toàn
    } else {
        // itemView là LinearLayout hoặc view khác → Item
        isHeader = false;
        tvEmojiIcon = itemView.findViewById(R.id.tvEmojiIcon);
        tvName = itemView.findViewById(R.id.tvItemName);
        // ... init các view khác
    }

scalar: trả về 1 đối tượng
execute trả về 1 list


# Hướng dẫn tích hợp PayOS Payment Gateway

## 🔧 Cài đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình environment variables
Tạo file `.env` với nội dung:

```env
# PayOS Configuration
# Lấy thông tin này từ PayOS Merchant Portal: https://payos.vn
PAYOS_CLIENT_ID=your_payos_client_id_here
PAYOS_API_KEY=your_payos_api_key_here  
PAYOS_CHECKSUM_KEY=your_payos_checksum_key_here
PAYOS_SANDBOX=true

# Application Configuration
BASE_URL=http://localhost:8000
SECRET_KEY=your_jwt_secret_key_here

# Database Configuration  
DATABASE_URL=sqlite:///./app.db
```

### 3. Lấy PayOS credentials

1. Đăng ký tài khoản merchant tại [PayOS](https://payos.vn)
2. Tạo ứng dụng mới trong PayOS Dashboard
3. Lấy thông tin:
   - **Client ID**: Mã định danh ứng dụng
   - **API Key**: Khóa API để gọi PayOS APIs
   - **Checksum Key**: Khóa để verify webhook data

### 4. Cấu hình webhook URL
Trong PayOS Dashboard, cấu hình webhook URL:
```
http://your-domain.com/api/v1/payment/webhook
```

## 📋 API Endpoints

### Store APIs
- `GET /api/v1/store/items` - Lấy danh sách items và gói token
- `POST /api/v1/store/purchase` - Mua items thường (bằng token)
- `POST /api/v1/store/topup` - Tạo PayOS payment link cho gói token
- `GET /api/v1/store/inventory` - Lấy inventory của user

### Payment APIs  
- `POST /api/v1/payment/create` - Tạo payment link PayOS
- `POST /api/v1/payment/webhook` - Webhook nhận thông báo từ PayOS
- `GET /api/v1/payment/status/{order_code}` - Kiểm tra trạng thái payment
- `GET /api/v1/payment/history` - Lịch sử thanh toán
- `GET /api/v1/payment/packages` - Danh sách gói token
- `POST /api/v1/payment/cancel/{order_code}` - Hủy payment

### Success/Cancel URLs
- `GET /api/v1/payment/success` - Trang thành công
- `GET /api/v1/payment/cancel` - Trang hủy

## 🔄 Flow hoạt động

### 1. Mua gói token từ Android App
```
1. User bấm mua gói token trong store
2. Android app gọi POST /api/v1/store/topup với package_id
3. Server tạo PayOS payment link
4. Android app nhận checkout_url và mở browser
5. User thanh toán trên PayOS
6. PayOS gửi webhook đến /api/v1/payment/webhook
7. Server cộng token vào tài khoản user
```

### 2. Webhook flow
```
1. PayOS gửi webhook khi payment thành công
2. Server verify webhook data
3. Tìm payment record trong database
4. Cập nhật status thành PAID
5. Cộng token vào user balance
6. Ghi log thành công
```

## 🧪 Testing

### 1. Test trong sandbox mode
Đặt `PAYOS_SANDBOX=true` để test với PayOS sandbox.

### 2. Test webhook local
Dùng ngrok để expose local server:
```bash
ngrok http 8000
```
Rồi cấu hình webhook URL: `https://your-ngrok-url.ngrok.io/api/v1/payment/webhook`

### 3. Test các gói token
```bash
# Tạo payment cho gói 1000 token
curl -X POST "http://localhost:8000/api/v1/store/topup" \
  -H "Authorization: Bearer your_jwt_token" \
  -H "Content-Type: application/json" \
  -d '{"package_id": 1001}'
```

## 📱 Android App Integration

Android app đã được tích hợp sẵn:

1. **StoreActivity**: Hiển thị gói token và gọi API topup
2. **ApiService**: Có method `createTopup()` 
3. **TopupResponse**: Model để nhận checkout_url

Khi user bấm mua gói token:
```java
// Android code đã có sẵn trong StoreActivity.java
api.createTopup(token, body).enqueue(new Callback<TopupResponse>() {
    @Override
    public void onResponse(Call<TopupResponse> call, Response<TopupResponse> response) {
        if (response.isSuccessful() && response.body() != null) {
            String url = response.body().getCheckoutUrl();
            // Mở browser để thanh toán
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        }
    }
});
```

## 🛡️ Security

1. **Webhook verification**: Server verify checksum từ PayOS
2. **JWT Authentication**: Tất cả APIs yêu cầu JWT token
3. **Environment variables**: Credentials không hardcode trong code
4. **Database transaction**: Đảm bảo consistency khi cập nhật token

## 📊 Monitoring

Kiểm tra logs để theo dõi:
- Payment creation
- Webhook events  
- Token balance updates
- Errors và exceptions

## 🔍 Troubleshooting

### Lỗi PayOS connection
- Kiểm tra credentials trong `.env`
- Kiểm tra network connectivity
- Xem logs PayOS request/response

### Webhook không nhận được
- Kiểm tra webhook URL đã đúng chưa
- Kiểm tra server có accessible từ internet không
- Xem logs webhook events

### Token không được cộng
- Kiểm tra webhook có verify thành công không
- Kiểm tra payment status trong database
- Xem logs token balance updates

## 🎯 Production Deployment

1. Đặt `PAYOS_SANDBOX=false`
2. Cập nhật `BASE_URL` với domain thật
3. Cấu hình webhook URL production
4. Setup monitoring và alerting
5. Backup database thường xuyên 