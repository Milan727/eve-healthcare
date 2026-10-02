import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Diagnostic test name")
    description: Optional[str] = Field(None, description="Detailed test description")
    category: Optional[str] = Field(None, max_length=100, description="Test category e.g. Pathology, Radiology")


class TestUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class TestResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
