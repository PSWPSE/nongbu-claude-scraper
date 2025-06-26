"""
NongBu 금융 투자 정보 Slack 클라이언트
"""

import logging
import os
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from .models import GeneratedContent, SlackMessage
from .app import db

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()


logger = logging.getLogger(__name__)


class NongBuSlackClient:
    """NongBu 금융 투자 정보 전용 Slack 클라이언트"""
    
    def __init__(self, token: str):
        self.client = WebClient(token=token)
        self.channel = os.getenv('SLACK_CHANNEL', '#financial-news')
        
    def send_financial_content(self, content: GeneratedContent) -> bool:
        """금융 콘텐츠를 슬랙으로 전송"""
        try:
            logger.info(f"금융 콘텐츠 슬랙 전송 시작: {content.title}")
            
            # 1. 간단한 마크다운 텍스트로 전송
            markdown_text = self._build_markdown_message(content)
            
            # 슬랙 메시지 전송 (마크다운 형태)
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=markdown_text,
                mrkdwn=True,
                unfurl_links=False,
                unfurl_media=False
            )
            
            # 2. 마크다운 소스코드를 메시지로 전송
            self._send_markdown_as_message(content)
            
            # 전송 기록 저장
            slack_message = SlackMessage(
                generated_content_id=content.id,
                channel=self.channel,
                message_ts=response['ts'],
                sent_at=datetime.utcnow(),
                status='sent'
            )
            
            db.session.add(slack_message)
            db.session.commit()
            
            logger.info(f"금융 콘텐츠 슬랙 전송 완료: {content.title}")
            return True
            
        except SlackApiError as e:
            logger.error(f"슬랙 API 오류: {e.response['error']}")
            self._save_failed_message(content, str(e))
            return False
        except Exception as e:
            logger.error(f"슬랙 전송 실패: {str(e)}")
            self._save_failed_message(content, str(e))
            return False
    
    def _build_markdown_message(self, content: GeneratedContent) -> str:
        """간단한 마크다운 형태의 메시지 구성"""
        
        # 기본 메시지 구성
        message_lines = [
            "📈 **NongBu 금융 투자 정보**",
            "─" * 40,
            "",
            f"**{content.title}**",
            "",
            content.content,
            "",
            "─" * 40,
        ]
        
        # 메타 정보 추가
        meta_lines = []
        
        # 태그 정보
        if content.tags:
            tags_text = " ".join([f"#{tag}" for tag in content.tags[:5]])
            meta_lines.append(f"🏷️ **태그**: {tags_text}")
        
        # 생성 시간
        meta_lines.append(f"⏰ **생성시간**: {content.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        # 출처 정보
        try:
            if hasattr(content, 'scraped_content') and content.scraped_content:
                if hasattr(content.scraped_content, 'target') and content.scraped_content.target:
                    meta_lines.append(f"🌐 **출처**: {content.scraped_content.target.name}")
                if content.scraped_content.url:
                    meta_lines.append(f"🔗 **원문**: {content.scraped_content.url}")
        except:
            pass  # 출처 정보가 없어도 계속 진행
        
        # 메타 정보를 메시지에 추가
        message_lines.extend(meta_lines)
        message_lines.extend([
            "",
            "💡 **NongBu와 함께하는 현명한 미국투자** | 투자에는 리스크가 따릅니다."
        ])
        
        return "\n".join(message_lines)
    
    def _send_markdown_as_message(self, content: GeneratedContent) -> bool:
        """마크다운 내용을 메시지로 전송"""
        try:
            # MD 파일 내용 생성
            md_content = self._generate_markdown_file_content(content)
            
            # 파일명 생성
            safe_title = "".join(c for c in content.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title[:50]
            filename = f"nongbu_{safe_title}_{content.id}.md"
            
            # 마크다운 소스를 코드 블록으로 전송
            source_message = f"📋 **마크다운 소스** (`{filename}`)\n"
            source_message += "복사해서 사용하세요:\n\n"
            source_message += f"```markdown\n{md_content}\n```"
            
            # 메시지가 너무 길면 분할 전송
            if len(source_message) > 3900:  # Slack 4000자 제한 고려
                # 헤더 부분
                header = f"📋 **마크다운 소스** (`{filename}`)\n복사해서 사용하세요:\n\n"
                
                # 콘텐츠를 적절한 크기로 분할
                max_content_length = 3900 - len(header) - 20  # ```markdown\n과 \n``` 고려
                
                if len(md_content) > max_content_length:
                    # 첫 번째 부분
                    part1 = md_content[:max_content_length]
                    self.client.chat_postMessage(
                        channel=self.channel,
                        text=f"{header}```markdown\n{part1}\n```\n\n📄 *계속...*",
                        mrkdwn=True
                    )
                    
                    # 나머지 부분
                    remaining = md_content[max_content_length:]
                    self.client.chat_postMessage(
                        channel=self.channel,
                        text=f"📄 **계속 - 마크다운 소스**\n\n```markdown\n{remaining}\n```",
                        mrkdwn=True
                    )
                else:
                    self.client.chat_postMessage(
                        channel=self.channel,
                        text=source_message,
                        mrkdwn=True
                    )
            else:
                self.client.chat_postMessage(
                    channel=self.channel,
                    text=source_message,
                    mrkdwn=True
                )
            
            logger.info(f"마크다운 소스 메시지 전송 완료: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"마크다운 소스 메시지 전송 실패: {str(e)}")
            return False
    
    def _generate_markdown_file_content(self, content: GeneratedContent) -> str:
        """MD 파일용 마크다운 콘텐츠 생성"""
        
        md_lines = [
            f"# {content.title}",
            "",
            f"> 📈 **NongBu 금융 투자 정보**  ",
            f"> 🕒 생성일시: {content.created_at.strftime('%Y년 %m월 %d일 %H:%M')}  ",
            f"> 🆔 콘텐츠 ID: {content.id}",
            "",
            "---",
            "",
            "## 📰 금융 뉴스 내용",
            "",
            content.content,
            "",
            "---",
            "",
            "## 📊 메타 정보",
            "",
        ]
        
        # 태그 정보
        if content.tags:
            md_lines.extend([
                "### 🏷️ 태그",
                "",
                " | ".join([f"`#{tag}`" for tag in content.tags]),
                ""
            ])
        
        # 출처 정보
        try:
            if hasattr(content, 'scraped_content') and content.scraped_content:
                md_lines.extend([
                    "### 🌐 출처 정보",
                    ""
                ])
                
                if hasattr(content.scraped_content, 'target') and content.scraped_content.target:
                    md_lines.append(f"- **사이트**: {content.scraped_content.target.name}")
                
                if content.scraped_content.url:
                    md_lines.append(f"- **원문 링크**: [{content.scraped_content.url}]({content.scraped_content.url})")
                
                if content.scraped_content.scraped_at:
                    md_lines.append(f"- **수집 시간**: {content.scraped_content.scraped_at.strftime('%Y년 %m월 %d일 %H:%M')}")
                
                md_lines.append("")
        except:
            pass
        
        # 요약 정보
        if content.summary:
            md_lines.extend([
                "### 📝 요약",
                "",
                content.summary,
                ""
            ])
        
        # 푸터
        md_lines.extend([
            "---",
            "",
            "**💡 NongBu와 함께하는 현명한 미국투자**",
            "",
            "> ⚠️ 투자에는 리스크가 따릅니다. 투자 결정은 충분한 검토 후 신중하게 하시기 바랍니다.",
            "",
            f"*Generated by NongBu Financial System v1.0 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        ])
        
        return "\n".join(md_lines)
    
    def send_batch_financial_contents(self, contents: List[GeneratedContent]) -> Dict[str, int]:
        """여러 금융 콘텐츠를 일괄 전송"""
        results = {"success": 0, "failed": 0}
        
        logger.info(f"금융 콘텐츠 일괄 전송 시작: {len(contents)}개")
        
        for content in contents:
            if self.send_financial_content(content):
                results["success"] += 1
            else:
                results["failed"] += 1
        
        # 일괄 전송 결과 요약 메시지
        if len(contents) > 1:
            self._send_batch_summary(results, len(contents))
        
        logger.info(f"금융 콘텐츠 일괄 전송 완료: 성공 {results['success']}개, 실패 {results['failed']}개")
        return results
    
    def _send_batch_summary(self, results: Dict[str, int], total: int):
        """일괄 전송 결과 요약 메시지"""
        try:
            summary_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📊 *NongBu 금융 콘텐츠 일괄 전송 완료*\n\n"
                                f"• 전체: {total}개\n"
                                f"• 성공: {results['success']}개 ✅\n"
                                f"• 실패: {results['failed']}개 ❌\n\n"
                                f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                }
            ]
            
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=summary_blocks,
                text=f"일괄 전송 완료: {results['success']}/{total}"
            )
            
        except Exception as e:
            logger.error(f"일괄 전송 요약 메시지 실패: {str(e)}")
    
    def send_financial_alert(self, title: str, message: str, alert_type: str = "info") -> bool:
        """금융 시장 알림 메시지 전송"""
        try:
            # 알림 타입별 이모지 및 색상
            alert_config = {
                "urgent": {"emoji": "🚨", "color": "#ff0000"},
                "warning": {"emoji": "⚠️", "color": "#ff9900"},
                "info": {"emoji": "ℹ️", "color": "#0099ff"},
                "success": {"emoji": "✅", "color": "#00cc00"}
            }
            
            config = alert_config.get(alert_type, alert_config["info"])
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{config['emoji']} *{title}*\n\n{message}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"NongBu 시스템 알림 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                }
            ]
            
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=blocks,
                text=f"{config['emoji']} {title}"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"금융 알림 전송 실패: {str(e)}")
            return False
    
    def send_system_error(self, error_message: str, error_details: str = None):
        """시스템 오류 알림"""
        try:
            error_text = f"🔥 *NongBu 시스템 오류 발생*\n\n"
            error_text += f"*오류:* {error_message}\n"
            
            if error_details:
                error_text += f"*상세:* ```{error_details[:500]}```\n"
            
            error_text += f"*시간:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            error_text += f"*조치:* 시스템 관리자에게 문의하세요."
            
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": error_text
                    }
                }
            ]
            
            self.client.chat_postMessage(
                channel=self.channel,
                blocks=blocks,
                text=f"🔥 시스템 오류: {error_message}"
            )
            
        except Exception as e:
            logger.error(f"오류 알림 전송 실패: {str(e)}")
    
    def test_connection(self) -> bool:
        """Slack 연결 테스트"""
        try:
            response = self.client.auth_test()
            logger.info(f"Slack 연결 성공: {response['user']}")
            
            # 연결 테스트 메시지
            self.send_financial_alert(
                "연결 테스트",
                "NongBu 금융 시스템이 Slack에 성공적으로 연결되었습니다! 📈",
                "success"
            )
            
            return True
            
        except SlackApiError as e:
            logger.error(f"Slack 연결 실패: {e.response['error']}")
            return False
    
    def _save_failed_message(self, content: GeneratedContent, error: str):
        """실패한 메시지 기록 저장"""
        try:
            slack_message = SlackMessage(
                generated_content_id=content.id,
                channel=self.channel,
                message_ts=None,
                sent_at=datetime.utcnow(),
                status='failed',
                error_message=error
            )
            
            db.session.add(slack_message)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"실패 메시지 저장 오류: {str(e)}")
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """일일 전송 통계"""
        from datetime import date
        today = date.today()
        
        # 오늘 전송된 메시지 통계
        total_sent = SlackMessage.query.filter(
            SlackMessage.sent_at >= today,
            SlackMessage.status == 'sent'
        ).count()
        
        failed_sent = SlackMessage.query.filter(
            SlackMessage.sent_at >= today,
            SlackMessage.status == 'failed'
        ).count()
        
        return {
            "date": today.isoformat(),
            "total_sent": total_sent,
            "failed_sent": failed_sent,
            "success_rate": round((total_sent / (total_sent + failed_sent)) * 100, 1) if (total_sent + failed_sent) > 0 else 0
        }


# 기존 SlackClient를 NongBuSlackClient로 대체
SlackClient = NongBuSlackClient 