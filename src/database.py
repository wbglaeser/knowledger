from sqlalchemy import create_engine, Column, Integer, String, DateTime, Table, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

ibit_categories = Table('ibit_categories', Base.metadata,
    Column('ibit_id', Integer, ForeignKey('ibits.id')),
    Column('category_id', Integer, ForeignKey('categories.id'))
)

ibit_entities = Table('ibit_entities', Base.metadata,
    Column('ibit_id', Integer, ForeignKey('ibits.id')),
    Column('entity_id', Integer, ForeignKey('entities.id'))
)

ibit_dates = Table('ibit_dates', Base.metadata,
    Column('ibit_id', Integer, ForeignKey('ibits.id')),
    Column('date_id', Integer, ForeignKey('dates.id'))
)

class Ibit(Base):
    __tablename__ = 'ibits'

    id = Column(Integer, primary_key=True)
    text = Column(String)
    source = Column(String)
    date_added = Column(DateTime, default=datetime.datetime.utcnow)
    categories = relationship("Category", secondary=ibit_categories, back_populates="ibits")
    entities = relationship("Entity", secondary=ibit_entities, back_populates="ibits")
    dates = relationship("Date", secondary=ibit_dates, back_populates="ibits")

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    ibits = relationship("Ibit", secondary=ibit_categories, back_populates="categories")

class Entity(Base):
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    linked_to_id = Column(Integer, ForeignKey('entities.id'), nullable=True)  # For entity aliasing
    ibits = relationship("Ibit", secondary=ibit_entities, back_populates="entities")
    linked_to = relationship("Entity", remote_side=[id], foreign_keys=[linked_to_id])  # Self-referential

class Date(Base):
    __tablename__ = 'dates'

    id = Column(Integer, primary_key=True)
    date = Column(String, unique=True)  # Format: YYYY-MM-DD or YYYY-MM or YYYY
    ibits = relationship("Ibit", secondary=ibit_dates, back_populates="dates")

class QuizProgress(Base):
    __tablename__ = 'quiz_progress'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    used_ibit_ids = Column(String)  # Comma-separated list of ibit IDs already shown

def init_db(db_uri="sqlite:///knowledger.db"):
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

