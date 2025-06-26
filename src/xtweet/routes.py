"""
NongBu 금융 투자 정보 Flask 라우트
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, render_template, current_app, send_from_directory
import os
import subprocess
import platform

# 환경 변수 로드
from dotenv import load_dotenv
load_dotenv()

from .models import ScrapingTarget, ScrapedContent, GeneratedContent, SlackMessage
from .scraper import FinancialScraper
from .content_generator import FinancialContentGenerator
from .slack_client import NongBuSlackClient
from .app import db


logger = logging.getLogger(__name__)

# Blueprint 생성
bp = Blueprint('api', __name__)


@bp.route('/')
def index():
    """NongBu 금융 시스템 대시보드"""
    return render_template('index.html')


@bp.route('/api/stats')
def get_stats():
    """시스템 통계 조회"""
    try:
        # 오늘 기준 통계
        today = datetime.utcnow().date()
        
        stats = {
            'scraped_today': ScrapedContent.query.filter(
                ScrapedContent.scraped_at >= today
            ).count(),
            'generated_today': GeneratedContent.query.filter(
                GeneratedContent.created_at >= today
            ).count(),
            'sent_today': SlackMessage.query.filter(
                SlackMessage.sent_at >= today,
                SlackMessage.status == 'sent'
            ).count(),
            'active_targets': ScrapingTarget.query.filter(
                ScrapingTarget.is_active == True
            ).count(),
            'total_scraped': ScrapedContent.query.count(),
            'total_generated': GeneratedContent.query.count(),
            'total_sent': SlackMessage.query.filter(
                SlackMessage.status == 'sent'
            ).count()
        }
        
        # 최근 7일 일별 통계
        daily_stats = []
        for i in range(7):
            date = today - timedelta(days=i)
            daily_stats.append({
                'date': date.isoformat(),
                'scraped': ScrapedContent.query.filter(
                    ScrapedContent.scraped_at >= date,
                    ScrapedContent.scraped_at < date + timedelta(days=1)
                ).count(),
                'generated': GeneratedContent.query.filter(
                    GeneratedContent.created_at >= date,
                    GeneratedContent.created_at < date + timedelta(days=1)
                ).count()
            })
        
        stats['daily_stats'] = daily_stats
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"통계 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/targets', methods=['GET'])
def get_targets():
    """스크래핑 대상 목록 조회"""
    try:
        targets = ScrapingTarget.query.all()
        return jsonify({
            'success': True,
            'data': [target.to_dict() for target in targets]
        })
    except Exception as e:
        logger.error(f"타겟 목록 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/targets', methods=['POST'])
def add_target():
    """새로운 금융 스크래핑 대상 추가"""
    try:
        data = request.get_json()
        
        # 기본 금융 사이트 설정
        if not data.get('scraping_config'):
            data['scraping_config'] = {
                'type': 'financial_news',
                'priority': 'normal'
            }
        
        target = ScrapingTarget(
            name=data['name'],
            url=data['url'],
            selector=data.get('selector', '.article'),
            scraping_config=data.get('scraping_config', {}),
            is_active=data.get('is_active', True),
            created_at=datetime.utcnow()
        )
        
        db.session.add(target)
        db.session.commit()
        
        logger.info(f"새로운 금융 타겟 추가: {target.name}")
        
        return jsonify({
            'success': True,
            'data': target.to_dict(),
            'message': f'금융 사이트 "{target.name}"가 추가되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"타겟 추가 실패: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/targets/<int:target_id>', methods=['PUT'])
def update_target(target_id):
    """스크래핑 대상 수정"""
    try:
        target = ScrapingTarget.query.get_or_404(target_id)
        data = request.get_json()
        
        target.name = data.get('name', target.name)
        target.url = data.get('url', target.url)
        target.selector = data.get('selector', target.selector)
        target.scraping_config = data.get('scraping_config', target.scraping_config)
        target.is_active = data.get('is_active', target.is_active)
        target.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': target.to_dict(),
            'message': f'"{target.name}" 설정이 업데이트되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"타겟 수정 실패: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/targets/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    """스크래핑 대상 삭제"""
    try:
        target = ScrapingTarget.query.get_or_404(target_id)
        target_name = target.name
        
        db.session.delete(target)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'"{target_name}"가 삭제되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"타겟 삭제 실패: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/scrape', methods=['POST'])
def manual_scrape():
    """수동 금융 뉴스 스크래핑 실행"""
    try:
        data = request.get_json() or {}
        target_id = data.get('target_id')
        test_mode = data.get('test_mode', True)  # 기본값을 테스트 모드로 설정
        
        scraper = FinancialScraper(test_mode=test_mode)
        
        if target_id:
            # 특정 타겟만 스크래핑
            target = ScrapingTarget.query.get_or_404(target_id)
            found, new = scraper.scrape_target(target)
            result = {
                'target_name': target.name,
                'found_count': found,
                'new_count': new
            }
        else:
            # 모든 활성 타겟 스크래핑
            result = scraper.scrape_all_active_targets()
        
        mode_message = "테스트 모드로" if test_mode else "전체 모드로"
        return jsonify({
            'success': True,
            'data': result,
            'message': f'금융 뉴스 스크래핑이 {mode_message} 완료되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"수동 스크래핑 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/contents/generate', methods=['POST'])
def generate_contents():
    """금융 콘텐츠 생성"""
    try:
        data = request.get_json() or {}
        limit = data.get('limit', 10)
        
        generator = FinancialContentGenerator()
        generated_contents = generator.generate_batch_content(limit=limit)
        
        return jsonify({
            'success': True,
            'data': {
                'generated_count': len(generated_contents),
                'contents': [content.to_dict() for content in generated_contents]
            },
            'message': f'{len(generated_contents)}개의 금융 콘텐츠가 생성되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"콘텐츠 생성 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/contents', methods=['GET'])
def get_contents():
    """생성된 금융 콘텐츠 목록 조회"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        contents = GeneratedContent.query\
            .order_by(GeneratedContent.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'success': True,
            'data': {
                'contents': [content.to_dict() for content in contents.items],
                'total': contents.total,
                'pages': contents.pages,
                'current_page': page
            }
        })
        
    except Exception as e:
        logger.error(f"콘텐츠 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/slack/test', methods=['POST'])
def test_slack_connection():
    """Slack 연결 테스트"""
    try:
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_token:
            return jsonify({
                'success': False,
                'error': 'Slack 토큰이 설정되지 않았습니다.'
            }), 400
        
        slack_client = NongBuSlackClient(slack_token)
        success = slack_client.test_connection()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'NongBu Slack 연결이 성공적으로 테스트되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Slack 연결 테스트에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"Slack 연결 테스트 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/slack/send', methods=['POST'])
