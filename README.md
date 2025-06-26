# 🚀 NongBu Claude 4 Sonnet Pro - Financial News Scraper & AI Content Generator

고급 금융 뉴스 스크래핑 및 AI 기반 콘텐츠 생성 시스템입니다. 다중 소스에서 금융 뉴스를 수집하고, Claude AI를 활용해 한국 투자자를 위한 분석 콘텐츠를 자동 생성합니다.

## ✨ 주요 기능

### 🔍 **고급 스크래핑 시스템**
- **5개 주요 금융 뉴스 소스**: BBC Business, AP News, NPR Business, FINVIZ, Yahoo Finance
- **다중 추출 기술**: Trafilatura, Newspaper3k, Readability, BeautifulSoup
- **지능적 콘텐츠 필터링**: 금융 관련성 검증 및 품질 점수 기반 선별
- **차단 방지 기능**: User-Agent 로테이션, 적응형 딜레이, 사이트별 최적화

### 🤖 **AI 콘텐츠 생성**
- **Claude 4 Sonnet Pro** 기반 전문 금융 분석
- **한국 투자자 맞춤**: 달러/원화 환율, 국내 영향 분석
- **구조화된 템플릿**: 핵심 내용, 배경, 파급효과, 투자 포인트
- **마크다운 자동 저장**: 생성된 콘텐츠 파일 관리

### 📊 **웹 대시보드**
- **실시간 모니터링**: 수집/생성 콘텐츠 현황
- **무한 스크롤**: 페이지네이션 지원
- **스케줄러**: 자동 수집 토글 기능
- **콘텐츠 관리**: 삭제, 마크다운 저장 등

## 🛠 설치 및 실행

### 필수 요구사항
- Python 3.8+
- Claude API 키

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 대시보드 실행
```bash
python dashboard.py
```

### 3. 브라우저 접속
```
http://localhost:8001
```

## 📁 프로젝트 구조

```
xtweet/
├── advanced_scraper.py      # 고급 스크래핑 엔진
├── dashboard.py             # 웹 대시보드 메인
├── src/xtweet/
│   ├── content_templates.py # AI 생성 템플릿
│   ├── models.py           # 데이터베이스 모델
│   └── ...
├── instance/               # 데이터베이스 파일
├── saved_markdown/         # 생성된 마크다운 파일
└── logs/                  # 로그 파일
```

## 🔧 핵심 컴포넌트

### Advanced Scraper
```python
from advanced_scraper import AdvancedScraper

scraper = AdvancedScraper(use_selenium=False)
results = scraper.scrape_all_targets()
```

### 콘텐츠 필터링
- **블랙리스트 패턴**: AP News 소개글 등 의미없는 콘텐츠 차단
- **최소 길이**: 300자 이상 콘텐츠만 수집
- **금융 관련성**: 키워드 기반 점수 4점 이상 필요
- **품질 점수**: 달러 금액, 퍼센트, 날짜 등 구체적 정보 포함도

### AI 생성 템플릿
```
🇺🇸 [한국어 제목 + 이모지]
🚨 핵심 내용 (4개 포인트)
⚡ 배경 및 경위
🎯 파급효과 & 의미 (시장 영향 + 투자 관점)
```

## 📊 스크래핑 대상 사이트

| 사이트 | URL | 특화 분야 | 방식 |
|--------|-----|-----------|------|
| BBC Business | bbc.com/business | 글로벌 경제 | requests |
| AP News | apnews.com/hub/business | 기업 뉴스 | requests |
| NPR Business | npr.org/sections/business | 경제 정책 | requests |
| FINVIZ | finviz.com/news.ashx | 주식 데이터 | requests |
| Yahoo Finance | finance.yahoo.com/news | 종합 금융 | requests |

## ⚙️ 설정 파일

### collection_settings.json
```json
{
  "keywords": ["stocks", "market", "investment"],
  "min_content_length": 300,
  "max_articles_per_site": 10
}
```

### scraping_config.json
```json
{
  "request_delay": 2,
  "timeout": 30,
  "user_agent_rotation": true
}
```

## 🔄 API 엔드포인트

### 수집 관련
- `POST /api/manual-collection` - 수동 스크래핑 실행
- `GET /api/scraped-content-detailed` - 수집된 콘텐츠 목록
- `DELETE /api/delete-all-scraped-content` - 수집 콘텐츠 삭제

### 생성 관련
- `POST /api/generate-content` - AI 콘텐츠 생성
- `GET /api/generated-content-detailed` - 생성된 콘텐츠 목록
- `POST /api/save-content-markdown` - 마크다운 저장

### 시스템
- `GET /api/stats` - 시스템 통계
- `POST /api/scheduler-toggle` - 스케줄러 토글

## 🧪 테스트

```bash
# 스크래핑 테스트
python -m pytest tests/test_scraper.py

# 콘텐츠 생성 테스트
python -m pytest tests/test_content_generator.py
```

## 📈 성능 특징

- **다중 채널**: 5개 사이트 동시 스크래핑
- **지능적 필터링**: 관련성 검증으로 품질 보장
- **차단 방지**: User-Agent 로테이션 및 적응형 딜레이
- **실시간 대시보드**: 무한 스크롤 및 페이지네이션
- **자동 저장**: 마크다운 파일 자동 생성

## 🔒 보안 고려사항

- API 키는 환경변수 또는 별도 설정 파일 관리
- 데이터베이스 파일 (.db) 제외
- 민감한 로그 파일 제외
- ChromeDriver 등 임시 파일 제외

## 🤝 기여 방법

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 라이선스

MIT License - 자세한 내용은 LICENSE 파일 참조

## 📞 지원

문제 발생 시 GitHub Issues를 통해 문의해주세요.

---

**Built with ❤️ for Korean Investors** 