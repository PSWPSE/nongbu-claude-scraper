# 설정 템플릿 파일
# 실제 사용 시 이 파일을 config.py로 복사하고 실제 값으로 교체하세요

import os

# Claude API 설정
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', 'your-claude-api-key-here')

# 데이터베이스 경로 설정
DB_PATHS = [
    'src/instance/nongbu_financial.db', 
    'instance/nongbu_financial.db', 
    'instance/nongbu_financial_clean.db', 
    'nongbu_financial.db'
]

# Flask 설정
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# 스크래핑 설정
SCRAPING_CONFIG = {
    'request_delay': 2,
    'timeout': 30,
    'user_agent_rotation': True,
    'max_articles_per_site': 10
}

# 콘텐츠 필터링 설정
CONTENT_FILTER = {
    'min_content_length': 300,
    'min_relevance_score': 4,
    'blacklist_patterns': [
        'the associated press is an independent global news organization',
        'founded in \\d{4}',
        'remains the most trusted source'
    ]
}

# 로깅 설정
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'logs/xtweet.log'
}