def send_to_slack():
    """선택된 금융 콘텐츠를 Slack으로 전송"""
    try:
        data = request.get_json()
        content_ids = data.get('content_ids', [])
        
        if not content_ids:
            return jsonify({
                'success': False,
                'error': '전송할 콘텐츠를 선택해주세요.'
            }), 400
        
        slack_token = os.getenv('SLACK_BOT_TOKEN')
        if not slack_token:
            return jsonify({
                'success': False,
                'error': 'Slack 토큰이 설정되지 않았습니다.'
            }), 400
        
        # 콘텐츠 조회
        contents = GeneratedContent.query.filter(
            GeneratedContent.id.in_(content_ids)
        ).all()
        
        if not contents:
            return jsonify({
                'success': False,
                'error': '선택된 콘텐츠를 찾을 수 없습니다.'
            }), 404
        
        # Slack 전송
        slack_client = NongBuSlackClient(slack_token)
        results = slack_client.send_batch_financial_contents(contents)
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f'성공: {results["success"]}개, 실패: {results["failed"]}개'
        })
        
    except Exception as e:
        logger.error(f"Slack 전송 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/slack/send/all', methods=['POST'])
def send_all_to_slack():
    """전송되지 않은 모든 금융 콘텐츠를 Slack으로 전송"""
    try:
        slack_token = current_app.config.get('SLACK_BOT_TOKEN')
        if not slack_token:
            return jsonify({
                'success': False,
                'error': 'Slack 토큰이 설정되지 않았습니다.'
            }), 400
        
        # 아직 전송되지 않은 콘텐츠 조회
        unsent_contents = db.session.query(GeneratedContent)\
            .outerjoin(GeneratedContent.slack_messages)\
            .filter(GeneratedContent.slack_messages == None)\
            .order_by(GeneratedContent.created_at.desc())\
            .limit(20)\
            .all()
        
        if not unsent_contents:
            return jsonify({
                'success': True,
                'message': '전송할 새로운 콘텐츠가 없습니다.'
            })
        
        # Slack 전송
        slack_client = NongBuSlackClient(slack_token)
        results = slack_client.send_batch_financial_contents(unsent_contents)
        
        return jsonify({
            'success': True,
            'data': results,
            'message': f'총 {len(unsent_contents)}개 중 성공: {results["success"]}개, 실패: {results["failed"]}개'
        })
        
    except Exception as e:
        logger.error(f"전체 Slack 전송 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/system/alert', methods=['POST'])
def send_system_alert():
    """시스템 알림 메시지 전송"""
    try:
        data = request.get_json()
        title = data.get('title', '시스템 알림')
        message = data.get('message', '')
        alert_type = data.get('type', 'info')
        
        slack_token = current_app.config.get('SLACK_BOT_TOKEN')
        if not slack_token:
            return jsonify({
                'success': False,
                'error': 'Slack 토큰이 설정되지 않았습니다.'
            }), 400
        
        slack_client = NongBuSlackClient(slack_token)
        success = slack_client.send_financial_alert(title, message, alert_type)
        
        if success:
            return jsonify({
                'success': True,
                'message': '시스템 알림이 전송되었습니다.'
            })
        else:
            return jsonify({
                'success': False,
                'error': '알림 전송에 실패했습니다.'
            }), 500
            
    except Exception as e:
        logger.error(f"시스템 알림 전송 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/financial/urgent', methods=['POST'])
def check_urgent_news():
    """긴급 금융 뉴스 수동 체크"""
    try:
        # 최근 1시간 내 스크래핑된 콘텐츠 중 긴급 키워드 검색
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        urgent_keywords = ['breaking', 'urgent', 'alert', 'fed', 'trump', 'crash', 'surge']
        
        urgent_contents = []
        for keyword in urgent_keywords:
            contents = ScrapedContent.query.filter(
                ScrapedContent.scraped_at >= one_hour_ago,
                ScrapedContent.title.ilike(f'%{keyword}%')
            ).limit(5).all()
            urgent_contents.extend(contents)
        
        # 중복 제거
        unique_contents = list({content.id: content for content in urgent_contents}.values())
        
        return jsonify({
            'success': True,
            'data': {
                'urgent_count': len(unique_contents),
                'contents': [content.to_dict() for content in unique_contents[:10]]
            },
            'message': f'{len(unique_contents)}개의 긴급 금융 뉴스를 발견했습니다.'
        })
        
    except Exception as e:
        logger.error(f"긴급 뉴스 체크 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/contents/save-markdown', methods=['POST'])
def save_content_as_markdown():
    """생성된 콘텐츠를 마크다운 파일로 저장"""
    try:
        data = request.get_json()
        content_id = data.get('content_id')
        
        if not content_id:
            return jsonify({
                'success': False,
                'error': '콘텐츠 ID가 필요합니다.'
            }), 400
        
        # 콘텐츠 조회
        content = GeneratedContent.query.get_or_404(content_id)
        
        # 마크다운 파일명 생성 (한글 제목 + 시간 + ID)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # 제목에서 특수문자 제거하고 공백을 언더스코어로 변경
        safe_title = "".join(c if c.isalnum() or c in (' ', '_', '-') else '' 
                           for c in (content.title or 'content'))[:50]
        safe_title = safe_title.replace(' ', '_')
        filename = f"nongbu_{safe_title}_{timestamp}_{content.id}.md"
        
        # 저장 디렉토리 확인 및 생성
        markdown_dir = os.path.join(os.getcwd(), 'saved_markdown')
        os.makedirs(markdown_dir, exist_ok=True)
        
        # 파일 경로
        file_path = os.path.join(markdown_dir, filename)
        
        # 마크다운 콘텐츠 포맷팅
        markdown_content = f"""# {content.title or '제목 없음'}

{content.content or '내용 없음'}

---

**생성 시간:** {content.created_at.strftime('%Y년 %m월 %d일 %H시 %M분')}  
**NongBu 금융 투자 정보 시스템**
"""
        
        # 파일 저장
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"마크다운 파일 저장 완료: {filename}")
        
        return jsonify({
            'success': True,
            'data': {
                'filename': filename,
                'file_path': file_path,
                'content_id': content_id
            },
            'message': f'마크다운 파일이 저장되었습니다: {filename}'
        })
        
    except Exception as e:
        logger.error(f"마크다운 파일 저장 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/contents/open-file', methods=['POST'])
def open_markdown_file():
    """저장된 마크다운 파일 열기"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({
                'success': False,
                'error': '파일명이 필요합니다.'
            }), 400
        
        # 파일 경로
        markdown_dir = os.path.join(os.getcwd(), 'saved_markdown')
        file_path = os.path.join(markdown_dir, filename)
        
        # 파일 존재 확인
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '파일을 찾을 수 없습니다.'
            }), 404
        
        # OS별 파일 열기
        try:
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            elif system == 'Windows':
                os.startfile(file_path)
            elif system == 'Linux':
                subprocess.run(['xdg-open', file_path])
            else:
                return jsonify({
                    'success': False,
                    'error': f'지원되지 않는 운영체제: {system}'
                }), 500
            
            logger.info(f"파일 열기 실행: {filename}")
            
            return jsonify({
                'success': True,
                'message': f'파일을 열었습니다: {filename}'
            })
            
        except Exception as e:
            logger.error(f"파일 열기 실패: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'파일 열기에 실패했습니다: {str(e)}'
            }), 500
        
    except Exception as e:
        logger.error(f"파일 열기 요청 처리 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/api/contents/list-markdown', methods=['GET'])
def list_markdown_files():
    """저장된 마크다운 파일 목록 조회"""
    try:
        markdown_dir = os.path.join(os.getcwd(), 'saved_markdown')
        
        if not os.path.exists(markdown_dir):
            return jsonify({
                'success': True,
                'data': []
            })
        
        # 마크다운 파일 목록 가져오기
        files = []
        for filename in os.listdir(markdown_dir):
            if filename.endswith('.md'):
                file_path = os.path.join(markdown_dir, filename)
                stat = os.stat(file_path)
                files.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # 생성 시간 역순으로 정렬
        files.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': files
        })
        
    except Exception as e:
        logger.error(f"마크다운 파일 목록 조회 실패: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# 에러 핸들러
@bp.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'API 엔드포인트를 찾을 수 없습니다.'
    }), 404


@bp.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': '서버 내부 오류가 발생했습니다.'
    }), 500 