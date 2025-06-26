#!/usr/bin/env python3
"""
NongBu 금융 투자 정보 시스템 실행 스크립트

사용법:
    python run.py                    # 개발 모드로 실행
    FLASK_ENV=production python run.py  # 프로덕션 모드로 실행
"""

import os
import sys
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Python 경로에 src 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.xtweet.app import create_app


def main():
    """메인 실행 함수"""
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)
    
    if env == 'development':
        print("🚀 NongBu 금융 시스템을 개발 모드로 시작합니다...")
        print("📊 대시보드: http://localhost:5001")
        print("🔧 API 문서: http://localhost:5001/api/stats")
        
        # 개발 서버 실행
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=True,
            use_reloader=True
        )
    else:
        print("🏢 NongBu 금융 시스템을 프로덕션 모드로 시작합니다...")
        print("📊 대시보드: http://localhost:5001")
        
        # 프로덕션 서버 실행 (gunicorn 권장)
        app.run(
            host='0.0.0.0',
            port=5001,
            debug=False
        )


if __name__ == '__main__':
    main() 