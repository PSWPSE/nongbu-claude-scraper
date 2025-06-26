# 🚀 Setup Guide - GitHub 설정 및 환경변수 구성

## 📋 목차
1. [GitHub 리포지토리 생성](#github-리포지토리-생성)
2. [환경변수 설정](#환경변수-설정)
3. [대시보드 실행](#대시보드-실행)
4. [트러블슈팅](#트러블슈팅)

---

## 🐙 GitHub 리포지토리 생성

### 방법 1: GitHub CLI 사용 (권장)

```bash
# GitHub CLI 인증
gh auth login

# 리포지토리 생성 및 푸시
gh repo create nongbu-financial-scraper --public --description "AI-powered financial news scraper with Claude 4 Sonnet Pro"
git remote add origin https://github.com/YOUR_USERNAME/nongbu-financial-scraper.git
git push -u origin main
```

### 방법 2: 웹에서 수동 생성

1. **GitHub 웹사이트 접속**: https://github.com
2. **New Repository 클릭**
3. **리포지토리 설정**:
   - Repository name: `nongbu-financial-scraper`
   - Description: `AI-powered financial news scraper with Claude 4 Sonnet Pro`
   - Public/Private 선택
   - README, .gitignore, License는 체크하지 않음 (이미 생성됨)

4. **Create repository 클릭**

5. **로컬에서 원격 저장소 연결**:
```bash
git remote add origin https://github.com/YOUR_USERNAME/nongbu-financial-scraper.git
git push -u origin main
```

---

## ⚙️ 환경변수 설정

### 1. 환경변수 파일 생성

```bash
# .env.example을 복사하여 .env 파일 생성
cp .env.example .env

# 텍스트 에디터로 .env 파일 편집
nano .env
```

### 2. 필수 환경변수 설정

`.env` 파일에 다음 내용을 입력:

```bash
# Claude API 설정 (필수)
CLAUDE_API_KEY=sk-ant-api03-your-actual-api-key-here

# Flask 설정
SECRET_KEY=your-unique-secret-key-for-flask-sessions
DEBUG=False

# 데이터베이스 설정
DATABASE_URL=sqlite:///src/instance/nongbu_financial.db

# 스크래핑 설정
SCRAPING_DELAY=2
SCRAPING_TIMEOUT=30
MAX_ARTICLES_PER_SITE=10

# 로그 레벨
LOG_LEVEL=INFO
```

### 3. Claude API 키 발급

1. **Anthropic Console 접속**: https://console.anthropic.com
2. **API Keys 섹션으로 이동**
3. **Create Key 클릭**
4. **키 이름 입력** (예: "nongbu-scraper")
5. **생성된 키를 복사하여** `.env` 파일의 `CLAUDE_API_KEY`에 입력

⚠️ **중요**: API 키는 절대 GitHub에 올리지 마세요. `.env` 파일은 `.gitignore`에 포함되어 있습니다.

---

## 🏃‍♂️ 대시보드 실행

### 1. 의존성 설치

```bash
# 가상환경 활성화 (권장)
python -m venv venv
source venv/bin/activate  # Mac/Linux
# venv\Scripts\activate   # Windows

# 패키지 설치
pip install -r requirements.txt
```

### 2. 대시보드 시작

```bash
python dashboard.py
```

### 3. 브라우저 접속

```
http://localhost:8001
```

---

## 🔧 트러블슈팅

### 문제 1: "Claude API 키가 설정되지 않음"

**해결책**:
1. `.env` 파일이 프로젝트 루트에 있는지 확인
2. `CLAUDE_API_KEY=` 다음에 실제 API 키가 입력되었는지 확인
3. API 키에 따옴표나 공백이 없는지 확인

### 문제 2: "데이터베이스 연결 실패"

**해결책**:
1. `src/instance/` 폴더가 존재하는지 확인
2. SQLite 데이터베이스 파일 권한 확인
3. 다음 명령어로 폴더 생성:
```bash
mkdir -p src/instance
```

### 문제 3: GitHub 인증 문제

**해결책**:
```bash
# GitHub CLI 재인증
gh auth logout
gh auth login

# 또는 개인 액세스 토큰 사용
git remote set-url origin https://YOUR_TOKEN@github.com/YOUR_USERNAME/REPO_NAME.git
```

### 문제 4: 포트 충돌

**해결책**:
- 대시보드는 자동으로 사용 가능한 포트 찾음 (8001부터 시작)
- 수동으로 포트 지정하려면 `dashboard.py` 파일 수정

### 문제 5: 스크래핑 차단

**해결책**:
1. VPN 사용
2. `scraping_config.json`에서 딜레이 시간 증가
3. User-Agent 로테이션 확인

---

## 📚 추가 자료

### 프로젝트 구조
```
xtweet/
├── .env                    # 환경변수 (Git 제외)
├── .env.example           # 환경변수 예시
├── dashboard.py           # 메인 대시보드
├── advanced_scraper.py    # 스크래핑 엔진
├── config_template.py     # 설정 템플릿
├── requirements.txt       # Python 의존성
└── src/xtweet/           # 핵심 모듈
```

### 유용한 명령어

```bash
# 로그 실시간 모니터링
tail -f logs/xtweet.log

# 데이터베이스 직접 접근
sqlite3 src/instance/nongbu_financial.db

# 수집된 콘텐츠 확인
curl http://localhost:8001/api/stats

# 수동 스크래핑 실행
curl -X POST http://localhost:8001/api/manual-collection
```

---

## 🔒 보안 체크리스트

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있음
- [ ] API 키가 환경변수로 관리됨
- [ ] 데이터베이스 파일이 Git에서 제외됨
- [ ] SECRET_KEY가 강력한 랜덤 문자열임
- [ ] 프로덕션에서 DEBUG=False 설정

---

## 🆘 도움말

문제가 지속되면 다음 정보와 함께 GitHub Issues에 문의하세요:

1. 운영체제 및 Python 버전
2. 에러 메시지 전문
3. 실행한 명령어
4. `logs/xtweet.log` 파일 내용

**GitHub Issues**: https://github.com/YOUR_USERNAME/nongbu-financial-scraper/issues

---

**🎉 설정 완료 후 대시보드에서 실시간 금융 뉴스 스크래핑을 즐기세요!**
