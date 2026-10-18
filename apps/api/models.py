from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


class RegisterReq(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    username: Optional[str] = None
    refCode: Optional[str] = None


class LoginReq(BaseModel):
    email: EmailStr
    password: str


class ForgotReq(BaseModel):
    email: EmailStr


class ResetReq(BaseModel):
    token: str
    password: str = Field(min_length=8)


class VerifyReq(BaseModel):
    token: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None


class StrategyReq(BaseModel):
    name: str
    description: Optional[str] = ""
    engineType: Optional[str] = "signal"
    signalTimeframe: Optional[str] = "1m"
    expiry: Optional[str] = "5m"
    indicators: List[dict] = []
    indicatorSettings: dict = {}
    rules: List[dict] = []
    parameters: dict = {}
    tags: List[str] = []
    category: Optional[str] = "general"
    visibility: Optional[str] = "PRIVATE"
    changelog: Optional[str] = ""


class VisibilityReq(BaseModel):
    visibility: str


class CommentReq(BaseModel):
    body: str
    parentId: Optional[str] = None


class ReportReq(BaseModel):
    targetType: str
    targetId: str
    reason: str
    details: Optional[str] = ""


class AffiliateSubmitReq(BaseModel):
    poUid: str
    email: Optional[str] = None
    note: Optional[str] = ""


class CheckoutReq(BaseModel):
    lookup_key: str
    origin_url: str


class DeviceReq(BaseModel):
    deviceName: Optional[str] = "Chrome Extension"
    installId: str
    extensionVersion: Optional[str] = None


class SyncPushReq(BaseModel):
    strategies: List[dict] = []
    since: Optional[str] = None


class BacktestReq(BaseModel):
    strategyId: str
    strategyVersion: Optional[int] = 1
    market: str
    timeframe: str
    expiry: str
    sampleStart: Optional[str] = None
    sampleEnd: Optional[str] = None
    trades: int
    wins: int
    losses: int
    ties: int = 0


class IndicatorReq(BaseModel):
    name: str
    description: Optional[str] = ""
    category: Optional[str] = "custom"
    parameters: dict = {}
    visibility: Optional[str] = "PRIVATE"


class ScriptReq(BaseModel):
    name: str
    description: Optional[str] = ""
    sourceType: Optional[str] = "PINE"
    source: Optional[str] = ""
    visibility: Optional[str] = "PRIVATE"
    tags: List[str] = []


class PlanReq(BaseModel):
    plans: List[dict]


class SettingsReq(BaseModel):
    key: str
    value: dict


class RoleReq(BaseModel):
    role: str
