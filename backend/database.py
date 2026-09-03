from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    password_hash = Column(String, nullable=False)
    avatar_url = Column(String)
    provider = Column(String)  # email/google/github
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    files = relationship("File", back_populates="user")
    analyses = relationship("Analysis", back_populates="user")
    chat_messages = relationship("ChatMessage", back_populates="user")
    user_categories = relationship("UserCategory")


class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    filename = Column(String, nullable=False)
    file_type = Column(String)  # ofx/csv/xlsx/pdf
    file_size = Column(Integer)
    parsed_data = Column(Text)  # JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="files")
    analyses = relationship("Analysis", back_populates="file")


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="SET NULL"), nullable=True, index=True)
    analysis_type = Column(String)  # full/monthly/investment
    result = Column(Text)  # JSON
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="analyses")
    file = relationship("File", back_populates="analyses")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    role = Column(String)  # user/assistant
    content = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    user = relationship("User", back_populates="chat_messages")


class UserCategory(Base):
    __tablename__ = "user_categories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    name = Column(String, nullable=False)
    keywords = Column(Text)  # JSON array of keywords
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
