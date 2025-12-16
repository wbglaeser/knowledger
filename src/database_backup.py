from sqlalchemy import create_engine, Column, Integer, String, DateTime, Table, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    telegram_user_id = Column(String, unique=True, nullable=True)
    linking_code = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)

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
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    text = Column(String)
    source = Column(String)
    date_added = Column(DateTime, default=datetime.datetime.utcnow)
    user = relationship("User")
    categories = relationship("Category", secondary=ibit_categories, back_populates="ibits")
    entities = relationship("Entity", secondary=ibit_entities, back_populates="ibits")
    dates = relationship("Date", secondary=ibit_dates, back_populates="ibits")

    __table_args__ = (UniqueConstraint('user_id', 'name', name='unique_category_per_user'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String)
    user = relationship("User"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    ibits = relationship("Ibit", secondary=ibit_categories, back_populates="categories")
    __table_args__ = (UniqueConstraint('user_id', 'name', name='unique_entity_per_user'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String)
    linked_to_id = Column(Integer, ForeignKey('entities.id'), nullable=True)  # For entity aliasing
    user = relationship("User", foreign_keys=[user_id])
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    linked_to_id = Column(Integer, ForeignKey('entities.id'), nullable=True)  # For entity aliasing
    ibits = relationship("Ibit", secondary=ibit_entities, back_populates="entities")
    linked_to = relationship("Entity", remote_side=[id], foreign_keys=[linked_to_id])  # Self-referential
    __table_args__ = (UniqueConstraint('user_id', 'date', name='unique_date_per_user'),)

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    date = Column(String)  # Format: YYYY-MM-DD or YYYY-MM or YYYY
    user = relationship("User")

    id = Column(Integer, primary_key=True)
    date = Column(String, unique=True)  # Format: YYYY-MM-DD or YYYY-MM or YYYY
    ibit_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    username = Column(String)  # Legacy field, will be deprecated
    used_ibit_ids = Column(String)  # Comma-separated list of ibit IDs already shown
    user = relationship("User")
class QuizProgress(Base):
    __tablename__ = 'quiz_progress'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    used_ibit_ids = Column(String)  # Comma-separated list of ibit IDs already shown

def init_db(db_uri="sqlite:///knowledger.db"):
    engine = create_engine(db_uri)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

