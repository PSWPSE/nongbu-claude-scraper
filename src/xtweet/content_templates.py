"""
금융/투자 전문 콘텐츠 템플릿
"""

import re
from typing import Dict, Any, List
from datetime import datetime


class FinancialNewsTemplate:
    """금융/투자 뉴스 전용 템플릿 - NongBu 브랜드"""
    
    def __init__(self):
        self.max_length = 1500
        self.brand_signature = "오늘도 현명한 투자 하세요! -NongBu"
        
    def format_content(self, title: str, summary: str, url: str, source: str, tags: List[str]) -> str:
        """금융 뉴스 형식으로 포맷팅"""
        content_parts = []
        
        # 1. 제목 및 서론 (관심을 끄는 제목)
        formatted_title = self._create_engaging_title(title, tags)
        content_parts.append(f"📈 **{formatted_title}**")
        content_parts.append("")
        
        # 2. 본문 섹션들
        formatted_summary = self._format_summary_with_symbols(summary)
        content_parts.append(formatted_summary)
        content_parts.append("")
        
        # 3. 핵심 요약 섹션
        key_points = self._extract_key_points(summary, tags)
        if key_points:
            content_parts.append("🔍 **핵심 포인트**")
            for point in key_points:
                content_parts.append(f"• {point}")
            content_parts.append("")
        
        # 4. 시장 영향 (해당하는 경우)
        market_impact = self._analyze_market_impact(summary, tags)
        if market_impact:
            content_parts.append(f"📊 {market_impact}")
            content_parts.append("")
        
        # 5. 출처 및 링크
        if url:
            content_parts.append(f"🔗 [전문 보기]({url})")
        content_parts.append(f"📰 출처: {source}")
        content_parts.append("")
        
        # 6. 해시태그
        hashtags = self._generate_financial_hashtags(tags, summary)
        content_parts.append(hashtags)
        content_parts.append("")
        
        # 7. 브랜드 서명
        content_parts.append(self.brand_signature)
        
        final_content = "\n".join(content_parts)
        
        # 길이 제한 체크 및 조정
        if len(final_content) > self.max_length:
            final_content = self._trim_content(content_parts)
            
        return final_content
    
    def _create_engaging_title(self, title: str, tags: List[str]) -> str:
        """관심을 끄는 제목 생성"""
        # 긴급성/중요성 키워드 감지
        urgent_keywords = ['breaking', 'urgent', 'alert', 'emergency', 'crash', 'surge', 'plunge']
        fed_keywords = ['fed', 'federal reserve', 'powell', 'interest rate']
        trump_keywords = ['trump', 'president']
        
        title_lower = title.lower()
        
        # 긴급 뉴스 표시
        if any(keyword in title_lower for keyword in urgent_keywords):
            return f"🚨 {title}"
        elif any(keyword in title_lower for keyword in fed_keywords):
            return f"🏛️ {title}"
        elif any(keyword in title_lower for keyword in trump_keywords):
            return f"🇺🇸 {title}"
        elif 'crypto' in tags or 'bitcoin' in title_lower:
            return f"₿ {title}"
        else:
            return title
    
    def _format_summary_with_symbols(self, summary: str) -> str:
        """종목 심볼 자동 추가"""
        # 주요 종목들의 심볼 매핑
        stock_symbols = {
            'apple': 'AAPL',
            'microsoft': 'MSFT',
            'google': 'GOOGL',
            'alphabet': 'GOOGL',
            'amazon': 'AMZN',
            'tesla': 'TSLA',
            'nvidia': 'NVDA',
            'meta': 'META',
            'facebook': 'META',
            'netflix': 'NFLX',
            'boeing': 'BA',
            'jpmorgan': 'JPM',
            'jp morgan': 'JPM',
            'goldman sachs': 'GS',
            'morgan stanley': 'MS',
            'blackrock': 'BLK',
            'berkshire': 'BRK.A',
            'coinbase': 'COIN',
            'palantir': 'PLTR',
            'amd': 'AMD',
            'intel': 'INTC'
        }
        
        formatted_summary = summary
        
        # 회사명 뒤에 심볼 추가
        for company, symbol in stock_symbols.items():
            pattern = rf'\b{re.escape(company)}\b'
            replacement = f'{company} ${symbol}'
            formatted_summary = re.sub(pattern, replacement, formatted_summary, flags=re.IGNORECASE)
        
        return formatted_summary
    
    def _extract_key_points(self, summary: str, tags: List[str]) -> List[str]:
        """핵심 포인트 추출"""
        key_points = []
        
        # 숫자가 포함된 중요 정보 추출
        percentage_pattern = r'(\d+(?:\.\d+)?%)'
        dollar_pattern = r'\$(\d+(?:,\d{3})*(?:\.\d{2})?(?:\s*(?:billion|million|trillion))?)'
        
        percentages = re.findall(percentage_pattern, summary)
        dollars = re.findall(dollar_pattern, summary)
        
        if percentages:
            key_points.append(f"주요 수치: {', '.join(percentages[:2])}")
        
        if dollars:
            key_points.append(f"금액 규모: ${', $'.join(dollars[:2])}")
        
        # 태그 기반 핵심 포인트
        if 'fed' in tags:
            key_points.append("연준 정책 관련 소식")
        if 'earnings' in tags:
            key_points.append("실적 발표 관련")
        if 'crypto' in tags:
            key_points.append("암호화폐 시장 영향")
        
        return key_points[:3]  # 최대 3개
    
    def _analyze_market_impact(self, summary: str, tags: List[str]) -> str:
        """시장 영향 분석"""
        summary_lower = summary.lower()
        
        positive_indicators = ['surge', 'rally', 'gain', 'rise', 'jump', 'boost', 'up']
        negative_indicators = ['fall', 'drop', 'decline', 'crash', 'plunge', 'down', 'loss']
        
        positive_count = sum(1 for word in positive_indicators if word in summary_lower)
        negative_count = sum(1 for word in negative_indicators if word in summary_lower)
        
        if positive_count > negative_count:
            return "시장에 긍정적 영향 예상"
        elif negative_count > positive_count:
            return "시장 변동성 주의 필요"
        elif 'fed' in tags:
            return "금리 정책 변화에 따른 시장 주목"
        else:
            return None
    
    def _generate_financial_hashtags(self, tags: List[str], summary: str) -> str:
        """금융 관련 해시태그 생성"""
        hashtags = ["#미국투자", "#주식시장"]
        
        # 기본 금융 태그들
        tag_mapping = {
            'crypto': '#암호화폐',
            'bitcoin': '#비트코인',
            'fed': '#연준',
            'earnings': '#실적발표',
            'tech': '#기술주',
            'finance': '#금융',
            'market': '#증시',
            'investment': '#투자정보',
            'breaking': '#속보',
            'trump': '#트럼프'
        }
        
        # 태그 기반 해시태그 추가
        for tag in tags[:3]:
            if tag.lower() in tag_mapping:
                hashtags.append(tag_mapping[tag.lower()])
        
        # 특정 키워드 기반 해시태그
        summary_lower = summary.lower()
        if 'nasdaq' in summary_lower:
            hashtags.append('#나스닥')
        if 's&p' in summary_lower or 'sp500' in summary_lower:
            hashtags.append('#SP500')
        if 'dow' in summary_lower:
            hashtags.append('#다우지수')
        
        # 중복 제거 및 최대 5개로 제한
        unique_hashtags = list(dict.fromkeys(hashtags))[:5]
        
        return " ".join(unique_hashtags)
    
    def _trim_content(self, content_parts: List[str]) -> str:
        """길이 제한에 맞게 콘텐츠 조정"""
        # 우선순위: 제목 > 본문 > 핵심포인트 > 해시태그 > 서명
        essential_parts = []
        optional_parts = []
        
        for i, part in enumerate(content_parts):
            if i <= 2:  # 제목과 첫 번째 본문
                essential_parts.append(part)
            elif "핵심 포인트" in part or part.startswith("•"):
                essential_parts.append(part)
            elif part == self.brand_signature:
                essential_parts.append(part)
            else:
                optional_parts.append(part)
        
        # 필수 부분부터 조합
        result = "\n".join(essential_parts)
        
        # 선택적 부분 추가 (길이 허용 시)
        for part in optional_parts:
            test_result = result + "\n" + part
            if len(test_result) <= self.max_length:
                result = test_result
            else:
                break
        
        return result


