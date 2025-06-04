"""
Slack MCP Server - 6.5.2
==========================================

FastMCP v2를 사용한 Slack MCP 서버 구현입니다.
과제 가이드라인에 따라 8개 필수/선택 기능과 뽀모도로 타이머를 포함합니다.

Features (기능):
🔴 Required Features (필수 기능 4개):
- ✅ send_slack_message: 메시지 전송
- ✅ get_slack_channels: 채널 목록 조회
- ✅ get_slack_channel_history: 메시지 히스토리 조회
- ✅ send_slack_direct_message: DM 전송

🟡 Optional Features (선택 기능 4개):
- ✅ get_slack_users: 사용자 목록 조회
- ✅ search_slack_messages: 메시지 검색
- ✅ upload_file_to_slack: 파일 업로드
- ✅ add_slack_reaction: 메시지 반응 추가

🟢 Bonus Features (보너스 기능):
- ✅ start_pomodoro_timer: 뽀모도로 타이머 시작
- ✅ cancel_pomodoro_timer: 타이머 취소
- ✅ list_active_timers: 활성 타이머 목록
- ✅ get_timer_status: 타이머 상태 조회

Author: JunHyuck Kwon  
Version: 6.5.2 (Lazy Initialization)
Updated: 2025-06-02
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone

# FastMCP imports
from fastmcp import FastMCP

# 모듈 imports
from slack_api_client import SlackAPIClient
from pomodoro_timer import PomodoroTimerManager

# ==================== 1. 환경 설정 및 초기화 ====================

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastMCP 서버 인스턴스 생성
mcp = FastMCP(
    name=os.getenv('MCP_SERVER_NAME', 'Slack MCP Server - Complete'),
    dependencies=["aiohttp>=3.9.0", "python-dotenv>=1.0.0"]
)

# 전역 클라이언트 변수들
slack_client: Optional[SlackAPIClient] = None
pomodoro_manager: Optional[PomodoroTimerManager] = None

# 동시성 보호를 위한 락
_initialize_lock = asyncio.Lock()

# ==================== 2. 서버 초기화 ====================

async def initialize_clients() -> tuple[SlackAPIClient, PomodoroTimerManager]:
    """
    Initialize all client modules with thread safety
    
    스레드 안전성을 보장하여 모든 클라이언트 모듈을 초기화합니다.
    
    Returns:
    --------
    tuple[SlackAPIClient, PomodoroTimerManager]
        Initialized Slack client, and pomodoro manager
        (초기화된 Slack 클라이언트, 뽀모도로 매니저)
    """
    global slack_client, pomodoro_manager
    
    # 동시성 보호
    async with _initialize_lock:
        if slack_client is None:
            try:
                # Slack API 클라이언트 초기화
                slack_client = SlackAPIClient()
                
                # 연결 테스트 (봇 토큰)
                bot_connection = await slack_client.test_connection(test_user_token=False)
                if bot_connection['success']:
                    bot_info = bot_connection['bot_info']
                    logger.info(f"✅ Slack Bot Token 연결 성공: {bot_info['user']} ({bot_info['team']})")
                else:
                    logger.error(f"❌ Slack Bot Token 연결 실패: {bot_connection.get('error')}")
                    raise Exception(f"Slack Bot Token 연결 실패: {bot_connection.get('error')}")
                
                # 사용자 토큰 연결 테스트 (선택적)
                if slack_client.user_token:
                    user_connection = await slack_client.test_connection(test_user_token=True)
                    if user_connection['success']:
                        logger.info("✅ Slack User Token 연결 성공 (검색, 파일업로드 기능 사용 가능)")
                    else:
                        logger.warning("⚠️ Slack User Token 연결 실패 (검색, 파일업로드 기능 제한)")
                else:
                    logger.info("ℹ️ User Token 없음 (검색, 파일업로드 기능 제한)")
                
                # 뽀모도로 매니저 초기화
                pomodoro_manager = PomodoroTimerManager(slack_client)
                logger.info("✅ 뽀모도로 매니저 초기화 완료")
                
                logger.info("🎉 모든 모듈 초기화 완료")
                
            except Exception as e:
                logger.error(f"❌ 클라이언트 초기화 실패: {e}")
                raise
    
    return slack_client, pomodoro_manager

# ==================== 3. 필수 기능 (Required Features - 4개) ====================

@mcp.tool()
async def send_slack_message(channel: str, text: str, thread_ts: str = None) -> Dict[str, Any]:
    """
    Send message to Slack channel
    
    UTF-8을 완전히 지원하는 Slack 채널 메시지 전송 기능입니다.
    
    Parameters:
    -----------
    channel : str
        Target channel ID or name (대상 채널 ID 또는 이름)
        Examples: 'C08UZKK9Q4R', '#bot-testserver', 'general'
    text : str
        Message content to send (전송할 메시지 내용)
        Supports Korean, emoji, mentions (한글, 이모지, 멘션 지원)
    thread_ts : str, optional
        Parent message timestamp for thread reply (스레드 답글용 부모 메시지 타임스탬프)
        
    Returns:
    --------
    Dict[str, Any]
        Message sending result (메시지 전송 결과)
        - success: bool (전송 성공 여부)
        - message: str (결과 메시지)
        - channel: str (실제 채널 ID)
        - timestamp: str (메시지 타임스탬프)
        
    Example:
    --------
    LLM can call this tool like:
    >>> send_slack_message("C08UZKK9Q4R", "Hello! MCP에서 보내는 메시지입니다! 🚀")
    """
    if slack_client is None:
        await initialize_clients()
    
    try:
        result = await slack_client.send_message(channel, text, thread_ts)
        
        if result['success']:
            logger.info(f"✅ 메시지 전송 성공: {channel} -> {text[:50]}{'...' if len(text) > 50 else ''}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 메시지 전송 실패: {e}")
        return {
            "success": False,
            "error": f"메시지 전송 중 오류: {str(e)}",
            "suggestion": "네트워크 연결과 채널 권한을 확인해주세요."
        }

@mcp.tool()
async def get_slack_channels(exclude_archived: bool = True, types: str = 'public_channel,private_channel') -> Dict[str, Any]:
    """
    Get list of accessible Slack channels
    
    접근 가능한 Slack 채널 목록을 조회합니다.
    
    Parameters:
    -----------
    exclude_archived : bool, default True
        Whether to exclude archived channels (보관된 채널 제외 여부)
    types : str, default 'public_channel,private_channel' 
        Channel types to include (포함할 채널 타입들)
        
    Returns:
    --------
    Dict[str, Any]
        Channel list with metadata (메타데이터가 포함된 채널 목록)
        - success: bool (조회 성공 여부)
        - channels: List[Dict] (채널 목록)
        - total_count: int (전체 채널 수)
        - member_count: int (봇이 멤버인 채널 수)
        
    Example:
    --------
    LLM can call this to see available channels:
    >>> get_slack_channels()
    """
    if slack_client is None:
        await initialize_clients()

    try:
        channels = await slack_client.get_channels(exclude_archived, types)
        
        # 통계 계산
        member_channels = [ch for ch in channels if ch.get('is_member', False)]
        
        logger.info(f"✅ 채널 목록 조회 성공: {len(channels)}개 채널 (멤버: {len(member_channels)}개)")
        
        return {
            "success": True,
            "channels": channels,
            "total_count": len(channels),
            "member_count": len(member_channels),
            "message": f"{len(channels)}개 채널 조회 완료 (봇이 멤버인 채널: {len(member_channels)}개)"
        }
        
    except Exception as e:
        logger.error(f"❌ 채널 목록 조회 실패: {e}")
        return {
            "success": False,
            "error": f"채널 목록 조회 중 오류: {str(e)}",
            "suggestion": "봇 권한과 스코프를 확인해주세요."
        }

@mcp.tool()
async def get_slack_channel_history(channel_id: str, limit: int = 10, latest: str = None, oldest: str = None) -> Dict[str, Any]:
    """
    Get message history from Slack channel
    
    Slack 채널의 메시지 히스토리를 조회합니다.
    
    Parameters:
    -----------
    channel_id : str
        Channel ID to fetch history from (히스토리를 가져올 채널 ID)
        Example: 'C08UZKK9Q4R'
    limit : int, default 10
        Number of recent messages to fetch (가져올 최근 메시지 수)
    latest : str, optional
        End of time range (시간 범위 끝)
    oldest : str, optional  
        Start of time range (시간 범위 시작)
        
    Returns:
    --------
    Dict[str, Any]
        Message history with metadata (메타데이터가 포함된 메시지 히스토리)
        - success: bool (조회 성공 여부)
        - messages: List[Dict] (메시지 목록)
        - message_count: int (메시지 수)
        - channel_id: str (채널 ID)
        
    Example:
    --------
    LLM can call this to read recent messages:
    >>> get_slack_channel_history("C08UZKK9Q4R", limit=5)
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        messages = await slack_client.get_channel_history(channel_id, limit, latest, oldest)
        
        logger.info(f"✅ 메시지 히스토리 조회 성공: {len(messages)}개 메시지")
        
        return {
            "success": True,
            "messages": messages,
            "message_count": len(messages),
            "channel_id": channel_id or os.getenv('SLACK_TEST_USER_ID'),
            "message": f"채널 {channel_id}에서 {len(messages)}개 메시지 조회 완료"
        }
        
    except Exception as e:
        logger.error(f"❌ 메시지 히스토리 조회 실패: {e}")
        return {
            "success": False,
            "error": f"메시지 히스토리 조회 중 오류: {str(e)}",
            "suggestion": "채널 ID와 봇 권한을 확인해주세요."
        }

