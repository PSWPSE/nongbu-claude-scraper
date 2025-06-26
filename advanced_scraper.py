"""
고급 웹 스크래핑 시스템
- 다중 기술 스택 활용 (requests, Selenium, Newspaper3k, Trafilatura)
- 본문 내용 추출 특화
- 카테고리별 키워드 필터링
- 안티-스크래핑 우회 기능
"""

import asyncio
import hashlib
import logging
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Set
import re
from urllib.parse import urljoin, urlparse
import sqlite3
import os

import requests
from bs4 import BeautifulSoup
import newspaper
from newspaper import Article
import trafilatura
from readability import Document
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 데이터베이스 경로
DB_PATHS = [
    'src/instance/nongbu_financial.db',
    'instance/nongbu_financial_clean.db',
    'nongbu_financial.db'
]

# 금융 관련 키워드 (한국 투자자 관심사)
FINANCIAL_KEYWORDS = {
    'stocks': ['stock', 'shares', 'equity', 'market', 'trading', 'nasdaq', 'dow', 's&p', 'russell'],
    'companies': ['apple', 'tesla', 'microsoft', 'amazon', 'google', 'nvidia', 'meta', 'berkshire'],
    'crypto': ['bitcoin', 'cryptocurrency', 'crypto', 'ethereum', 'blockchain', 'defi'],
    'fed': ['federal reserve', 'fed', 'powell', 'interest rate', 'monetary policy', 'fomc'],
    'economy': ['inflation', 'gdp', 'employment', 'economic', 'recession', 'growth'],
    'earnings': ['earnings', 'revenue', 'profit', 'quarterly', 'financial results'],
    'geopolitics': ['trade war', 'china', 'tariff', 'sanction', 'oil', 'energy']
}

# User-Agent 풀 (차단 방지)
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
]

# 사이트별 맞춤 설정
SITE_CONFIGS = {
    'bbc.com': {'delay_range': (1, 3), 'timeout': 20},
    'apnews.com': {'delay_range': (2, 4), 'timeout': 25},
    'npr.org': {'delay_range': (1, 2), 'timeout': 15},
    'finviz.com': {'delay_range': (1, 3), 'timeout': 15},
    'finance.yahoo.com': {'delay_range': (2, 5), 'timeout': 20}
}


