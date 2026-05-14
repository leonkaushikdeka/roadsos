from sqlalchemy import Column, String, Text, BigInteger, ARRAY
from app.database import Base


class ProtocolChunk(Base):
    __tablename__ = "protocol_chunks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    source = Column(String(80), nullable=False)
    language = Column(String(8), default="en")
    chunk_text = Column(Text, nullable=False)
    protocol_type = Column(String(40), nullable=False, index=True)
    tags = Column(ARRAY(String), default=list)
    embedding = Column(String, nullable=True)
