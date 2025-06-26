#!/usr/bin/env python3
"""
XTweet CLI 명령줄 인터페이스
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 로그 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_logging(level='INFO'):
    """로깅 설정"""
    log_level = getattr(logging, level.upper())
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def cmd_scrape(args):
    """스크래핑 명령"""
    from .scraper import ContentScraper
    
    logger.info("스크래핑을 시작합니다...")
    
    scraper = ContentScraper(use_selenium=args.selenium)
    
    try:
        if args.target_id:
            # 특정 타겟만 스크래핑
            from .models import ScrapingTarget
            target = ScrapingTarget.query.get(args.target_id)
            if not target:
                logger.error(f"타겟을 찾을 수 없습니다: ID {args.target_id}")
                return 1
            
            found, new = scraper.scrape_target(target)
            logger.info(f"스크래핑 완료: {found}개 발견, {new}개 신규")
        else:
            # 모든 활성 타겟 스크래핑
            result = scraper.scrape_all_active_targets()
            logger.info(f"전체 스크래핑 완료: {result}")
            
    except Exception as e:
        logger.error(f"스크래핑 실패: {str(e)}")
        return 1
    finally:
        scraper.close()
        
    return 0


def cmd_generate(args):
    """콘텐츠 생성 명령"""
    from .content_generator import ContentGenerator
    
    logger.info("콘텐츠 생성을 시작합니다...")
    
    generator = ContentGenerator()
    
    try:
        if args.scraped_id:
            # 특정 스크래핑 콘텐츠에서 생성
            from .models import ScrapedContent
            scraped = ScrapedContent.query.get(args.scraped_id)
            if not scraped:
                logger.error(f"스크래핑된 콘텐츠를 찾을 수 없습니다: ID {args.scraped_id}")
                return 1
                
            generated = generator.generate_from_scraped_content(scraped)
            if generated:
                logger.info(f"콘텐츠 생성 완료: {generated.title}")
            else:
                logger.error("콘텐츠 생성 실패")
                return 1
        else:
            # 일괄 생성
            generated_contents = generator.generate_batch_content(limit=args.limit)
            logger.info(f"일괄 콘텐츠 생성 완료: {len(generated_contents)}개")
            
    except Exception as e:
        logger.error(f"콘텐츠 생성 실패: {str(e)}")
        return 1
        
    return 0


def cmd_slack(args):
    """슬랙 전송 명령"""
    from .slack_client import SlackClient
    from .models import GeneratedContent
    
    slack_token = os.getenv('SLACK_BOT_TOKEN')
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN 환경 변수가 설정되지 않았습니다.")
        return 1
    
    logger.info("슬랙 전송을 시작합니다...")
    
    try:
        slack_client = SlackClient(slack_token)
        
        if args.test:
            # 연결 테스트
            result = slack_client.test_connection()
            if result['success']:
                logger.info(f"슬랙 연결 성공: {result}")
            else:
                logger.error(f"슬랙 연결 실패: {result['error']}")
                return 1
        elif args.content_id:
            # 특정 콘텐츠 전송
            content = GeneratedContent.query.get(args.content_id)
            if not content:
                logger.error(f"콘텐츠를 찾을 수 없습니다: ID {args.content_id}")
                return 1
                
            success = slack_client.send_content(content, args.channel)
            if success:
                logger.info("슬랙 전송 성공")
            else:
                logger.error("슬랙 전송 실패")
                return 1
        else:
            logger.error("--test 또는 --content-id 옵션이 필요합니다.")
            return 1
            
    except Exception as e:
        logger.error(f"슬랙 작업 실패: {str(e)}")
        return 1
        
    return 0


def cmd_add_target(args):
    """스크래핑 타겟 추가 명령"""
    from .app import create_app, db
    from .models import ScrapingTarget
    
    app = create_app()
    
    with app.app_context():
        try:
            target = ScrapingTarget(
                name=args.name,
                url=args.url,
                selector=args.selector or '',
                is_active=True
            )
            
            db.session.add(target)
            db.session.commit()
            
            logger.info(f"스크래핑 타겟 추가됨: {args.name} ({args.url})")
            
        except Exception as e:
            logger.error(f"타겟 추가 실패: {str(e)}")
            return 1
            
    return 0


def cmd_list_targets(args):
    """스크래핑 타겟 목록 명령"""
    from .app import create_app
    from .models import ScrapingTarget
    
    app = create_app()
    
    with app.app_context():
        targets = ScrapingTarget.query.all()
        
        if not targets:
            logger.info("등록된 스크래핑 타겟이 없습니다.")
            return 0
            
        logger.info(f"등록된 스크래핑 타겟 ({len(targets)}개):")
        for target in targets:
            status = "활성" if target.is_active else "비활성"
            logger.info(f"  ID: {target.id}, 이름: {target.name}, URL: {target.url}, 상태: {status}")
            
    return 0


def cmd_stats(args):
    """통계 명령"""
    from .app import create_app
    from .models import ScrapingTarget, ScrapedContent, GeneratedContent
    
    app = create_app()
    
    with app.app_context():
        targets_total = ScrapingTarget.query.count()
        targets_active = ScrapingTarget.query.filter_by(is_active=True).count()
        scraped_total = ScrapedContent.query.count()
        generated_total = GeneratedContent.query.count()
        published = GeneratedContent.query.filter_by(is_published=True).count()
        
        logger.info("=== XTweet 시스템 통계 ===")
        logger.info(f"스크래핑 타겟: {targets_total}개 (활성: {targets_active}개)")
        logger.info(f"스크래핑된 콘텐츠: {scraped_total}개")
        logger.info(f"생성된 콘텐츠: {generated_total}개")
        logger.info(f"발행된 콘텐츠: {published}개")
        
    return 0


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='XTweet - 웹 스크래핑 기반 자동 콘텐츠 생성 시스템',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--log-level', 
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
        default='INFO',
        help='로그 레벨 설정'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='사용 가능한 명령')
    
    # 스크래핑 명령
    scrape_parser = subparsers.add_parser('scrape', help='웹 스크래핑 실행')
    scrape_parser.add_argument('--target-id', type=int, help='특정 타겟 ID')
    scrape_parser.add_argument('--selenium', action='store_true', help='Selenium 사용')
    
    # 콘텐츠 생성 명령
    generate_parser = subparsers.add_parser('generate', help='콘텐츠 생성')
    generate_parser.add_argument('--scraped-id', type=int, help='특정 스크래핑 콘텐츠 ID')
    generate_parser.add_argument('--limit', type=int, default=10, help='일괄 생성 개수')
    
    # 슬랙 명령
    slack_parser = subparsers.add_parser('slack', help='슬랙 관련 작업')
    slack_parser.add_argument('--test', action='store_true', help='슬랙 연결 테스트')
    slack_parser.add_argument('--content-id', type=int, help='전송할 콘텐츠 ID')
    slack_parser.add_argument('--channel', default='#general', help='슬랙 채널')
    
    # 타겟 추가 명령
    add_parser = subparsers.add_parser('add-target', help='스크래핑 타겟 추가')
    add_parser.add_argument('name', help='타겟 이름')
    add_parser.add_argument('url', help='타겟 URL')
    add_parser.add_argument('--selector', help='CSS 셀렉터')
    
    # 타겟 목록 명령
    subparsers.add_parser('list-targets', help='스크래핑 타겟 목록')
    
    # 통계 명령
    subparsers.add_parser('stats', help='시스템 통계')
    
    args = parser.parse_args()
    
    # 로그 레벨 설정
    setup_logging(args.log_level)
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 명령 실행
    command_map = {
        'scrape': cmd_scrape,
        'generate': cmd_generate,
        'slack': cmd_slack,
        'add-target': cmd_add_target,
        'list-targets': cmd_list_targets,
        'stats': cmd_stats,
    }
    
    if args.command in command_map:
        return command_map[args.command](args)
    else:
        logger.error(f"알 수 없는 명령: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 