@mcp.tool()
async def send_slack_direct_message(user_id: str, text: str) -> Dict[str, Any]:
    """
    Send direct message to specific user
    
    특정 사용자에게 다이렉트 메시지를 전송합니다.
    
    Parameters:
    -----------
    user_id : str
        Target user ID (대상 사용자 ID)
        Example: 'U08VBHQCFME'
    text : str
        Message content to send (전송할 메시지 내용)
        
    Returns:
    --------
    Dict[str, Any]
        DM sending result (DM 전송 결과)
        - success: bool (전송 성공 여부)
        - message: str (결과 메시지)
        - target_user_id: str (대상 사용자 ID)
        - dm_channel_id: str (DM 채널 ID)
        - timestamp: str (메시지 타임스탬프)
        
    Example:
    --------
    LLM can call this to send DMs:
    >>> send_slack_direct_message("U08VBHQCFME", "안녕하세요! MCP에서 보내는 DM입니다.")
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        result = await slack_client.send_direct_message(user_id, text)
        
        if result['success']:
            logger.info(f"✅ DM 전송 성공: {user_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ DM 전송 실패: {e}")
        return {
            "success": False,
            "error": f"DM 전송 중 오류: {str(e)}",
            "suggestion": "사용자 ID와 DM 권한을 확인해주세요."
        }

# ==================== 4. 선택 기능 (Optional Features - 4개) ====================

@mcp.tool()
async def get_slack_users(
    include_bots: bool = False,
    limit: int = 50,
    user_types: str = None
) -> Dict[str, Any]:
    """
    Get workspace users with comprehensive filtering and categorization
    
    포괄적인 필터링과 분류를 지원하는 워크스페이스 사용자 조회 기능입니다.
    
    Parameters:
    -----------
    include_bots : bool, default False
        Whether to include bot users (봇 사용자 포함 여부)
    limit : int, default 50
        Maximum number of users to return (반환할 최대 사용자 수)
    user_types : str, optional
        Filter by specific user types (특정 사용자 타입으로 필터링)
        Comma-separated: 'member,admin,owner,bot'
        
    Returns:
    --------
    Dict[str, Any]
        User list with comprehensive metadata
        - success: bool (조회 성공 여부)
        - users: List[Dict] (사용자 목록)
        - total_count: int (총 사용자 수)
        - user_stats: Dict (사용자 타입별 통계)
        
    Example:
    --------
    LLM can call this to see workspace users:
    >>> get_slack_users()
    >>> get_slack_users(include_bots=True, limit=100)
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        # 사용자 타입 필터링 처리
        user_type_list = None
        if user_types:
            user_type_list = [t.strip() for t in user_types.split(',')]
        
        users = await slack_client.get_users(include_bots, limit, user_type_list)
        
        # 통계 계산
        user_stats = {}
        dm_candidates = 0
        
        for user in users:
            user_type = user.get('user_type', 'member')
            user_stats[user_type] = user_stats.get(user_type, 0) + 1
            
            if user.get('can_receive_dm', False):
                dm_candidates += 1
        
        logger.info(f"✅ 사용자 목록 조회 성공: {len(users)}명 (DM 가능: {dm_candidates}명)")
        
        return {
            "success": True,
            "users": users,
            "total_count": len(users),
            "user_stats": user_stats,
            "dm_candidates_count": dm_candidates,
            "message": f"{len(users)}명 사용자 조회 완료 (DM 가능: {dm_candidates}명)"
        }
        
    except Exception as e:
        logger.error(f"❌ 사용자 목록 조회 실패: {e}")
        return {
            "success": False,
            "error": f"사용자 목록 조회 중 오류: {str(e)}",
            "suggestion": "봇 권한과 users:read 스코프를 확인해주세요."
        }
    
