# Setup logging
from datetime import datetime, timedelta
import logging
from typing import List

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.core.models import Payment, User
from app.core.schemas import TOKEN_PACKAGES, CreatePaymentRequest, CreatePaymentResponse, PaymentStatus, PaymentStatusResponse
from app.core.config import settings
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
# Tạm thời comment out PayOS import vì package chưa có sẵn
from payos import PayOS, PaymentData, ItemData

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Khởi tạo PayOS client
try:
    settings.validate_payos_config()
    payos_client = PayOS(
        client_id=settings.PAYOS_CLIENT_ID,
        api_key=settings.PAYOS_API_KEY,
        checksum_key=settings.PAYOS_CHECKSUM_KEY
    )
    logger.info("PayOS client được khởi tạo thành công")
except Exception as e:
    logger.error(f"Không thể khởi tạo PayOS client: {e}")
    payos_client = None

router = APIRouter(prefix="/payment", tags=["payment"])

@router.post("/create", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
): 
    """Tạo payment link cho gói token với PayOS"""
    
    if not payos_client:
        raise HTTPException(500, "PayOS chưa được cấu hình đúng")
    
    # 1. Validate package
    if request.package_id not in TOKEN_PACKAGES:
        raise HTTPException(404, f"Gói token {request.package_id} không tồn tại")
    
    package_info = TOKEN_PACKAGES[request.package_id]
    
    # 2. Tạo order code unique (timestamp + user_id)
    order_code = int(datetime.utcnow().timestamp() * 1000)  # milliseconds timestamp
    
    try:
        # 3. Tạo PayOS payment data
        # Tạo description ngắn (PayOS giới hạn 25 ký tự)
        short_description = f"Nap token {current_user.username[:10]}"[:25]
        
        payment_data = PaymentData(
            orderCode = order_code,
            amount = package_info["price"],
            description = short_description,
            cancelUrl = settings.PAYMENT_CANCEL_URL,
            returnUrl = settings.PAYMENT_SUCCESS_URL,
            items = [
                ItemData(
                    name = package_info["name"],
                    quantity = 1,
                    price = package_info["price"]
                )
            ]
        )
        
        # 4. Gọi PayOS API để tạo payment link
        result = await payos_client.createPaymentLink(payment_data)
        
        # 5. Lưu payment record vào database
        # Sử dụng description đầy đủ cho database (không bị giới hạn như PayOS)
        full_description = f"Nạp {package_info['name']} cho tài khoản {current_user.username}"
        
        new_payment = Payment(
            user_id=current_user.id,
            order_code=order_code,
            payos_payment_id=result.paymentLinkId,
            package_id=request.package_id,
            package_name=package_info["name"],
            amount=package_info["price"],
            tokens=package_info["tokens"],
            status=PaymentStatus.PENDING,
            checkout_url=result.checkoutUrl,
            description=full_description,
            expires_at=datetime.utcnow() + timedelta(hours=1)  # Hết hạn sau 1 giờ
        )

        db.add(new_payment)
        await db.commit()
        await db.refresh(new_payment)
        
        logger.info(f"Tạo payment thành công: order_code={order_code}, user_id={current_user.id}")

        return CreatePaymentResponse(
            payment_id=str(new_payment.id),
            order_code=order_code,
            checkout_url=result.checkoutUrl,
            package_info=package_info,
            amount=package_info["price"],
            status=PaymentStatus.PENDING.value
        )
        
    except Exception as e:
        logger.error(f"Lỗi tạo payment: {e}")
        await db.rollback()
        raise HTTPException(500, f"Không thể tạo payment: {str(e)}")
    
