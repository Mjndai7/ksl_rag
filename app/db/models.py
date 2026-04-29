from sqlalchemy import Column,String
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(
        String,
        primary_key=True,
        default=lambda:
            str(uuid.uuid4())
    )

    title = Column(String)
    source = Column(String)

    checksum = Column(
        String,
        unique=True,
    )