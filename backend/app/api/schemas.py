from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.employee import EmploymentType, UserRole


# === Auth ===

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# === Department ===

class DepartmentCreate(BaseModel):
    name: str
    short_name: Optional[str] = None
    parent_id: Optional[int] = None
    cost_center: Optional[str] = None
    manager_id: Optional[int] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    parent_id: Optional[int] = None
    cost_center: Optional[str] = None
    manager_id: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    short_name: Optional[str]
    parent_id: Optional[int]
    cost_center: Optional[str]
    manager_id: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# === Employee ===

class EmployeeCreate(BaseModel):
    personnel_number: str
    ad_username: Optional[str] = None
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    date_of_birth: Optional[date] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    department_id: Optional[int] = None
    role: UserRole = UserRole.EMPLOYEE
    job_title: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.FULLTIME
    weekly_hours: float = 38.5
    hire_date: date
    vacation_days_per_year: int = 30
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    date_of_birth: Optional[date] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    department_id: Optional[int] = None
    role: Optional[UserRole] = None
    job_title: Optional[str] = None
    employment_type: Optional[EmploymentType] = None
    weekly_hours: Optional[float] = None
    exit_date: Optional[date] = None
    is_active: Optional[bool] = None
    vacation_days_per_year: Optional[int] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None


class QualificationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    valid_until: Optional[date]

    model_config = {"from_attributes": True}


class EmployeeResponse(BaseModel):
    id: int
    personnel_number: str
    ad_username: Optional[str]
    first_name: str
    last_name: str
    email: Optional[str]
    phone: Optional[str]
    mobile: Optional[str]
    date_of_birth: Optional[date] = None
    street: Optional[str] = None
    zip_code: Optional[str] = None
    city: Optional[str] = None
    department_id: Optional[int]
    department: Optional[DepartmentResponse] = None
    role: UserRole
    job_title: Optional[str]
    employment_type: EmploymentType
    weekly_hours: float
    hire_date: date
    exit_date: Optional[date]
    is_active: bool
    vacation_days_per_year: int = 30
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    qualifications: list[QualificationResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    id: int
    personnel_number: str
    first_name: str
    last_name: str
    email: Optional[str]
    department_id: Optional[int]
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


# === Qualification ===

class QualificationCreate(BaseModel):
    name: str
    description: Optional[str] = None
    valid_until: Optional[date] = None


# === Pagination ===

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    pages: int