class AdvancedScraper:
    """고급 웹 스크래핑 시스템"""
    
    def __init__(self, use_selenium=False):
        self.use_selenium = use_selenium
        self.driver = None
        self.session = self._create_session()
        
        # 요청 간격 (초)
        self.request_delay = 2
        
        # 스크래핑 대상 사이트 (작동 확인된 사이트들)
        self.targets = {
            'BBC Business': {
                'url': 'https://www.bbc.com/business',
                'article_selectors': ['article a', '.gs-c-promo-heading a', 'h3 a', 'h2 a'],
                'keywords': ['stocks', 'companies', 'economy', 'earnings'],
                'use_selenium': False,  # requests 우선 사용
                'content_type': 'news'
            },
            'AP News Business': {
                'url': 'https://apnews.com/hub/business',
                'article_selectors': ['h2 a', 'h3 a', '.PagePromo-title a', 'article a'],
                'keywords': ['stocks', 'companies', 'crypto', 'earnings'],
                'use_selenium': False,  # requests 우선 사용
                'content_type': 'news'
            },
            'NPR Business': {
                'url': 'https://www.npr.org/sections/business/',
                'article_selectors': ['h2 a', 'h3 a', '.item-info-wrap a', 'article a'],
                'keywords': ['stocks', 'fed', 'economy', 'earnings'],
                'use_selenium': False,  # requests 우선 사용
                'content_type': 'news'
            },
            'FINVIZ': {
                'url': 'https://finviz.com/news.ashx',
                'article_selectors': ['.news-link-container a', '.news-link a', 'td a[target="_blank"]'],
                'keywords': ['stocks', 'companies', 'earnings', 'market'],
                'use_selenium': False,
                'content_type': 'financial_data'
            },
            'Yahoo Finance': {
                'url': 'https://finance.yahoo.com/news/',
                'article_selectors': ['h3 a', 'h2 a', '.js-content-viewer a', '[data-module="stream"] a'],
                'keywords': ['stocks', 'companies', 'earnings', 'market', 'fed'],
                'use_selenium': False,
                'content_type': 'financial_news'
            }
        }
    
    def _create_session(self) -> requests.Session:
        """HTTP 세션 생성 - 개선된 차단 방지 기능"""
        session = requests.Session()
        
        # 랜덤 User-Agent 선택
        user_agent = random.choice(USER_AGENTS)
        
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none'
        })
        return session
    
    def _get_selenium_driver(self) -> webdriver.Chrome:
        """Selenium WebDriver 초기화"""
        if self.driver is None:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=options
            )
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self.driver
    
    def get_db_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결"""
        for db_path in DB_PATHS:
            if os.path.exists(db_path):
                return sqlite3.connect(db_path)
        raise FileNotFoundError("데이터베이스 파일을 찾을 수 없습니다.")
    
    def extract_with_multiple_methods(self, url: str) -> str:
        """다중 방법을 사용한 본문 추출"""
        logger.info(f"다중 방법으로 본문 추출 시작: {url}")
        
        best_content = ""
        best_score = 0
        
        # 방법 1: Trafilatura (가장 강력한 본문 추출 도구)
        try:
            content = trafilatura.fetch_url(url)
            if content:
                extracted = trafilatura.extract(content, include_comments=False, include_tables=False)
                if extracted and len(extracted) > best_score:
                    best_content = extracted
                    best_score = len(extracted)
                    logger.info(f"Trafilatura로 {len(extracted)}자 추출")
        except Exception as e:
            logger.warning(f"Trafilatura 실패: {e}")
        
        # 방법 2: Newspaper3k (뉴스 특화)
        try:
            article = Article(url)
            article.download()
            article.parse()
            if article.text and len(article.text) > best_score:
                best_content = article.text
                best_score = len(article.text)
                logger.info(f"Newspaper3k로 {len(article.text)}자 추출")
        except Exception as e:
            logger.warning(f"Newspaper3k 실패: {e}")
        
        # 방법 3: Readability (가독성 중심 추출)
        try:
            response = self.session.get(url, timeout=15)
            if response.status_code == 200:
                doc = Document(response.content)
                content = BeautifulSoup(doc.summary(), 'html.parser').get_text(strip=True)
                if content and len(content) > best_score:
                    best_content = content
                    best_score = len(content)
                    logger.info(f"Readability로 {len(content)}자 추출")
        except Exception as e:
            logger.warning(f"Readability 실패: {e}")
        
        # 방법 4: Selenium (JavaScript 렌더링 필요한 경우)
        if self.use_selenium and best_score < 500:
            try:
                content = self._extract_with_selenium(url)
                if content and len(content) > best_score:
                    best_content = content
                    best_score = len(content)
                    logger.info(f"Selenium으로 {len(content)}자 추출")
            except Exception as e:
                logger.warning(f"Selenium 실패: {e}")
        
        # 방법 5: 커스텀 BeautifulSoup (기본 방법)
        if best_score < 300:
            try:
                content = self._extract_with_beautifulsoup(url)
                if content and len(content) > best_score:
                    best_content = content
                    best_score = len(content)
                    logger.info(f"BeautifulSoup으로 {len(content)}자 추출")
            except Exception as e:
                logger.warning(f"BeautifulSoup 실패: {e}")
        
        logger.info(f"최종 추출 결과: {best_score}자")
        return best_content
    
    def _extract_with_selenium(self, url: str) -> str:
        """Selenium을 사용한 본문 추출"""
        driver = self._get_selenium_driver()
        driver.get(url)
        
        # 페이지 로딩 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)  # 동적 콘텐츠 로딩 대기
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        return self._extract_content_from_soup(soup)
    
    def _extract_with_beautifulsoup(self, url: str) -> str:
        """BeautifulSoup을 사용한 본문 추출"""
        response = self.session.get(url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        return self._extract_content_from_soup(soup)
    
    def _extract_content_from_soup(self, soup: BeautifulSoup) -> str:
        """BeautifulSoup 객체에서 본문 추출"""
        # 불필요한 요소 제거
        for unwanted in soup.select('script, style, nav, header, footer, .ad, .advertisement, .social-share, .related-articles'):
            unwanted.decompose()
        
        # 다양한 본문 셀렉터 시도
        content_selectors = [
            'article', '.article', '.content', '.post-content', '.entry-content',
            '.story-body', '.article-body', '.body-text', '.text-content',
            '[data-module="ArticleBody"]', '.article__content', '.story-content',
            'main .content', '.main-content', '.primary-content'
        ]
        
        best_content = ""
        best_length = 0
        
        for selector in content_selectors:
            elements = soup.select(selector)
            for element in elements:
                content = element.get_text(separator='\n', strip=True)
                if len(content) > best_length:
                    best_content = content
                    best_length = len(content)
        
        # paragraph 방식도 시도
        if best_length < 500:
            paragraphs = soup.select('p')
            meaningful_paragraphs = [
                p.get_text(strip=True) for p in paragraphs 
                if len(p.get_text(strip=True)) > 30
            ]
            if meaningful_paragraphs:
                paragraph_content = '\n'.join(meaningful_paragraphs)
                if len(paragraph_content) > best_length:
                    best_content = paragraph_content
        
        return best_content
    
    def is_relevant_content(self, title: str, content: str) -> bool:
        """콘텐츠의 금융 관련성 및 품질 검사"""
        text = (title + " " + content).lower()
        
        # 1. 콘텐츠 길이 검사 (최소 300자 이상)
        if len(content) < 300:
            logger.info(f"⚠️ 콘텐츠가 너무 짧음: {len(content)}자")
            return False
        
        # 2. 블랙리스트 패턴 검사 (의미없는 콘텐츠 차단)
        blacklist_patterns = [
            # 회사 소개글 패턴
            r'the associated press is an independent global news organization',
            r'founded in \d{4}',
            r'remains the most trusted source',
            r'more than half the world\'s population sees',
            r'essential provider of the technology',
            r'vital to the news business',
            
            # 일반적인 소개 패턴  
            r'subscribe to our newsletter',
            r'follow us on social media',
            r'contact us for more information',
            r'copyright \d{4}',
            r'all rights reserved',
            r'privacy policy',
            r'terms of service',
            r'cookie policy',
            
            # 네비게이션/메뉴 텍스트
            r'home\s+news\s+business',
            r'breaking news',
            r'latest news',
            r'trending now',
            
            # 너무 일반적인 문구들
            r'click here to',
            r'read more about',
            r'learn more at',
            r'visit our website',
        ]
        
        for pattern in blacklist_patterns:
            if re.search(pattern, text):
                logger.info(f"⚠️ 블랙리스트 패턴 감지: {pattern}")
                return False
        
        # 3. 키워드 매칭 점수 계산
        relevance_score = 0
        for category, keywords in FINANCIAL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    relevance_score += 1
        
        # 4. 기본 금융 용어 체크
        basic_financial_terms = [
            'stock', 'market', 'price', 'trade', 'investment', 'investor',
            'financial', 'economy', 'economic', 'revenue', 'profit', 'loss',
            'nasdaq', 'dow jones', 'sp500', 'wall street', 'trading', 'earnings',
            'billion', 'million', 'percent', '%', 'shares', 'ceo', 'quarterly'
        ]
        
        for term in basic_financial_terms:
            if term in text:
                relevance_score += 1
        
        # 5. 제목의 금융 관련성 강화 점수
        title_score = 0
        title_lower = title.lower()
        for term in basic_financial_terms:
            if term in title_lower:
                title_score += 2  # 제목에 있으면 가중치 2배
        
        total_score = relevance_score + title_score
        
        # 6. 콘텐츠 품질 점수 (구체적 숫자나 날짜 포함)
        quality_patterns = [
            r'\$\d+(?:\.\d+)?(?:\s*(?:billion|million|trillion))?',  # 달러 금액
            r'\d+(?:\.\d+)?%',  # 퍼센트
            r'\d{4}-\d{2}-\d{2}',  # 날짜
            r'q[1-4]\s+\d{4}',  # 분기 정보
        ]
        
        quality_score = 0
        for pattern in quality_patterns:
            if re.search(pattern, text):
                quality_score += 1
        
        final_score = total_score + quality_score
        min_score = 6  # 최소 4점 이상 필요
        
        logger.info(f"콘텐츠 점수: 관련성={relevance_score}, 제목={title_score}, 품질={quality_score}, 총합={final_score}/{min_score}")
        return final_score >= min_score
    
    def scrape_all_targets(self) -> Dict[str, Any]:
        """모든 타겟 사이트 스크래핑"""
        results = {
            'total_found': 0,
            'total_new': 0,
            'target_results': []
        }
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        for target_name, config in self.targets.items():
            try:
                logger.info(f"🚀 {target_name} 스크래핑 시작")
                target_result = self._scrape_target(target_name, config, cursor)
                results['target_results'].append(target_result)
                results['total_found'] += target_result['found']
                results['total_new'] += target_result['new']
                
                # 요청 간격 준수
                self.adaptive_delay(config['url'])
                
            except Exception as e:
                logger.error(f"❌ {target_name} 스크래핑 실패: {e}")
                results['target_results'].append({
                    'target': target_name,
                    'status': 'failed',
                    'error': str(e),
                    'found': 0,
                    'new': 0
                })
        
        conn.commit()
        conn.close()
        return results
    
    def _scrape_target(self, target_name: str, config: Dict[str, Any], cursor) -> Dict[str, Any]:
        """개별 타겟 스크래핑"""
        url = config['url']
        article_selectors = config['article_selectors']
        
        logger.info(f"타겟 스크래핑 시작: {target_name} -> {url}")
        
        # 메인 페이지에서 기사 링크 수집
        try:
            # 개별 타겟의 Selenium 사용 여부 확인 (기본값은 False)
            target_use_selenium = config.get('use_selenium', False)
            
            if target_use_selenium:
                logger.info("Selenium을 사용하여 페이지 로드 중...")
                driver = self._get_selenium_driver()
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(3)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                logger.info(f"페이지 소스 길이: {len(driver.page_source)}자")
            else:
                logger.info("requests를 사용하여 페이지 요청 중...")
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                logger.info(f"응답 내용 길이: {len(response.content)}자")
        
        except Exception as e:
            logger.error(f"페이지 접근 실패: {str(e)}")
            return {
                'target': target_name,
                'status': 'failed',
                'error': f'메인 페이지 접근 실패: {str(e)}',
                'found': 0,
                'new': 0
            }
        
        # 기사 링크 추출
        logger.info("기사 링크 추출 시작...")
        article_links = self._extract_article_links(soup, article_selectors, url)
        
        found_count = len(article_links)
        new_count = 0
        
        logger.info(f"📰 {target_name}에서 {found_count}개 기사 링크 발견")
        
        if found_count == 0:
            logger.warning("기사 링크를 찾지 못했습니다. 페이지 구조 확인이 필요합니다.")
            return {
                'target': target_name,
                'status': 'failed',
                'error': '기사 링크를 찾을 수 없음',
                'found': 0,
                'new': 0
            }
        
        # 각 기사의 본문 추출
        for i, (article_title, article_url) in enumerate(article_links[:3]):  # 테스트용으로 3개만
            try:
                logger.info(f"📖 기사 {i+1}/{min(len(article_links), 3)}: {article_title[:50]}...")
                logger.info(f"기사 URL: {article_url}")
                
                # 본문 추출
                content = self.extract_with_multiple_methods(article_url)
                
                if not content or len(content) < 100:
                    logger.warning(f"⚠️ 본문이 너무 짧음: {len(content) if content else 0}자")
                    continue
                
                # 관련성 검사
                if not self.is_relevant_content(article_title, content):
                    logger.info(f"⏭️ 금융 관련성 낮음, 건너뜀")
                    continue
                
                # 중복 검사
                content_hash = hashlib.sha256((article_title + content).encode('utf-8')).hexdigest()
                cursor.execute("SELECT COUNT(*) FROM scraped_contents WHERE content_hash = ?", (content_hash,))
                if cursor.fetchone()[0] > 0:
                    logger.info(f"⏭️ 중복 콘텐츠, 건너뜀")
                    continue
                
                # 데이터베이스에 저장
                cursor.execute("""
                    INSERT INTO scraped_contents (title, content, url, content_hash, scraped_at, target_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    article_title, 
                    content, 
                    article_url, 
                    content_hash, 
                    datetime.now().isoformat(), 
                    1  # 기본 target_id
                ))
                
                new_count += 1
                logger.info(f"✅ 새 콘텐츠 저장: {len(content)}자")
                
                # 요청 간격 준수
                self.adaptive_delay(article_url)
                
            except Exception as e:
                logger.error(f"⚠️ 기사 처리 실패: {str(e)}")
                continue
        
        return {
            'target': target_name,
            'status': 'success',
            'found': found_count,
            'new': new_count
        }
    
    def _extract_article_links(self, soup: BeautifulSoup, selectors: List[str], base_url: str) -> List[Tuple[str, str]]:
        """기사 링크 추출"""
        links = []
        
        logger.info(f"기사 링크 추출 시작 - 시도할 셀렉터: {selectors}")
        
        for selector in selectors:
            logger.info(f"셀렉터 시도: {selector}")
            elements = soup.select(selector)
            logger.info(f"발견된 요소 수: {len(elements)}")
            
            for i, element in enumerate(elements[:10]):  # 처음 10개만 확인
                try:
                    # 링크와 제목 추출
                    if element.name == 'a':
                        link_elem = element
                        title = element.get_text(strip=True)
                    else:
                        link_elem = element.find('a')
                        title = element.get_text(strip=True)
                    
                    if not link_elem or not title:
                        logger.debug(f"요소 {i}: 링크 또는 제목 없음")
                        continue
                    
                    href = link_elem.get('href')
                    if not href:
                        logger.debug(f"요소 {i}: href 속성 없음")
                        continue
                    
                    # href가 문자열인지 확인
                    if not isinstance(href, str):
                        logger.debug(f"요소 {i}: href가 문자열이 아님: {type(href)}")
                        continue
                    
                    # 절대 URL로 변환
                    full_url = urljoin(base_url, href)
                    
                    # 유효한 URL인지 확인
                    if not full_url.startswith('http'):
                        logger.debug(f"요소 {i}: 유효하지 않은 URL: {full_url}")
                        continue
                    
                    # 제목이 너무 짧거나 긴 경우 제외
                    if len(title) < 10 or len(title) > 200:
                        logger.debug(f"요소 {i}: 제목 길이 부적절: {len(title)}자")
                        continue
                    
                    logger.info(f"유효한 링크 발견: {title[:50]}... -> {full_url}")
                    links.append((title, full_url))
                    
                except Exception as e:
                    logger.warning(f"요소 {i} 처리 중 오류: {e}")
                    continue
            
            if links:
                logger.info(f"셀렉터 '{selector}'로 {len(links)}개 링크 발견")
                break  # 링크를 찾았으면 다른 셀렉터는 시도하지 않음
        
        # 중복 제거
        seen = set()
        unique_links = []
        for title, url in links:
            if url not in seen:
                seen.add(url)
                unique_links.append((title, url))
        
        logger.info(f"총 {len(unique_links)}개 고유 링크 추출 완료")
        return unique_links
    
    def close(self):
        """리소스 정리"""
        if self.driver:
            self.driver.quit()
            self.driver = None
        if self.session:
            self.session.close()
    
    def get_site_config(self, url: str) -> Dict[str, Any]:
        """URL에서 사이트별 설정 가져오기"""
        domain = urlparse(url).netloc.lower()
        for site, config in SITE_CONFIGS.items():
            if site in domain:
                return config
        # 기본 설정
        return {'delay_range': (2, 4), 'timeout': 20}
    
    def adaptive_delay(self, url: str) -> None:
        """사이트별 적응형 딜레이"""
        config = self.get_site_config(url)
        min_delay, max_delay = config['delay_range']
        delay = random.uniform(min_delay, max_delay)
        logger.info(f"⏱️ {delay:.1f}초 대기 중...")
        time.sleep(delay)
    
    def save_to_database(self, title: str, content: str, url: str, source: str = "Manual Collection") -> bool:
        """스크래핑된 콘텐츠를 데이터베이스에 저장 - 강화된 메타데이터 포함"""
        try:
            # DB 연결 경로들
            db_paths = [
                'src/instance/nongbu_financial.db',  # 우선 경로
                'instance/nongbu_financial.db',
                'nongbu_financial.db'
            ]
            
            db_path = None
            for path in db_paths:
                if os.path.exists(path):
                    db_path = path
                    break
            
            if not db_path:
                logger.error("데이터베이스 파일을 찾을 수 없음")
                return False
            
            # 메타데이터 생성
            metadata = self._generate_content_metadata(title, content, source)
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO scraped_contents (title, content, url, source, created_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (title, content, url, source, datetime.now().isoformat(), metadata))
                conn.commit()
                logger.info(f"✅ 데이터베이스 저장 완료: {title[:50]}...")
                return True
                
        except Exception as e:
            logger.error(f"데이터베이스 저장 실패: {e}")
            return False
    
    def _generate_content_metadata(self, title: str, content: str, source: str) -> str:
        """콘텐츠 메타데이터 생성"""
        text = (title + " " + content).lower()
        
        # 키워드 매칭 분석
        keyword_matches = {}
        total_score = 0
        
        for category, keywords in FINANCIAL_KEYWORDS.items():
            category_score = sum(1 for keyword in keywords if keyword in text)
            if category_score > 0:
                keyword_matches[category] = category_score
                total_score += category_score
        
        # 소스 타입 분류
        source_type = "unknown"
        reliability = "medium"
        
        if "bbc" in source.lower():
            source_type = "news_major"
            reliability = "high"
        elif "reuters" in source.lower() or "ap news" in source.lower():
            source_type = "news_wire"
            reliability = "high"
        elif "finviz" in source.lower() or "yahoo finance" in source.lower():
            source_type = "financial_data"
            reliability = "medium"
        elif "npr" in source.lower():
            source_type = "news_public"
            reliability = "high"
        
        # 메타데이터 구조화
        metadata = {
            "relevance_score": total_score,
            "keyword_matches": keyword_matches,
            "source_type": source_type,
            "reliability": reliability,
            "content_length": len(content),
            "processed_at": datetime.now().isoformat()
        }
        
        return str(metadata)  # JSON 문자열로 저장


def main():
    """메인 실행 함수"""
    scraper = AdvancedScraper(use_selenium=False)
    
    try:
        logger.info("🚀 고급 스크래핑 시스템 시작")
        results = scraper.scrape_all_targets()
        
        logger.info("📊 스크래핑 결과:")
        logger.info(f"총 발견: {results['total_found']}개")
        logger.info(f"새로 수집: {results['total_new']}개")
        
        for target_result in results['target_results']:
            status = "✅" if target_result['status'] == 'success' else "❌"
            logger.info(f"{status} {target_result['target']}: 발견 {target_result['found']}개, 새로운 {target_result['new']}개")
        
        return results
        
    except Exception as e:
        logger.error(f"스크래핑 실행 중 오류: {e}")
        return {'error': str(e)}
    finally:
        scraper.close()


if __name__ == "__main__":
    main() 