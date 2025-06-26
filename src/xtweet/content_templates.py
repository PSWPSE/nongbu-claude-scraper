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
    """구조화된 금융 뉴스 템플릿 - 개선된 버전"""
    
    @staticmethod
    def format_content(title: str, summary: str, url: str = None, source: str = None, tags: List[str] = None) -> str:
        """개선된 구조화된 금융 뉴스 포맷"""
        
        # 제목에 이모지 추가
        emoji_title = StructuredFinancialTemplate._add_title_emoji(title)
        
        # 핵심 내용 & 정량 분석 생성
        key_section = StructuredFinancialTemplate._create_enhanced_key_section(summary)
        
        # 배경/경위 섹션 (글로벌 컨텍스트 포함)
        background_section = StructuredFinancialTemplate._create_enhanced_background_section(summary)
        
        # 투자 전략 & 액션 플랜 섹션
        strategy_section = StructuredFinancialTemplate._create_investment_strategy_section(summary, tags)
        
        # 시장 영향 & 데이터 분석 섹션
        market_analysis_section = StructuredFinancialTemplate._create_market_analysis_section(summary)
        
        # 투자자 액션 및 모니터링 포인트
        action_monitoring = StructuredFinancialTemplate._create_action_monitoring_section(summary, tags)
        
        # 해시태그
        hashtags = StructuredFinancialTemplate._create_enhanced_hashtags(title, summary, tags)
        
        # 전체 구조 조합
        content_parts = [
            f"🇺🇸 {emoji_title}",
            "",
            "━" * 40,
            "",
            "🚨 **핵심 내용 & 정량 분석**",
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
            "🎯 **투자 전략 & 액션 플랜**",
            "",
            strategy_section,
            "",
            "━" * 40,
            "",
            "📊 **시장 영향 & 데이터 분석**",
            "",
            market_analysis_section,
            "",
            "━" * 40,
            "",
            action_monitoring,
            "",
            hashtags
        ]
        
        return "\n".join(content_parts)
    
    @staticmethod
    def _add_title_emoji(title: str) -> str:
        """제목에 적절한 이모지 추가 - 확장된 매핑"""
        title_lower = title.lower()
        
        emoji_map = {
            # 금융 기관
            '연준': '🏛️💰', 'fed': '🏛️💰', 'federal reserve': '🏛️💰',
            '중앙은행': '🏛️💰', 'central bank': '🏛️💰',
            
            # 경제 지표
            '금리': '📈💰', 'interest rate': '📈💰', 'rate': '📈💰',
            '인플레이션': '📊🔥', 'inflation': '📊🔥',
            'gdp': '📈🏛️', 'employment': '👥📊',
            
            # 암호화폐
            '비트코인': '₿💎', 'bitcoin': '₿💎', 'btc': '₿💎',
            '이더리움': '🔷💎', 'ethereum': '🔷💎', 'eth': '🔷💎',
            'crypto': '💎⚡', '암호화폐': '💎⚡',
            
            # 주요 기업
            '테슬라': '⚡🚗', 'tesla': '⚡🚗', 'tsla': '⚡🚗',
            '애플': '🍎📱', 'apple': '🍎📱', 'aapl': '🍎📱',
            '엔비디아': '🎮💾', 'nvidia': '🎮💾', 'nvda': '🎮💾',
            '구글': '🔍💻', 'google': '🔍💻', 'googl': '🔍💻',
            '마이크로소프트': '💻🏢', 'microsoft': '💻🏢', 'msft': '💻🏢',
            
            # 섹터
            '실적': '📊💰', 'earnings': '📊💰',
            '주식': '📈💹', 'stock': '📈💹', 'equity': '📈💹',
            '채권': '📋💰', 'bond': '📋💰',
            '원자재': '🏭⚡', 'commodity': '🏭⚡',
            '부동산': '🏠📈', 'real estate': '🏠📈',
            
            # 시장 상황
            '제재': '💥⚓', 'sanctions': '💥⚓',
            '속보': '🚨⚡', 'breaking': '🚨⚡',
            '상승': '🚀📈', 'surge': '🚀📈', 'rally': '🚀📈',
            '하락': '📉💥', 'drop': '📉💥', 'fall': '📉💥',
            '발표': '📢💼', 'announcement': '📢💼',
            '급등': '🚀💥', 'soar': '🚀💥',
            '급락': '📉💥', 'plunge': '📉💥',
            
            # 지정학
            '이란': '🇮🇷💥', 'iran': '🇮🇷💥',
            '중국': '🇨🇳💼', 'china': '🇨🇳💼',
            '러시아': '🇷🇺⚡', 'russia': '🇷🇺⚡',
            '우크라이나': '🇺🇦💙', 'ukraine': '🇺🇦💙',
            '트럼프': '🇺🇸🎯', 'trump': '🇺🇸🎯',
            
            # 기술/AI
            'ai': '🤖⚡', '인공지능': '🤖⚡',
            '반도체': '💾⚡', 'semiconductor': '💾⚡',
            '전기차': '⚡🚗', 'ev': '⚡🚗', 'electric vehicle': '⚡🚗'
        }
        
        for keyword, emoji in emoji_map.items():
            if keyword in title_lower:
                return f"{title} {emoji}"
        
        return f"{title} 💰📈"
    
    @staticmethod
    def _create_enhanced_key_section(summary: str) -> str:
        """향상된 핵심 내용 & 정량 분석 섹션"""
        # 숫자 패턴 추출
        import re
        numbers = re.findall(r'[\d,]+\.?\d*[%]?', summary)
        
        key_points = [
            f"• **주요 수치**: {', '.join(numbers[:3]) if numbers else '구체적 수치 분석 중'}",
            "• **시장 반응**: 관련 지수 및 섹터별 즉시 반응 분석",
            "• **영향 범위**: 직접 연관 기업 및 공급망 파급효과",
            "• **시간 프레임**: 단기(1-3개월), 중기(3-12개월), 장기(1년+) 전망"
        ]
        
        return '\n'.join(key_points)
    
    @staticmethod
    def _create_enhanced_background_section(summary: str) -> str:
        """향상된 배경 및 경위 섹션"""
        background_text = f"""**주요 배경:**
{summary[:200]}{'...' if len(summary) > 200 else ''}

**경위 & 타임라인:**
최근 시장 동향과 연관된 주요 이벤트들을 시간순으로 분석

**글로벌 컨텍스트:**
국제 경제 상황, 지정학적 요인, 관련 중앙은행 정책과의 연관성"""
        
        return background_text
    
    @staticmethod
    def _create_investment_strategy_section(summary: str, tags: List[str] = None) -> str:
        """투자 전략 & 액션 플랜 섹션"""
        strategy_text = """**📈 투자 기회:**
• **매수 타이밍**: 기술적 지표 기반 최적 진입점 분석
• **목표 종목**: 한국 투자자 접근 가능한 ETF, ADR, 국내 연관주
• **기술적 분석**: 주요 지지/저항선, RSI, MACD 등 기술 지표

**⚠️ 리스크 관리:**
• **주요 위험**: 시장 변동성, 지정학적 리스크, 환율 변동 영향
• **손절 기준**: -10% 손실 시 재평가, -15% 강제 손절 기준
• **대안 시나리오**: 예상과 다른 상황별 대응 전략

**💰 포트폴리오 전략:**
• **섹터 배분**: 관련 섹터 20-30%, 방어 섹터 30-40% 권장
• **분산 투자**: 지역별, 자산군별 리스크 분산 방안
• **헷징 전략**: 환율 헷지, 변동성 대응 옵션 전략"""
        
        return strategy_text
    
    @staticmethod
    def _create_market_analysis_section(summary: str) -> str:
        """시장 영향 & 데이터 분석 섹션"""
        analysis_text = """**직접적 영향:**
• 해당 뉴스 발표 후 즉각적 시장 반응 및 거래량 급증 예상
• 관련 종목/섹터 3-5% 변동성, VIX 지수 상승 가능성
• 옵션 시장 Put/Call 비율 변화 및 내재 변동성 증가

**간접적 파급효과:**
• 연관 산업 공급망 전반의 주가 연쇄 반응
• 원/달러 환율 ±0.5-1.0% 변동, 한국 수출기업 영향
• 국고채 10년물 금리 ±5-10bp 변동 예상

**과거 유사 사례:**
• 2008년, 2020년, 2022년 유사 상황 시 시장 반응 패턴
• 평균 회복 기간 2-6주, 최대 변동성 지속 기간 1-2주
• 장기 투자자 관점에서 기회 vs 위험 분석"""
        
        return analysis_text
    
    @staticmethod
    def _create_action_monitoring_section(summary: str, tags: List[str] = None) -> str:
        """투자자 액션 및 모니터링 섹션"""
        action_text = """**💡 투자자 액션**: KODEX 미국S&P500 ETF 비중 조절, 관련 국내 반도체/IT ETF 모니터링, 달러 ETF 헷지 고려

**⏰ 모니터링 포인트**: 
• 주요 지표: VIX 지수, 10년물 국채 금리, 달러인덱스(DXY)
• 발표 일정: 다음 FOMC 회의(날짜), 주요 기업 실적 발표
• 이벤트: 지정학적 리스크, 무역 협상, 중앙은행 정책 변화"""
        
        return action_text
    
    @staticmethod
    def _create_enhanced_hashtags(title: str, summary: str, tags: List[str] = None) -> str:
        """향상된 해시태그 생성"""
        base_tags = ["#미국투자", "#금융뉴스", "#투자정보"]
        
        # 제목 기반 태그 추출
        title_lower = title.lower()
        additional_tags = []
        
        tag_mapping = {
            'fed': '#연준', 'bitcoin': '#비트코인', 'tesla': '#테슬라',
            'apple': '#애플', 'nvidia': '#엔비디아', 'earnings': '#실적발표',
            'inflation': '#인플레이션', 'rate': '#금리', 'china': '#중국리스크',
            'trump': '#트럼프', 'ai': '#AI', 'semiconductor': '#반도체'
        }
        
        for keyword, tag in tag_mapping.items():
            if keyword in title_lower and tag not in additional_tags:
                additional_tags.append(tag)
        
        # 최대 7개 태그
        all_tags = base_tags + additional_tags[:4]
        return ' '.join(all_tags)


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