from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import create_access_token, hash_password, verify_password
from app.models import Permission, Role, User
from app.schemas.rbac import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    RoleCreate,
    RoleListResponse,
    RolePermissionsUpdate,
    RoleRead,
    RoleUpdate,
    UserBrief,
    UserCreate,
    UserListResponse,
    UserRead,
    UserUpdate,
)


def _role_to_read(role: Role) -> RoleRead:
    return RoleRead(
        id=role.id,
        name=role.name,
        key=role.key,
        status=role.status,
        level=role.level,
        is_system=role.is_system,
        permiss=[p.code for p in role.permissions],
    )


def _user_to_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        name=user.username,
        email=user.email,
        phone=user.phone,
        role=user.role.name,
        role_id=user.role_id,
        date=user.created_at.strftime("%Y-%m-%d"),
    )


def _user_brief(user: User) -> UserBrief:
    return UserBrief(
        id=user.id,
        username=user.username,
        role_name=user.role.name,
        role_key=user.role.key,
        level=user.role.level,
    )


def _permission_codes(user: User) -> list[str]:
    return sorted({p.code for p in user.role.permissions})


def _get_user_by_username(db: Session, username: str) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.role).joinedload(Role.permissions))
        .filter(User.username == username)
        .first()
    )


def _get_user_by_id(db: Session, user_id: int) -> User | None:
    return (
        db.query(User)
        .options(joinedload(User.role).joinedload(Role.permissions))
        .filter(User.id == user_id)
        .first()
    )


def _get_role_by_id(db: Session, role_id: int) -> Role | None:
    return db.query(Role).options(joinedload(Role.permissions)).filter(Role.id == role_id).first()


def _assert_min_level(actor: User, required_level: int, message: str = "权限不足") -> None:
    if actor.role.level > required_level:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=message)


def _assert_can_manage_role(actor: User, target_role: Role) -> None:
    if actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅超级管理员可管理角色")
    if target_role.is_system and actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不可修改系统内置角色")


def _assert_can_assign_role(actor: User, target_role: Role) -> None:
    if actor.role.level == 1:
        return
    if actor.role.level == 2 and target_role.level >= 3:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权分配该角色")


def _assert_can_manage_user(actor: User, target: User) -> None:
    if actor.id == target.id and actor.role.level > 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不能修改自己的账号")
    if target.username == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不可操作超级管理员账号")
    if actor.role.level == 1:
        return
    if actor.role.level == 2 and target.role.level >= 3:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权操作该用户")


def login(db: Session, payload: LoginRequest) -> LoginResponse:
    user = _get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")
    if not user.role.status:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色已禁用")
    token = create_access_token(
        subject=user.username,
        user_id=user.id,
        role_key=user.role.key,
        level=user.role.level,
    )
    return LoginResponse(
        access_token=token,
        user=_user_brief(user),
        permissions=_permission_codes(user),
    )


def get_me(user: User) -> MeResponse:
    return MeResponse(user=_user_brief(user), permissions=_permission_codes(user))


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码不正确")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与旧密码相同")
    user.password_hash = hash_password(payload.new_password)
    db.commit()


def list_users(db: Session, actor: User, *, name: str | None = None, page: int = 1, page_size: int = 10) -> UserListResponse:
    _assert_min_level(actor, 2, "仅管理员及以上可查看用户")
    query = db.query(User).options(joinedload(User.role))
    if name:
        query = query.filter(User.username.ilike(f"%{name}%"))
    total = query.count()
    rows = query.order_by(User.id).offset((page - 1) * page_size).limit(page_size).all()
    return UserListResponse(list=[_user_to_read(row) for row in rows], pageTotal=total)


