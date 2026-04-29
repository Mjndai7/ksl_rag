from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.settings import settings

engine = create_engine(settings.POSTGRES_URL)
SessionLocal = sessionmaker(bind=engine)