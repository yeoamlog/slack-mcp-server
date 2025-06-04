"""
Slack API Client for FastMCP Server Integration
===============================================

FastMCP 서버와 통합하기 위한 Slack API 클라이언트 모듈입니다.
구조화된 절충안으로 설계되어 확장성과 사용 편의성을 모두 고려했습니다.
UTF-8 한글 지원, 비동기 처리, 상세한 에러 핸들링을 제공합니다.
SDK를 사용하여 file upload 기능을 강화했습니다.

Token Management (토큰 관리):
- Bot Token (xoxb-): 일반적인 봇 기능 (메시지 전송, 채널 조회 등)
- User Token (xoxp-): 사용자 권한이 필요한 기능 (검색, 파일 업로드 등)

Function Organization (함수 구성):
1. Core Infrastructure (핵심 인프라)
2. Connection & Authentication (연결 및 인증)  
3. Message Operations (메시지 작업)
4. Channel Operations (채널 작업)
5. User Operations (사용자 작업)
6. Direct Message Operations (DM 작업)
7. Utility Functions (유틸리티 함수)
8. Additional Features (추가 기능)

Author: JunHyuck Kwon
Version: 6.5.0 (Token Separation)
Updated: 2025-06-02
"""

import os
import json
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class SlackAPIError(Exception):
    """
    Custom exception for Slack API errors with detailed information
    
    Slack API 에러를 위한 커스텀 예외 클래스입니다.
    에러 코드, 응답 데이터, 해결 제안을 포함합니다.
    """
    
    def __init__(self, error_code: str, response_data: Dict[str, Any], suggestion: str = ""):
        self.error_code = error_code
        self.response_data = response_data
        self.suggestion = suggestion
        
        error_message = f"Slack API 에러: {error_code}"
        if suggestion:
            error_message += f"\n💡 해결 제안: {suggestion}"
            
        super().__init__(error_message)