@mcp.tool()
async def search_slack_messages(
    query: str,
    sort: str = 'timestamp',
    sort_dir: str = 'desc',
    count: int = 20
) -> Dict[str, Any]:
    """
    Search messages in workspace using User Token
    
    User Token을 사용한 워크스페이스 메시지 검색 기능입니다.
    
    Parameters:
    -----------
    query : str
        Search query string (검색 쿼리 문자열)
        Examples: 'MCP', 'from:@user', 'in:#channel', 'has:link'
    sort : str, default 'timestamp'
        Sort method: 'timestamp' or 'score' (정렬 방식)
    sort_dir : str, default 'desc'
        Sort direction: 'asc' or 'desc' (정렬 방향)
    count : int, default 20
        Number of results to return (반환할 결과 수)
        
    Returns:
    --------
    Dict[str, Any]
        Search results with comprehensive metadata
        - success: bool (검색 성공 여부)
        - messages: List[Dict] (검색된 메시지 목록)
        - total: int (총 검색 결과 수)
        - query: str (검색 쿼리)
        
    Example:
    --------
    LLM can call this to search messages:
    >>> search_slack_messages("MCP 서버")
    >>> search_slack_messages("from:@jhyuck", count=10)
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        result = await slack_client.search_messages(query, sort, sort_dir, count)
        
        if result['success']:
            logger.info(f"✅ 메시지 검색 성공: '{query}' - {len(result.get('messages', []))}개 결과")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 메시지 검색 실패: {e}")
        return {
            "success": False,
            "error": f"메시지 검색 중 오류: {str(e)}",
            "suggestion": "User Token과 search:read 스코프를 확인해주세요.",
            "query": query
        }

@mcp.tool()
async def upload_file_to_slack(
    file_path: str,
    channels: str = os.getenv('SLACK_TEST_CHANNEL_ID'), 
    title: str = None,
    comment: str = None
) -> Dict[str, Any]:
    """
    Upload file to Slack channel with smart processing
    
    스마트 처리가 포함된 Slack 채널 파일 업로드 기능입니다.
    
    Parameters:
    -----------
    file_path : str
        Path to file to upload (업로드할 파일 경로)
        Supports: PDF, DOC, DOCX, TXT, MD, JPG, PNG, MP3, WAV, MP4, ZIP, etc.
    channel_id : str, default 'C08UZKK9Q4R'
        Target channel ID (대상 채널 ID)
    title : str, optional
        File title (파일 제목)
    comment : str, optional
        File description (파일 설명)
        
    Returns:
    --------
    Dict[str, Any]
        Upload result with processing method
        - success: bool (업로드 성공 여부)
        - method: str (사용된 처리 방식)
        - message: str (결과 메시지)
        - file_info: dict (파일 정보)
        
    Example:
    --------
    LLM can call this to upload files:
    >>> upload_file_to_slack("/path/to/report.pdf", comment="분석 보고서")
    >>> upload_file_to_slack("./data.csv", title="데이터 파일")
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        result = await slack_client.smart_upload(file_path=file_path, channel_id=channels, title=title, comment=comment)
        
        if result['success']:
            logger.info(f"✅ 파일 업로드 성공: {result.get('file_info', {}).get('filename', file_path)} ({result.get('method')})")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 파일 업로드 실패: {e}")
        return {
            "success": False,
            "error": f"파일 업로드 중 오류: {str(e)}",
            "suggestion": "파일 경로와 권한을 확인해주세요."
        }

