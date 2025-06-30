from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from .database import Base

class Discipline(Base):

    __tablename__ = 'disciplines'

    name = Column(Integer, nullable=False, primary_key=True)
    groups = Column(ARRAY(String), nullable=False)
    time = Column(String, nullable=False)
    lecture = Column(Boolean, nullable=False, default='False'),
    classroom = Column(String, nullable=True)
    special_data = Column(ARRAY(String), nullable=True)