class SlackAPIClient:
    """
    Async Slack API client for MCP server integration with dual token support
    
    이중 토큰 지원을 포함한 FastMCP 서버 통합을 위한 비동기 Slack API 클라이언트입니다.

    Token Types (토큰 타입):
    - Bot Token (xoxb-): General bot operations (일반 봇 작업)
    - User Token (xoxp-): User-level operations like search (검색 등 사용자 수준 작업)

    Features organized by category (카테고리별 구성 기능):
    - Core Infrastructure: Session management, error handling (세션 관리, 에러 처리)
    - Authentication: Connection testing, token validation (연결 테스트, 토큰 검증)
    - Messages: Send, format, thread handling (메시지 전송, 포맷팅, 스레드 처리)
    - Channels: List, history, management (채널 목록, 히스토리, 관리)
    - Users: List, categorize, search (사용자 목록, 분류, 검색)
    - Direct Messages: Send, manage DM channels (DM 전송, DM 채널 관리)
    - Utilities: Helper functions, data formatting (도우미 함수, 데이터 포맷팅)
    - Advanced Features: Search, file upload (검색, 파일 업로드)
    """
    
    BASE_URL = "https://slack.com/api"
    
    def __init__(self, bot_token: Optional[str] = None, user_token: Optional[str] = None):
        """
        Initialize Slack API client with dual token support
        
        이중 토큰 지원으로 Slack API 클라이언트를 초기화합니다.
        
        Parameters:
        -----------
        bot_token : str, optional
            Slack bot token (Slack 봇 토큰)
            If not provided, loads from SLACK_BOT_TOKEN env var
            (제공되지 않으면 환경변수 SLACK_BOT_TOKEN에서 가져옴)
        user_token : str, optional
            Slack user token (Slack 사용자 토큰)
            If not provided, loads from SLACK_USER_TOKEN env var
            (제공되지 않으면 환경변수 SLACK_USER_TOKEN에서 가져옴)
            
        Raises:
        -------
        ValueError
            When bot_token is missing or has invalid format
            (봇 토큰이 없거나 잘못된 형식일 때)
        """
        # Load tokens from environment or parameters
        self.bot_token = bot_token or os.getenv('SLACK_BOT_TOKEN')
        self.user_token = user_token or os.getenv('SLACK_USER_TOKEN')
        
        # Validate bot token (required)
        if not self.bot_token:
            raise ValueError(
                "SLACK_BOT_TOKEN이 설정되지 않았습니다. "
                "환경변수를 확인하거나 bot_token 매개변수를 제공해주세요."
            )
        
        if not self.bot_token.startswith('xoxb-'):
            raise ValueError(
                "잘못된 봇 토큰 형식입니다. 'xoxb-'로 시작해야 합니다."
            )
        
        # Validate user token (optional, but check format if provided)
        if self.user_token and not self.user_token.startswith('xoxp-'):
            logger.warning(
                "User Token 형식이 올바르지 않습니다. 'xoxp-'로 시작해야 합니다. "
                "검색 및 파일 업로드 기능이 제한될 수 있습니다."
            )
            self.user_token = None  # Invalid token, disable user features
        
        # File size limits
        self.text_message = int(os.getenv('TEXT_MESSAGE_LIMIT', '51200'))        # 50KB (free plan)
        self.snippet = int(os.getenv('MEDIUM_FILE_LIMIT', '1048576'))            # 1MB (free plan)
        self.standard = int(os.getenv('STANDARD_FILE_LIMIT', '104857600'))   # 100MB (free plan)
        self.large = int(os.getenv('LARGE_FILE_LIMIT', '1073741824'))        # 1GB (paid plan only)

        # Available file extensions
        self.text_extensions = {
            '.txt', '.md', '.json', '.csv', '.log', '.ini', '.cfg', 
            '.yml', '.yaml', '.xml', '.py', '.js', '.html', '.css'
        }
        
        
        # Environment-based configuration
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.rate_limit_delay = int(os.getenv('RATE_LIMIT_DELAY', '1'))
        self.exponential_backoff_base = int(os.getenv('EXPONENTIAL_BACKOFF_BASE', '2'))
        
        # Customizable user interface icons
        self.user_type_icons = {
            'owner': os.getenv('USER_ICON_OWNER', '👑'),
            'admin': os.getenv('USER_ICON_ADMIN', '🛡️'),
            'member': os.getenv('USER_ICON_MEMBER', '👤'),
            'bot': os.getenv('USER_ICON_BOT', '🤖'),
            'single_channel_guest': os.getenv('USER_ICON_GUEST_SINGLE', '🎫'),
            'multi_channel_guest': os.getenv('USER_ICON_GUEST_MULTI', '👥'),
            'unknown': os.getenv('USER_ICON_UNKNOWN', '❓')
        }
        
        # Status icons
        self.status_icons = {
            'success': os.getenv('ICON_SUCCESS', '✅'),
            'error': os.getenv('ICON_ERROR', '❌'),
            'warning': os.getenv('ICON_WARNING', '⚠️'),
            'info': os.getenv('ICON_INFO', 'ℹ️')
        }
        
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Log token availability
        logger.info("Slack API 클라이언트가 초기화되었습니다.")
        logger.info(f"Bot Token: {'✅ 사용가능' if self.bot_token else '❌ 없음'}")
        logger.info(f"User Token: {'✅ 사용가능' if self.user_token else '❌ 없음 (검색/파일업로드 제한)'}")

    # ==================== 1. CORE INFRASTRUCTURE ====================

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def _ensure_session(self) -> None:
        """Ensure aiohttp session exists for requests"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={'User-Agent': 'SlackMCP/2.5.0'}
            )
            logger.debug("새로운 aiohttp 세션을 생성했습니다.")

    async def close(self) -> None:
        """Clean up session resources"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("aiohttp 세션을 종료했습니다.")

    def _get_headers(self, use_user_token: bool = False) -> Dict[str, str]:
        """
        Get appropriate headers for the request
        
        요청에 적절한 헤더를 가져옵니다.
        
        Parameters:
        -----------
        use_user_token : bool, default False
            Whether to use user token instead of bot token
            (봇 토큰 대신 사용자 토큰 사용 여부)
            
        Returns:
        --------
        Dict[str, str]
            Request headers with appropriate authorization
            (적절한 인증이 포함된 요청 헤더)
            
        Raises:
        -------
        ValueError
            When user token is required but not available
            (사용자 토큰이 필요하지만 사용할 수 없을 때)
        """
        if use_user_token:
            if not self.user_token:
                raise ValueError(
                    "이 기능에는 SLACK_USER_TOKEN이 필요합니다. "
                    "환경변수를 설정하거나 user_token 매개변수를 제공해주세요."
                )
            token = self.user_token
        else:
            token = self.bot_token
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'SlackMCP/7.0.0'
        }

    def _get_error_suggestion(self, error_code: str, response_data: Dict[str, Any]) -> str:
        """Get helpful suggestions for common Slack API errors"""
        suggestions = {
            'missing_scope': f'Slack 앱 설정에서 OAuth 스코프를 추가해주세요. 필요한 스코프: {response_data.get("needed", "확인 필요")}',
            'not_in_channel': '봇이 이 채널에 추가되지 않았습니다. 채널에 봇을 초대해주세요.',
            'channel_not_found': '채널 ID나 이름이 올바른지 확인해주세요. 채널이 삭제되었거나 접근 권한이 없을 수 있습니다.',
            'user_not_found': '사용자 ID가 올바른지 확인해주세요. 사용자가 워크스페이스에 존재하지 않을 수 있습니다.',
            'invalid_auth': '토큰이 유효하지 않거나 만료되었습니다. 새로운 토큰을 생성해주세요.',
            'account_inactive': 'Slack 워크스페이스가 비활성화되었거나 일시 중단되었습니다.',
            'token_revoked': '토큰이 취소되었습니다. Slack 앱 설정에서 새로운 토큰을 생성해주세요.',
            'ratelimited': 'API 요청 한도를 초과했습니다. 잠시 후 다시 시도해주세요.',
            'access_denied': '이 작업에 대한 권한이 없습니다. 스코프와 채널 권한을 확인해주세요.',
            'cannot_dm_bot': '봇 사용자에게는 DM을 보낼 수 없습니다. 일반 사용자 ID를 사용해주세요.',
            'user_disabled': '해당 사용자 계정이 비활성화되었습니다.',
            'not_allowed_token_type': 'search.messages API는 User Token(xoxp-)이 필요합니다. Bot Token으로는 사용할 수 없습니다.',
            'invalid_arguments': 'API 파라미터를 확인해주세요. 필수 필드가 누락되었거나 잘못된 형식일 수 있습니다.',
            'file_too_large': '파일 크기가 너무 큽니다. Slack의 파일 크기 제한을 확인해주세요.',
            'upload_failed': '파일 업로드에 실패했습니다. 네트워크 연결과 파일 권한을 확인해주세요.',
        }
        
        return suggestions.get(
            error_code, 
            f'"{error_code}" 에러에 대한 구체적인 제안이 없습니다. Slack API 문서를 참조해주세요.'
        )
    
    async def _make_request(
        self, 
        endpoint: str, 
        method: str = 'GET', 
        data: Optional[Dict[str, Any]] = None,
        use_user_token: bool = False
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Slack API with appropriate token
        
        적절한 토큰으로 Slack API HTTP 요청을 수행합니다.
        
        Parameters:
        -----------
        endpoint : str
            API endpoint
        method : str, default 'GET'
            HTTP method
        data : Dict[str, Any], optional
            Request data
        use_user_token : bool, default False
            Whether to use user token for this request
            (이 요청에 사용자 토큰 사용 여부)
            
        Returns:
        --------
        Dict[str, Any]
            Slack API response data
            
        Raises:
        -------
        SlackAPIError
            When API request fails
        """
        await self._ensure_session()
        url = f"{self.BASE_URL}/{endpoint}"
        
        # Get appropriate headers based on token type needed
        headers = self._get_headers(use_user_token=use_user_token)
        
        # Request configuration based on HTTP method
        if method.upper() == 'POST':
            request_kwargs = {'json': data, 'headers': headers}
        else:  # GET
            request_kwargs = {'params': data, 'headers': headers}
        
        # Log which token is being used
        token_type = "User Token" if use_user_token else "Bot Token"
        logger.debug(f"{endpoint} 요청 ({token_type} 사용)")
        
        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                async with self._session.request(method.upper(), url, **request_kwargs) as response:
                    response_text = await response.text()
                    
                    # JSON parsing with error handling
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        logger.error(f"{endpoint} 응답의 JSON 파싱 실패. 상태코드: {response.status}")
                        raise SlackAPIError(
                            "json_parse_error",
                            {"raw_response": response_text[:500], "status": response.status},
                            "Slack이 유효하지 않은 JSON을 반환했습니다."
                        )
                    
                    # Check for Slack API errors
                    if not response_data.get('ok', False):
                        error_code = response_data.get('error', 'unknown_error')
                        suggestion = self._get_error_suggestion(error_code, response_data)
                        
                        logger.error(f"{endpoint} API 에러: {error_code} ({token_type})")
                        
                        # Special handling for rate limiting
                        if error_code == 'ratelimited':
                            retry_after = int(response.headers.get('Retry-After', self.rate_limit_delay))
                            logger.warning(f"Rate limit 적용. {retry_after}초 후 재시도... (시도 {attempt + 1}/{self.max_retries})")
                            
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(retry_after)
                                continue
                            else:
                                suggestion += f" 최대 재시도 횟수({self.max_retries})를 초과했습니다."
                        
                        raise SlackAPIError(error_code, response_data, suggestion)
                    
                    # Success case
                    logger.debug(f"{endpoint} 요청 성공 (시도 {attempt + 1}, {token_type})")
                    return response_data
                    
            except aiohttp.ClientError as e:
                logger.warning(f"{endpoint} 네트워크 에러 (시도 {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt == self.max_retries - 1:
                    raise SlackAPIError(
                        "network_error",
                        {"original_error": str(e)},
                        "네트워크 연결을 확인하거나 Slack API 상태를 확인해주세요."
                    )
                
                sleep_time = self.rate_limit_delay * (self.exponential_backoff_base ** attempt)
                logger.debug(f"네트워크 에러 재시도 대기: {sleep_time}초")
                await asyncio.sleep(sleep_time)
            
            except SlackAPIError:
                raise
                
        raise SlackAPIError(
            "max_retries_exceeded",
            {"max_retries": self.max_retries},
            f"최대 재시도 횟수({self.max_retries})를 초과했습니다."
        )

    # ==================== 2. CONNECTION & AUTHENTICATION ====================
    
    async def test_connection(self, test_user_token: bool = False) -> Dict[str, Any]:
        """
        Test Slack API connection and get bot/user information
        
        Slack API 연결을 테스트하고 봇/사용자 정보를 가져옵니다.
        
        Parameters:
        -----------
        test_user_token : bool, default False
            Whether to test user token instead of bot token
            (봇 토큰 대신 사용자 토큰 테스트 여부)
            
        Returns:
        --------
        Dict[str, Any]
            Connection test result with token information
        """
        try:
            response = await self._make_request('auth.test', 'GET', use_user_token=test_user_token)
            
            token_type = "User Token" if test_user_token else "Bot Token"
            logger.info(f"Slack API 연결 테스트 성공 ({token_type})")
            
            return {
                "success": True,
                "token_type": token_type,
                "bot_info": {
                    "user": response.get('user'),
                    "user_id": response.get('user_id'),
                    "team": response.get('team'),
                    "team_id": response.get('team_id'),
                    "url": response.get('url')
                }
            }
            
        except SlackAPIError as e:
            token_type = "User Token" if test_user_token else "Bot Token"
            logger.error(f"Slack API 연결 테스트 실패 ({token_type}): {e}")
            return {
                "success": False,
                "token_type": token_type,
                "error": f"연결 실패: {e.error_code}",
                "suggestion": e.suggestion
            }

    # ==================== 3. MESSAGE OPERATIONS ====================

    async def send_message(
        self, 
        channel: str, 
        text: str, 
        thread_ts: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send message to Slack channel using Bot Token"""
        data = {'channel': channel, 'text': text}
        if thread_ts:
            data['thread_ts'] = thread_ts
            
        logger.info(f"채널 {channel}에 메시지 전송: {text[:50]}{'...' if len(text) > 50 else ''}")
        
        try:
            response = await self._make_request('chat.postMessage', 'POST', data, use_user_token=False)
            
            return {
                "success": True,
                "message": "메시지가 성공적으로 전송되었습니다.",
                "channel": response.get('channel'),
                "timestamp": response.get('ts'),
                "text": text
            }
            
        except SlackAPIError as e:
            logger.error(f"메시지 전송 실패: {e}")
            return {
                "success": False,
                "error": f"메시지 전송 실패: {e.error_code}",
                "suggestion": e.suggestion
            }

    # ==================== 4. CHANNEL OPERATIONS ====================
    
    async def get_channels(
        self, 
        exclude_archived: bool = True, 
        types: str = 'public_channel,private_channel'
    ) -> List[Dict[str, Any]]:
        """Get list of accessible Slack channels using Bot Token"""
        params = {
            'types': types,
            'exclude_archived': 'true' if exclude_archived else 'false',
            'limit': 200
        }
        
        logger.info(f"채널 목록 조회 시작 (타입: {types}, 보관됨 제외: {exclude_archived})...")
        
        try:
            all_channels = []
            cursor = None
            
            while True:
                if cursor:
                    params['cursor'] = cursor
                    
                response = await self._make_request('conversations.list', 'GET', params, use_user_token=False)
                channels_batch = response.get('channels', [])
                all_channels.extend(channels_batch)
                
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
                    
                logger.debug(f"다음 페이지 로드 중... (현재까지 {len(all_channels)}개 채널)")
            
            # Format channel data
            formatted_channels = []
            stats = {'public': 0, 'private': 0}
            
            for ch in all_channels:
                channel_name = ch.get('name', f"channel_{ch.get('id', 'unknown')}")
                is_private = ch.get('is_private', False)
                
                if is_private:
                    stats['private'] += 1
                else:
                    stats['public'] += 1
                
                formatted_channels.append({
                    'id': ch.get('id'),
                    'name': channel_name,
                    'is_private': is_private,
                    'is_member': ch.get('is_member', False),
                    'num_members': ch.get('num_members', 0),
                    'topic': ch.get('topic', {}).get('value', ''),
                    'purpose': ch.get('purpose', {}).get('value', ''),
                    'created': ch.get('created', 0),
                    'is_archived': ch.get('is_archived', False),
                    'is_general': ch.get('is_general', False)
                })
            
            logger.info(f"채널 목록 조회 완료: {len(formatted_channels)}개 채널 - 공개: {stats['public']}, 비공개: {stats['private']}")
            return formatted_channels
            
        except SlackAPIError as e:
            logger.error(f"채널 목록 조회 실패: {e}")
            raise

    async def get_channel_history(
        self, 
        channel_id: str, 
        limit: int = 10, 
        latest: Optional[str] = None,
        oldest: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent message history from Slack channel using Bot Token"""
        default_limit = int(os.getenv('DEFAULT_MESSAGE_LIMIT', '10'))
        limit = max(1, min(limit or default_limit, 1000))
        
        params = {
            'channel': channel_id,
            'limit': limit,
            'inclusive': 'true'
        }
        
        if latest:
            params['latest'] = latest
        if oldest:
            params['oldest'] = oldest
            
        logger.info(f"채널 {channel_id}에서 최대 {limit}개 메시지 히스토리 조회...")
        
        try:
            response = await self._make_request('conversations.history', 'GET', params, use_user_token=False)
            messages_raw = response.get('messages', [])
            
            logger.info(f"메시지 히스토리 조회 완료: {len(messages_raw)}개 메시지")
            
            formatted_messages = []
            for msg in messages_raw:
                if msg.get('type') == 'message' and 'text' in msg:
                    try:
                        ts_float = float(msg.get('ts', 0))
                        readable_time = datetime.fromtimestamp(ts_float).strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, TypeError):
                        readable_time = 'Unknown time'
                    
                    formatted_messages.append({
                        'text': msg.get('text', ''),
                        'user': msg.get('user', 'Unknown'),
                        'user_name': msg.get('username', ''),
                        'timestamp': readable_time,
                        'ts': msg.get('ts', ''),
                        'type': msg.get('type', 'message'),
                        'subtype': msg.get('subtype', ''),
                        'reactions': msg.get('reactions', []),
                        'reply_count': msg.get('reply_count', 0),
                        'thread_ts': msg.get('thread_ts'),
                        'is_edited': 'edited' in msg,
                        'bot_id': msg.get('bot_id'),
                        'app_id': msg.get('app_id')
                    })
            
            return formatted_messages
            
        except SlackAPIError as e:
            logger.error(f"메시지 히스토리 조회 실패: {e}")
            raise

    # ==================== 5. USER OPERATIONS ====================

    def _categorize_user_type(self, user: Dict[str, Any]) -> str:
        """Categorize user type based on Slack user properties"""
        if user.get('is_bot', False):
            return 'bot'
        elif user.get('is_owner', False):
            return 'owner'
        elif user.get('is_admin', False):
            return 'admin'
        elif user.get('is_ultra_restricted', False):
            return 'single_channel_guest'
        elif user.get('is_restricted', False):
            return 'multi_channel_guest'
        else:
            return 'member'

    async def get_users(
        self, 
        include_bots: bool = False, 
        limit: int = 50,
        user_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get workspace users using Bot Token"""
        default_limit = int(os.getenv('DEFAULT_USER_LIMIT', '50'))
        limit = min(limit or default_limit, 200)
        
        params = {'limit': limit}
        
        logger.info(f"사용자 목록 조회 (봇 포함: {include_bots}, 최대: {limit}명)...")
        
        try:
            response = await self._make_request('users.list', 'GET', params, use_user_token=False)
            users_raw = response.get('members', [])
            
            formatted_users = []
            for user in users_raw:
                # Skip deleted users and Slackbot
                if user.get('deleted', False) or user.get('id') == 'USLACKBOT':
                    continue
                
                is_bot = user.get('is_bot', False)
                if not include_bots and is_bot:
                    continue
                
                user_type = self._categorize_user_type(user)
                
                # Filter by user types if specified
                if user_types and user_type not in user_types:
                    continue
                
                profile = user.get('profile', {})
                
                formatted_users.append({
                    'id': user.get('id'),
                    'name': user.get('name', ''),
                    'real_name': profile.get('real_name', ''),
                    'display_name': profile.get('display_name', ''),
                    'email': profile.get('email', ''),
                    'is_bot': is_bot,
                    'is_admin': user.get('is_admin', False),
                    'is_owner': user.get('is_owner', False),
                    'is_restricted': user.get('is_restricted', False),
                    'is_ultra_restricted': user.get('is_ultra_restricted', False),
                    'user_type': user_type,
                    'status_text': profile.get('status_text', ''),
                    'timezone': user.get('tz', ''),
                    'can_receive_dm': user_type not in ['bot']
                })
                
                # Stop when we reach the limit
                if len(formatted_users) >= limit:
                    break
            
            logger.info(f"사용자 목록 조회 완료: {len(formatted_users)}명")
            return formatted_users
            
        except SlackAPIError as e:
            logger.error(f"사용자 목록 조회 실패: {e}")
            raise

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email address using Bot Token"""
        users = await self.get_users(include_bots=False, limit=200)
        for user in users:
            if user.get('email', '').lower() == email.lower():
                return user
        return None

    async def get_dm_candidates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get users who can receive direct messages using Bot Token"""
        users = await self.get_users(include_bots=False, limit=limit)
        return [user for user in users if user.get('can_receive_dm', False)]

    # ==================== 6. DIRECT MESSAGE OPERATIONS ====================

    async def send_direct_message(self, user_id: str, text: str) -> Dict[str, Any]:
        """Send direct message to specific user using Bot Token"""
        logger.info(f"사용자 {user_id}에게 DM 전송 시작...")
        
        try:
            # Step 1: Open DM channel
            dm_data = {'users': user_id}
            dm_response = await self._make_request('conversations.open', 'POST', dm_data, use_user_token=False)
            dm_channel_id = dm_response['channel']['id']
            
            logger.info(f"DM 채널 생성/확인 완료: {dm_channel_id}")
            
            # Step 2: Send message to DM channel
            result = await self.send_message(dm_channel_id, text)
            
            if result['success']:
                logger.info(f"✅ DM 전송 성공: {user_id}")
                result['target_user_id'] = user_id
                result['dm_channel_id'] = dm_channel_id
            
            return result
            
        except SlackAPIError as e:
            if e.error_code in ['cannot_dm_bot', 'user_disabled']:
                logger.error(f"❌ DM 전송 불가: {user_id} ({e.error_code})")
                return {
                    "success": False,
                    "error": e.error_code,
                    "suggestion": e.suggestion,
                    "target_user_id": user_id
                }
            else:
                logger.error(f"❌ DM 전송 실패: {e}")
                raise

    # ==================== 7. UTILITY FUNCTIONS ====================

    def _format_timestamp(self, timestamp: str) -> str:
        """Format Slack timestamp to readable format"""
        try:
            ts_float = float(timestamp)
            dt = datetime.fromtimestamp(ts_float)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return timestamp

    def get_user_type_icon(self, user_type: str) -> str:
        """Get emoji icon for user type"""
        return self.user_type_icons.get(user_type, self.user_type_icons['unknown'])

    def get_status_icon(self, status: str) -> str:
        """Get emoji icon for status"""
        return self.status_icons.get(status, self.status_icons['info'])

    async def get_workspace_info(self) -> Dict[str, Any]:
        """Get comprehensive workspace information using Bot Token"""
        try:
            # Collect information concurrently
            auth_info, channels, users = await asyncio.gather(
                self.test_connection(),
                self.get_channels(),
                self.get_users(),
                return_exceptions=True
            )

            if isinstance(auth_info, Exception):
                raise auth_info

            # Channel statistics
            channel_stats = {
                'total': len(channels) if not isinstance(channels, Exception) else 0,
                'public': 0,
                'private': 0,
                'member': 0
            }

            if not isinstance(channels, Exception):
                for ch in channels:
                    if ch.get('is_member', False):
                        channel_stats['member'] += 1
                    
                    if ch.get('is_private', False):
                        channel_stats['private'] += 1
                    else:
                        channel_stats['public'] += 1
            
            # User statistics by type
            user_stats = {type_name: 0 for type_name in self.user_type_icons.keys()}
            dm_candidates = 0
            
            if not isinstance(users, Exception):
                for user in users:
                    user_type = user.get('user_type', 'member')
                    if user_type in user_stats:
                        user_stats[user_type] += 1
                    if user.get('can_receive_dm', False):
                        dm_candidates += 1
            
            return {
                "success": True,
                'workspace': {
                    'name': auth_info.get('bot_info', {}).get('team', 'Unknown'),
                    'id': auth_info.get('bot_info', {}).get('team_id', 'Unknown'),
                    'url': auth_info.get('bot_info', {}).get('url', 'Unknown')
                },
                'bot': {
                    'name': auth_info.get('bot_info', {}).get('user', 'Unknown'),
                    'id': auth_info.get('bot_info', {}).get('user_id', 'Unknown')
                },
                'stats': {
                    'channels': channel_stats,
                    'users': {
                        **user_stats,
                        'total': sum(user_stats.values()),
                        'dm_candidates': dm_candidates
                    }
                },
                'capabilities': {
                    'send_messages': True,
                    'read_channels': True,
                    'read_history': channel_stats['member'] > 0,
                    'send_dm': dm_candidates > 0,
                    'search_messages': bool(self.user_token),
                    'upload_files': bool(self.user_token)
                }
            }
            
        except SlackAPIError as e:
            logger.error(f"워크스페이스 정보 조회 실패: {e}")
            return {
                "success": False,
                "error": f"워크스페이스 정보 조회 실패: {e.error_code}",
                "suggestion": e.suggestion
            }

    # ==================== 8. ADDITIONAL FEATURES (USER TOKEN REQUIRED) ====================

    async def search_messages(
        self, 
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
        sort : str, default 'timestamp'
            Sort method for results (결과 정렬 방식)
        sort_dir : str, default 'desc'
            Sort direction (정렬 방향)
        count : int, default 20
            Number of results to return (반환할 결과 수)
            
        Returns:
        --------
        Dict[str, Any]
            Search results with comprehensive metadata
            
        Raises:
        -------
        ValueError
            When user token is not available
        """
        # Check if user token is available
        if not self.user_token:
            return {
                "success": False,
                "error": "검색 기능에는 SLACK_USER_TOKEN이 필요합니다.",
                "suggestion": "환경변수 SLACK_USER_TOKEN을 설정하고 search:read 스코프를 추가해주세요.",
                "query": query
            }
        
        # Validate and adjust parameters
        count = max(1, min(count, 100))
        
        params = {
            'query': query,
            'sort': sort,
            'sort_dir': sort_dir,
            'count': count
        }
        
        logger.info(f"메시지 검색 시작: '{query}' (결과: {count}개, User Token 사용)")
        
        try:
            response = await self._make_request('search.messages', 'GET', params, use_user_token=True)
            
            # Parse search results
            messages_data = response.get('messages', {})
            matches = messages_data.get('matches', [])
            total = messages_data.get('total', 0)
            
            # Format search results
            formatted_messages = []
            for match in matches:
                try:
                    ts_float = float(match.get('ts', 0))
                    readable_time = datetime.fromtimestamp(ts_float).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError):
                    readable_time = 'Unknown time'
                
                formatted_messages.append({
                    'text': match.get('text', ''),
                    'user': match.get('user', 'Unknown'),
                    'username': match.get('username', ''),
                    'channel': match.get('channel', {}),
                    'timestamp': readable_time,
                    'ts': match.get('ts', ''),
                    'type': match.get('type', 'message'),
                    'permalink': match.get('permalink', ''),
                    'score': match.get('score', 0)
                })
            
            logger.info(f"메시지 검색 완료: {len(formatted_messages)}개 결과 (전체: {total}개)")
            
            return {
                "success": True,
                "messages": formatted_messages,
                "total": total,
                "count": len(formatted_messages),
                "query": query,
                "message": f"'{query}' 검색 완료: {len(formatted_messages)}개 결과",
                "token_used": "User Token"
            }
            
        except SlackAPIError as e:
            logger.error(f"메시지 검색 실패: {e}")
            return {
                "success": False,
                "error": f"메시지 검색 실패: {e.error_code}",
                "suggestion": e.suggestion,
                "query": query,
                "token_used": "User Token"
            }

    async def add_reaction(
        self, 
        channel: str, 
        timestamp: str, 
        name: str
    ) -> Dict[str, Any]:
        """Add emoji reaction to specific message using Bot Token"""
        clean_name = name.strip(':')
        
        data = {
            'channel': channel,
            'timestamp': timestamp,
            'name': clean_name
        }
        
        logger.info(f"메시지 반응 추가: {channel}의 {timestamp}에 :{clean_name}:")
        
        try:
            response = await self._make_request('reactions.add', 'POST', data, use_user_token=False)
            
            logger.info(f"✅ 반응 추가 성공: :{clean_name}:")
            
            return {
                "success": True,
                "message": f"반응 :{clean_name}: 이 성공적으로 추가되었습니다.",
                "channel": channel,
                "timestamp": timestamp,
                "emoji": clean_name
            }
            
        except SlackAPIError as e:
            logger.error(f"반응 추가 실패: {e}")
            return {
                "success": False,
                "error": f"반응 추가 실패: {e.error_code}",
                "suggestion": e.suggestion,
                "channel": channel,
                "timestamp": timestamp,
                "emoji": clean_name
            }

    def _verify_or_create_file(
        self,
        file_path: Union[str, Path],
        content: str = None
    ) -> Dict[str, Any]:
        """
        Verify or create file based on file path and content

        파일이 존재하는지 확인하거나 내용으로 파일을 생성합니다.
        
        Parameters:
        -----------
        file_path : Union[str, Path]
            Path to file (파일 경로)
        content : str, optional
            Content to write if file doesn't exist (파일이 없을 때 작성할 내용)
            
        Returns:
        --------
        Dict[str, Any]
            File verification/creation result
            - success: bool (성공 여부)
            - file_exists: bool (파일 존재 여부)
            - file_created: bool (파일 생성 여부, 해당시)
            - file_path: str (파일 경로)
            - file_info: dict (파일 정보)
        """
        file_path_obj = Path(file_path)

        try:
            if file_path_obj.exists():
                # File not exists
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
                # File path not exists
                if not content:
                    logger.warning(f"파일이 존재하지 않으며 내용이 제공되지 않았습니다: {file_path_obj}")
                    return {
                        "success": False,
                        "error": f"파일이 존재하지 않으며 내용이 제공되지 않았습니다: {file_path_obj}",
                        "suggestion": "파일을 생성하려면 내용을 제공해주세요.",
                        "path_exists": False
                    }
                
                try:
                    # Create file directory(필요시)
                    file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create file
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
                
                except SlackAPIError as e:
                    logger.error(f"파일 처리 중 예기치 않은 에러 ({file_path_obj}): {e}")
                    return {
                        "success": False,
                        "error": f"파일 처리 중 예기치 않은 에러: {file_path_obj}",
                        "suggestion": "디렉토리/파일 쓰기 권한을 확인하거나 관리자 권한으로 실행해주세요.",
                        "path_exists": False,
                        "is_file": False
                    }
        
        except SlackAPIError as e:
            logger.error(f"파일 처리 중 예기치 않은 에러 ({file_path_obj}): {type(e).__name__}: {e}")
            return {
                "success": False,
                "error": f"파일 처리 중 예기치 않은 에러: {type(e).__name__}: {str(e)}",
                "suggestion": "파일 경로와 권한을 확인해주세요. 문제가 지속되면 시스템 관리자에게 문의하세요.",
                "path_exists": False,
                "is_file": False
            }

    def _get_file_preview(self, file_path: Union[str, Path], max_lines: int = 20) -> Dict[str, Any]:
        """
        Preview file content without uploading
        
        업로드하지 않고 파일 내용을 미리보기합니다.
        
        Parameters:
        -----------
        file_path : Union[str, Path]
            Path to file (파일 경로)
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
        """
        file_path_obj = Path(file_path)

        try:
            if not file_path_obj.exists():
                logger.warning(f"파일이 존재하지 않습니다: {file_path}")
                return {
                    "success": False,
                    "error": f"파일이 존재하지 않습니다: {file_path}",
                    "suggestion": "파일 경로를 확인해주세요."
                }
            
            file_stat = file_path_obj.stat()
            file_size = file_stat.st_size
            file_ext = file_path_obj.suffix.lower()

            file_info = {
                'name': file_path_obj.name,
                'path': str(file_path_obj),
                'size': file_size,
                'size_mb': round(file_size / (1024*1024), 2),
                'extension': file_ext,
                'is_text': file_ext in self.text_extensions,
                'modified': datetime.fromtimestamp(file_stat.st_mtime, tz=timezone.utc).isoformat(),
                'created': datetime.fromtimestamp(file_stat.st_ctime, tz=timezone.utc).isoformat()
            }

            # Preview content
            preview_content = None
            lines_shown = 0

            if file_ext in self.text_extensions:
                try:
                    with open(file_path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = []
                        for i, line in enumerate(f, start=1):
                            if i > max_lines:
                                lines.append(f"... (파일에 {max_lines}줄 이상의 내용이 있습니다)")
                                break
                            lines.append(line.rstrip())
                        
                        preview_content = '\n'.join(lines)
                        lines_shown = min(max_lines, len(lines))
                    
                except SlackAPIError as e:
                    logger.error(f"파일 미리보기 읽기 실패: {e}")
                    preview_content = f"파일 내용을 읽을 수 없습니다. {str(e)}"
                    lines_shown = 0
                
            logger.info(f"파일 미리보기 완료: {file_path_obj.name} ({lines_shown}줄 표시)")

            return {
                "success": True,
                "file_info": file_info,
                "preview_content": preview_content,
                "lines_shown": lines_shown,
                "message": f"파일 미리보기 완료: {file_path_obj.name} ({lines_shown}줄 표시)"
            }
        
        except SlackAPIError as e:
            logger.error(f"파일 미리보기 중 예기치 않은 에러 ({file_path_obj}): {e}")
            return {
                "success": False,
                "error": f"파일 미리보기 중 오류: {str(e)}",
                "suggestion": "파일 경로를 확인해주세요."
            }
    
    async def _upload_as_message(
            self, 
            file_path: Union[str, Path], 
            channel_id: str, 
            title: str, 
            comment: str
        ) -> Dict[str, Any]:
            """
            Upload small text file as message content
            
            작은 텍스트 파일을 메시지 내용으로 전송
            """
            try:
                # 파일 내용 읽기
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 내용이 너무 길면 자르기
                if len(content) > self.text_message:
                    content = content[:self.text_message] + "\n\n... (내용이 잘렸습니다)"
                
                # 메시지 구성
                message_text = f"""🤖 **MCP 서버 파일 공유: {title}**

    📁 파일명: `{Path(file_path).name}`
    📏 크기: `{Path(file_path).stat().st_size}` bytes
    {f'💬 {comment}' if comment else ''}

    ```
    {content}
    ```

    📝 *파일 내용이 메시지로 공유되었습니다.*"""
                
                result = await self.send_message(channel=channel_id, text=message_text)
                
                if result['success']:
                    return {
                        "success": True,
                        "method": "text_message",
                        "message": f"파일 '{title}'이 메시지로 공유되었습니다.",
                        "size": len(content),
                        "channel": result['channel'],
                        "timestamp": result['timestamp']
                    }
                else:
                    return {
                        "success": False,
                        "method": "text_message",
                        "error": result.get('error', 'Unknown error')
                    }
                    
            except Exception as e:
                logger.error(f"텍스트 메시지 업로드 실패: {e}")
                return {
                    "success": False,
                    "method": "text_message",
                    "error": str(e)
                }
    
    async def _upload_as_snippet(
        self,
        file_path: Union[str, Path],
        channel_id: str,
        title: str,
        comment: str
    ) -> Dict[str, Any]:
        """
        Upload small text file as code snippet
        
        작은 텍스트 파일을 코드 스니펫으로 전송
        """
        path_obj = Path(file_path)

        try:
            from slack_sdk.web.async_client import AsyncWebClient
            SDK_AVAILABLE = True
        except ImportError:
            SDK_AVAILABLE = False
            logger.warning("Slack SDK 미설치. 기존 로직 사용")
        try: 
            if SDK_AVAILABLE:
                try:
                    user_client = AsyncWebClient(token=self.bot_token)
                    logger.info("SDK Bot Token 코드 스니펫 업로드 시도...")
                        
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                        if len(content) > self.text_message:
                            content = content[:self.text_message] + "\n\n... (내용이 잘렸습니다)"
                            
                        file_type = self._get_file_type_for_snippet(file_path.suffix.lower())
                        
                        response = await user_client.files_upload_v2(
                            channel=channel_id,
                            file=path_obj,
                            title=f'🤖 {title}',
                            initial_comment=f'🤖 MCP 서버: {comment}',
                            filetype=file_type
                        )

                        file_info = response.get('file', {})
                        
                        logger.info(f"✅ SDK 코드 스니펫 업로드 성공: {path_obj.name}")
                        
                        return {
                            "success": True,
                            "method": "code_snippet",
                            "message": f"파일 '{title}'이 코드 스니펫으로 공유되었습니다.",
                            "file_info": {
                                "id": file_info.get('id'),
                                "name": file_info.get('name'),
                                "title": file_info.get('title'),
                                "filetype": file_info.get('filetype'),
                                "url_private": file_info.get('url_private')
                            },
                            "size": len(content),
                            "sdk_used": True
                        }
                    
                except SlackAPIError as sdk_error:
                    logger.warning(f"SDK 코드 스니펫 업로드 실패, 풀백 시도: {sdk_error}")
                    
            return await self._upload_as_file(
                file_path=file_path,
                channels=channel_id,
                title=title,
                initial_comment=f'🤖 MCP 서버: {comment}'
            )
        except Exception as e:
            logger.error(f"코드 스니펫 업로드 실패: {e}")
            return {
                "success": False,
                "method": "code_snippet",
                "error": str(e)
            }
                    
    def _get_file_type_for_snippet(self, file_extension: str) -> str:
        """Get appropriate file type for code snippet syntax highlighting"""
        extension_map = {
            '.py': 'python',
            '.js': 'javascript', 
            '.html': 'html',
            '.css': 'css',
            '.json': 'json',
            '.xml': 'xml',
            '.sql': 'sql',
            '.sh': 'shell',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.md': 'markdown',
            '.dockerfile': 'dockerfile'
        }
        
        return extension_map.get(file_extension.lower(), 'text')

    async def _upload_as_file(
        self, 
        file_path: Union[str, Path], 
        channels: str, 
        title: str = None,
        initial_comment: str = None
    ) -> Dict[str, Any]:
        """
        Enhanced file upload with SDK integration and smart fallback
        
        SDK 통합과 스마트 폴백을 포함한 향상된 파일 업로드 기능입니다.
        
        Supports various file formats and automatic strategy selection:
        - Documents: PDF, DOC, DOCX, TXT, MD
        - Images: JPG, PNG, GIF, BMP, TIFF  
        - Audio: MP3, WAV, FLAC, AAC, OGG
        - Video: MP4, AVI, MOV, WMV, FLV
        - Archives: ZIP, RAR, 7Z, TAR
        - Code: PY, JS, HTML, CSS, JSON, XML
        - Data: CSV, XLS, XLSX, SQL
        
        File Size Limits (Slack 공식 문서 기준):
        - Small files (< 50KB): Can be sent as message content for text files
        - Medium files (50KB - 1MB): Code snippet upload for text files
        - Standard files (1MB - 100MB): Standard file upload (free plan)
        - Large files (100MB - 1GB): Large file upload (paid plan, User Token)
        - Massive files (> 1GB): File info sharing only
        """
        try:
            from slack_sdk.web.async_client import AsyncWebClient
            SDK_AVAILABLE = True  
        except ImportError:
            SDK_AVAILABLE = False
            logger.warning("Slack SDK 미설치. 기존 로직 사용")

        # Validate file first (기존 검증 로직 유지)
        file_path_obj = Path(file_path)
        if not file_path_obj.exists():
            return {
                "success": False,
                "error": f"파일을 찾을 수 없습니다: {file_path}",
                "suggestion": "파일 경로가 올바른지 확인해주세요."
            }
        
        if not file_path_obj.is_file():
            return {
                "success": False,
                "error": f"지정된 경로가 파일이 아닙니다: {file_path}",
                "suggestion": "파일 경로를 확인해주세요."
            }
        
        file_size = file_path_obj.stat().st_size
        filename = file_path_obj.name
        
        if not title:
            title = filename
        
        
        if file_size > self.large:
            logger.warning(f"파일이 너무 큽니다: {file_size} bytes (> 1GB)")
            return {
                "success": False,
                "error": f"파일 크기가 1GB를 초과합니다: {file_size / (1024*1024):.1f}MB",
                "suggestion": "파일을 분할하거나 압축해서 업로드해주세요.",
                "filename": filename,
                "file_size": file_size
            }
        
        try:
            if SDK_AVAILABLE:
                try:
                    if file_size > self.standard:
                        logger.warning(f"파일이 무료 플랜 허용 용량을 초과합니다: {file_size} bytes (> 100MB)")
            
                        print(f"Bot Token으로는 100MB 이하 파일만 업로드 가능합니다. 현재: {file_size / (1024*1024):.1f}MB",
                        "SLACK_USER_TOKEN을 설정하여 유료 플랜의 대용량 파일 업로드를 사용하거나, 파일을 압축해주세요.")
            
                        user_client = AsyncWebClient(token=self.user_token)
                        logger.info("SDK User Token 파일 업로드 시도...")
                    
                    else:
                        user_client = AsyncWebClient(token=self.bot_token)
                        logger.info("SDK Bot Token 파일 업로드 시도...")

                    upload_response = await user_client.files_upload_v2(
                        channel=channels,
                        file=file_path_obj,
                        title=f'🤖 {title}',
                        initial_comment=f'🤖 MCP 서버: {initial_comment}' if initial_comment else None
                    )

                    file_info = upload_response.get('file', {})
                    
                    logger.info(f"✅ SDK 파일 업로드 성공: {filename}")
                    
                    return {
                        "success": True,
                        "method": "file_upload",
                        "is_sdk_used": SDK_AVAILABLE,
                        "message": f"파일 '{title}'이 업로드되었습니다.",
                        "file_info": {
                            "id": file_info.get('id'),
                            "name": file_info.get('name'),
                            "title": file_info.get('title'),
                            "size": file_info.get('size'),
                            "filetype": file_info.get('filetype'),
                            "mimetype": file_info.get('mimetype'),
                            "url_private": file_info.get('url_private')
                        },
                        "size": file_size,
                        "size_mb": round(file_size / (1024*1024), 2),
                        "token_used": "User Token (SDK)"
                    }
                    
                except SlackAPIError as sdk_error:
                    logger.warning(f"SDK 업로드 실패, 기존 방식으로 폴백: {sdk_error}")

            else:
                # Step 1: Get upload URL (기존 코드)
                upload_data = {
                    'filename': filename,
                    'length': file_size
                }
                
                logger.info("1단계: 업로드 URL 요청...")
                if file_size > self.standard:
                    upload_response = await self._make_request('files.getUploadURLExternal', 'POST', upload_data, use_user_token=True)
                else:
                    upload_response = await self._make_request('files.getUploadURLExternal', 'POST', upload_data, use_user_token=False)
                
                upload_url = upload_response['upload_url']
                file_id = upload_response['file_id']
                
                logger.info(f"업로드 URL 획득: {file_id}")
                
                # Step 2: Upload file to external URL (기존 코드)
                logger.info("2단계: 파일 업로드...")
                
                with open(file_path, 'rb') as file_content:
                    upload_headers = {'Content-Type': 'application/octet-stream'}
                    
                    async with self._session.put(upload_url, data=file_content, headers=upload_headers) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"파일 업로드 실패: HTTP {response.status} - {error_text}")
                            raise SlackAPIError(
                                "file_upload_failed",
                                {"status": response.status, "response": error_text},
                                "외부 서버로의 파일 업로드가 실패했습니다. 네트워크 연결을 확인해주세요."
                            )
                
                logger.info("파일 업로드 완료")
                
                # Step 3: Complete upload and share to channels (기존 코드)
                logger.info("3단계: 업로드 완료 및 채널 공유...")
                
                complete_data = {
                    'files': [
                        {
                            'id': file_id,
                            'title': title
                        }
                    ],
                    'channel_id': channels
                }
                
                if initial_comment:
                    complete_data['initial_comment'] = initial_comment
                
                if file_size > self.standard:
                    complete_response = await self._make_request('files.completeUploadExternal', 'POST', complete_data, use_user_token=True)
                else:
                    complete_response = await self._make_request('files.completeUploadExternal', 'POST', complete_data, use_user_token=False)
                
                # Extract file information
                files_info = complete_response.get('files', [])
                if files_info:
                    file_info = files_info[0]
                    
                    logger.info(f"✅ 파일 업로드 성공: {filename}")
                    
                    return {
                        "success": True,
                        "method": "file_upload",
                        "is_sdk_used": SDK_AVAILABLE,
                        "message": f"파일 '{filename}'이 성공적으로 업로드되었습니다.",
                        "file_info": {
                            "id": file_info.get('id'),
                            "name": file_info.get('name'),
                            "title": file_info.get('title'),
                            "size": file_info.get('size'),
                            "url_private": file_info.get('url_private'),
                            "filetype": file_info.get('filetype'),
                            "mimetype": file_info.get('mimetype')
                        },
                        "channels": channels.split(','),
                        "filename": filename,
                        "file_size": file_size,
                        "file_size_mb": round(file_size / (1024*1024), 2),
                        "token_used": "User Token" if file_size > self.standard else "Bot Token"
                    }
                else:
                    raise SlackAPIError(
                        "file_info_missing",
                        complete_response,
                        "파일 업로드는 완료되었지만 파일 정보를 받을 수 없습니다."
                    )
            
            
        except SlackAPIError as e:
            logger.error(f"파일 업로드 중 예외 발생: {e}")
            return {
                "success": False,
                "error": f"파일 업로드 중 예외 발생: {str(e)}",
                "suggestion": "파일 크기와 형식을 확인해주세요. 네트워크 연결도 확인해주세요.",
                "filename": filename,
                "file_size": file_size,
                "sdk_available": SDK_AVAILABLE,
                "token_used": "User Token" if file_size > self.standard else "Bot Token"
            }
    
    async def _share_file_info(
        self,
        file_path: Union[str, Path],
        channel_id: str,
        title: str,
        comment: str
    ) -> Dict[str, Any]:
        """Share file information only"""
        try:
            file_size = file_path.stat().st_size
            file_size_mb = self._format_file_size(file_size)
            
            message_text = f"""🤖 **대용량 파일 정보**

📁 파일명: `{file_path.name}`
📏 크기: `{file_size_mb}`
📄 확장자: `{file_path.suffix}`
📂 경로: `{str(file_path)}`
{f'💬 {comment}' if comment else ''}

⚠️ 파일이 {self.standard / (1024*1024):.0f}MB를 초과하여 직접 업로드할 수 없습니다.

💡 **해결 방법:**
• 파일을 여러 개로 분할해주세요
• 압축하여 크기를 줄여주세요  
• 클라우드 스토리지 링크를 공유해주세요

📝 *필요시 파일을 직접 다운로드하거나 작은 파일로 분할해주세요.*"""
            
            result = await self.send_message(channel=channel_id, text=message_text)
            
            if result['success']:
                return {
                    "success": True,
                    "method": "file_info_only",
                    "message": f"대용량 파일 '{title}' 정보가 공유되었습니다.",
                    "size": file_size_mb,
                    "channel": result['channel'],
                    "timestamp": result['timestamp']
                }
            else:
                return {
                    "success": False,
                    "method": "file_info_only",
                    "error": result.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"파일 정보 공유 실패: {e}")
            return {
                "success": False,
                "method": "file_info_only",
                "error": str(e)
            }
        
    def _is_sensitive_file(self, file_path: Path) -> bool:
        """
        Check if file contains sensitive information
        
        민감한 정보가 포함된 파일인지 확인
        """
        # 확장자 기반 필터링
        sensitive_extensions = {'.key', '.pem', '.p12', '.jks', '.keystore'}
        if file_path.suffix.lower() in sensitive_extensions:
            return True
        
        # 파일명 기반 필터링
        sensitive_names = {'passwd', 'shadow', 'private', 'secrets', 'credentials', 'config', 'settings', 'token', 'api_key', 'password'}
        if any(sensitive in file_path.name.lower() for sensitive in sensitive_names):
            return True
        
        # 시스템 디렉토리 확인
        system_paths = {'/etc', '/usr', '/sys', '/proc', '/var'}
        if any(str(file_path).startswith(sys_path) for sys_path in system_paths):
            return True
        
        # 민감한 디렉토리 패턴 추가
        sensitive_dirs = {'.ssh', '.aws', '.config', '.env', 'credentials', 'secrets'}
        if any(part in sensitive_dirs for part in file_path.parts):
            return True
        
        # 백업 및 임시 파일 추가
        sensitive_patterns = {'.bak', '.tmp', '.swp', '~', '.DS_Store'}
        if any(file_path.name.endswith(pattern) for pattern in sensitive_patterns):
            return True
        
        return False
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size to human readable format
        
        파일 크기를 사람이 읽기 쉬운 형태로 포맷팅
        """
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    async def smart_upload(
        self, 
        file_path: Union[str, Path], 
        channel_id: str, 
        title: str = None, 
        comment: str = None,
        auto_create: bool = False,
        create_content: str = None,
        preview_first: bool = False
    ) -> Dict[str, Any]:
        """
        Enhanced smart file upload with unified workflow
        
        통합 워크플로우를 포함한 향상된 스마트 파일 업로드입니다.
        
        Workflow:
        1. Verify file exists or create it (파일 존재 확인 또는 생성)
        2. Preview file content if requested (요청시 파일 내용 미리보기)
        3. Determine upload strategy (업로드 전략 결정)
        4. Execute upload with best method (최적 방법으로 업로드 실행)
        
        Parameters:
        -----------
        file_path : Union[str, Path]
            Path to file to upload (업로드할 파일 경로)
        channel_id : str
            Target Slack channel ID (대상 Slack 채널 ID)
        title : str, optional
            File title (파일 제목, 없으면 파일명 사용)
        comment : str, optional
            File description (파일 설명)
        auto_create : bool, default False
            Whether to create file if it doesn't exist (파일이 없을 때 자동 생성 여부)
        create_content : str, optional
            Content for auto-created file (자동 생성할 파일의 내용)
        preview_first : bool, default False
            Whether to preview file before upload (업로드 전 파일 미리보기 여부)
            
        Returns:
        --------
        Dict[str, Any]
            Enhanced upload result with workflow information
            (워크플로우 정보가 포함된 향상된 업로드 결과)
        """
        # Step 1: Verify or create file
        logger.info(f"🔍 Step 1: 파일 확인/생성 - {file_path}")
        
        if auto_create and create_content:
            verify_result = self._verify_or_create_file(file_path, create_content)
        else:
            verify_result = self._verify_or_create_file(file_path)
        
        if not verify_result['success']:
            return {
                "success": False,
                "error": verify_result['error'],
                "suggestion": verify_result['suggestion'],
                "workflow_step": "file_verification"
            }
        
        file_path_obj = Path(verify_result['file_path']).resolve()
        file_info = verify_result['file_info']

        # 보안 검사
        if self._is_sensitive_file(file_path_obj):
            return {
                "success": False,
                "error": "보안상 중요한 파일은 업로드할 수 없습니다.",
                "suggestion": "일반 사용자 파일만 업로드해주세요."
            }
        
        # Step 2: Preview file if requested
        preview_result = None
        if preview_first:
            logger.info(f"👀 Step 2: 파일 미리보기 - {file_path_obj.name}")
            preview_result = self._get_file_preview(file_path_obj)
        
        # Step 3: Determine upload strategy
        
        file_size = file_info['size']
        file_ext = file_info['extension'].lower()
        filename = file_path_obj.name

        logger.info(f"🎯 Step 3: 업로드 전략 결정")
        if not title:
            title = filename
        
        logger.info(f"🤖 MCP 스마트 파일 업로드: {filename} ({self._format_file_size(file_size)})")
        
        # 업로드 전략 선택
        if file_ext in self.text_extensions and file_size < self.text_message:
            logger.info("🎯 전략: 텍스트 메시지로 전송")
            upload_result = await self._upload_as_message(file_path, channel_id, title, comment)
            
        elif file_size < self.snippet:
            logger.info("🎯 전략: 중간 파일 업로드")
            upload_result = await self._upload_as_snippet(file_path, channel_id, title, comment)
            
        elif file_size < self.large:
            logger.info("🎯 전략: 큰 파일 업로드")
            upload_result = await self._upload_as_file(file_path, channel_id, title, comment)
            
        else:
            logger.info("🎯 전략: 초대용량 파일 정보 공유")
            upload_result = await self._share_file_info(file_path, channel_id, title, comment)
        
        # Combine results
        enhanced_result = {
            **upload_result,
            "workflow": {
                "file_verification": verify_result,
                "file_preview": preview_result,
                "upload_strategy": upload_result['method'],
                "workflow_completed": True
            },
            "file_info": file_info
        }
        
        if upload_result['success']:
            logger.info(f"✅ 향상된 스마트 업로드 완료: {file_path_obj.name} ({upload_result['method']})")
        
        return enhanced_result


# ==================== FACTORY FUNCTIONS ====================

async def create_slack_client(bot_token: Optional[str] = None, user_token: Optional[str] = None) -> SlackAPIClient:
    """
    Create Slack API client with dual token support
    
    이중 토큰 지원으로 Slack API 클라이언트를 생성하는 팩토리 함수입니다.
    """
    return SlackAPIClient(bot_token=bot_token, user_token=user_token)

# ==================== CONVENIENCE FUNCTIONS ====================

async def quick_send_message(channel: str, text: str) -> bool:
    """Quick utility function to send a message"""
    try:
        async with SlackAPIClient() as client:
            result = await client.send_message(channel, text)
            return result.get('success', False)
    except Exception as e:
        logger.error(f"Quick message send failed: {e}")
        return False

async def quick_get_channels() -> List[Dict[str, Any]]:
    """Quick utility function to get channels"""
    try:
        async with SlackAPIClient() as client:
            return await client.get_channels()
    except Exception as e:
        logger.error(f"Quick channel retrieval failed: {e}")
        return []

async def quick_get_dm_candidates(limit: int = 10) -> List[Dict[str, Any]]:
    """Quick utility function to get DM candidates"""
    try:
        async with SlackAPIClient() as client:
            return await client.get_dm_candidates(limit)
    except Exception as e:
        logger.error(f"Quick DM candidates retrieval failed: {e}")
        return []

async def quick_search_messages(query: str, count: int = 10) -> Dict[str, Any]:
    """
    Quick utility function to search messages (requires User Token)
    
    메시지 검색을 위한 빠른 유틸리티 함수입니다 (User Token 필요).
    """
    try:
        async with SlackAPIClient() as client:
            return await client.search_messages(query, count=count)
    except Exception as e:
        logger.error(f"Quick message search failed: {e}")
        return {
            "success": False,
            "error": f"검색 실패: {str(e)}",
            "query": query
        }

async def quick_upload_file(file_path: str, channels: str, title: str = None, comment: str = None) -> Dict[str, Any]:
    """
    Quick utility function to upload a file (requires User Token)
    
    파일 업로드를 위한 빠른 유틸리티 함수입니다 (User Token 필요).
    """
    try:
        async with SlackAPIClient() as client:
            return await client.smart_upload(file_path=file_path, channel_id=channels, title=title, comment=comment)
    except Exception as e:
        logger.error(f"Quick file upload failed: {e}")
        return {
            "success": False,
            "error": f"파일 업로드 실패: {str(e)}",
            "filename": Path(file_path).name if file_path else "unknown"
        }

# ==================== MODULE EXPORTS ====================

__all__ = [
    'SlackAPIClient',
    'SlackAPIError', 
    'create_slack_client',
    'quick_send_message',
    'quick_get_channels',
    'quick_get_dm_candidates',
    'quick_search_messages',
    'quick_upload_file'
]