@mcp.tool()
async def get_file_preview(
    file_path: str,
    max_lines: int = 20
) -> Dict[str, Any]:
    """
    Preview file content without uploading
    
    업로드하지 않고 파일 내용을 미리보기합니다.
    
    Parameters:
    -----------
    file_path : str
        Path to file (파일 경로)
        Example: '/path/to/file.txt', './data.csv'
    max_lines : int, default 20
        Maximum lines to preview (미리보기할 최대 라인 수)
        
    Returns:
    --------
    Dict[str, Any]
        File preview result with content info
        - success: bool (미리보기 성공 여부)
        - file_info: dict (파일 정보)
        - preview_content: str (미리보기 내용, 텍스트 파일인 경우)
        - lines_shown: int (표시된 라인 수)
        
    Example:
    --------
    LLM can call this to preview files:
    >>> get_file_preview("/path/to/report.txt")
    >>> get_file_preview("./data.csv", max_lines=50)
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        # SlackAPIClient의 _get_file_preview 메서드 사용
        result = slack_client._get_file_preview(file_path, max_lines)
        
        if result['success']:
            logger.info(f"✅ 파일 미리보기 성공: {result.get('file_info', {}).get('name', file_path)}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 파일 미리보기 실패: {e}")
        return {
            "success": False,
            "error": f"파일 미리보기 중 오류: {str(e)}",
            "suggestion": "파일 경로를 확인해주세요."
        }

@mcp.tool()
async def add_slack_reaction(
    channel: str,
    timestamp: str,
    emoji: str
) -> Dict[str, Any]:
    """
    Add emoji reaction to specific message
    
    특정 메시지에 이모지 반응을 추가합니다.
    
    Parameters:
    -----------
    channel : str
        Channel ID where the message is located (메시지가 있는 채널 ID)
        Example: 'C08UZKK9Q4R'
    timestamp : str
        Message timestamp (메시지 타임스탬프)
        Example: '1234567890.123456'
    emoji : str
        Emoji name to add (추가할 이모지 이름)
        Examples: 'thumbsup', 'heart', 'rocket', '👍'
        
    Returns:
    --------
    Dict[str, Any]
        Reaction add result (반응 추가 결과)
        - success: bool (추가 성공 여부)
        - message: str (결과 메시지)
        - channel: str (채널 ID)
        - timestamp: str (메시지 타임스탬프)
        - emoji: str (추가된 이모지)
        
    Example:
    --------
    LLM can call this to add reactions:
    >>> add_slack_reaction("C08UZKK9Q4R", "1234567890.123456", "thumbsup")
    >>> add_slack_reaction("C08UZKK9Q4R", "1234567890.123456", "🚀")
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        result = await slack_client.add_reaction(channel, timestamp, emoji)
        
        if result['success']:
            logger.info(f"✅ 반응 추가 성공: {emoji} -> {channel}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 반응 추가 실패: {e}")
        return {
            "success": False,
            "error": f"반응 추가 중 오류: {str(e)}",
            "suggestion": "채널 ID, 타임스탬프, 이모지 이름을 확인해주세요."
        }

