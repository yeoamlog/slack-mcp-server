"""
Pomodoro Timer Module for MCP Server
====================================

MCP 서버용 뽀모도로 타이머 전용 모듈입니다.
수업, 작업, 휴식 등의 시간 관리를 자동화합니다.

Features (기능):
- Smart timer management with customizable durations (사용자 정의 시간 관리)
- Automatic Slack notifications at start and end (시작/종료 시 자동 Slack 알림)
- Multiple timer types: study, work, break, meeting (다양한 타이머 타입)
- Persistent timer state management (지속적인 타이머 상태 관리)
- Timer cancellation and status checking (타이머 취소 및 상태 확인)

Author: JunHyuck Kwon
Version: 2.0.0 (Refactored Architecture)
Updated: 2025-06-02
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# 로깅 설정
logger = logging.getLogger(__name__)

# ==================== 1. 타이머 타입 및 데이터 클래스 ====================

class TimerType(Enum):
    """Timer types with Korean descriptions"""
    STUDY = "study"        # 수업/공부
    WORK = "work"          # 업무
    BREAK = "break"        # 휴식
    MEETING = "meeting"    # 회의
    CUSTOM = "custom"      # 사용자 정의

@dataclass
class TimerConfig:
    """
    Timer configuration class
    
    타이머 설정을 저장하는 데이터 클래스입니다.
    """
    timer_type: TimerType
    duration_minutes: int
    start_message: str
    end_message: str
    channel_id: str
    user_id: Optional[str] = None
    custom_name: Optional[str] = None

@dataclass
class ActiveTimer:
    """
    Active timer state class
    
    활성 타이머의 상태를 저장하는 데이터 클래스입니다.
    """
    timer_id: str
    config: TimerConfig
    start_time: datetime
    end_time: datetime
    is_active: bool = True
    task: Optional[asyncio.Task] = None

# ==================== 2. 뽀모도로 타이머 매니저 클래스 ====================

class PomodoroTimerManager:
    """
    Pomodoro Timer Manager for MCP server
    
    MCP 서버용 뽀모도로 타이머 매니저입니다.
    다양한 타이머를 관리하고 자동 알림을 제공합니다.
    
    Features:
    - Multiple timer types with custom durations
    - Automatic Slack notifications
    - Timer state management and persistence
    - Concurrent timer support
    - Status tracking and cancellation
    """
    
    def __init__(self, slack_client):
        """
        Initialize pomodoro timer manager
        
        뽀모도로 타이머 매니저를 초기화합니다.
        
        Parameters:
        -----------
        slack_client : SlackAPIClient
            Initialized Slack API client (초기화된 Slack API 클라이언트)
        """
        self.client = slack_client
        self.active_timers: Dict[str, ActiveTimer] = {}
        
        # Environment-configurable default durations (환경변수로 설정 가능한 기본 시간)
        self.default_durations = {
            TimerType.STUDY: int(os.getenv('DEFAULT_STUDY_MINUTES', '50')),      # 수업: 50분
            TimerType.WORK: int(os.getenv('DEFAULT_WORK_MINUTES', '25')),        # 업무: 25분 (전통적 뽀모도로)
            TimerType.BREAK: int(os.getenv('DEFAULT_BREAK_MINUTES', '10')),      # 휴식: 10분
            TimerType.MEETING: int(os.getenv('DEFAULT_MEETING_MINUTES', '30')),  # 회의: 30분
            TimerType.CUSTOM: int(os.getenv('DEFAULT_CUSTOM_MINUTES', '25'))     # 사용자 정의: 25분
        }
        
        # Customizable message templates (사용자 정의 가능한 메시지 템플릿)
        self.message_templates = {
            TimerType.STUDY: {
                'start': "🎓 **수업을 시작합니다!** 📚\n집중해서 학습해보세요! ⏰ {duration}분",
                'end': "🎉 \n수고하셨습니다! 이제 쉬는 시간입니다 😊 ☕"
            },
            TimerType.WORK: {
                'start': "💼 **업무를 시작합니다!** 🚀\n집중 모드 ON! ⏰ {duration}분",
                'end': "✅ \n잠시 휴식을 취하세요! 🌸"
            },
            TimerType.BREAK: {
                'start': "☕ **휴식 시간 시작!** 🌸\n잠시 쉬어가세요~ ⏰ {duration}분",
                'end': "⚡ **휴식 시간이 끝났습니다!** 💪\n다시 집중할 시간이에요! 🔥"
            },
            TimerType.MEETING: {
                'start': "👥 **회의를 시작합니다!** 🗣️\n생산적인 회의가 되길! ⏰ {duration}분",
                'end': "🏆 **회의가 끝났습니다!** 📋\n수고하셨습니다! 결과를 정리해보세요 📝"
            },
            TimerType.CUSTOM: {
                'start': "⏱️ **타이머를 시작합니다!** ✨\n목표를 향해 달려보세요! ⏰ {duration}분",
                'end': "🎊 **타이머가 끝났습니다!** 🎈\n목표를 달성하셨나요? 훌륭해요! 👏"
            }
        }
        
        logger.debug("PomodoroTimerManager 초기화 완료")
    
    async def start_timer(
        self,
        timer_type: str,
        channel_id: str,
        duration_minutes: Optional[int] = None,
        custom_name: Optional[str] = None,
        custom_start_message: Optional[str] = None,
        custom_end_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a new pomodoro timer
        
        새로운 뽀모도로 타이머를 시작합니다.
        
        Parameters:
        -----------
        timer_type : str
            Timer type ('study', 'work', 'break', 'meeting', 'custom')
            타이머 타입 ('study', 'work', 'break', 'meeting', 'custom')
        channel_id : str
            Target Slack channel ID (대상 Slack 채널 ID)
        duration_minutes : int, optional
            Timer duration in minutes (타이머 지속 시간, 분 단위)
            If not provided, uses default for timer type
        custom_name : str, optional
            Custom timer name (사용자 정의 타이머 이름)
        custom_start_message : str, optional
            Custom start message (사용자 정의 시작 메시지)
        custom_end_message : str, optional
            Custom end message (사용자 정의 종료 메시지)
            
        Returns:
        --------
        Dict[str, Any]
            Timer start result with comprehensive information
            - success: bool (타이머 시작 성공 여부)
            - timer_id: str (고유 타이머 ID)
            - timer_type: str (타이머 타입)
            - duration_minutes: int (지속 시간)
            - start_time: str (시작 시간 ISO 형식)
            - end_time: str (종료 예정 시간 ISO 형식)
            - channel_id: str (채널 ID)
            - custom_name: str (사용자 정의 이름)
            - message: str (결과 메시지)
            
        Example:
        --------
        >>> await start_timer("study", "C08UZKK9Q4R", 50, "파이썬 학습")
        >>> await start_timer("work", "C08UZKK9Q4R", custom_name="프로젝트 개발")
        """
        try:
            # Validate timer type (타이머 타입 검증)
            try:
                timer_enum = TimerType(timer_type)
            except ValueError:
                return {
                    "success": False,
                    "error": f"지원하지 않는 타이머 타입: {timer_type}",
                    "suggestion": f"다음 중 선택해주세요: {[t.value for t in TimerType]}",
                    "available_types": [t.value for t in TimerType]
                }
            
            # Set duration (지속 시간 설정)
            if duration_minutes is None:
                duration_minutes = self.default_durations[timer_enum]
            
            # Validate duration (지속 시간 검증)
            if not isinstance(duration_minutes, int) or duration_minutes <= 0:
                return {
                    "success": False,
                    "error": f"잘못된 지속 시간: {duration_minutes}",
                    "suggestion": "1 이상의 정수로 시간을 입력해주세요."
                }
            
            # Configure messages (메시지 설정)
            if custom_start_message and custom_end_message:
                start_msg = custom_start_message.format(duration=duration_minutes)
                end_msg = custom_end_message
            else:
                templates = self.message_templates[timer_enum]
                start_msg = templates['start'].format(duration=duration_minutes)
                end_msg = templates['end']
            
            # Add custom name to messages (사용자 정의 이름 추가)
            if custom_name:
                start_msg = f"📝 **{custom_name}**\n{start_msg}"
                end_msg = f"📝 **{custom_name} 완료**\n{end_msg}"
            
            # Create timer configuration (타이머 설정 생성)
            config = TimerConfig(
                timer_type=timer_enum,
                duration_minutes=duration_minutes,
                start_message=start_msg,
                end_message=end_msg,
                channel_id=channel_id,
                custom_name=custom_name
            )
            
            # Generate unique timer ID (고유 타이머 ID 생성)
            timer_id = f"{timer_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # Calculate start and end times (시작 및 종료 시간 계산)
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            # Send start notification (시작 알림 전송)
            start_result = await self.client.send_message(channel_id, start_msg)
            if not start_result['success']:
                return {
                    "success": False,
                    "error": f"시작 메시지 전송 실패: {start_result.get('error')}",
                    "suggestion": "채널 ID와 봇 권한을 확인해주세요.",
                    "timer_type": timer_type,
                    "channel_id": channel_id
                }
            
            # Create and start timer task (타이머 태스크 생성 및 시작)
            timer_task = asyncio.create_task(
                self._timer_countdown(timer_id, config, duration_minutes)
            )
            
            # Add to active timers (활성 타이머에 추가)
            active_timer = ActiveTimer(
                timer_id=timer_id,
                config=config,
                start_time=start_time,
                end_time=end_time,
                is_active=True,
                task=timer_task
            )
            
            self.active_timers[timer_id] = active_timer
            
            logger.info(f"✅ 타이머 시작: {timer_id} ({duration_minutes}분, {timer_type})")
            
            return {
                "success": True,
                "timer_id": timer_id,
                "timer_type": timer_type,
                "duration_minutes": duration_minutes,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "channel_id": channel_id,
                "custom_name": custom_name,
                "message": f"{timer_type} 타이머가 시작되었습니다 ({duration_minutes}분)",
                "start_notification_sent": True
            }
            
        except Exception as e:
            logger.error(f"❌ 타이머 시작 실패: {e}")
            return {
                "success": False,
                "error": f"타이머 시작 중 오류: {str(e)}",
                "suggestion": "설정값들을 확인하고 다시 시도해주세요.",
                "timer_type": timer_type
            }
    
    async def _timer_countdown(self, timer_id: str, config: TimerConfig, duration_minutes: int):
        """
        Internal timer countdown function
        
        내부 타이머 카운트다운 함수입니다.
        
        Parameters:
        -----------
        timer_id : str
            Unique timer ID (고유 타이머 ID)
        config : TimerConfig
            Timer configuration (타이머 설정)
        duration_minutes : int
            Timer duration in minutes (타이머 지속 시간)
        """
        try:
            # Wait for the specified duration (설정된 시간만큼 대기)
            await asyncio.sleep(duration_minutes * 60)
            
            # Check if timer is still active (타이머가 여전히 활성 상태인지 확인)
            if timer_id in self.active_timers and self.active_timers[timer_id].is_active:
                # Send completion notification (완료 알림 전송)
                end_result = await self.client.send_message(
                    config.channel_id, 
                    config.end_message
                )
                
                if end_result['success']:
                    logger.info(f"✅ 타이머 완료 알림 전송: {timer_id}")
                else:
                    logger.error(f"❌ 타이머 완료 알림 전송 실패: {timer_id} - {end_result.get('error')}")
                
                # Mark timer as completed (타이머를 완료 상태로 변경)
                self.active_timers[timer_id].is_active = False
                logger.info(f"🏁 타이머 완료: {timer_id}")
            
        except asyncio.CancelledError:
            logger.info(f"⏹️ 타이머 취소됨: {timer_id}")
            # Mark as cancelled if still exists (존재하는 경우 취소 상태로 표시)
            if timer_id in self.active_timers:
                self.active_timers[timer_id].is_active = False
        except Exception as e:
            logger.error(f"❌ 타이머 실행 중 오류: {timer_id} - {e}")
            # Mark as failed if still exists (존재하는 경우 실패 상태로 표시)
            if timer_id in self.active_timers:
                self.active_timers[timer_id].is_active = False
    
    async def cancel_timer(self, timer_id: str) -> Dict[str, Any]:
        """
        Cancel an active timer
        
        활성 타이머를 취소합니다.
        
        Parameters:
        -----------
        timer_id : str
            Timer ID to cancel (취소할 타이머 ID)
            
        Returns:
        --------
        Dict[str, Any]
            Cancellation result with detailed information
            - success: bool (취소 성공 여부)
            - timer_id: str (타이머 ID)
            - message: str (결과 메시지)
            - timer_info: dict (타이머 정보, 성공 시)
            
        Example:
        --------
        >>> await cancel_timer("study_20250602_143022_123456")
        """
        try:
            if timer_id not in self.active_timers:
                return {
                    "success": False,
                    "error": f"타이머를 찾을 수 없습니다: {timer_id}",
                    "suggestion": "활성 타이머 목록을 확인해주세요.",
                    "timer_id": timer_id
                }
            
            timer = self.active_timers[timer_id]
            
            if not timer.is_active:
                return {
                    "success": False,
                    "error": f"이미 완료되거나 취소된 타이머입니다: {timer_id}",
                    "suggestion": "활성 타이머만 취소할 수 있습니다.",
                    "timer_id": timer_id,
                    "timer_status": "inactive"
                }
            
            # Cancel the task (태스크 취소)
            if timer.task and not timer.task.done():
                timer.task.cancel()
                try:
                    await timer.task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
            
            # Mark timer as inactive (타이머 비활성화)
            timer.is_active = False
            
            # Prepare cancellation message (취소 메시지 준비)
            remaining_time = timer.end_time - datetime.now()
            remaining_minutes = max(0, int(remaining_time.total_seconds() / 60))
            
            cancel_message = f"""⏹️ **타이머가 취소되었습니다** ❌

🆔 타이머 ID: `{timer_id}`
⏰ 타입: {timer.config.timer_type.value}
📝 이름: {timer.config.custom_name or '없음'}
⏳ 남은 시간: {remaining_minutes}분

타이머가 중단되었습니다."""
            
            # Send cancellation notification (취소 알림 전송)
            cancel_result = await self.client.send_message(
                timer.config.channel_id, 
                cancel_message
            )
            
            if cancel_result['success']:
                logger.info(f"✅ 타이머 취소됨: {timer_id}")
                
                return {
                    "success": True,
                    "timer_id": timer_id,
                    "message": f"타이머 {timer_id}가 취소되었습니다.",
                    "timer_info": {
                        "timer_type": timer.config.timer_type.value,
                        "custom_name": timer.config.custom_name,
                        "remaining_minutes": remaining_minutes,
                        "channel_id": timer.config.channel_id
                    },
                    "cancellation_notification_sent": True
                }
            else:
                # Timer cancelled but notification failed (타이머는 취소되었지만 알림 실패)
                logger.warning(f"⚠️ 타이머 취소됨 (알림 실패): {timer_id}")
                return {
                    "success": True,  # Timer was cancelled successfully
                    "timer_id": timer_id,
                    "message": f"타이머 {timer_id}가 취소되었습니다 (알림 전송 실패).",
                    "timer_info": {
                        "timer_type": timer.config.timer_type.value,
                        "custom_name": timer.config.custom_name,
                        "remaining_minutes": remaining_minutes,
                        "channel_id": timer.config.channel_id
                    },
                    "cancellation_notification_sent": False,
                    "notification_error": cancel_result.get('error')
                }
            
        except Exception as e:
            logger.error(f"❌ 타이머 취소 실패: {e}")
            return {
                "success": False,
                "error": f"타이머 취소 중 오류: {str(e)}",
                "suggestion": "타이머 ID를 확인하고 다시 시도해주세요.",
                "timer_id": timer_id
            }
    
    async def list_active_timers(self) -> Dict[str, Any]:
        """
        List all active timers
        
        모든 활성 타이머 목록을 조회합니다.
        
        Returns:
        --------
        Dict[str, Any]
            Active timers list with comprehensive information
            - success: bool (조회 성공 여부)
            - active_timers: List[dict] (활성 타이머 목록)
            - total_active: int (총 활성 타이머 수)
            - message: str (결과 메시지)
            
        Example:
        --------
        >>> await list_active_timers()
        """
        try:
            active_timers_info = []
            current_time = datetime.now()
            
            for timer_id, timer in self.active_timers.items():
                if timer.is_active:
                    remaining_time = timer.end_time - current_time
                    remaining_minutes = max(0, int(remaining_time.total_seconds() / 60))
                    remaining_seconds = max(0, int(remaining_time.total_seconds() % 60))
                    
                    # Progress calculation (진행률 계산)
                    total_duration = timer.config.duration_minutes * 60
                    elapsed_seconds = (current_time - timer.start_time).total_seconds()
                    progress_percent = min(100, max(0, (elapsed_seconds / total_duration) * 100))
                    
                    timer_info = {
                        'timer_id': timer_id,
                        'timer_type': timer.config.timer_type.value,
                        'custom_name': timer.config.custom_name,
                        'start_time': timer.start_time.isoformat(),
                        'end_time': timer.end_time.isoformat(),
                        'duration_minutes': timer.config.duration_minutes,
                        'remaining_minutes': remaining_minutes,
                        'remaining_seconds': remaining_seconds,
                        'progress_percent': round(progress_percent, 1),
                        'channel_id': timer.config.channel_id,
                        'is_active': timer.is_active,
                        'status': 'running' if remaining_minutes > 0 else 'completing'
                    }
                    active_timers_info.append(timer_info)
            
            logger.info(f"✅ 활성 타이머 목록 조회: {len(active_timers_info)}개")
            
            return {
                "success": True,
                "active_timers": active_timers_info,
                "total_active": len(active_timers_info),
                "message": f"현재 {len(active_timers_info)}개의 활성 타이머가 있습니다.",
                "query_time": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 활성 타이머 목록 조회 실패: {e}")
            return {
                "success": False,
                "error": f"활성 타이머 조회 중 오류: {str(e)}",
                "suggestion": "다시 시도해주세요."
            }
    
    async def get_timer_status(self, timer_id: str) -> Dict[str, Any]:
        """
        Get status of specific timer
        
        특정 타이머의 상태를 조회합니다.
        
        Parameters:
        -----------
        timer_id : str
            Timer ID to check (확인할 타이머 ID)
            
        Returns:
        --------
        Dict[str, Any]
            Timer status information with detailed state
            - success: bool (조회 성공 여부)
            - timer_id: str (타이머 ID)
            - status: str (타이머 상태: 'running', 'completed', 'cancelled')
            - timer_info: dict (상세 타이머 정보)
            
        Example:
        --------
        >>> await get_timer_status("study_20250602_143022_123456")
        """
        try:
            if timer_id not in self.active_timers:
                return {
                    "success": False,
                    "error": f"타이머를 찾을 수 없습니다: {timer_id}",
                    "suggestion": "타이머 ID를 확인해주세요.",
                    "timer_id": timer_id
                }
            
            timer = self.active_timers[timer_id]
            current_time = datetime.now()
            
            # Determine timer status (타이머 상태 결정)
            if timer.is_active and current_time < timer.end_time:
                remaining_time = timer.end_time - current_time
                remaining_minutes = int(remaining_time.total_seconds() / 60)
                remaining_seconds = int(remaining_time.total_seconds() % 60)
                status = "running"
            elif timer.is_active and current_time >= timer.end_time:
                remaining_minutes = 0
                remaining_seconds = 0
                status = "completed"
            else:
                remaining_minutes = 0
                remaining_seconds = 0
                status = "cancelled"
            
            # Calculate progress (진행률 계산)
            total_duration = timer.config.duration_minutes * 60
            elapsed_seconds = (current_time - timer.start_time).total_seconds()
            progress_percent = min(100, max(0, (elapsed_seconds / total_duration) * 100))
            
            logger.info(f"✅ 타이머 상태 조회: {timer_id} ({status})")
            
            return {
                "success": True,
                "timer_id": timer_id,
                "status": status,
                "timer_info": {
                    "timer_type": timer.config.timer_type.value,
                    "custom_name": timer.config.custom_name,
                    "start_time": timer.start_time.isoformat(),
                    "end_time": timer.end_time.isoformat(),
                    "duration_minutes": timer.config.duration_minutes,
                    "remaining_minutes": remaining_minutes,
                    "remaining_seconds": remaining_seconds,
                    "progress_percent": round(progress_percent, 1),
                    "channel_id": timer.config.channel_id,
                    "is_active": timer.is_active
                },
                "message": f"타이머 {timer_id}는 현재 {status} 상태입니다.",
                "query_time": current_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 타이머 상태 조회 실패: {e}")
            return {
                "success": False,
                "error": f"타이머 상태 조회 중 오류: {str(e)}",
                "suggestion": "타이머 ID를 확인하고 다시 시도해주세요.",
                "timer_id": timer_id
            }
    
    def cleanup_completed_timers(self) -> Dict[str, Any]:
        """
        Clean up completed and cancelled timers
        
        완료된 및 취소된 타이머들을 정리합니다.
        
        Returns:
        --------
        Dict[str, Any]
            Cleanup result with statistics
            - cleaned_count: int (정리된 타이머 수)
            - remaining_count: int (남은 활성 타이머 수)
            - message: str (결과 메시지)
        """
        completed_timers = []
        current_time = datetime.now()
        
        for timer_id, timer in list(self.active_timers.items()):
            # Find completed or cancelled timers (완료되었거나 취소된 타이머들 찾기)
            should_cleanup = (
                not timer.is_active or 
                current_time > timer.end_time or
                (timer.task and timer.task.done())
            )
            
            if should_cleanup:
                completed_timers.append(timer_id)
        
        # Remove completed timers (완료된 타이머들 제거)
        for timer_id in completed_timers:
            if timer_id in self.active_timers:
                del self.active_timers[timer_id]
                logger.debug(f"🧹 완료된 타이머 정리: {timer_id}")
        
        remaining_count = len(self.active_timers)
        logger.info(f"🧹 타이머 정리 완료: {len(completed_timers)}개 타이머 제거, {remaining_count}개 남음")
        
        return {
            "cleaned_count": len(completed_timers),
            "remaining_count": remaining_count,
            "message": f"타이머 정리 완료: {len(completed_timers)}개 제거, {remaining_count}개 활성"
        }

# ==================== 3. 편의 함수들 ====================

async def create_pomodoro_manager(slack_client) -> PomodoroTimerManager:
    """
    Factory function to create pomodoro timer manager
    
    뽀모도로 타이머 매니저 생성을 위한 팩토리 함수입니다.
    
    Parameters:
    -----------
    slack_client : SlackAPIClient
        Initialized Slack API client (초기화된 Slack API 클라이언트)
        
    Returns:
    --------
    PomodoroTimerManager
        Initialized pomodoro timer manager (초기화된 뽀모도로 타이머 매니저)
    """
    return PomodoroTimerManager(slack_client)

# ==================== 4. 모듈 정보 ====================

__all__ = [
    'PomodoroTimerManager',
    'TimerType',
    'TimerConfig',
    'ActiveTimer',
    'create_pomodoro_manager'
]