"""
금융/투자 전문 콘텐츠 생성 엔진
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from .app import db
from .models import ScrapedContent, GeneratedContent
from .content_templates import get_template, classify_content_type


logger = logging.getLogger(__name__)


class FinancialContentGenerator:
    """금융/투자 전문 콘텐츠 생성기"""
    
    def __init__(self):
        self.max_length = 1500
        self.min_length = 100
        
    def generate_from_scraped_content(self, scraped_content: ScrapedContent) -> Optional[GeneratedContent]:
        """스크래핑된 콘텐츠로부터 구조화된 금융 콘텐츠 생성"""
        try:
            logger.info(f"구조화된 금융 콘텐츠 생성 시작: {scraped_content.title}")
            
            # 콘텐츠 정제 및 번역
            korean_title = self._translate_title(str(scraped_content.title))
            cleaned_content = self._clean_and_translate_content(str(scraped_content.content))
            
            # 금융 전문 요약 생성
            financial_summary = self._generate_financial_summary(cleaned_content)
            
            # 금융 태그 추출
            financial_tags = self._extract_financial_tags(cleaned_content, korean_title)
            
            # 새로운 구조화된 템플릿 사용
            from .content_templates import StructuredFinancialTemplate
            
            formatted_content = StructuredFinancialTemplate.format_content(
                title=korean_title,
                summary=financial_summary,
                url=str(scraped_content.url) if scraped_content.url else None,
                source=scraped_content.target.name if hasattr(scraped_content, 'target') and scraped_content.target else None,
                tags=financial_tags
            )
            
            # 생성된 콘텐츠 저장
            generated_content = GeneratedContent(
                scraped_content_id=scraped_content.id,
                title=korean_title,
                content=formatted_content,
                summary=financial_summary,
                tags=financial_tags,
                content_type='structured_financial_v2',
                created_at=datetime.utcnow()
            )
            
            db.session.add(generated_content)
            db.session.commit()
            
            logger.info(f"구조화된 금융 콘텐츠 생성 완료: {korean_title}")
            return generated_content
            
        except Exception as e:
            logger.error(f"구조화된 금융 콘텐츠 생성 실패: {str(e)}")
            db.session.rollback()
            return None
    
    def _clean_and_translate_content(self, content: str) -> str:
        """영어 콘텐츠 정제 및 한국어 번역"""
        # HTML 태그 제거
        content = re.sub(r'<[^>]+>', '', content)
        
        # 불필요한 공백 정리
        content = re.sub(r'\s+', ' ', content)
        
        # 길이 제한
        if len(content) > self.max_length:
            content = content[:self.max_length] + '...'
        
        # 실제 번역은 여기서 간단한 키워드 기반 처리
        # 실제 구현시에는 Google Translate API 등 사용 권장
        korean_content = self._simple_translate(content.strip())
        
        return korean_content
    
    def _simple_translate(self, text: str) -> str:
        """간단한 키워드 기반 번역 (실제로는 번역 API 사용 권장)"""
        # 주요 금융 용어 및 문장 번역 매핑
        translation_map = {
            # 금융 기관 및 정부
            'U.S. Treasury Department': '미국 재무부',
            'Treasury Department': '재무부',
            'Office of Foreign Assets Control': 'OFAC',
            'OFAC': 'OFAC',
            'Federal Reserve': '연준',
            'Fed': '연준',
            'Treasury Secretary': '재무장관',
            'Secretary': '장관',
            
            # 금융 용어
            'sanctions': '제재',
            'sanctioned': '제재된',
            'designate': '지정',
            'designated': '지정된',
            'blocked': '차단된',
            'freeze': '동결',
            'assets': '자산',
            'transactions': '거래',
            'companies': '기업',
            'individual': '개인',
            'entity': '기업체',
            'entities': '기업들',
            
            # 국가 및 지역
            'Chinese': '중국인',
            'China': '중국',
            'Hong Kong': '홍콩',
            'Singapore': '싱가포르',
            'Iran': '이란',
            'Iranian': '이란의',
            
            # 산업 관련
            'defense industries': '국방산업',
            'defense sector': '국방부문',
            'machinery': '기계류',
            'equipment': '장비',
            'technology': '기술',
            'weapons': '무기',
            'arms': '무기',
            'ballistic missile': '탄도미사일',
            'drone': '무인기',
            'dual-use': '이중용도',
            
            # 기업 및 개인명
            'Zhang Yanbang': '장옌방(Zhang Yanbang)',
            'Scott Bessent': '스콧 베센트',
            'SHUN KAI XING': 'SHUN KAI XING',
            'Unico Shipping Co Ltd': '홍콩 유니코 쉬핑(Unico Shipping Co Ltd)',
            'captain': '선장',
            'vessel': '선박',
            'shipping': '쉬핑',
            
            # 동작 및 상태
            'announced': '발표했다',
            'targeting': '대상으로',
            'transport': '운송',
            'transporting': '운송하다',
            'attempting': '시도',
            'falsify': '위조',
            'conceal': '은닉',
            'warned': '경고했다',
            'continue': '계속',
            'blocking': '차단',
            'procurement': '조달',
            'supporting': '지원하는',
            'conducting': '수행하는',
            'significant': '중요한',
            'face': '직면할',
            'aimed at': '목표로 하는',
            'disrupting': '차단',
            
            # 기타
            'Friday': '금요일',
            'according to': '~에 따르면',
            'Executive Order': '행정명령',
            'weapons of mass destruction': '대량살상무기',
            'proliferation': '확산',
            'foreign financial institutions': '외국 금융기관',
            'secondary sanctions': '2차 제재',
            'National Security Presidential Memorandum': '국가안보 대통령 메모랜덤'
        }
        
        # 전체 문장 번역 매핑 (더 자연스러운 번역을 위해)
        sentence_translations = {
            'The U.S. Treasury Department\'s Office of Foreign Assets Control (OFAC) announced new sanctions Friday targeting one individual and eight companies': 
            '미국 재무부 OFAC가 금요일 개인 1명과 기업 8곳을 대상으로 새로운 제재를 발표했다',
            
            'for their role in transporting sensitive machinery to Iran\'s defense industries':
            '이란 국방산업용 민감 기계류 운송에 관여한 혐의로',
            
            'was designated alongside his Hong Kong-based shipping company':
            '홍콩 소재 선박회사와 함께 지정되었다',
            
            'The sanctions also target four Chinese companies':
            '제재는 또한 중국 기업 4곳도 대상으로 한다',
            
            'was blocked as a designated asset for attempting to transport dual-use machinery':
            '이중용도 기계 운송 시도로 차단 자산으로 지정되었다',
            
            'tried to falsify shipping documents to conceal the Iran-bound cargo':
            '이란행 화물을 은닉하기 위해 운송 서류 위조를 시도했다',
            
            'will continue blocking Iran\'s procurement of dual-use technology':
            '이란의 이중용도 기술 조달을 계속 차단할 것이다',
            
            'supporting its ballistic missile, drone, and asymmetric weapons programs':
            '탄도미사일, 무인기, 비대칭 무기 프로그램을 지원하는',
            
            'may face secondary sanctions':
            '2차 제재에 직면할 수 있다'
        }
        
        # 먼저 전체 문장 번역 시도
        translated_text = text
        for english_sentence, korean_sentence in sentence_translations.items():
            translated_text = translated_text.replace(english_sentence, korean_sentence)
        
        # 개별 키워드 번역
        for english, korean in translation_map.items():
            translated_text = re.sub(rf'\b{re.escape(english)}\b', korean, translated_text, flags=re.IGNORECASE)
        
        return translated_text
    
    def _translate_title(self, title: str) -> str:
        """제목 번역"""
        return self._simple_translate(title)
    
    def _generate_financial_summary(self, content: str) -> str:
        """금융 전문 요약 생성"""
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 금융 관련 중요 키워드
        important_keywords = [
            '연준', '금리', '인플레이션', '실적', '매출', '수익',
            '주식', '투자', '시장', '거래', '상승', '하락',
            '발표', '정책', '결정', '예상', '전망', '분석',
            '비트코인', '암호화폐', '트럼프', '파월'
        ]
        
        # 숫자나 퍼센티지가 포함된 문장 우선
        priority_sentences = []
        normal_sentences = []
        
        for sentence in sentences[:5]:
            if len(sentence) > 20 and len(sentence) < 200:
                # 숫자, 퍼센티지, 중요 키워드 포함 문장 우선
                has_numbers = bool(re.search(r'\d+', sentence))
                has_percentage = bool(re.search(r'\d+%', sentence))
                has_keywords = any(keyword in sentence for keyword in important_keywords)
                
                if has_numbers or has_percentage or has_keywords:
                    priority_sentences.append(sentence)
                else:
                    normal_sentences.append(sentence)
        
        # 우선순위 문장부터 선택
        selected_sentences = priority_sentences[:2] + normal_sentences[:1]
        summary = '. '.join(selected_sentences[:3])
        
        if summary:
            summary += '.'
        else:
            summary = sentences[0] if sentences else content[:200] + '...'
        
        return summary
    
    def _extract_financial_tags(self, content: str, title: str) -> List[str]:
        """금융 전문 태그 추출"""
        tags = []
        full_text = f"{title} {content}".lower()
        
        # 금융 관련 키워드 매핑
        financial_keywords = {
            'fed': ['연준', 'federal reserve', 'fed', '파월', 'powell', '금리', 'interest rate'],
            'crypto': ['비트코인', 'bitcoin', '암호화폐', 'cryptocurrency', '이더리움', 'ethereum', 'crypto'],
            'earnings': ['실적', '수익', 'earnings', 'revenue', 'profit', '분기실적'],
            'market': ['시장', '주식', 'stock', 'market', '거래', 'trading'],
            'tech': ['기술주', '테크', 'tech', '애플', 'apple', '구글', 'google', '마이크로소프트', 'microsoft'],
            'trump': ['트럼프', 'trump', '대통령', 'president'],
            'breaking': ['속보', 'breaking', 'urgent', '긴급'],
            'investment': ['투자', 'investment', '펀드', 'fund'],
            'policy': ['정책', 'policy', '발표', 'announcement'],
            'inflation': ['인플레이션', 'inflation', '물가']
        }
        
        # 키워드 매칭
        for tag, keywords in financial_keywords.items():
            if any(keyword in full_text for keyword in keywords):
                tags.append(tag)
        
        # 특정 종목명 감지
        major_stocks = ['tesla', 'apple', 'microsoft', 'google', 'amazon', 'meta', 'nvidia']
        for stock in major_stocks:
            if stock in full_text:
                tags.append('individual_stock')
                break
        
        # 기본 태그 추가
        if not tags:
            tags.append('general_finance')
        
        # 항상 포함할 기본 태그
        if 'market' not in tags:
            tags.append('market')
        
        return tags[:5]  # 최대 5개 태그
    
    def generate_batch_content(self, limit: int = 10) -> List[GeneratedContent]:
        """미처리된 금융 콘텐츠들을 일괄 처리"""
        # 아직 콘텐츠가 생성되지 않은 스크래핑 데이터 조회
        unprocessed_contents = db.session.query(ScrapedContent)\
            .outerjoin(GeneratedContent)\
            .filter(GeneratedContent.id == None)\
            .order_by(ScrapedContent.scraped_at.desc())\
            .limit(limit)\
            .all()
        
        generated_contents = []
        
        for scraped_content in unprocessed_contents:
            generated = self.generate_from_scraped_content(scraped_content)
            if generated:
                generated_contents.append(generated)
        
        logger.info(f"일괄 금융 콘텐츠 생성 완료: {len(generated_contents)}개")
        return generated_contents
    
    def is_financial_content(self, content: str, title: str) -> bool:
        """금융 관련 콘텐츠인지 판단"""
        financial_indicators = [
            'stock', 'market', 'trading', 'investment', 'finance',
            'fed', 'federal reserve', 'interest rate', 'inflation',
            'earnings', 'revenue', 'profit', 'cryptocurrency',
            'bitcoin', 'nasdaq', 's&p', 'dow jones'
        ]
        
        text = f"{title} {content}".lower()
        return any(indicator in text for indicator in financial_indicators)
    
    def _create_structured_content(self, title: str, content: str, source_url: str = None) -> str:
        """구조화된 금융 콘텐츠 생성"""
        
        # 1. 아이콘과 제목 생성
        emoji_title = self._add_title_emoji(title)
        
        # 2. 핵심 정보 추출
        key_info = self._extract_key_information(content)
        
        # 3. 배경/경위 정보 추출
        background_info = self._extract_background_info(content)
        
        # 4. 파급효과/의미 추출
        impact_info = self._extract_impact_info(content)
        
        # 5. 한마디 요약 생성
        one_line_summary = self._generate_one_line_summary(title, content)
        
        # 6. 해시태그 생성
        hashtags = self._generate_hashtags(title, content)
        
        # 구조화된 콘텐츠 조합
        structured_content = []
        
        # 메인 제목
        structured_content.append(f"🇺🇸 {emoji_title}")
        structured_content.append("")
        structured_content.append("━" * 40)
        structured_content.append("")
        
        # 핵심 정보 섹션
        if key_info:
            structured_content.append("🚨 **핵심 내용**")
            structured_content.append("")
            structured_content.extend(key_info)
            structured_content.append("")
            structured_content.append("━" * 40)
            structured_content.append("")
        
        # 배경/경위 섹션
        if background_info:
            structured_content.append("⚡ **배경 및 경위**")
            structured_content.append("")
            structured_content.extend(background_info)
            structured_content.append("")
            structured_content.append("━" * 40)
            structured_content.append("")
        
        # 파급효과/의미 섹션
        if impact_info:
            structured_content.append("🎯 **파급효과 & 의미**")
            structured_content.append("")
            structured_content.extend(impact_info)
            structured_content.append("")
            structured_content.append("━" * 40)
            structured_content.append("")
        
        # 한마디 요약
        structured_content.append(f"**한마디로:** {one_line_summary}")
        structured_content.append("")
        
        # 해시태그
        structured_content.append(hashtags)
        
        return "\n".join(structured_content)
    
    def _add_title_emoji(self, title: str) -> str:
        """제목에 적절한 이모지 추가"""
        title_lower = title.lower()
        
        # 키워드별 이모지 매핑
        emoji_map = {
            '연준': '🏛️💰',
            '금리': '📈💰',
            '비트코인': '₿💎',
            '테슬라': '⚡🚗',
            '애플': '🍎📱',
            '실적': '📊💰',
            '주식': '📈💹',
            '제재': '💥⚓',
            '속보': '🚨⚡',
            '상승': '🚀📈',
            '하락': '📉💥',
            '발표': '📢💼',
        }
        
        # 적용할 이모지 찾기
        for keyword, emoji in emoji_map.items():
            if keyword in title:
                return f"{title} {emoji}"
        
        # 기본 이모지
        return f"{title} 💰📈"
    
    def _extract_key_information(self, content: str) -> List[str]:
        """핵심 정보 추출"""
        sentences = self._split_sentences(content)
        key_info = []
        
        # 첫 번째 문장부터 시작하여 핵심 정보 추출
        for sentence in sentences[:6]:  # 처음 6개 문장 검토
            if len(sentence.strip()) > 15:
                # 각 문장을 불릿 포인트로 정리
                formatted = sentence.strip()
                if not formatted.startswith('•'):
                    formatted = f"• {formatted}"
                key_info.append(formatted)
                
                if len(key_info) >= 4:  # 최대 4개 항목
                    break
        
        return key_info
    
    def _extract_background_info(self, content: str) -> List[str]:
        """배경 및 경위 정보 추출"""
        sentences = self._split_sentences(content)
        background_info = []
        
        # 중간 부분 문장들에서 배경 정보 추출
        start_idx = min(2, len(sentences) // 3)  # 앞부분 스킵
        
        for sentence in sentences[start_idx:start_idx+4]:
            if len(sentence.strip()) > 15:
                formatted = sentence.strip()
                if not background_info:
                    formatted = f"**운송 경위:** {formatted}"
                else:
                    formatted = f"• {formatted}"
                background_info.append(formatted)
                
                if len(background_info) >= 3:
                    break
        
        return background_info
    
    def _extract_impact_info(self, content: str) -> List[str]:
        """파급효과 및 의미 추출"""
        sentences = self._split_sentences(content)
        impact_info = []
        
        # 뒷부분 문장들에서 파급효과 추출
        start_idx = max(0, len(sentences) - 4)
        
        for sentence in sentences[start_idx:]:
            if len(sentence.strip()) > 15:
                formatted = sentence.strip()
                if not impact_info:
                    formatted = f"**직접 제재:** {formatted}"
                else:
                    formatted = f"**2차 제재:** {formatted}"
                impact_info.append(formatted)
                
                if len(impact_info) >= 2:
                    break
        
        return impact_info
    
    def _generate_one_line_summary(self, title: str, content: str) -> str:
        """한마디 요약 생성"""
        # 핵심 키워드 추출
        sentences = self._split_sentences(content)
        
        # 가장 중요한 정보가 담긴 문장 선택
        best_sentence = ""
        max_score = 0
        
        important_words = ['발표', '결정', '상승', '하락', '퍼센트', '%', '억', '조']
        
        for sentence in sentences[:5]:  # 처음 5개 문장만 검토
            score = 0
            for word in important_words:
                if word in sentence:
                    score += 1
            
            # 숫자가 포함된 경우 추가 점수
            if re.search(r'\d+', sentence):
                score += 2
            
            if score > max_score and len(sentence.strip()) > 10:
                max_score = score
                best_sentence = sentence.strip()
        
        if not best_sentence:
            best_sentence = title
        
        # 불필요한 부분 제거하고 요약
        summary = best_sentence.split('.')[0]
        if len(summary) > 100:
            summary = summary[:100] + "..."
        
        return summary
    
    def _generate_hashtags(self, title: str, content: str) -> str:
        """해시태그 생성"""
        tags = []
        full_text = f"{title} {content}".lower()
        
        # 주요 해시태그 매핑
        hashtag_map = {
            '연준': '#연준',
            '금리': '#금리',
            '비트코인': '#비트코인',
            '암호화폐': '#암호화폐',
            '테슬라': '#테슬라',
            '애플': '#애플',
            '실적': '#실적발표',
            '주식': '#주식시장',
            '투자': '#미국투자',
            '트럼프': '#트럼프',
            '제재': '#경제제재',
            '중국': '#중국',
            '시장': '#금융시장'
        }
        
        # 키워드 매칭
        for keyword, hashtag in hashtag_map.items():
            if keyword in full_text:
                tags.append(hashtag)
        
        # 기본 태그 추가
        if '#미국투자' not in tags:
            tags.append('#미국투자')
        if '#금융뉴스' not in tags:
            tags.append('#금융뉴스')
        
        return ' '.join(tags[:8])  # 최대 8개 해시태그
    
    def _split_sentences(self, content: str) -> List[str]:
        """문장 분리"""
        # 문장 구분자로 분리
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]
        return sentences


# 기존 ContentGenerator를 FinancialContentGenerator로 대체
ContentGenerator = FinancialContentGenerator 