"""
NongBu 금융 투자 정보 스케줄링 시스템
"""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from flask import current_app
from .scraper import FinancialScraper
from .content_generator import FinancialContentGenerator
from .slack_client import NongBuSlackClient
from .models import ScrapingTarget, ScrapedContent, GeneratedContent
from .app import db
from .config import BaseConfig


logger = logging.getLogger(__name__)


class NongBuFinancialScheduler:
    """NongBu 금융 투자 정보 전용 스케줄러"""
    
    def __init__(self, app=None):
        self.scheduler = BackgroundScheduler(timezone=BaseConfig.SCHEDULER_TIMEZONE)
        self.scraper = FinancialScraper()
        self.content_generator = FinancialContentGenerator()
        self.slack_client = None
        
        if BaseConfig.SLACK_BOT_TOKEN:
            self.slack_client = NongBuSlackClient(BaseConfig.SLACK_BOT_TOKEN)
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Flask 앱과 연동"""
        self.app = app
        
        # 앱 컨텍스트 내에서 스케줄러 설정
        with app.app_context():
            self._setup_financial_jobs()
    
    def _setup_financial_jobs(self):
        """금융 전문 작업 스케줄 설정"""
        
        # 1. 금융 뉴스 스크래핑 (3시간마다)
        self.scheduler.add_job(
            func=self._run_financial_scraping_cycle,
            trigger=IntervalTrigger(minutes=BaseConfig.SCRAPING_INTERVAL_MINUTES),
            id='financial_scraping_cycle',
            name='NongBu 금융 뉴스 스크래핑',
            max_instances=1,
            replace_existing=True
        )
        
        # 2. 시장 오픈 전 특별 스크래핑 (미국 시장 기준 - 한국시간 오후 10:30)
        self.scheduler.add_job(
            func=self._run_pre_market_scraping,
            trigger=CronTrigger(hour=22, minute=30, timezone='Asia/Seoul'),
            id='pre_market_scraping',
            name='시장 오픈 전 특별 스크래핑',
            max_instances=1,
            replace_existing=True
        )
        
        # 3. 장중 속보 체크 (미국 시장 시간 중 30분마다)
        self.scheduler.add_job(
            func=self._run_breaking_news_check,
            trigger=CronTrigger(
                hour='23-6,22',  # 한국시간 오후 11시 ~ 새벽 6시, 오후 10시 
                minute='*/30',
                timezone='Asia/Seoul'
            ),
            id='breaking_news_check',
            name='시장 시간 중 속보 체크',
            max_instances=1,
            replace_existing=True
        )
        
        # 4. 일일 시스템 상태 체크 (매일 오전 9시)
        self.scheduler.add_job(
            func=self._run_daily_system_check,
            trigger=CronTrigger(hour=9, minute=0, timezone='Asia/Seoul'),
            id='daily_system_check',
            name='일일 시스템 상태 점검',
            max_instances=1,
            replace_existing=True
        )
        
        # 5. 주말 주요 뉴스 모니터링 (토, 일 12시, 18시)
        self.scheduler.add_job(
            func=self._run_weekend_monitoring,
            trigger=CronTrigger(
                day_of_week='sat,sun',
                hour='12,18',
                minute=0,
                timezone='Asia/Seoul'
            ),
            id='weekend_monitoring',
            name='주말 주요 뉴스 모니터링',
            max_instances=1,
            replace_existing=True
        )
        
        logger.info("NongBu 금융 스케줄러 작업 설정 완료")
    
    def _run_financial_scraping_cycle(self):
        """금융 뉴스 스크래핑 사이클 실행"""
        logger.info("=== NongBu 금융 스크래핑 사이클 시작 ===")
        
        try:
            with self.app.app_context():
                # 1. 금융 사이트 스크래핑
                scraped_count = self._scrape_financial_sources()
                
                # 2. 콘텐츠 생성
                generated_count = self._generate_financial_contents()
                
                # 3. Slack 전송
                sent_count = self._send_to_slack()
                
                # 4. 결과 로깅 및 알림
                self._log_cycle_results(scraped_count, generated_count, sent_count)
                
                logger.info("=== NongBu 금융 스크래핑 사이클 완료 ===")
                
        except Exception as e:
            logger.error(f"금융 스크래핑 사이클 오류: {str(e)}")
            if self.slack_client:
                self.slack_client.send_system_error(
                    "금융 스크래핑 사이클 오류",
                    str(e)
                )
    
    def _scrape_financial_sources(self) -> int:
        """금융 소스 스크래핑"""
        financial_targets = ScrapingTarget.query.filter(
            ScrapingTarget.is_active == True
        ).all()
        
        if not financial_targets:
            logger.warning("활성화된 금융 타겟이 없습니다")
            return 0
        
        total_scraped = 0
        
        for target in financial_targets:
            try:
                scraped_contents = self.scraper.scrape_target(target)
                total_scraped += len(scraped_contents)
                logger.info(f"{target.name}: {len(scraped_contents)}개 스크래핑 완료")
                
            except Exception as e:
                logger.error(f"{target.name} 스크래핑 실패: {str(e)}")
        
        return total_scraped
    
    def _generate_financial_contents(self) -> int:
        """금융 콘텐츠 생성"""
        generated_contents = self.content_generator.generate_batch_content(limit=20)
        return len(generated_contents)
    
    def _send_to_slack(self) -> int:
        """Slack 전송"""
        if not self.slack_client:
            logger.warning("Slack 클라이언트가 설정되지 않음")
            return 0
        
        # 아직 Slack으로 전송되지 않은 콘텐츠 조회
        unsent_contents = db.session.query(GeneratedContent)\
            .outerjoin(GeneratedContent.slack_messages)\
            .filter(GeneratedContent.slack_messages == None)\
            .order_by(GeneratedContent.created_at.desc())\
            .limit(10)\
            .all()
        
        if not unsent_contents:
            logger.info("전송할 새로운 금융 콘텐츠가 없습니다")
            return 0
        
        # 일괄 전송
        results = self.slack_client.send_batch_financial_contents(unsent_contents)
        return results["success"]
    
    def _run_pre_market_scraping(self):
        """시장 오픈 전 특별 스크래핑"""
        logger.info("=== 시장 오픈 전 특별 스크래핑 시작 ===")
        
        try:
            with self.app.app_context():
                # 장 시작 전 중요 뉴스만 필터링
                self._scrape_urgent_financial_news()
                
                if self.slack_client:
                    self.slack_client.send_financial_alert(
                        "시장 오픈 전 체크 완료",
                        "미국 시장 오픈 전 주요 뉴스를 확인했습니다 📈",
                        "info"
                    )
                    
        except Exception as e:
            logger.error(f"시장 오픈 전 스크래핑 오류: {str(e)}")
    
    def _run_breaking_news_check(self):
        """장중 속보 체크"""
        logger.info("장중 속보 체크 시작")
        
        try:
            with self.app.app_context():
                # 최근 30분 내 긴급 뉴스 체크
                urgent_contents = self._check_urgent_financial_news()
                
                if urgent_contents:
                    logger.info(f"긴급 금융 뉴스 {len(urgent_contents)}개 발견")
                    
                    # 즉시 콘텐츠 생성 및 전송
                    for content in urgent_contents:
                        generated = self.content_generator.generate_from_scraped_content(content)
                        if generated and self.slack_client:
                            self.slack_client.send_financial_content(generated)
                            
        except Exception as e:
            logger.error(f"속보 체크 오류: {str(e)}")
    
    def _run_daily_system_check(self):
        """일일 시스템 상태 점검"""
        logger.info("=== 일일 시스템 상태 점검 시작 ===")
        
        try:
            with self.app.app_context():
                # 시스템 통계 수집
                stats = self._collect_daily_stats()
                
                # Slack으로 일일 리포트 전송
                if self.slack_client:
                    self._send_daily_report(stats)
                    
        except Exception as e:
            logger.error(f"일일 시스템 점검 오류: {str(e)}")
    
    def _run_weekend_monitoring(self):
        """주말 주요 뉴스 모니터링"""
        logger.info("주말 금융 뉴스 모니터링")
        
        try:
            with self.app.app_context():
                # 주말에도 중요한 금융 뉴스 체크
                weekend_contents = self._scrape_weekend_financial_news()
                
                if weekend_contents:
                    # 중요도가 높은 뉴스만 처리
                    for content in weekend_contents:
                        if self._is_high_priority_news(content):
                            generated = self.content_generator.generate_from_scraped_content(content)
                            if generated and self.slack_client:
                                self.slack_client.send_financial_content(generated)
                                
        except Exception as e:
            logger.error(f"주말 모니터링 오류: {str(e)}")
    
    def _scrape_urgent_financial_news(self):
        """긴급 금융 뉴스 스크래핑"""
        # 긴급 키워드 기반 필터링 스크래핑
        urgent_keywords = ['breaking', 'urgent', 'fed', 'trump', 'crash', 'surge']
        # 구현 로직...
        pass
    
    def _check_urgent_financial_news(self) -> list:
        """긴급 금융 뉴스 체크"""
        # 최근 30분 내 생성된 콘텐츠 중 긴급 표시가 있는 것들
        thirty_minutes_ago = datetime.utcnow() - timedelta(minutes=30)
        
        urgent_contents = ScrapedContent.query.filter(
            ScrapedContent.scraped_at >= thirty_minutes_ago
        ).filter(
            ScrapedContent.title.contains('Breaking') |
            ScrapedContent.title.contains('URGENT') |
            ScrapedContent.title.contains('ALERT')
        ).all()
        
        return urgent_contents
    
    def _scrape_weekend_financial_news(self) -> list:
        """주말 금융 뉴스 스크래핑"""
        # 주말에는 제한된 소스만 체크
        weekend_targets = ScrapingTarget.query.filter(
            ScrapingTarget.is_active == True,
            ScrapingTarget.config.contains('weekend_active')
        ).all()
        
        contents = []
        for target in weekend_targets:
            try:
                scraped = self.scraper.scrape_target(target)
                contents.extend(scraped)
            except Exception as e:
                logger.error(f"주말 스크래핑 실패 {target.name}: {str(e)}")
        
        return contents
    
    def _is_high_priority_news(self, content: ScrapedContent) -> bool:
        """고우선순위 뉴스 판단"""
        high_priority_keywords = [
            'fed', 'federal reserve', 'interest rate', 'inflation',
            'trump', 'biden', 'breaking', 'crash', 'surge',
            'bitcoin', 'cryptocurrency', 'market'
        ]
        
        title_content = f"{content.title} {content.content}".lower()
        return any(keyword in title_content for keyword in high_priority_keywords)
    
    def _collect_daily_stats(self) -> dict:
        """일일 통계 수집"""
        from datetime import date
        today = date.today()
        
        stats = {
            "date": today.isoformat(),
            "scraped_count": ScrapedContent.query.filter(
                ScrapedContent.scraped_at >= today
            ).count(),
            "generated_count": GeneratedContent.query.filter(
                GeneratedContent.created_at >= today
            ).count(),
            "active_targets": ScrapingTarget.query.filter(
                ScrapingTarget.is_active == True
            ).count()
        }
        
        # Slack 전송 통계 추가
        if self.slack_client:
            slack_stats = self.slack_client.get_daily_stats()
            stats.update(slack_stats)
        
        return stats
    
    def _send_daily_report(self, stats: dict):
        """일일 리포트 전송"""
        report_text = f"📊 *NongBu 금융 시스템 일일 리포트*\n\n"
        report_text += f"📅 날짜: {stats['date']}\n"
        report_text += f"🔍 스크래핑: {stats['scraped_count']}개\n"
        report_text += f"📝 콘텐츠 생성: {stats['generated_count']}개\n"
        report_text += f"📤 Slack 전송: {stats.get('total_sent', 0)}개\n"
        report_text += f"🎯 활성 타겟: {stats['active_targets']}개\n"
        report_text += f"✅ 성공률: {stats.get('success_rate', 0)}%\n\n"
        report_text += f"💡 *투자자들에게 유용한 정보를 전달했습니다!*"
        
        if self.slack_client:
            self.slack_client.send_financial_alert(
                "일일 시스템 리포트",
                report_text,
                "info"
            )
    
    def _log_cycle_results(self, scraped: int, generated: int, sent: int):
        """사이클 결과 로깅"""
        logger.info(f"스크래핑 사이클 결과 - 스크래핑: {scraped}개, 생성: {generated}개, 전송: {sent}개")
        
        if self.slack_client and (scraped > 0 or generated > 0):
            self.slack_client.send_financial_alert(
                "자동 스크래핑 완료",
                f"새로운 금융 정보 {scraped}개를 수집하여 {generated}개의 콘텐츠를 생성하고 {sent}개를 전송했습니다.",
                "success"
            )
    
    def start(self):
        """스케줄러 시작"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("NongBu 금융 스케줄러 시작됨")
    
    def stop(self):
        """스케줄러 중지"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("NongBu 금융 스케줄러 중지됨")
    
    def get_jobs(self):
        """현재 실행 중인 작업 목록"""
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
            for job in self.scheduler.get_jobs()
        ]


# 기존 Scheduler를 NongBuFinancialScheduler로 대체
Scheduler = NongBuFinancialScheduler


def register_scheduled_jobs(scheduler):
    """스케줄된 작업 등록
    
    Args:
        scheduler: APScheduler 인스턴스
    """
    try:
        # 기존 작업 삭제 (중복 방지)
        scheduler.remove_all_jobs()
        
        # 주기적 스크래핑 및 콘텐츠 생성 작업 등록
        interval_minutes = current_app.config.get('SCRAPING_INTERVAL_MINUTES', 60)
        
        scheduler.add_job(
            id='scraping_and_generation',
            func=scheduled_scraping_and_generation,
            trigger='interval',
            minutes=interval_minutes,
            name='스크래핑 및 콘텐츠 생성',
            replace_existing=True
        )
        
        logger.info(f"스케줄 작업 등록 완료: {interval_minutes}분 간격")
        
    except Exception as e:
        logger.error(f"스케줄 작업 등록 실패: {str(e)}")


def get_job_status() -> Dict[str, Any]:
    """스케줄 작업 상태 조회
    
    Returns:
        Dict[str, Any]: 작업 상태 정보
    """
    try:
        from .app import scheduler
        
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
            
        return {
            'success': True,
            'running': scheduler.running,
            'jobs': jobs
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        } 