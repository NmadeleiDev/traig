import pydantic


class FailServerResponse(pydantic.BaseModel):
    message: str
