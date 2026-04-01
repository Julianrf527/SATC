from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Expediente(Base):
    