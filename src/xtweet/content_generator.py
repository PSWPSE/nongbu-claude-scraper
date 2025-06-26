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
    """금융/투자 전문 콘텐츠 생성기 - 개선된 버전"""
    
    def __init__(self):
        self.max_length = 2000  # 더 상세한 분석을 위해 증가
        self.min_length = 150
        
    def generate_from_scraped_content(self, scraped_content: ScrapedContent) -> Optional[GeneratedContent]:
        """스크래핑된 콘텐츠로부터 개선된 구조화된 금융 콘텐츠 생성"""
        try:
            logger.info(f"개선된 구조화된 금융 콘텐츠 생성 시작: {scraped_content.title}")
            
            # 콘텐츠 정제 및 분석
            korean_title = self._translate_title(str(scraped_content.title))
            cleaned_content = self._clean_and_analyze_content(str(scraped_content.content))
            
            # 개선된 금융 전문 요약 생성
            financial_summary = self._generate_enhanced_financial_summary(cleaned_content)
            
            # 정량적 금융 태그 추출
            financial_tags = self._extract_quantitative_financial_tags(cleaned_content, korean_title)
            
            # 새로운 개선된 구조화된 템플릿 사용
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
                content_type='enhanced_structured_financial_v3',
                created_at=datetime.utcnow()
            )
            
            db.session.add(generated_content)
            db.session.commit()
            
            logger.info(f"개선된 구조화된 금융 콘텐츠 생성 완료: {korean_title}")
            return generated_content
            
        except Exception as e:
            logger.error(f"개선된 구조화된 금융 콘텐츠 생성 실패: {str(e)}")
            db.session.rollback()
            return None
    
    def _clean_and_analyze_content(self, content: str) -> str:
        """영어 콘텐츠 정제 및 분석 - 개선된 버전"""
        # HTML 태그 제거
        content = re.sub(r'<[^>]+>', '', content)
        
        # 불필요한 공백 정리
        content = re.sub(r'\s+', ' ', content)
        
        # 숫자와 퍼센트 패턴 보존
        content = self._preserve_numerical_data(content)
        
        # 길이 제한 (더 상세한 분석을 위해 증가)
        if len(content) > self.max_length:
            content = content[:self.max_length] + '...'
        
        # 실제 번역은 여기서 간단한 키워드 기반 처리
        # 실제 구현시에는 Google Translate API 등 사용 권장
        korean_content = self._enhanced_translate(content.strip())
        
        return korean_content
    
    def _preserve_numerical_data(self, content: str) -> str:
        """숫자 데이터 보존 및 강조"""
        import re
        
        # 퍼센트, 달러, 숫자 패턴 보존
        patterns = [
            (r'(\d+\.?\d*%)', r'【\1】'),  # 퍼센트
            (r'(\$\d+\.?\d*[BMK]?)', r'【\1】'),  # 달러
            (r'(\d+\.?\d*\s*billion)', r'【\1】'),  # 억 단위
            (r'(\d+\.?\d*\s*million)', r'【\1】'),  # 백만 단위
            (r'(\d+\.?\d*\s*trillion)', r'【\1】'),  # 조 단위
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
        
        return content
    
    def _enhanced_translate(self, content: str) -> str:
        """개선된 번역 함수"""
        # 보존된 숫자 데이터 복원
        content = content.replace('【', '').replace('】', '')
        
        # 간단한 키워드 기반 번역 (실제로는 번역 API 사용 권장)
        translations = {
            'Federal Reserve': '연방준비제도',
            'interest rate': '금리',
            'inflation': '인플레이션',
            'GDP': 'GDP',
            'stock market': '주식시장',
            'recession': '경기침체',
            'earnings': '실적',
            'revenue': '매출',
            'profit': '이익',
            'investment': '투자',
            'portfolio': '포트폴리오',
            'volatility': '변동성'
        }
        
        for english, korean in translations.items():
            content = content.replace(english, korean)
        
        return content
    
    def _generate_enhanced_financial_summary(self, content: str) -> str:
        """개선된 금융 전문 요약 생성"""
        # 핵심 문장 추출 (숫자가 포함된 문장 우선)
        sentences = content.split('.')
        important_sentences = []
        
        for sentence in sentences:
            if any(char.isdigit() for char in sentence) or len(sentence.strip()) > 50:
                important_sentences.append(sentence.strip())
                if len(important_sentences) >= 3:
                    break
        
        if not important_sentences:
            important_sentences = sentences[:2]
        
        summary = '. '.join(important_sentences).strip()
        return summary[:500] + '...' if len(summary) > 500 else summary
    
    def _extract_quantitative_financial_tags(self, content: str, title: str) -> List[str]:
        """정량적 금융 태그 추출"""
        tags = []
        content_lower = (content + ' ' + title).lower()
        
        # 정량적 키워드 매핑
        quantitative_keywords = {
            # 시장 지표
            'gdp': 'GDP', 'inflation': '인플레이션', 'unemployment': '실업률',
            'interest rate': '금리', 'yield': '수익률', 'volatility': '변동성',
            
            # 기업 실적
            'earnings': '실적', 'revenue': '매출', 'profit': '이익', 'eps': 'EPS',
            'dividend': '배당', 'buyback': '자사주매입',
            
            # 섹터
            'technology': '기술주', 'healthcare': '헬스케어', 'finance': '금융주',
            'energy': '에너지', 'consumer': '소비재', 'industrial': '산업재',
            
            # 암호화폐
            'bitcoin': '비트코인', 'ethereum': '이더리움', 'crypto': '암호화폐',
            
            # 지정학
            'fed': '연준', 'china': '중국', 'trade war': '무역전쟁',
            'sanctions': '제재', 'recession': '경기침체'
        }
        
        for keyword, tag in quantitative_keywords.items():
            if keyword in content_lower and tag not in tags:
                tags.append(tag)
        
        # 숫자 패턴 기반 태그
        import re
        if re.search(r'\d+\.?\d*%', content):
            tags.append('퍼센트지표')
        if re.search(r'\$\d+', content):
            tags.append('달러수치')
        if re.search(r'\d+\.?\d*\s*(billion|million|trillion)', content):
            tags.append('대규모수치')
        
        return tags[:10]  # 최대 10개 태그
    
    def _translate_title(self, title: str) -> str:
        """제목 번역"""
        return self._enhanced_translate(title)
    
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