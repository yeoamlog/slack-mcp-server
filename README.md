# Slack MCP Server - Complete Implementation

## 📋 프로젝트 개요

FastMCP v2를 사용하여 구현한 완전한 Slack API 연동 MCP 서버입니다. 과제 가이드라인에 따라 **필수 기능 4개**, **선택 기능 4개**, 그리고 **보너스 뽀모도로 타이머 기능 4개**를 모두 구현했습니다.

### 🎯 주요 특징

- ✅ **완전한 UTF-8 한글 지원** - 모든 메시지에서 한글 완벽 지원
- ✅ **이중 토큰 시스템** - Bot Token + User Token으로 모든 기능 지원
- ✅ **스마트 파일 업로드** - 크기별 최적 업로드 방식 자동 선택
- ✅ **뽀모도로 타이머** - 자동 알림 기능이 포함된 시간 관리 도구
- ✅ **비동기 처리** - 고성능 asyncio 기반 구현
- ✅ **상세한 에러 핸들링** - 모든 API 호출에 대한 적절한 예외 처리

## 🚀 기능 목록

### 🔴 필수 기능 (Required Features - 4개)

1. **`send_slack_message`** - 메시지 전송
   - 채널 또는 DM에 메시지 전송
   - 스레드 답글 지원
   - 완전한 UTF-8 한글 지원

2. **`get_slack_channels`** - 채널 목록 조회
   - 공개/비공개 채널 구분
   - 멤버십 상태 확인
   - 보관된 채널 필터링

3. **`get_slack_channel_history`** - 메시지 히스토리 조회
   - 최신 메시지부터 조회
   - 시간 범위 지정 가능
   - 메시지 메타데이터 포함

4. **`send_slack_direct_message`** - DM 전송
   - 특정 사용자에게 1:1 메시지 전송
   - 자동 DM 채널 생성
   - 봇 사용자 필터링

### 🟡 선택 기능 (Optional Features - 4개)

5. **`get_slack_users`** - 사용자 목록 조회
   - 사용자 타입별 분류 (관리자, 멤버, 게스트, 봇)
   - DM 가능 사용자 필터링
   - 상세한 프로필 정보

6. **`search_slack_messages`** - 메시지 검색 (User Token 필요)
   - 키워드 기반 전체 워크스페이스 검색
   - 정렬 및 필터링 옵션
   - 검색 결과 메타데이터

7. **`upload_file_to_slack`** - 스마트 파일 업로드
   - 파일 크기별 최적 업로드 방식
   - 다양한 파일 형식 지원
   - 자동 미리보기 및 코드 하이라이팅

8. **`add_slack_reaction`** - 메시지 반응 추가
   - 이모지 반응 추가
   - 다양한 이모지 형식 지원

### 🟢 보너스 기능 (Bonus Features - 4개)

9. **`start_pomodoro_timer`** - 뽀모도로 타이머 시작
   - 5가지 타이머 타입 (study, work, break, meeting, custom)
   - 자동 시작/종료 알림
   - 사용자 정의 시간 및 메시지

10. **`cancel_pomodoro_timer`** - 타이머 취소
    - 실행 중인 타이머 즉시 중단
    - 취소 알림 전송

11. **`list_active_timers`** - 활성 타이머 목록
    - 현재 실행 중인 모든 타이머
    - 진행률 및 남은 시간 표시

12. **`get_timer_status`** - 타이머 상태 조회
    - 특정 타이머의 상세 상태
    - 실시간 진행 상황

### 🛠️ 유틸리티 기능

13. **`test_slack_connection`** - 연결 테스트
14. **`get_workspace_info`** - 워크스페이스 정보
15. **`get_file_preview`** - 파일 미리보기
16. **`verify_or_create_file`** - 파일 확인/생성

## 📦 설치 및 실행 방법

### 1. 프로젝트 초기화

```bash
# 프로젝트 클론 또는 다운로드 후
cd slack-mcp

# uv 패키지 매니저 설치 (없는 경우)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 가상환경 생성 및 활성화
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# 의존성 설치
uv sync
# 또는
uv pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음과 같이 설정:

```env
# 필수: Slack Bot Token (xoxb-로 시작)
SLACK_BOT_TOKEN=xoxb-your-bot-token-here

# 선택: Slack User Token (xoxp-로 시작) - 검색, 파일업로드용
SLACK_USER_TOKEN=xoxp-your-user-token-here

# 선택: 기본 채널 ID (테스트용)
SLACK_TEST_CHANNEL_ID=C08UZKK9Q4R

