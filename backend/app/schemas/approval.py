from pydantic import BaseModel


class ApprovalResumeRequest(BaseModel):
    transaction_id: str
    approved: bool


class ApprovalResumeResponse(BaseModel):
    transaction_id: str
    status: str
    message: str
