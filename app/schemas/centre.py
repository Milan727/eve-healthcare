import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CentreCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Centre name")
    location: str = Field(..., min_length=1, max_length=500, description="Centre location / address")
    contact_number: Optional[str] = Field(None, max_length=50)


class CentreUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, min_length=1, max_length=500)
    contact_number: Optional[str] = None
    is_active: Optional[bool] = None


class CentreTestAssign(BaseModel):
    test_id: uuid.UUID
    price: float = Field(..., gt=0, description="Price for this test at this specific centre")
    is_available: bool = Field(True, description="Whether the test is currently available at this centre")


class CentreTestResponse(BaseModel):
    test_id: uuid.UUID
    test_name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float
    is_available: bool

    model_config = {"from_attributes": True}


class CentreResponse(BaseModel):
    id: uuid.UUID
    name: str
    location: str
    contact_number: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CentreDetailResponse(CentreResponse):
    tests: List[CentreTestResponse] = []
