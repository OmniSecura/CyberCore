from pydantic import BaseModel

class CreateUser(BaseModel):
    email: str
    full_name: str
    password: str
