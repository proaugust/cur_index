from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserBrief(BaseModel):
    id: int
    username: str
    role_name: str
    role_key: str
    level: int

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBrief
    permissions: list[str]


class MeResponse(BaseModel):
    user: UserBrief
    permissions: list[str]


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class RoleRead(BaseModel):
    id: int
    name: str
    key: str
    status: bool
    level: int
    is_system: bool
    permiss: list[str]

    model_config = {"from_attributes": True}


class RoleListResponse(BaseModel):
    list: list[RoleRead]
    pageTotal: int


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    key: str = Field(min_length=1, max_length=50)
    status: bool = True
    level: int = Field(default=3, ge=1, le=99)
    permiss: list[str] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    status: bool | None = None
    level: int | None = Field(default=None, ge=1, le=99)
    permiss: list[str] | None = None


class RolePermissionsUpdate(BaseModel):
    permiss: list[str]


class UserRead(BaseModel):
    id: int
    name: str
    email: str | None = None
    phone: str | None = None
    role: str
    role_id: int
    date: str


class UserListResponse(BaseModel):
    list: list[UserRead]
    pageTotal: int


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)
    email: str | None = None
    phone: str | None = None
    role_id: int


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    password: str | None = Field(default=None, min_length=1)
    email: str | None = None
    phone: str | None = None
    role_id: int | None = None
    is_active: bool | None = None


class PermissionRead(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    route_path: str | None = None
    icon: str | None = None
    is_system: bool = True

    model_config = {"from_attributes": True}


class MenuRead(BaseModel):
    id: str
    pid: str | None = None
    title: str
    index: str
    icon: str | None = None
    permiss: str
    is_system: bool = True
    type: str = "menu"
    children: list["MenuRead"] = Field(default_factory=list)


class PermissionTreeNode(BaseModel):
    id: str
    title: str
    type: str
    api_method: str | None = None
    api_path: str | None = None
    children: list["PermissionTreeNode"] = Field(default_factory=list)


class PermissionTreeResponse(BaseModel):
    tree: list[PermissionTreeNode]
    menu_count: int
    api_count: int
    hint: str = (
        "勾选「菜单」控制侧边栏页面是否可见；勾选「接口」控制对应 API 是否允许调用。"
        "菜单与接口需分别勾选，可精细控制每个页面及其内部接口权限。"
    )


class MenuCreate(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    parent_code: str | None = None
    route_path: str | None = None
    icon: str | None = None


class MenuUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_code: str | None = None
    route_path: str | None = None
    icon: str | None = None