# 선택: 로그 레벨
LOG_LEVEL=INFO
```

### 3. Slack App 설정

#### 필요한 Bot Token Scopes:
```
channels:read        # 채널 목록 조회
channels:history     # 채널 메시지 히스토리 조회
chat:write          # 메시지 전송
im:read             # DM 채널 읽기
im:write            # DM 메시지 전송
im:history          # DM 히스토리 조회
users:read          # 사용자 정보 조회
reactions:write     # 반응 추가
```

#### 추가 User Token Scopes (선택 기능용):
```
search:read         # 메시지 검색
files:write         # 파일 업로드
```

### 4. 서버 실행

```bash
# MCP 서버 실행
python slack_mcp_server.py

# 또는 직접 실행
uv run slack_mcp_server.py
```

## 💡 사용법 및 예시

### 기본 메시지 전송
```python
# Claude/LLM이 도구 호출 시
send_slack_message(
    channel="C08UZKK9Q4R", 
    text="안녕하세요! MCP에서 보내는 메시지입니다! 🚀"
)
```

### 파일 업로드 (스마트 처리)
```python
# 다양한 크기의 파일을 자동으로 최적 방식으로 업로드
upload_file_to_slack(
    file_path="./report.pdf",
    channels="C08UZKK9Q4R",
    title="분석 보고서",
    comment="월간 데이터 분석 결과입니다."
)
```

### 뽀모도로 타이머 사용
```python
# 수업 타이머 시작 (50분)
start_pomodoro_timer(
    timer_type="study",
    channel_id="C08UZKK9Q4R",
    duration_minutes=50,
    custom_name="파이썬 고급 문법 학습"
)

# 활성 타이머 확인
list_active_timers()

# 타이머 취소
cancel_pomodoro_timer("study_20250602_143022_123456")
```

### 메시지 검색 (User Token 필요)
```python
# 워크스페이스 전체에서 메시지 검색
search_slack_messages(
    query="MCP 서버",
    count=10,
    sort="timestamp"
)
```

## 🏗️ 프로젝트 구조

```
slack-mcp/
├── .env                     # 환경 변수 (Git 제외)
├── .env.example            # 환경 변수 템플릿
├── .gitignore              # Git 무시 파일
├── README.md               # 이 파일
├── requirements.txt        # 의존성 목록
├── pyproject.toml         # 프로젝트 설정
├── slack_api_client.py    # Slack API 클라이언트 (핵심 모듈)
├── pomodoro_timer.py      # 뽀모도로 타이머 모듈
└── slack_mcp_server.py    # FastMCP 서버 메인
```

## 🔧 기술적 구현 세부사항

### 이중 토큰 시스템
- **Bot Token (xoxb-)**: 일반적인 봇 기능 (메시지 전송, 채널 조회 등)
- **User Token (xoxp-)**: 사용자 권한 필요한 기능 (검색, 대용량 파일 업로드)

### 스마트 파일 업로드 전략
1. **작은 텍스트 파일 (< 50KB)**: 메시지 내용으로 직접 전송
2. **중간 파일 (50KB - 1MB)**: 코드 스니펫으로 업로드
3. **일반 파일 (1MB - 100MB)**: 표준 파일 업로드
4. **대용량 파일 (100MB - 1GB)**: User Token으로 업로드
5. **초대용량 파일 (> 1GB)**: 파일 정보만 공유

### 비동기 처리 및 동시성
- `asyncio` 기반 완전 비동기 구현
- 뽀모도로 타이머의 병렬 실행 지원
- 락(Lock)을 통한 클라이언트 초기화 안전성 보장

### UTF-8 한글 지원
```python
headers = {
    'Content-Type': 'application/json; charset=utf-8'
}
```

## 🐛 개발 과정에서 겪은 어려움과 해결 방법

### 1. 함수들 간의 Input 변수명 통일 어려움
**문제**: API 함수마다 매개변수 이름이 달라서 일관성 부족
- `channel` vs `channel_id` vs `channels`
- `text` vs `message` vs `content`

**해결책**: 
- Slack API 공식 문서 기준으로 변수명 통일(향후 업데이트 예정)
- 내부 함수에서는 일관된 네이밍 컨벤션 적용
- docstring에 명확한 매개변수 설명 추가

```python
async def send_message(
    self, 
    channel: str,      # 가능한 부분들은 channel 로 통일 예정
    text: str,         # 통일: text
    thread_ts: Optional[str] = None
) -> Dict[str, Any]:
```

### 2. Input-Output 변수명 찾기 어려움
**문제**: Slack API 응답의 복잡한 중첩 구조로 필요한 데이터 추출 어려움

**해결책**:
- API 응답을 로그로 출력하여 구조 파악
- 공통 데이터 추출 함수 작성
- 응답 데이터 정규화 및 포맷팅

```python
# 응답 데이터 정규화 예시
formatted_messages.append({
    'text': msg.get('text', ''),
    'user': msg.get('user', 'Unknown'),
    'timestamp': readable_time,
    'ts': msg.get('ts', ''),
    # ... 필요한 필드만 추출
})
```

### 3. Outdated file_upload 함수를 최신 버전으로 사용하기까지 많은 시행착오
**문제**: Slack의 파일 업로드 API가 여러 번 변경되어 기존 방식 deprecated

**해결책**:
- `files.upload` (deprecated) → `files.getUploadURLExternal` + `files.completeUploadExternal`
- Slack SDK와 기존 REST API의 하이브리드 접근법
- 파일 크기별 다른 업로드 전략 구현

```python
# 새로운 파일 업로드 플로우
# 1. 업로드 URL 요청
upload_response = await self._make_request('files.getUploadURLExternal', 'POST', upload_data)

