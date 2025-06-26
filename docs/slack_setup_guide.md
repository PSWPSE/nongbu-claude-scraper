# NongBu 금융 시스템 Slack Bot 설정 가이드

## 📋 필요한 Bot 권한 (OAuth Scopes)

### Bot Token Scopes
다음 권한들을 추가해야 합니다:

```
chat:write          # 메시지 전송
chat:write.public   # 공개 채널에 메시지 전송
channels:read       # 채널 정보 읽기
groups:read         # 비공개 채널 정보 읽기
im:read            # DM 정보 읽기
mpim:read          # 그룹 DM 정보 읽기
users:read         # 사용자 정보 읽기
files:write        # 파일 업로드
```

### User Token Scopes (선택사항)
```
channels:read      # 채널 목록 조회
```

## 🔧 설정 단계

### 1. OAuth & Permissions 설정
1. 좌측 메뉴에서 "OAuth & Permissions" 클릭
2. "Scopes" 섹션에서 "Bot Token Scopes" 찾기
3. 위의 권한들을 하나씩 추가
4. "Install to Workspace" 버튼 클릭
5. 권한 승인

### 2. Bot Token 복사
- "Bot User OAuth Token" 복사 (xoxb-로 시작)
- 이 토큰을 환경 변수에 설정

### 3. 채널 설정
1. Slack에서 #financial-news 채널 생성
2. 봇을 채널에 초대: `/invite @NongBu Financial Bot`

## 🔐 보안 주의사항
- 토큰을 절대 코드에 하드코딩하지 마세요
- .env 파일을 .gitignore에 추가하세요
- 프로덕션에서는 환경 변수로 관리하세요 