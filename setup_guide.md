# Slack MCP Server - 상세 설정 가이드

## 📋 목차

1. [Slack App 생성 및 설정](#1-slack-app-생성-및-설정)
2. [개발 환경 설정](#2-개발-환경-설정)
3. [토큰 발급 및 설정](#3-토큰-발급-및-설정)
4. [서버 실행](#4-서버-실행)
5. [Claude/MCP 클라이언트 연결](#5-claudemcp-클라이언트-연결)
6. [기능 테스트](#6-기능-테스트)
7. [트러블슈팅](#7-트러블슈팅)

## 1. Slack App 생성 및 설정

### 1.1 Slack App 생성

1. [Slack API 웹사이트](https://api.slack.com/apps) 접속
2. **"Create New App"** 버튼 클릭
3. **"From scratch"** 선택
4. 앱 정보 입력:
   - **App Name**: `MCP Slack Bot` (원하는 이름)
   - **Pick a workspace**: 개발할 워크스페이스 선택
5. **"Create App"** 클릭

### 1.2 OAuth & Permissions 설정

#### Bot Token Scopes 추가 (필수)

**OAuth & Permissions** 메뉴로 이동하여 다음 스코프들을 **Bot Token Scopes**에 추가:

```
channels:read        # 채널 목록 조회
channels:history     # 채널 메시지 히스토리 조회  
chat:write          # 메시지 전송
im:read             # DM 채널 읽기
im:write            # DM 메시지 전송
im:history          # DM 히스토리 조회
users:read          # 사용자 정보 조회
reactions:write     # 메시지에 반응 추가
```

#### User Token Scopes 추가 (선택사항 - 고급 기능용)

고급 기능(메시지 검색, 대용량 파일 업로드)을 사용하려면 **User Token Scopes**에 추가:

```
search:read         # 메시지 검색
files:write         # 파일 업로드
```

### 1.3 앱 설치

1. **"Install App to Workspace"** 클릭
2. 권한 승인
3. **Bot User OAuth Token** 복사하여 저장 (xoxb-로 시작)
4. (선택사항) **User OAuth Token** 복사하여 저장 (xoxp-로 시작)

### 1.4 봇을 채널에 추가

1. Slack 워크스페이스에서 테스트할 채널로 이동
2. 채널 이름 클릭 → **"Integrations"** → **"Add apps"**
3. 생성한 봇 추가

## 2. 개발 환경 설정

### 2.1 uv 패키지 매니저 설치

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.sh | iex"

# 설치 확인
uv --version
```

### 2.2 프로젝트 설정

```bash
# 프로젝트 디렉토리 생성
mkdir slack-mcp
cd slack-mcp

# 프로젝트 파일들 복사 (소스 코드들)
# - slack_api_client.py
# - pomodoro_timer.py  
# - slack_mcp_server.py
# - requirements.txt
# - pyproject.toml

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# 의존성 설치
uv sync
# 또는
uv pip install -r requirements.txt
```

## 3. 토큰 발급 및 설정

### 3.1 환경 변수 파일 생성

```bash
# .env.example을 .env로 복사
cp .env.example .env
```

### 3.2 .env 파일 수정

```env
# 필수: Slack Bot Token
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token-here

# 선택: Slack User Token (검색, 파일업로드용)
SLACK_USER_TOKEN=xoxp-your-actual-user-token-here

# 선택: 테스트용 채널 ID
SLACK_TEST_CHANNEL_ID=C08UZKK9Q4R
```

### 3.3 채널 ID 찾기

#### 방법 1: Slack 웹/앱에서
1. 채널 이름 클릭
2. **"About"** 탭 하단에서 Channel ID 확인

#### 방법 2: 브라우저 URL에서
```
https://app.slack.com/client/T123456789/C08UZKK9Q4R
                                       ↑ 이 부분이 Channel ID
```

#### 방법 3: 서버 실행 후 조회
```bash
# 서버 실행 후 Claude에서
get_slack_channels()
```

## 4. 서버 실행

### 4.1 직접 실행

```bash
# 가상환경 활성화 확인
source .venv/bin/activate

# 서버 실행
python slack_mcp_server.py

# 성공 시 출력 예시:
# 🚀 Complete Slack MCP 서버 시작...
# ✅ Slack Bot Token 연결 성공: bot_name (workspace_name)
# ✅ 뽀모도로 매니저 초기화 완료
# 📡 Complete MCP 서버가 준비되었습니다.
```

### 4.2 uv로 실행

```bash
uv run slack_mcp_server.py
```

### 4.3 서버 종료

```bash
# Ctrl+C 또는 Cmd+C
# 정상 종료 시: 🧹 서버 리소스 정리 완료
```

## 5. Claude/MCP 클라이언트 연결

### 5.1 Claude Desktop에서 연결

`~/.claude_desktop_config.json` 파일 수정:

```json
{
  "mcpServers": {
    "slack-mcp": {
      "command": "python",
      "args": ["/path/to/your/slack-mcp/slack_mcp_server.py"],
      "env": {
        "PATH": "/path/to/your/slack-mcp/.venv/bin:/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

### 5.2 연결 확인

1. Claude Desktop 재시작
2. 새 대화에서 MCP 도구 사용 가능한지 확인
3. 연결 테스트: "Slack 연결을 테스트해줘"

## 6. 기능 테스트

### 6.1 기본 연결 테스트

```
Claude에게 말하기: "Slack 연결을 테스트해줘"
```

### 6.2 메시지 전송 테스트

```
Claude에게 말하기: "Slack 채널에 '안녕하세요! MCP 테스트입니다.' 라고 메시지 보내줘"
```

### 6.3 채널 목록 조회

```
Claude에게 말하기: "Slack 채널 목록을 보여줘"
```

### 6.4 파일 업로드 테스트

```bash
# 테스트 파일 생성
echo "MCP 파일 업로드 테스트" > test.txt

# Claude에게 말하기
"test.txt 파일을 Slack에 업로드해줘"
```

### 6.5 뽀모도로 타이머 테스트

```
Claude에게 말하기: "25분 업무 타이머를 시작해줘"
```

## 7. 트러블슈팅

### 7.1 일반적인 오류들

#### "SLACK_BOT_TOKEN이 설정되지 않았습니다"
**원인**: `.env` 파일이 없거나 토큰이 설정되지 않음
**해결**:
```bash
# .env 파일 확인
cat .env

# 토큰 형식 확인 (xoxb-로 시작해야 함)
```

#### "missing_scope" 에러
**원인**: Slack App에 필요한 권한이 없음
**해결**:
1. Slack API 웹사이트에서 앱 설정 확인
2. OAuth & Permissions에서 누락된 스코프 추가
3. 앱 재설치

#### "channel_not_found" 에러
**원인**: 잘못된 채널 ID 또는 봇이 채널에 추가되지 않음
**해결**:
1. 채널 ID 확인
2. 봇을 해당 채널에 추가
3. `get_slack_channels()`로 접근 가능한 채널 확인

#### "not_in_channel" 에러
**원인**: 봇이 해당 채널의 멤버가 아님
**해결**:
```
Slack에서 해당 채널로 이동 → @봇이름 입력하여 초대
```

### 7.2 파일 업로드 관련 오류

#### "User Token이 필요합니다"
**원인**: 100MB 이상 파일이나 검색 기능에 User Token 필요
**해결**:
1. Slack App에서 User Token 발급
2. `.env`에 `SLACK_USER_TOKEN` 추가

#### "파일이 너무 큽니다"
**원인**: 파일이 Slack 제한을 초과
**해결**:
```bash
# 파일 크기 확인
ls -lh your_file.txt

# 100MB 이상이면 분할 또는 압축
split -b 50M large_file.txt part_
```

### 7.3 뽀모도로 타이머 관련 오류

#### 타이머 알림이 오지 않음
**원인**: 채널 ID가 잘못되었거나 봇 권한 부족
**해결**:
1. 채널 ID 확인
2. 봇이 채널에 추가되어 있는지 확인

#### 여러 타이머가 동시에 실행되지 않음
**원인**: 정상 동작 - 동시 실행 지원됨
**확인**:
```
Claude에게: "활성 타이머 목록을 보여줘"
```

### 7.4 환경 관련 오류

#### Python 모듈을 찾을 수 없음
**해결**:
```bash
# 가상환경 활성화 확인
which python
# 출력: /path/to/slack-mcp/.venv/bin/python

# 의존성 재설치
uv pip install -r requirements.txt
```

#### Permission denied 오류
**해결**:
```bash
# 실행 권한 추가
chmod +x slack_mcp_server.py

# 디렉토리 권한 확인
ls -la
```

### 7.5 네트워크 관련 오류

#### "network_error" 
**원인**: 인터넷 연결 또는 Slack API 접근 불가
**해결**:
1. 인터넷 연결 확인
2. 방화벽/프록시 설정 확인
3. Slack API 상태 확인: https://status.slack.com/

### 7.6 로그 확인 방법

#### 디버그 모드 실행
```bash
# .env 파일에서 로그 레벨 변경
LOG_LEVEL=DEBUG

# 서버 재실행
python slack_mcp_server.py
```

#### 로그 파일로 저장
```bash
# 로그를 파일로 저장
python slack_mcp_server.py > server.log 2>&1

# 로그 실시간 확인
tail -f server.log
```

## 📞 추가 지원

### 유용한 명령어들

```bash
# 패키지 정보 확인
uv pip list

# 환경 변수 확인
printenv | grep SLACK

# 포트 사용 확인
lsof -i :3000  # MCP 기본 포트

# 프로세스 확인
ps aux | grep slack_mcp_server
```

### 참고 문서

- [Slack API 문서](https://api.slack.com/)
- [FastMCP 문서](https://gofastmcp.com)
- [uv 문서](https://docs.astral.sh/uv/)
- [Python asyncio 문서](https://docs.python.org/3/library/asyncio.html)

### 문의 및 버그 리포트

문제가 지속되면 다음 정보와 함께 문의해주세요:

1. 오류 메시지 전문
2. 서버 로그 (민감한 토큰 정보 제외)
3. 사용 중인 OS 및 Python 버전
4. Slack App 설정 스크린샷 (토큰 제외)

---

이 가이드를 따라하시면 Slack MCP 서버를 성공적으로 설정하고 사용할 수 있습니다! 🚀