@mcp.tool()
async def verify_or_create_file(
    file_path: str,
    content: str = None
) -> Dict[str, Any]:
    """
    Verify or create file based on file path and content

    파일이 존재하는지 확인하거나 내용으로 파일을 생성합니다.
    
    Parameters:
    -----------
    file_path : str
        Path to file (파일 경로)
        Example: '/path/to/file.txt', './data.csv'
    content : str, optional
        Content to write if file doesn't exist (파일이 없을 때 작성할 내용)
        
    Returns:
    --------
    Dict[str, Any]
        File verification/creation result
        - success: bool (성공 여부)
        - path_exists: bool (경로 존재 여부)
        - is_file: bool (파일 여부)
        - file_created: bool (파일 생성 여부)
        - file_path: str (파일 경로)
        - file_info: dict (파일 정보)
        
    Example:
    --------
    LLM can call this to verify or create files:
    >>> verify_or_create_file("/path/to/report.txt")
    >>> verify_or_create_file("./new_file.txt", content="Hello World!")
    """
    file_path_obj = Path(file_path)

    try:
        if file_path_obj.exists():
            # 파일이 존재함
            if not file_path_obj.is_file():
                logger.warning(f"지정된 경로가 파일이 아닙니다: {file_path}")
                return {
                    "success": False,
                    "error": f"지정된 경로가 파일이 아닙니다: {file_path}",
                    "suggestion": "파일 경로를 확인해주세요.",
                    "path_exists": True,
                    "is_file": False
                }
            
            file_stat = file_path_obj.stat()
            file_size = file_stat.st_size
            
            logger.info(f"✅ 파일 존재 확인: {file_path_obj.name} ({file_size} bytes)")

            return {
                "success": True,
                "path_exists": True,
                "is_file": True,
                "file_created": False,
                "file_path": str(file_path_obj),
                "file_info": {
                    "name": file_path_obj.name,
                    "size": file_size,
                    "size_mb": round(file_size / (1024*1024), 2),
                    "extension": file_path_obj.suffix,
                    "modified": datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).isoformat(),
                    "created": datetime.fromtimestamp(file_stat.st_ctime, tz=timezone.utc).isoformat()
                },
                "message": f"파일이 존재합니다: {file_path_obj.name}"
            }
        
        else:
            # 파일이 존재하지 않음
            if not content:
                logger.warning(f"파일이 존재하지 않으며 내용이 제공되지 않았습니다: {file_path_obj}")
                return {
                    "success": False,
                    "error": f"파일이 존재하지 않으며 내용이 제공되지 않았습니다: {file_path_obj}",
                    "suggestion": "파일을 생성하려면 내용을 제공해주세요.",
                    "path_exists": False
                }
            
            try:
                # 필요시 디렉토리 생성
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # 파일 생성
                with open(file_path_obj, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                file_stat = file_path_obj.stat()
                file_size = file_stat.st_size

                logger.info(f"🎉 파일 생성 완료: {file_path_obj.name} ({file_size} bytes)")
                return {
                    "success": True,
                    "path_exists": True,
                    "is_file": True,
                    "file_created": True,
                    "file_path": str(file_path_obj),
                    "file_info": {
                        "name": file_path_obj.name,
                        "size": file_size,
                        "size_mb": round(file_size / (1024*1024), 2),
                        "extension": file_path_obj.suffix,
                        "modified": datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).isoformat(),
                        "created": datetime.fromtimestamp(file_stat.st_ctime, tz=timezone.utc).isoformat()
                    },
                    "message": f"파일이 생성되었습니다: {file_path_obj.name}"
                }
            
            except OSError as e:
                logger.error(f"파일 생성 중 오류 ({file_path_obj}): {e}")
                return {
                    "success": False,
                    "error": f"파일 생성 중 오류: {str(e)}",
                    "suggestion": "디렉토리/파일 쓰기 권한을 확인하거나 관리자 권한으로 실행해주세요.",
                    "path_exists": False,
                    "is_file": False
                }
    
    except Exception as e:
        logger.error(f"파일 처리 중 예기치 않은 오류 ({file_path_obj}): {type(e).__name__}: {e}")
        return {
            "success": False,
            "error": f"파일 처리 중 예기치 않은 오류: {type(e).__name__}: {str(e)}",
            "suggestion": "파일 경로와 권한을 확인해주세요. 문제가 지속되면 시스템 관리자에게 문의하세요.",
            "path_exists": False,
            "is_file": False
        }

