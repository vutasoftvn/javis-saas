from typing import Literal
from pydantic import BaseModel, StringConstraints
from typing_extensions import Annotated

class OperatingUnitCreate(BaseModel):
    slug: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=255)]

class OfferingCreate(BaseModel):
    operating_unit_id: int
    slug: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{1,98}$")]
    name: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    kind: Literal["product", "service", "hybrid"]
