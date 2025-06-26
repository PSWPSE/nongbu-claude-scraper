"""
데이터베이스 모델 정의
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from .app import db

Base = declarative_base()


class ScrapingTarget(db.Model):
    """스크래핑 대상 웹사이트 모델"""
    
    __tablename__ = 'scraping_targets'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, comment='사이트명')
    url = Column(String(500), nullable=False, comment='스크래핑 대상 URL')
    selector = Column(String(200), comment='CSS 셀렉터')
    is_active = Column(Boolean, default=True, comment='활성화 여부')
    scraping_config = Column(JSON, comment='스크래핑 설정 (JSON)')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f'<ScrapingTarget {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'url': self.url,
            'selector': self.selector,
            'is_active': self.is_active,
            'scraping_config': self.scraping_config,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ScrapedContent(db.Model):
    """스크래핑된 원본 콘텐츠 모델"""
    
    __tablename__ = 'scraped_contents'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, db.ForeignKey('scraping_targets.id'), nullable=False)
    title = Column(String(500), comment='콘텐츠 제목')
    content = Column(Text, nullable=False, comment='원본 콘텐츠')
    url = Column(String(500), comment='콘텐츠 원본 URL')
    content_hash = Column(String(64), unique=True, comment='콘텐츠 해시 (중복 방지)')
    meta_data = Column(JSON, comment='추가 메타데이터')
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    target = db.relationship('ScrapingTarget', backref='scraped_contents')
    
    def __repr__(self) -> str:
        return f'<ScrapedContent {self.title[:50] if self.title else "No Title"}...>'


class GeneratedContent(db.Model):
    """생성된 콘텐츠 모델"""
    
    __tablename__ = 'generated_contents'
    
    id = Column(Integer, primary_key=True)
    scraped_content_id = Column(Integer, db.ForeignKey('scraped_contents.id'), nullable=False)
    title = Column(String(500), nullable=False, comment='생성된 콘텐츠 제목')
    content = Column(Text, nullable=False, comment='생성된 콘텐츠 (마크다운)')
    summary = Column(Text, comment='콘텐츠 요약')
    tags = Column(JSON, comment='태그 목록')
    content_type = Column(String(50), default='twitter', comment='콘텐츠 타입')
    is_published = Column(Boolean, default=False, comment='발행 여부')
    published_at = Column(DateTime, comment='발행 시간')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    scraped_content = db.relationship('ScrapedContent', backref='generated_contents')
    
    def __repr__(self) -> str:
        return f'<GeneratedContent {self.title[:50] if self.title else "No Title"}...>'

    def to_dict(self):
        return {
            'id': self.id,
            'scraped_content_id': self.scraped_content_id,
            'title': self.title,
            'content': self.content,
            'summary': self.summary,
            'tags': self.tags,
            'content_type': self.content_type,
            'is_published': self.is_published,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class SlackMessage(db.Model):
    """슬랙 메시지 발송 로그 모델"""
    
    __tablename__ = 'slack_messages'
    
    id = Column(Integer, primary_key=True)
    generated_content_id = Column(Integer, db.ForeignKey('generated_contents.id'), nullable=False)
    channel = Column(String(100), nullable=False, comment='슬랙 채널')
    message_ts = Column(String(50), comment='슬랙 메시지 타임스탬프')
    status = Column(String(20), default='pending', comment='발송 상태')
    error_message = Column(Text, comment='에러 메시지')
    sent_at = Column(DateTime, comment='발송 시간')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계 설정
    generated_content = db.relationship('GeneratedContent', backref='slack_messages')
    
    def __repr__(self) -> str:
        return f'<SlackMessage {self.channel} - {self.status}>'


class ScrapingLog(db.Model):
    """스크래핑 실행 로그 모델"""
    
    __tablename__ = 'scraping_logs'
    
    id = Column(Integer, primary_key=True)
    target_id = Column(Integer, db.ForeignKey('scraping_targets.id'), nullable=False)
    status = Column(String(20), nullable=False, comment='실행 상태')
    items_found = Column(Integer, default=0, comment='발견된 아이템 수')
    items_new = Column(Integer, default=0, comment='새로운 아이템 수')
    error_message = Column(Text, comment='에러 메시지')
    execution_time = Column(Integer, comment='실행 시간 (초)')
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    
    # 관계 설정
    target = db.relationship('ScrapingTarget', backref='scraping_logs')
    
    def __repr__(self) -> str:
        return f'<ScrapingLog {self.target.name if self.target else "Unknown"} - {self.status}>' 