# 2. 외부 URL로 파일 업로드
async with self._session.put(upload_url, data=file_content) as response:
    # 파일 업로드

# 3. 업로드 완료 처리
complete_response = await self._make_request('files.completeUploadExternal', 'POST', complete_data)
```

### 4. User Token이 필요한 경우 vs Bot Token만으로 해결되는 경우
**문제**: 어떤 기능에 어떤 토큰이 필요한지 파악하기 어려움

**해결책**:
- 기능별 토큰 요구사항 명확히 분류
- 이중 토큰 시스템으로 자동 선택
- 토큰 부족 시 명확한 안내 메시지

```python
# Bot Token으로 가능한 기능
- 메시지 전송 (chat.postMessage)
- 채널 목록 (conversations.list)
- 사용자 목록 (users.list)
- 파일 업로드 (< 100MB)

# User Token이 필요한 기능  
- 메시지 검색 (search.messages)
- 대용량 파일 업로드 (> 100MB)
```

### 5. GET vs POST의 차이
**문제**: 언제 GET을 쓰고 언제 POST를 써야 하는지 혼란

**해결책**:
- Slack API 문서의 HTTP 메소드 정확히 확인
- 데이터 조회는 GET, 데이터 생성/수정은 POST
- 통일된 `_make_request` 함수로 처리

```python
# GET: 데이터 조회
await self._make_request('conversations.list', 'GET', params)
await self._make_request('users.list', 'GET', params)

# POST: 데이터 생성/수정
await self._make_request('chat.postMessage', 'POST', data)
await self._make_request('files.getUploadURLExternal', 'POST', data)
```

### 6. 기타 해결한 이슈들
- **Rate Limiting**: 지수 백오프와 재시도 로직
- **Error Handling**: 각 에러 코드별 맞춤형 해결 제안
- **UTF-8 Encoding**: 한글 메시지 완벽 지원
- **Async Safety**: 뽀모도로 타이머의 동시 실행 처리

## 📊 성능 및 제한사항

### 파일 업로드 제한
- **무료 플랜**: 최대 5GB 워크스페이스 스토리지
- **개별 파일**: 최대 1GB (유료 플랜에서)
- **Bot Token**: 최대 100MB 파일 업로드
- **User Token**: 최대 1GB 파일 업로드

### API Rate Limits
- **Tier 1 메소드**: 1+ per minute
- **Tier 2 메소드**: 20+ per minute  
- **Tier 3 메소드**: 50+ per minute
- **Tier 4 메소드**: 100+ per minute

## 🔍 테스트 방법

### 1. 연결 테스트
```bash
# 서버 실행 후 Claude에서 테스트
test_slack_connection()
```

### 2. 기본 기능 테스트
```bash
# 채널 목록 조회
get_slack_channels()

# 메시지 전송 테스트  
send_slack_message("C08UZKK9Q4R", "테스트 메시지입니다! 🎉")
```

### 3. 고급 기능 테스트
```bash
# 파일 업로드 테스트
upload_file_to_slack("./test.txt", title="테스트 파일")

# 뽀모도로 타이머 테스트
start_pomodoro_timer("work", duration_minutes=25, custom_name="테스트 작업")
```

## 🤝 기여 방법

1. 이슈 제보: GitHub Issues 사용
2. 기능 제안: Feature Request 템플릿 사용  
3. 코드 기여: Pull Request 환영
4. 문서 개선: README 및 docstring 개선

## 📄 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다.

## 🙋‍♂️ 문의 및 지원

- **개발자**: JunHyuck Kwon
- **버전**: 8.5.2 (Complete Implementation)
- **최종 업데이트**: 2025-06-04

---

**과제 완성도**: ✅ 필수 4개 + ✅ 선택 4개 + ✅ 보너스 4개 + ✅ 유틸리티 4개 = **총 16개 기능 완전 구현**

이 프로젝트를 통해 실제 업무에서 활용할 수 있는 고품질 Slack 연동 도구를 구축할 수 있습니다! 🚀