def create_user(db: Session, actor: User, payload: UserCreate) -> UserRead:
    _assert_min_level(actor, 2, "仅管理员及以上可创建用户")
    role = _get_role_by_id(db, payload.role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    _assert_can_assign_role(actor, role)
    if db.query(User).filter(User.username == payload.name).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
    user = User(
        username=payload.name,
        password_hash=hash_password(payload.password),
        email=payload.email,
        phone=payload.phone,
        role_id=payload.role_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    user = _get_user_by_id(db, user.id)
    assert user is not None
    return _user_to_read(user)


def update_user(db: Session, actor: User, user_id: int, payload: UserUpdate) -> UserRead:
    _assert_min_level(actor, 2, "仅管理员及以上可编辑用户")
    user = _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    _assert_can_manage_user(actor, user)
    if payload.name and payload.name != user.username:
        if db.query(User).filter(User.username == payload.name, User.id != user_id).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在")
        user.username = payload.name
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.email is not None:
        user.email = payload.email
    if payload.phone is not None:
        user.phone = payload.phone
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.role_id is not None:
        role = _get_role_by_id(db, payload.role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
        _assert_can_assign_role(actor, role)
        _assert_can_manage_user(actor, user)
        user.role_id = payload.role_id
    db.commit()
    user = _get_user_by_id(db, user_id)
    assert user is not None
    return _user_to_read(user)


def delete_user(db: Session, actor: User, user_id: int) -> None:
    _assert_min_level(actor, 2, "仅管理员及以上可删除用户")
    user = _get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    _assert_can_manage_user(actor, user)
    db.delete(user)
    db.commit()


def list_roles(db: Session, actor: User) -> RoleListResponse:
    _assert_min_level(actor, 2, "仅管理员及以上可查看角色")
    rows = db.query(Role).options(joinedload(Role.permissions)).order_by(Role.level, Role.id).all()
    return RoleListResponse(list=[_role_to_read(row) for row in rows], pageTotal=len(rows))


def create_role(db: Session, actor: User, payload: RoleCreate) -> RoleRead:
    _assert_min_level(actor, 1, "仅超级管理员可创建角色")
    if db.query(Role).filter(Role.key == payload.key).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色标识已存在")
    if payload.level < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自定义角色等级不能高于管理员")
    role = Role(
        name=payload.name,
        key=payload.key,
        level=payload.level,
        is_system=False,
        status=payload.status,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    if payload.permiss:
        update_role_permissions(db, actor, role.id, RolePermissionsUpdate(permiss=payload.permiss))
        role = _get_role_by_id(db, role.id)
    assert role is not None
    return _role_to_read(role)


def update_role(db: Session, actor: User, role_id: int, payload: RoleUpdate) -> RoleRead:
    role = _get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    _assert_can_manage_role(actor, role)
    if payload.name is not None:
        role.name = payload.name
    if payload.status is not None:
        role.status = payload.status
    if payload.level is not None:
        if role.is_system:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统内置角色不可修改等级")
        if payload.level < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="自定义角色等级不能高于管理员")
        role.level = payload.level
    db.commit()
    db.refresh(role)
    if payload.permiss is not None:
        return update_role_permissions(db, actor, role_id, RolePermissionsUpdate(permiss=payload.permiss))
    return _role_to_read(role)


def delete_role(db: Session, actor: User, role_id: int) -> None:
    role = _get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    _assert_can_manage_role(actor, role)
    if role.is_system:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="系统内置角色不可删除")
    if db.query(User).filter(User.role_id == role_id).count() > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="角色下仍有用户，无法删除")
    db.delete(role)
    db.commit()


def update_role_permissions(db: Session, actor: User, role_id: int, payload: RolePermissionsUpdate) -> RoleRead:
    role = _get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在")
    _assert_can_manage_role(actor, role)
    permissions = db.query(Permission).filter(Permission.code.in_(payload.permiss)).all()
    found = {p.code for p in permissions}
    missing = [code for code in payload.permiss if code not in found]
    if missing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未知权限码: {', '.join(missing)}")
    role.permissions = permissions
    db.commit()
    role = _get_role_by_id(db, role_id)
    assert role is not None
    return _role_to_read(role)