# ==================== 5. 뽀모도로 타이머 기능 (Bonus Features - 4개) ====================

@mcp.tool()
async def start_pomodoro_timer(
    timer_type: str,
    channel_id: str = 'C08UZKK9Q4R',
    duration_minutes: int = None,
    custom_name: str = None
) -> Dict[str, Any]:
    """
    Start a pomodoro timer with automatic Slack notifications
    
    자동 Slack 알림 기능이 포함된 뽀모도로 타이머를 시작합니다.
    
    Parameters:
    -----------
    timer_type : str
        Type of timer (타이머 타입)
        Options: 'study', 'work', 'break', 'meeting', 'custom'
    channel_id : str, default 'C08UZKK9Q4R'
        Channel for notifications (알림을 받을 채널 ID)
    duration_minutes : int, optional
        Timer duration in minutes (타이머 지속 시간, 분 단위)
        If not provided, uses default for timer type
    custom_name : str, optional
        Custom name for the timer (타이머의 사용자 정의 이름)
        
    Returns:
    --------
    Dict[str, Any]
        Timer start result (타이머 시작 결과)
        - success: bool (시작 성공 여부)
        - timer_id: str (고유 타이머 ID)
        - timer_type: str (타이머 타입)
        - duration_minutes: int (지속 시간)
        - start_time: str (시작 시간)
        - end_time: str (종료 예정 시간)
        
    Example:
    --------
    LLM can call this to start timers:
    >>> start_pomodoro_timer("study", duration_minutes=50, custom_name="파이썬 학습")
    >>> start_pomodoro_timer("work", custom_name="MCP 서버 개발")
    >>> start_pomodoro_timer("break", duration_minutes=15)
    """
    if pomodoro_manager is None:
        await initialize_clients()
        
    try:
        result = await pomodoro_manager.start_timer(
            timer_type=timer_type,
            channel_id=channel_id,
            duration_minutes=duration_minutes,
            custom_name=custom_name
        )
        
        if result['success']:
            logger.info(f"✅ 뽀모도로 타이머 시작: {result.get('timer_id')} ({timer_type}, {result.get('duration_minutes')}분)")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 뽀모도로 타이머 시작 실패: {e}")
        return {
            "success": False,
            "error": f"뽀모도로 타이머 시작 중 오류: {str(e)}",
            "suggestion": "타이머 타입과 설정을 확인해주세요."
        }