class CryptoNewsTemplate(FinancialNewsTemplate):
    """암호화폐 전문 템플릿"""
    
    def _create_engaging_title(self, title: str, tags: List[str]) -> str:
        """암호화폐 전용 제목"""
        return f"₿ {title}"
    
    def _generate_financial_hashtags(self, tags: List[str], summary: str) -> str:
        """암호화폐 전용 해시태그"""
        hashtags = ["#암호화폐", "#비트코인", "#크립토"]
        
        crypto_mapping = {
            'bitcoin': '#BTC',
            'ethereum': '#ETH',
            'binance': '#BNB',
            'cardano': '#ADA',
            'solana': '#SOL',
            'defi': '#디파이',
            'nft': '#NFT'
        }
        
        summary_lower = summary.lower()
        for keyword, hashtag in crypto_mapping.items():
            if keyword in summary_lower:
                hashtags.append(hashtag)
        
        hashtags.append("#미국투자")
        unique_hashtags = list(dict.fromkeys(hashtags))[:5]
        return " ".join(unique_hashtags)


class FedNewsTemplate(FinancialNewsTemplate):
    """연준 관련 뉴스 전문 템플릿"""
    
    def _create_engaging_title(self, title: str, tags: List[str]) -> str:
        """연준 전용 제목"""
        return f"🏛️ {title}"
    
    def _analyze_market_impact(self, summary: str, tags: List[str]) -> str:
        """연준 뉴스의 시장 영향"""
        if 'rate' in summary.lower():
            return "금리 정책 변화로 전 시장 주목"
        else:
            return "연준 발언에 따른 시장 변동성 예상"


