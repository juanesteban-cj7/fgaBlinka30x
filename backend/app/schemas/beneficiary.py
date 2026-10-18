from pydantic import BaseModel, ConfigDict, Field


class BeneficiaryBase(BaseModel):
    name: str
    allowed: bool = True
    reference_code: str | None = None
    category: str | None = None


class BeneficiaryOut(BeneficiaryBase):
    id: str
    company_id: str
    normalized_name: str

    model_config = ConfigDict(from_attributes=True)


class BeneficiaryCreate(BeneficiaryBase):
    id: str
    company_id: str
    normalized_name: str | None = None


class BeneficiaryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    allowed: bool | None = None
    reference_code: str | None = None
    category: str | None = None