@mcp.tool()
async def cancel_pomodoro_timer(timer_id: str) -> Dict[str, Any]:
    """
    Cancel an active pomodoro timer
    
    활성 뽀모도로 타이머를 취소합니다.
    
    Parameters:
    -----------
    timer_id : str
        Timer ID to cancel (취소할 타이머 ID)
        Example: 'study_20250602_143022_123456'
        
    Returns:
    --------
    Dict[str, Any]
        Cancellation result (취소 결과)
        - success: bool (취소 성공 여부)
        - timer_id: str (타이머 ID)
        - message: str (결과 메시지)
        - timer_info: dict (타이머 정보)
        
    Example:
    --------
    LLM can call this to cancel timers:
    >>> cancel_pomodoro_timer("study_20250602_143022_123456")
    """
    if pomodoro_manager is None:
        await initialize_clients()
        
    try:
        result = await pomodoro_manager.cancel_timer(timer_id)
        
        if result['success']:
            logger.info(f"✅ 뽀모도로 타이머 취소: {timer_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 뽀모도로 타이머 취소 실패: {e}")
        return {
            "success": False,
            "error": f"뽀모도로 타이머 취소 중 오류: {str(e)}",
            "suggestion": "타이머 ID를 확인해주세요."
        }

@mcp.tool()
async def list_active_timers() -> Dict[str, Any]:
    """
    List all active pomodoro timers
    
    현재 활성화된 모든 뽀모도로 타이머 목록을 조회합니다.
    
    Returns:
    --------
    Dict[str, Any]
        Active timers list (활성 타이머 목록)
        - success: bool (조회 성공 여부)
        - active_timers: List[dict] (활성 타이머 목록)
        - total_active: int (총 활성 타이머 수)
        - message: str (결과 메시지)
        
    Example:
    --------
    LLM can call this to see active timers:
    >>> list_active_timers()
    """
    if pomodoro_manager is None:
        await initialize_clients()
        
    try:
        result = await pomodoro_manager.list_active_timers()
        
        if result['success']:
            logger.info(f"✅ 활성 타이머 목록 조회: {result.get('total_active', 0)}개")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 활성 타이머 목록 조회 실패: {e}")
        return {
            "success": False,
            "error": f"활성 타이머 목록 조회 중 오류: {str(e)}",
            "suggestion": "타이머 상태를 확인해주세요."
        }

@mcp.tool()
async def get_timer_status(timer_id: str) -> Dict[str, Any]:
    """
    Get status of specific pomodoro timer
    
    특정 뽀모도로 타이머의 상태를 조회합니다.
    
    Parameters:
    -----------
    timer_id : str
        Timer ID to check (확인할 타이머 ID)
        Example: 'study_20250602_143022_123456'
        
    Returns:
    --------
    Dict[str, Any]
        Timer status information (타이머 상태 정보)
        - success: bool (조회 성공 여부)
        - timer_id: str (타이머 ID)
        - status: str (타이머 상태)
        - timer_info: dict (상세 타이머 정보)
        
    Example:
    --------
    LLM can call this to check timer status:
    >>> get_timer_status("study_20250602_143022_123456")
    """
    if pomodoro_manager is None:
        await initialize_clients()
        
    try:
        result = await pomodoro_manager.get_timer_status(timer_id)
        
        if result['success']:
            logger.info(f"✅ 타이머 상태 조회: {timer_id} ({result.get('status')})")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 타이머 상태 조회 실패: {e}")
        return {
            "success": False,
            "error": f"타이머 상태 조회 중 오류: {str(e)}",
            "suggestion": "타이머 ID를 확인해주세요."
        }

# ==================== 6. 기타 유틸리티 도구들 ====================

