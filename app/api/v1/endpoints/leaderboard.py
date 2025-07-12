from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.v1.endpoints.auth import get_current_user
from app.core.database import get_db
from app.core.models import User
from app.core.schemas import LeaderboardEntry, LeaderboardResponse, UserOut

from app.core.security import decode_access_token
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])
bearer_scheme = HTTPBearer(auto_error=False)

@router.get("/", response_model=LeaderboardResponse)
async def get_leaderboard(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
):
    """
    Lấy bảng xếp hạng top 10 người chơi có điểm cao nhất
    Loại bỏ những người có điểm = 0
    """
    
    # Lấy top 10 users có score > 0, sắp xếp theo score giảm dần
    stmt = (
        select(User)
        .where(User.score > 0)
        .order_by(desc(User.score))
        .limit(10)
    )
    
    result = await db.execute(stmt)
    top_users = result.scalars().all()
    
    # Tạo danh sách leaderboard entries
    leaderboard_entries = []
    for idx, user in enumerate(top_users, start=1):
        user_out = UserOut(
            id=user.id,
            name=user.name,
            username=user.username,
            email=user.email,
            role=user.role.value,
            avatar_url=user.avatar_url or "",
            token_balance=user.token_balance,
            score=user.score
        )

        entry = LeaderboardEntry(
            user=user_out,
            total_score=user.score,
            rank=idx
        )
        leaderboard_entries.append(entry)
    
    # Tính hạng của user hiện tại (nếu có token)
    your_rank = None
    if credentials and credentials.credentials:
        try:
            payload = decode_access_token(credentials.credentials)
            if payload:
                current_user_id = int(payload["sub"])
                
                # Đếm số users có score cao hơn user hiện tại
                user_score_stmt = select(User.score).where(User.id == current_user_id)
                user_score_result = await db.execute(user_score_stmt)
                user_score = user_score_result.scalar()
                
                if user_score is not None and user_score > 0:
                    # Đếm số users có score cao hơn
                    rank_stmt = select(func.count(User.id)).where(User.score > user_score)
                    rank_result = await db.execute(rank_stmt)
                    rank_count = rank_result.scalar()
                    your_rank = rank_count + 1
                    
        except Exception:
            # Nếu token không hợp lệ, bỏ qua
            pass
    return LeaderboardResponse(
        data=leaderboard_entries,
        your_rank=your_rank
    )

@router.post("/update-score")
async def update_user_score(
    score: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cập nhật điểm số cho user hiện tại
    (API này chỉ dùng để test, trong thực tế sẽ được gọi từ game logic)
    """
    if score < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Điểm số phải >= 0"
        )
    
    # Cập nhật điểm số (cộng thêm vào điểm hiện tại)
    current_user.score = (current_user.score or 0) + score
    
    await db.commit()
    await db.refresh(current_user)
    
    return {
        "message": f"Đã cập nhật điểm số thành công",
        "new_score": current_user.score,
        "added_points": score
    } 