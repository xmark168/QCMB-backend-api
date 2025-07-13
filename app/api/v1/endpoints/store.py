
from typing import List
from fastapi import APIRouter, Depends, HTTPException

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.core.models import Card, User, Inventory
from app.core.schemas import STORE_ITEMS, TOKEN_PACKAGES, CreatePaymentRequest, CreatePaymentResponse, InventoryRead, PurchaseItemData, PurchaseResponse, PurchaseRequest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import update, select


router = APIRouter(prefix="/store", tags=["store"])

@router.get("/items")
async def get_store_items(
    # yêu cầu token
    current_user: User = Depends(get_current_user)
    ):
    """Lấy danh sách store items (hardcode như Android)"""
    
    items = []
    for item_id, item_info in STORE_ITEMS.items():
        items.append({
            "id": item_id,
            "name": item_info["name"],
            "price": item_info["price"],
            "description": item_info["description"],
            "effect_type": item_info["effect_type"]
        })
    
    return {"data": items}

@router.post("/purchase", response_model=PurchaseResponse)
async def purchase_item(
    purchase_data: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Mua item (hardcode logic như Android) - chỉ cho items thường, không phải gói token"""

    # 1. Validate item từ hardcode list
    if purchase_data.item_id not in STORE_ITEMS:
        raise HTTPException(404, "Item không tồn tại")
    
    item_info = STORE_ITEMS[purchase_data.item_id]
    
    # 2. Kiểm tra xem có phải gói token không - nếu phải thì redirect đến payment API
    if item_info["effect_type"].startswith("TOKEN_PACKAGE"):
        raise HTTPException(400, {
            "detail": "Gói token cần thanh toán qua PayOS",
            "redirect_to": "/payment/create",
            "package_id": purchase_data.item_id
        })
    
    total_cost = item_info["price"] * purchase_data.quantity

    # 3. Kiểm tra số dư token của người dùng
    if current_user.token_balance < total_cost:
        raise HTTPException(400, "Không đủ token")
    
    # 4. Trừ token balance
    new_balance = current_user.token_balance - total_cost
    await db.execute(
        update(User)
        .where(User.id == current_user.id)
        .values(token_balance=new_balance)
    )

    # 5. Tạo hoặc tìm Card tương ứng
    card_data = None

    # Tìm xem đã có Card nào cho store item này chưa
    existing_card = await db.scalar(
        select(Card).where(
            Card.type == item_info["effect_type"],
            Card.title == item_info["name"]
        )
    )

    if not existing_card:
        # Tạo Card mới cho store item
        new_card = Card(
            type=item_info["effect_type"],
            title=item_info["name"],
            description=item_info["description"]
        )
        db.add(new_card)
        await db.flush()  # Để lấy ID
        card_data = new_card
    else:
        card_data = existing_card

    # 6. Thêm Card vào inventory của người dùng
    existing_inventory = await db.scalar(
        select(Inventory)
        .where(
            Inventory.user_id == current_user.id,
            Inventory.card_id == card_data.id
        )
    )

    if existing_inventory:
        new_quantity = existing_inventory.quantity + purchase_data.quantity
        await db.execute(
            update(Inventory)
            .where(Inventory.id == existing_inventory.id)
            .values(quantity=new_quantity)
        )
        inventory_quantity = new_quantity
    else:
        new_inventory = Inventory(
            user_id=current_user.id,
            card_id=card_data.id,
            quantity=purchase_data.quantity
        )
        db.add(new_inventory)
        inventory_quantity = purchase_data.quantity
    
    await db.commit()

    # 7. Response với hardcode item info
    purchased_item = {
        "id": purchase_data.item_id,
        "name": item_info["name"],
        "price": item_info["price"],
        "description": item_info["description"],
        "effect_type": item_info["effect_type"],
        "quantity": purchase_data.quantity
    }
    
    return PurchaseResponse(
        data=PurchaseItemData(
            item=purchased_item,
            new_balance=new_balance,
            inventory_quantity=inventory_quantity
        )
    )

@router.get("/inventory", response_model=List[InventoryRead])
async def get_user_inventory(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lấy inventory của user từ database"""
    
    inventory_items = await db.execute(
        select(Inventory)
        .options(selectinload(Inventory.card))
        .where(Inventory.user_id == current_user.id)
    )
    
    return inventory_items.scalars().all()

@router.post("/topup", response_model=CreatePaymentResponse)
async def create_topup(
    request: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    API để tạo PayOS payment link cho gói token.
    Đây là API mà Android app gọi khi user bấm mua gói token.
    """
    
    # Validate package_id
    if request.package_id not in TOKEN_PACKAGES:
        raise HTTPException(404, f"Gói token {request.package_id} không tồn tại")
    
    # Gọi payment API để tạo PayOS link
    # Import payment functions
    from .payment import create_payment

    try:
        payment_response = await create_payment(request, current_user, db)
        
        # Return response với format Android app expect
        return {
            "checkout_url": payment_response.checkout_url,
            "payment_id": payment_response.payment_id,
            "order_code": payment_response.order_code,
            "package_info": payment_response.package_info,
            "amount": payment_response.amount,
            "status": payment_response.status
        }
        
    except Exception as e:
        raise HTTPException(500, f"Không thể tạo payment: {str(e)}")