@mcp.tool()
async def test_slack_connection() -> Dict[str, Any]:
    """
    Test Slack API connection and get bot information
    
    Slack API 연결을 테스트하고 봇 정보를 확인합니다.
    
    Returns:
    --------
    Dict[str, Any]
        Connection test result (연결 테스트 결과)
        - success: bool (연결 성공 여부)
        - bot_info: Dict (봇 정보, 성공 시)
        - user_token_available: bool (사용자 토큰 사용 가능 여부)
        
    Example:
    --------
    LLM can call this to check Slack connectivity:
    >>> test_slack_connection()
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        # 봇 토큰 테스트
        bot_result = await slack_client.test_connection(test_user_token=False)
        
        # 사용자 토큰 테스트 (선택적)
        user_token_available = False
        if slack_client.user_token:
            user_result = await slack_client.test_connection(test_user_token=True)
            user_token_available = user_result.get('success', False)
        
        if bot_result['success']:
            logger.info("✅ Slack 연결 테스트 성공")
            
            return {
                "success": True,
                "bot_info": bot_result.get('bot_info', {}),
                "user_token_available": user_token_available,
                "message": "Slack 연결이 정상적으로 작동합니다.",
                "capabilities": {
                    "send_messages": True,
                    "read_channels": True,
                    "read_history": True,
                    "send_dm": True,
                    "search_messages": user_token_available,
                    "upload_files": user_token_available
                }
            }
        else:
            logger.error(f"❌ Slack 연결 테스트 실패: {bot_result.get('error')}")
            return bot_result
        
    except Exception as e:
        logger.error(f"❌ 연결 테스트 중 오류: {e}")
        return {
            "success": False,
            "error": f"연결 테스트 중 오류: {str(e)}",
            "suggestion": "봇 토큰과 네트워크 연결을 확인해주세요."
        }

@mcp.tool()
async def get_workspace_info() -> Dict[str, Any]:
    """
    Get comprehensive workspace information
    
    워크스페이스의 종합적인 정보를 조회합니다.
    
    Returns:
    --------
    Dict[str, Any]
        Comprehensive workspace information (종합 워크스페이스 정보)
        - success: bool (조회 성공 여부)
        - workspace: dict (워크스페이스 정보)
        - stats: dict (통계 정보)
        - capabilities: dict (사용 가능한 기능)
        
    Example:
    --------
    LLM can call this to get workspace overview:
    >>> get_workspace_info()
    """
    if slack_client is None:
        await initialize_clients()
        
    try:
        result = await slack_client.get_workspace_info()
        
        if result['success']:
            logger.info("✅ 워크스페이스 정보 조회 성공")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ 워크스페이스 정보 조회 실패: {e}")
        return {
            "success": False,
            "error": f"워크스페이스 정보 조회 중 오류: {str(e)}",
            "suggestion": "봇 권한을 확인해주세요."
        }

# ==================== 7. 메인 서버 실행 ====================

async def main():
    """
    MCP 서버 메인 실행 함수
    
    Main function to run the complete MCP server with all features
    """
    try:
        # 모든 모듈 초기화
        logger.info("🚀 Complete Slack MCP 서버 시작...")
        await initialize_clients()
        
        # MCP 서버 실행 정보
        logger.info("📡 Complete MCP 서버가 준비되었습니다.")
        logger.info("🔴 필수 기능 (Required Features):")
        logger.info("   📨 send_slack_message: 메시지 전송")
        logger.info("   📋 get_slack_channels: 채널 목록 조회")
        logger.info("   📜 get_slack_channel_history: 메시지 히스토리 조회")
        logger.info("   💬 send_slack_direct_message: DM 전송")
        
        logger.info("🟡 선택 기능 (Optional Features):")
        logger.info("   👥 get_slack_users: 사용자 목록 조회")
        logger.info("   🔍 search_slack_messages: 메시지 검색")
        logger.info("   📤 upload_file_to_slack: 파일 업로드")
        logger.info("   📁 get_file_preview: 파일 미리보기")
        logger.info("   😀 add_slack_reaction: 메시지 반응 추가")
        logger.info("   📋 verify_or_create_file: 파일 확인/생성")
        
        logger.info("🟢 보너스 기능 (Bonus Features):")
        logger.info("   ⏰ start_pomodoro_timer: 뽀모도로 타이머 시작")
        logger.info("   ⏹️ cancel_pomodoro_timer: 타이머 취소")
        logger.info("   📋 list_active_timers: 활성 타이머 목록")
        logger.info("   📊 get_timer_status: 타이머 상태 조회")
        
        logger.info("🛠️ 유틸리티 기능:")
        logger.info("   🔌 test_slack_connection: 연결 테스트")
        logger.info("   🏢 get_workspace_info: 워크스페이스 정보")
        
        logger.info("📊 총 등록된 도구: 16개")
        
        # stdio로 MCP 서버 실행
        await mcp.run_stdio_async()
        
    except KeyboardInterrupt:
        logger.info("🛑 서버가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        logger.error(f"❌ 서버 실행 중 오류: {e}")
        raise
    finally:
        # 리소스 정리
        if slack_client:
            await slack_client.close()
        logger.info("🧹 서버 리소스 정리 완료")

if __name__ == "__main__":
    asyncio.run(main())