@router.post("/webhook")
async def payos_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Webhook endpoint để nhận thông báo từ PayOS khi thanh toán thành công"""
    try:
        # 1. Lấy raw body và verify webhook
        body = await request.body()
        webhook_data = await request.json()
        
        logger.info(f"Nhận webhook từ PayOS: {webhook_data}")
        
        # 2. Verify webhook data với PayOS
        if payos_client:
            try:
                verified_data = payos_client.verifyPaymentWebhookData(webhook_data)
                order_code = verified_data.orderCode
            except Exception as e:
                logger.error(f"Lỗi verify webhook: {e}")
                raise HTTPException(400, "Webhook không hợp lệ")
            
        else:
            # Fallback nếu PayOS client không có
            order_code = webhook_data.get("orderCode")
            
        if not order_code:
            raise HTTPException(400, "Thiếu order code trong webhook")
        
        # 3. Tìm payment record
        payment = await db.scalar(
            select(Payment)
            .options(selectinload(Payment.user))
            .where(Payment.order_code == order_code)
        )

        if not payment:
            logger.warning(f"Không tìm thấy payment với order_code: {order_code}")
            raise HTTPException(404, "Không tìm thấy payment")
        
        # 4. Kiểm tra trạng thái payment
        if payment.status == PaymentStatus.PAID:
            logger.info(f"Payment đã được xử lý: {order_code}")
            return {"message": "Payment đã được xử lý"}
        
        # 5. Cập nhật payment status thành PAID
        payment.status = PaymentStatus.PAID
        payment.paid_at = datetime.utcnow()
        payment.payos_reference = webhook_data.get("reference")
        payment.payos_account_number = webhook_data.get("accountNumber")
        if webhook_data.get("transactionDateTime"):
            payment.transaction_datetime = datetime.fromisoformat(
                webhook_data["transactionDateTime"].replace("Z", "+00:00")
            )
        
        # 6. Cộng token vào tài khoản user
        user = payment.user
        new_balance = user.token_balance + payment.tokens
        
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(token_balance=new_balance)
        )
        
        await db.commit()
        
        logger.info(f"Thanh toán thành công! User {user.username} nhận {payment.tokens} token. Balance mới: {new_balance}")
        
        return {
            "message": "Webhook xử lý thành công",
            "order_code": order_code,
            "tokens_added": payment.tokens,
            "new_balance": new_balance
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lỗi xử lý webhook: {e}")
        await db.rollback()
        raise HTTPException(500, f"Lỗi xử lý webhook: {str(e)}")
    
@router.get("/status/{order_code}", response_model=PaymentStatusResponse)
async def get_payment_status(
    order_code: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Kiểm tra trạng thái thanh toán"""

    # Tìm payment của user
    payment = await db.scalar(
        select(Payment)
        .where(
            Payment.order_code == order_code,
            Payment.user_id == current_user.id
        )
    )
    
    if not payment:
        raise HTTPException(404, "Không tìm thấy payment")
    
    # Nếu payment vẫn pending, kiểm tra với PayOS API
    if payment.status == PaymentStatus.PENDING and payos_client:
        try:
            payos_info = await payos_client.getPaymentLinkInformation(order_code)
            
            # Cập nhật status nếu PayOS có thông tin mới
            if payos_info.status == "PAID" and payment.status != PaymentStatus.PAID:
                payment.status = PaymentStatus.PAID
                payment.paid_at = datetime.utcnow()
                
                # Cộng token cho user
                await db.execute(
                    update(User)
                    .where(User.id == current_user.id)
                    .values(token_balance=User.token_balance + payment.tokens)
                )
                
                await db.commit()
                
            elif payos_info.status == "CANCELLED":
                payment.status = PaymentStatus.CANCELLED
                await db.commit()
                
        except Exception as e:
            logger.warning(f"Không thể kiểm tra PayOS status: {e}")
    
    return PaymentStatusResponse(
        payment_id=str(payment.id),
        order_code=payment.order_code,
        status=payment.status,
        amount=payment.amount,
        description=payment.description,
        created_at=payment.created_at,
        paid_at=payment.paid_at
    )

@router.get("/history", response_model=List[PaymentStatusResponse])
async def get_payment_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 10,
    offset: int = 0
):
    """Lấy lịch sử thanh toán của user"""

    payments = await db.execute(
        select(Payment)
        .where(Payment.user_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return [
        PaymentStatusResponse(
            payment_id=str(payment.id),
            order_code=payment.order_code,
            status=payment.status,
            amount=payment.amount,
            description=payment.description,
            created_at=payment.created_at,
            paid_at=payment.paid_at
        )
        for payment in payments.scalars().all()
    ]

@router.get("/packages")
async def get_token_packages():
    """Lấy danh sách gói token có sẵn"""

    packages = []
    for package_id, package_info in TOKEN_PACKAGES.items():
        packages.append({
            "id": package_id,
            "name": package_info["name"],
            "price": package_info["price"],
            "tokens": package_info["tokens"],
            "description": package_info["description"],
            "price_per_token": round(package_info["price"] / package_info["tokens"], 2)
        })
    
    return {"data": packages}

@router.post("/cancel/{order_code}")
async def cancel_payment(
    order_code: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Hủy payment (nếu chưa thanh toán)"""
    
    payment = await db.scalar(
        select(Payment)
        .where(
            Payment.order_code == order_code,
            Payment.user_id == current_user.id,
            Payment.status == PaymentStatus.PENDING
        )
    )
    
    if not payment:
        raise HTTPException(404, "Không tìm thấy payment hoặc payment đã được xử lý")
    
    try:
        # Hủy payment trên PayOS (nếu có thể)
        if payos_client and payment.payos_payment_id:
            await payos_client.cancelPaymentLink(
                order_id=order_code,
                cancellationReason="Người dùng hủy"
            )
    except Exception as e:
        logger.warning(f"Không thể hủy payment trên PayOS: {e}")
    
    # Cập nhật status trong database
    payment.status = PaymentStatus.CANCELLED
    await db.commit()
    
    return {"message": "Payment đã được hủy thành công"}

# Success/Cancel page handlers
@router.get("/success")
async def payment_success(
    orderCode: int = None,
    status: str = None
):
    """Trang success sau khi thanh toán thành công"""
    
    if orderCode and status == "PAID":
        message = f"Thanh toán thành công! Mã đơn hàng: {orderCode}"
    else:
        message = "Thanh toán đã được thực hiện. Vui lòng kiểm tra trạng thái trong ứng dụng."
    
    return {
        "message": message,
        "order_code": orderCode,
        "status": status,
        "redirect_info": "Bạn có thể đóng trang này và quay lại ứng dụng"
    }

@router.get("/cancel")
async def payment_cancel(
    orderCode: int = None
):
    """Trang cancel khi người dùng hủy thanh toán"""
    
    return {
        "message": "Thanh toán đã bị hủy",
        "order_code": orderCode,
        "redirect_info": "Bạn có thể đóng trang này và thử lại trong ứng dụng"
    } 