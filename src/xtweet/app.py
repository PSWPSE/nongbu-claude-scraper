"""
NongBu 금융 투자 정보 시스템 - Flask 애플리케이션
"""

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from typing import Optional

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

# 전역 객체들
db = SQLAlchemy()


def create_app(config_name: Optional[str] = None) -> Flask:
    """NongBu 금융 시스템 Flask 애플리케이션 팩토리"""
    
    # 설정 이름 결정
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Flask 앱 생성
    app = Flask(__name__)
    
    # 설정 로드
    from .config import config
    app.config.from_object(config[config_name])
    
    # 데이터베이스 연결
    db.init_app(app)
    
    # 로깅 설정
    setup_logging(app)
    
    # 블루프린트 등록
    register_blueprints(app)
    
    # 데이터베이스 테이블 생성
    with app.app_context():
        create_tables()
        setup_initial_data(app)
    
    # 스케줄러 설정 (프로덕션에서만)
    if config_name == 'production' and app.config.get('SCHEDULER_API_ENABLED'):
        setup_scheduler(app)
    
    app.logger.info(f"NongBu 금융 시스템이 {config_name} 모드로 시작되었습니다.")
    
    return app


def setup_logging(app):
    """로깅 설정"""
    if not app.debug and not app.testing:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(app.config.get('LOG_FILE', 'logs/nongbu_financial.log'))
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 파일 핸들러 설정
        if app.config.get('LOG_FILE'):
            file_handler = logging.FileHandler(app.config['LOG_FILE'])
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
            ))
            file_handler.setLevel(logging.INFO)
            app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('NongBu 금융 시스템 시작')


def register_blueprints(app):
    """블루프린트 등록"""
    from .routes import bp as api_bp
    app.register_blueprint(api_bp)


def create_tables():
    """데이터베이스 테이블 생성"""
    try:
        db.create_all()
        logging.info("데이터베이스 테이블이 생성되었습니다.")
    except Exception as e:
        logging.error(f"데이터베이스 테이블 생성 실패: {str(e)}")


def setup_initial_data(app):
    """초기 데이터 설정"""
    try:
        from .models import ScrapingTarget
        
        # 기본 금융 타겟이 없으면 추가
        if ScrapingTarget.query.count() == 0:
            default_targets = app.config.get('DEFAULT_FINANCIAL_TARGETS', [])
            
            for target_data in default_targets:
                target = ScrapingTarget(
                    name=target_data['name'],
                    url=target_data['url'],
                    selector=target_data['selector'],
                    scraping_config=target_data.get('config', {}),
                    is_active=True
                )
                db.session.add(target)
            
            if default_targets:
                db.session.commit()
                app.logger.info(f"{len(default_targets)}개의 기본 금융 타겟이 추가되었습니다.")
            
    except Exception as e:
        app.logger.error(f"초기 데이터 설정 실패: {str(e)}")
        db.session.rollback()


def setup_scheduler(app):
    """스케줄러 설정"""
    try:
        from .scheduler import NongBuFinancialScheduler
        
        scheduler = NongBuFinancialScheduler(app)
        scheduler.start()
        
        app.logger.info("NongBu 금융 스케줄러가 시작되었습니다.")
        
        # 앱 종료 시 스케줄러도 종료
        import atexit
        atexit.register(lambda: scheduler.stop())
        
    except Exception as e:
        app.logger.error(f"스케줄러 설정 실패: {str(e)}")


# CLI 지원을 위한 app 인스턴스 생성 함수
def create_cli_app():
    """CLI용 앱 인스턴스 생성"""
    return create_app('development') 