# 새로운 구조화된 금융 뉴스 템플릿 추가

class StructuredFinancialTemplate:
    """구조화된 금융 뉴스 템플릿 - 예시 형식 기반"""
    
    @staticmethod
    def format_content(title: str, summary: str, url: str = None, source: str = None, tags: List[str] = None) -> str:
        """구조화된 금융 뉴스 포맷"""
        
        # 제목에 이모지 추가
        emoji_title = StructuredFinancialTemplate._add_title_emoji(title)
        
        # 핵심 내용 생성
        key_section = StructuredFinancialTemplate._create_key_section(summary)
        
        # 배경/경위 섹션
        background_section = StructuredFinancialTemplate._create_background_section(summary)
        
        # 파급효과 섹션
        impact_section = StructuredFinancialTemplate._create_impact_section(summary)
        
        # 한마디 요약
        one_line = StructuredFinancialTemplate._create_one_line_summary(title, summary)
        
        # 해시태그
        hashtags = StructuredFinancialTemplate._create_hashtags(title, summary, tags)
        
        # 전체 구조 조합
        content_parts = [
            f"🇺🇸 {emoji_title}",
            "",
            "━" * 40,
            "",
            "🚨 **핵심 내용**",
            "",
            key_section,
            "",
            "━" * 40,
            "",
            "⚡ **배경 및 경위**",
            "",
            background_section,
            "",
            "━" * 40,
            "",
            "🎯 **파급효과 & 의미**",
            "",
            impact_section,
            "",
            "━" * 40,
            "",
            f"**한마디로:** {one_line}",
            "",
            hashtags
        ]
        
        return "\n".join(content_parts)
    
    @staticmethod
    def _add_title_emoji(title: str) -> str:
        """제목에 적절한 이모지 추가"""
        title_lower = title.lower()
        
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
            '이란': '💥⚓',
            '중국': '🇨🇳💥'
        }
        
        for keyword, emoji in emoji_map.items():
            if keyword in title:
                return f"{title} {emoji}"
        
        return f"{title} 💰📈"
    
    @staticmethod
    def _create_key_section(summary: str) -> str:
        """핵심 내용 섹션 생성"""
        sentences = summary.split('. ')[:4]  # 처음 4개 문장
        
        key_points = []
        for sentence in sentences:
            if sentence.strip():
                formatted = f"• {sentence.strip()}"
                if not formatted.endswith('.'):
                    formatted += '.'
                key_points.append(formatted)
        
        return '\n'.join(key_points) if key_points else "• 주요 금융 뉴스가 발표되었습니다."
    
    @staticmethod
    def _create_background_section(summary: str) -> str:
        """배경 및 경위 섹션 생성"""
        return f"**주요 배경:**\n{summary[:200]}..." if len(summary) > 200 else summary
    
    @staticmethod
    def _create_impact_section(summary: str) -> str:
        """파급효과 섹션 생성"""
        return "**시장 영향:**\n• 관련 섹터 주목 필요\n• 투자자 심리에 영향 가능"
    
    @staticmethod
    def _create_one_line_summary(title: str, summary: str) -> str:
        """한마디 요약 생성"""
        return summary.split('.')[0] if '.' in summary else title
    
    @staticmethod
    def _create_hashtags(title: str, summary: str, tags: List[str] = None) -> str:
        """해시태그 생성"""
        base_tags = ['#미국투자', '#금융뉴스']
        
        if tags:
            for tag in tags[:6]:  # 최대 6개 추가
                formatted_tag = f"#{tag}" if not tag.startswith('#') else tag
                if formatted_tag not in base_tags:
                    base_tags.append(formatted_tag)
        
        return ' '.join(base_tags[:8])  # 최대 8개


# 템플릿 매핑 업데이트
TEMPLATES = {
    "financial_news": FinancialNewsTemplate(),
    "crypto_news": CryptoNewsTemplate(),
    "fed_news": FedNewsTemplate(),
}


def get_template(content_type: str = "financial_news") -> FinancialNewsTemplate:
    """템플릿 가져오기"""
    return TEMPLATES.get(content_type, FinancialNewsTemplate())


def classify_content_type(title: str, summary: str, tags: List[str]) -> str:
    """콘텐츠 타입 자동 분류"""
    title_lower = title.lower()
    summary_lower = summary.lower()
    
    # 암호화폐 관련
    crypto_keywords = ['bitcoin', 'crypto', 'ethereum', 'blockchain', 'defi', 'nft']
    if any(keyword in title_lower or keyword in summary_lower for keyword in crypto_keywords):
        return "crypto_news"
    
    # 연준 관련
    fed_keywords = ['fed', 'federal reserve', 'powell', 'interest rate', 'monetary policy']
    if any(keyword in title_lower or keyword in summary_lower for keyword in fed_keywords):
        return "fed_news"
    
    # 기본 금융 뉴스
    return "financial_news" 