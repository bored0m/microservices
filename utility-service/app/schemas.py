from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    water = "water"
    heating = "heating"
    electricity = "electricity"
    elevator = "elevator"
    cleaning = "cleaning"
    other = "other"


class IssueStatus(str, Enum):
    new = "new"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"


class IssueCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5, max_length=5000)
    category: Category = Category.other
    address: str = Field(min_length=3, max_length=255)


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    category: Category
    address: str
    status: IssueStatus
    author_id: int
    author_username: str
    created_at: datetime
    updated_at: datetime
