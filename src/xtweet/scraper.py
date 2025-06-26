"""
웹 스크래핑 모듈
"""

import hashlib
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from .app import db
from .models import ScrapingTarget, ScrapedContent, ScrapingLog


logger = logging.getLogger(__name__)

# 콘텐츠 수집 시간 제한 (분)
CONTENT_TIME_LIMIT_MINUTES = 180  # 3시간

# 테스트 모드: 수집할 기사 수 제한
TEST_MODE_ARTICLE_LIMIT = 5


class ContentScraper:
    """웹 콘텐츠 스크래핑 클래스"""
    def __init__(self, use_selenium: bool = False, test_mode: bool = True):
        """스크래퍼 초기화
        
        Args:
            use_selenium: Selenium 사용 여부 (JavaScript 렌더링이 필요한 경우)
            test_mode: 테스트 모드 여부 (기사 수 제한)
        """
        self.use_selenium = use_selenium
        self.test_mode = test_mode
        self.session = requests.Session()
        self._setup_session()
        self.driver = None
        self.scrape_cutoff_time = datetime.utcnow() - timedelta(minutes=CONTENT_TIME_LIMIT_MINUTES)
        
    def _setup_session(self) -> None:
        """requests 세션 설정"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
    def _get_selenium_driver(self) -> webdriver.Chrome:
        """Selenium WebDriver 초기화
        
        Returns:
            webdriver.Chrome: Chrome WebDriver 인스턴스
        """
        if self.driver is None:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
        return self.driver
        
    def scrape_target(self, target: ScrapingTarget) -> Tuple[int, int]:
        """특정 타겟 스크래핑 실행
        
        Args:
            target: 스크래핑 대상 객체
            
        Returns:
            Tuple[int, int]: (발견된 아이템 수, 새로운 아이템 수)
        """
        logger.info(f"스크래핑 시작: {target.name} ({target.url})")
        logger.info(f"수집 대상: {self.scrape_cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} UTC 이후 발행된 콘텐츠")
        
        # 스크래핑 로그 생성
        log = ScrapingLog(
            target_id=target.id,
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        try:
            start_time = time.time()
            
            # 콘텐츠 추출
            contents = self._extract_content(target)
            items_found = len(contents)
            items_new = 0
            
            # 새로운 콘텐츠 저장
            for content_data in contents:
                if self._save_content(target, content_data):
                    items_new += 1
            
            # 로그 업데이트
            execution_time = int(time.time() - start_time)
            log.status = 'completed'
            log.items_found = items_found
            log.items_new = items_new
            log.execution_time = execution_time
            log.finished_at = datetime.utcnow()
            
            logger.info(f"스크래핑 완료: {target.name}, 발견: {items_found}, 새로운: {items_new}")
            
        except Exception as e:
            logger.error(f"스크래핑 실패: {target.name}, 오류: {str(e)}")
            log.status = 'failed'
            log.error_message = str(e)
            log.finished_at = datetime.utcnow()
            raise
            
        finally:
            db.session.commit()
            
        return items_found, items_new
        
    def _extract_content(self, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """웹페이지에서 콘텐츠 추출
        
        Args:
            target: 스크래핑 대상 객체
            
        Returns:
            List[Dict[str, Any]]: 추출된 콘텐츠 목록
        """
        if self.use_selenium:
            return self._extract_with_selenium(target)
        else:
            return self._extract_with_requests(target)
            
    def _extract_with_requests(self, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """requests를 사용한 콘텐츠 추출
        
        Args:
            target: 스크래핑 대상 객체
            
        Returns:
            List[Dict[str, Any]]: 추출된 콘텐츠 목록
        """
        try:
            response = self.session.get(target.url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return self._parse_content(soup, target)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP 요청 실패: {target.url}, 오류: {str(e)}")
            raise
            
    def _extract_with_selenium(self, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """Selenium을 사용한 콘텐츠 추출
        
        Args:
            target: 스크래핑 대상 객체
            
        Returns:
            List[Dict[str, Any]]: 추출된 콘텐츠 목록
        """
        try:
            driver = self._get_selenium_driver()
            driver.get(target.url)
            
            # 페이지 로딩 대기
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 추가 로딩 대기 (동적 콘텐츠)
            time.sleep(3)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            return self._parse_content(soup, target)
            
        except (TimeoutException, WebDriverException) as e:
            logger.error(f"Selenium 추출 실패: {target.url}, 오류: {str(e)}")
            raise
            
    def _parse_content(self, soup: BeautifulSoup, target: ScrapingTarget) -> List[Dict[str, Any]]:
        """HTML에서 콘텐츠 파싱
        
        Args:
            soup: BeautifulSoup 객체
            target: 스크래핑 대상 객체
            
        Returns:
            List[Dict[str, Any]]: 파싱된 콘텐츠 목록
        """
        contents = []
        config = target.scraping_config or {}
        
        # 기본 셀렉터 또는 설정에서 가져온 셀렉터 사용
        selector = config.get('content_selector', target.selector)
        if not selector:
            # 뉴스 사이트별 기본 셀렉터들
            selectors = [
                'article', 
                '.article', 
                '.story',
                '.post', 
                '.content', 
                '.entry',
                '.news-item',
                '.headline',
                'main'
            ]
            for sel in selectors:
                elements = soup.select(sel)
                if elements:
                    selector = sel
                    break
        
        if selector:
            elements = soup.select(selector)
        else:
            # 링크가 있는 제목들을 찾기
            elements = soup.select('h1 a, h2 a, h3 a, .title a')
            
        # 테스트 모드에서는 제한된 수만 처리
        if self.test_mode:
            elements = elements[:TEST_MODE_ARTICLE_LIMIT]
            logger.info(f"테스트 모드: 최대 {TEST_MODE_ARTICLE_LIMIT}개 기사만 처리")
            
        for element in elements:
            content_data = self._extract_element_data(element, target, config)
            if content_data and self._is_valid_content(content_data):
                contents.append(content_data)
                
        return contents
        
    def _extract_element_data(self, element, target: ScrapingTarget, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """개별 엘리먼트에서 데이터 추출
        
        Args:
            element: BeautifulSoup 엘리먼트
            target: 스크래핑 대상 객체
            config: 스크래핑 설정
            
        Returns:
            Optional[Dict[str, Any]]: 추출된 데이터 또는 None
        """
        try:
            # 제목 추출
            title_selector = config.get('title_selector', 'h1, h2, h3, .title')
            title_elem = element.select_one(title_selector)
            if not title_elem:
                title_elem = element if element.name in ['h1', 'h2', 'h3'] else element.select_one('a')
            title = title_elem.get_text(strip=True) if title_elem else ''
            
            # URL 추출 (링크가 있는 경우)
            link_elem = element.select_one('a[href]') if element.name != 'a' else element
            url = ''
            if link_elem:
                href = link_elem.get('href')
                url = urljoin(target.url, href) if href else ''
            
            # 개별 기사 페이지에서 본문 추출
            content_text = ''
            if url and url.startswith('http'):
                content_text = self._extract_article_content(url)
            
            # 개별 기사에서 본문을 가져오지 못한 경우, 현재 엘리먼트에서 추출
            if not content_text:
                content_text = element.get_text(separator='\n', strip=True)
            
            # 발행 시간 추출 시도
            published_time = self._extract_published_time(element)
            
            content_data = {
                'title': title,
                'content': content_text,
                'url': url,
                'published_time': published_time,
                'metadata': {
                    'source_url': target.url,
                    'scraped_at': datetime.utcnow().isoformat(),
                    'element_tag': element.name,
                    'element_classes': element.get('class', []),
                    'content_length': len(content_text),
                    'has_detailed_content': len(content_text) > 500
                }
            }
            
            # 시간 필터링 적용
            if not self._is_recent_content(content_data):
                logger.debug(f"시간 필터링으로 제외: {title[:50]}...")
                return None
                
            return content_data
            
        except Exception as e:
            logger.warning(f"엘리먼트 데이터 추출 실패: {str(e)}")
            return None
    
    def _extract_article_content(self, article_url: str) -> str:
        """개별 기사 페이지에서 본문 내용 추출
        
        Args:
            article_url: 기사 URL
            
        Returns:
            str: 추출된 본문 내용
        """
        try:
            logger.debug(f"기사 본문 추출 시작: {article_url}")
            
            # 개별 기사 페이지 요청
            response = self.session.get(article_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 본문 추출을 위한 다양한 셀렉터 시도 (우선순위 순)
            content_selectors = [
                # 일반적인 기사 본문 셀렉터
                '.article-body',
                '.story-body',
                '.content-body',
                '.post-content',
                '.entry-content',
                '.article-content',
                '.body-text',
                
                # 특정 뉴스 사이트 셀렉터
                '[data-module="ArticleBody"]',  # Reuters
                '.InlineVideo-container + div',  # MarketWatch
                '.story-body__inner',  # CNN
                '.caas-body',  # Yahoo
                
                # 범용 셀렉터
                'article .content',
                'main article',
                '.main-content article'
            ]
            
            best_content = ''
            best_length = 0
            
            # 각 셀렉터로 본문 추출 시도
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 불필요한 요소 제거
                    for unwanted in content_elem.select('script, style, .ad, .advertisement, .social-share, nav, header, footer'):
                        unwanted.decompose()
                    
                    content_text = content_elem.get_text(separator='\n', strip=True)
                    if len(content_text) > best_length:
                        best_content = content_text
                        best_length = len(content_text)
                        logger.debug(f"{selector}에서 {len(content_text)}자 추출")
            
            # 디버깅에서 성공한 paragraph 방식 추가
            if best_length < 500:  # 충분하지 않은 경우 paragraph 방식 시도
                paragraphs = soup.select('p')
                if paragraphs:
                    # 30자 이상의 의미있는 paragraph만 선택
                    meaningful_paragraphs = [
                        p.get_text(strip=True) for p in paragraphs 
                        if len(p.get_text(strip=True)) > 30
                    ]
                    
                    if meaningful_paragraphs:
                        paragraph_content = '\n'.join(meaningful_paragraphs)
                        if len(paragraph_content) > best_length:
                            best_content = paragraph_content
                            best_length = len(paragraph_content)
                            logger.debug(f"paragraph 방식에서 {len(paragraph_content)}자 추출")
            
            # 여전히 짧은 경우 main/article 태그에서 전체 추출
            if best_length < 200:
                main_content = soup.select_one('main') or soup.select_one('article')
                if main_content:
                    # 불필요한 요소 제거
                    for unwanted in main_content.select('nav, header, footer, aside, .menu, .navigation, script, style, .ad'):
                        unwanted.decompose()
                    
                    fallback_content = main_content.get_text(separator='\n', strip=True)
                    if len(fallback_content) > best_length:
                        best_content = fallback_content
                        best_length = len(fallback_content)
                        logger.debug(f"fallback 방식에서 {len(fallback_content)}자 추출")
            
            if best_length > 0:
                logger.debug(f"본문 추출 성공: {best_length}자")
            else:
                logger.warning(f"본문 추출 실패: {article_url}")
            
            return best_content
            
        except Exception as e:
            logger.warning(f"기사 본문 추출 실패: {article_url}, 오류: {str(e)}")
            return ''
    
    def _extract_published_time(self, element) -> Optional[datetime]:
        """HTML 엘리먼트에서 발행 시간 추출
        
        Args:
            element: BeautifulSoup 엘리먼트
            
        Returns:
            Optional[datetime]: 발행 시간 또는 None
        """
        try:
            # 다양한 시간 관련 셀렉터 시도
            time_selectors = [
                'time[datetime]',
                '.published, .date, .time',
                '[data-timestamp]',
                '.post-date, .article-date'
            ]
            
            for selector in time_selectors:
                time_elem = element.select_one(selector)
                if time_elem:
                    # datetime 속성 확인
                    datetime_attr = time_elem.get('datetime')
                    if datetime_attr:
                        return self._parse_datetime_string(datetime_attr)
                    
                    # data-timestamp 속성 확인
                    timestamp_attr = time_elem.get('data-timestamp')
                    if timestamp_attr:
                        try:
                            return datetime.fromtimestamp(int(timestamp_attr))
                        except (ValueError, TypeError):
                            pass
                    
                    # 텍스트에서 시간 정보 추출
                    time_text = time_elem.get_text(strip=True)
                    parsed_time = self._parse_time_text(time_text)
                    if parsed_time:
                        return parsed_time
            
            # 전체 엘리먼트 텍스트에서 상대 시간 추출 시도
            full_text = element.get_text()
            relative_time = self._extract_relative_time(full_text)
            if relative_time:
                return relative_time
                
        except Exception as e:
            logger.debug(f"시간 추출 실패: {str(e)}")
            
        return None
    
    def _parse_datetime_string(self, datetime_str: str) -> Optional[datetime]:
        """ISO 형식 등의 datetime 문자열 파싱
        
        Args:
            datetime_str: datetime 문자열
            
        Returns:
            Optional[datetime]: 파싱된 datetime 또는 None
        """
        formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
                
        return None
    
    def _parse_time_text(self, time_text: str) -> Optional[datetime]:
        """시간 텍스트에서 datetime 추출
        
        Args:
            time_text: 시간 관련 텍스트
            
        Returns:
            Optional[datetime]: 추출된 datetime 또는 None
        """
        try:
            # "1시간 전", "2 hours ago" 등의 상대 시간
            relative_time = self._extract_relative_time(time_text)
            if relative_time:
                return relative_time
                
            # 절대 시간 형식들
            formats = [
                '%Y-%m-%d %H:%M',
                '%Y.%m.%d %H:%M',
                '%m/%d/%Y %H:%M',
                '%d.%m.%Y %H:%M'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(time_text.strip(), fmt)
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.debug(f"시간 텍스트 파싱 실패: {time_text}, 오류: {str(e)}")
            
        return None
    
    def _extract_relative_time(self, text: str) -> Optional[datetime]:
        """텍스트에서 상대 시간 추출 ("1시간 전", "2 hours ago" 등)
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            Optional[datetime]: 계산된 절대 시간 또는 None
        """
        try:
            text = text.lower().strip()
            now = datetime.utcnow()
            
            # 한국어 패턴
            korean_patterns = [
                (r'(\d+)분\s*전', 'minutes'),
                (r'(\d+)시간\s*전', 'hours'),
                (r'(\d+)일\s*전', 'days'),
                (r'(\d+)주\s*전', 'weeks'),
                (r'(\d+)개월\s*전', 'months'),
            ]
            
            # 영어 패턴
            english_patterns = [
                (r'(\d+)\s*minutes?\s*ago', 'minutes'),
                (r'(\d+)\s*hours?\s*ago', 'hours'),
                (r'(\d+)\s*days?\s*ago', 'days'),
                (r'(\d+)\s*weeks?\s*ago', 'weeks'),
                (r'(\d+)\s*months?\s*ago', 'months'),
            ]
            
            all_patterns = korean_patterns + english_patterns
            
            for pattern, unit in all_patterns:
                match = re.search(pattern, text)
                if match:
                    value = int(match.group(1))
                    
                    if unit == 'minutes':
                        return now - timedelta(minutes=value)
                    elif unit == 'hours':
                        return now - timedelta(hours=value)
                    elif unit == 'days':
                        return now - timedelta(days=value)
                    elif unit == 'weeks':
                        return now - timedelta(weeks=value)
                    elif unit == 'months':
                        return now - timedelta(days=value * 30)  # 근사치
            
            # "방금 전", "just now" 등
            immediate_patterns = [
                r'방금\s*전', r'just\s*now', r'a\s*moment\s*ago'
            ]
            
            for pattern in immediate_patterns:
                if re.search(pattern, text):
                    return now - timedelta(minutes=1)
                    
        except Exception as e:
            logger.debug(f"상대 시간 추출 실패: {text}, 오류: {str(e)}")
            
        return None
    
    def _is_recent_content(self, content_data: Dict[str, Any]) -> bool:
        """콘텐츠가 최근 발행된 것인지 확인
        
        Args:
            content_data: 콘텐츠 데이터
            
        Returns:
            bool: 최근 콘텐츠 여부 (3시간 이내)
        """
        published_time = content_data.get('published_time')
        
        if published_time is None:
            # 발행 시간을 알 수 없는 경우, 최근 콘텐츠로 간주
            logger.debug(f"발행 시간 정보 없음, 수집 대상으로 처리: {content_data.get('title', '')[:50]}")
            return True
            
        if published_time >= self.scrape_cutoff_time:
            logger.debug(f"최신 콘텐츠 수집: {published_time.strftime('%Y-%m-%d %H:%M:%S')} - {content_data.get('title', '')[:50]}")
            return True
        else:
            logger.debug(f"시간 초과로 제외: {published_time.strftime('%Y-%m-%d %H:%M:%S')} - {content_data.get('title', '')[:50]}")
            return False
            
    def _is_valid_content(self, content_data: Dict[str, Any]) -> bool:
        """콘텐츠 유효성 검사
        
        Args:
            content_data: 콘텐츠 데이터
            
        Returns:
            bool: 유효성 여부
        """
        # 제목이 없으면 무효
        if not content_data.get('title', '').strip():
            return False
            
        # 본문이 너무 짧으면 무효 (개선된 조건)
        content = content_data.get('content', '')
        if len(content.strip()) < 50:  # 최소 50자
            return False
            
        # 제목과 본문이 너무 유사하면 무효 (제목만 반복하는 경우)
        title = content_data.get('title', '').strip()
        if title and content.strip() == title:
            return False
        
        # 테스트 모드에서는 더 엄격한 검증
        if self.test_mode:
            # 상세 본문이 있는지 확인
            if len(content.strip()) < 200:
                logger.debug(f"테스트 모드: 본문이 너무 짧음 ({len(content)}자): {title[:50]}...")
                return False
        
        return True
        
    def _save_content(self, target: ScrapingTarget, content_data: Dict[str, Any]) -> bool:
        """콘텐츠 저장
        
        Args:
            target: 스크래핑 대상 객체
            content_data: 콘텐츠 데이터
            
        Returns:
            bool: 새로운 콘텐츠 여부
        """
        # 콘텐츠 해시 생성 (중복 방지)
        content_hash = hashlib.sha256(
            content_data['content'].encode('utf-8')
        ).hexdigest()
        
        # 중복 체크
        existing = ScrapedContent.query.filter_by(content_hash=content_hash).first()
        if existing:
            return False
            
        # 메타데이터에 발행 시간 추가
        metadata = content_data.get('metadata', {})
        if content_data.get('published_time'):
            metadata['published_time'] = content_data['published_time'].isoformat()
            
        # 새로운 콘텐츠 저장
        scraped_content = ScrapedContent(
            target_id=target.id,
            title=content_data['title'],
            content=content_data['content'],
            url=content_data.get('url', ''),
            content_hash=content_hash,
            metadata=metadata,
            scraped_at=datetime.utcnow()
        )
        
        db.session.add(scraped_content)
        return True
        
    def scrape_all_active_targets(self) -> Dict[str, Any]:
        """모든 활성 타겟 스크래핑
        
        Returns:
            Dict[str, Any]: 스크래핑 결과 요약
        """
        # 스크래핑 시작 시 cutoff 시간 갱신
        self.scrape_cutoff_time = datetime.utcnow() - timedelta(minutes=CONTENT_TIME_LIMIT_MINUTES)
        
        active_targets = ScrapingTarget.query.filter_by(is_active=True).all()
        
        total_found = 0
        total_new = 0
        results = []
        
        logger.info(f"전체 스크래핑 시작: {len(active_targets)}개 타겟")
        logger.info(f"수집 대상: {self.scrape_cutoff_time.strftime('%Y-%m-%d %H:%M:%S')} UTC 이후 발행된 콘텐츠")
        
        for target in active_targets:
            try:
                found, new = self.scrape_target(target)
                total_found += found
                total_new += new
                
                results.append({
                    'target': target.name,
                    'status': 'success',
                    'found': found,
                    'new': new
                })
                
            except Exception as e:
                logger.error(f"타겟 스크래핑 실패: {target.name}, 오류: {str(e)}")
                results.append({
                    'target': target.name,
                    'status': 'failed',
                    'error': str(e)
                })
                
        return {
            'total_targets': len(active_targets),
            'total_found': total_found,
            'total_new': total_new,
            'cutoff_time': self.scrape_cutoff_time.isoformat(),
            'results': results
        }
        
    def close(self) -> None:
        """리소스 정리"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
        self.session.close()


# 기존 ContentScraper를 FinancialScraper로 대체
FinancialScraper = ContentScraper 