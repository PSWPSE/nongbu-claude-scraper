#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
NongBu Claude 4 Sonnet Pro 대시보드 - 최적화된 버전
- API 키 고정 설정
- 스케줄러 토글 스위치
- 무한 스크롤 UI
- 효율적인 코드 구조
"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template_string, jsonify, request
import anthropic
import time
import threading
import uuid
import requests
from bs4 import BeautifulSoup
import hashlib
from urllib.parse import urljoin
import asyncio
import logging
import random
from concurrent.futures import ThreadPoolExecutor

# 스크래퍼 모듈 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

SCRAPER_AVAILABLE = False
try:
    # 현재 디렉토리에서 src 폴더의 모듈 import 시도
    from src.xtweet.scraper import ContentScraper
    from src.xtweet.app import db
    from src.xtweet.models import ScrapingTarget, ScrapedContent, ScrapingLog
    SCRAPER_AVAILABLE = True
    print("✅ 스크래퍼 모듈 로드 성공 (src.xtweet)")
except ImportError as e1:
    try:
        # 직접 xtweet 모듈 import 시도
        from xtweet.scraper import ContentScraper
        from xtweet.app import db
        from xtweet.models import ScrapingTarget, ScrapedContent, ScrapingLog
        SCRAPER_AVAILABLE = True
        print("✅ 스크래퍼 모듈 로드 성공 (xtweet)")
    except ImportError as e2:
        try:
            # 절대 경로로 시도
            import sys
            import os
            current_dir = os.path.dirname(os.path.abspath(__file__))
            src_path = os.path.join(current_dir, 'src')
            if src_path not in sys.path:
                sys.path.insert(0, src_path)
            from xtweet.scraper import ContentScraper
            from xtweet.app import db
            from xtweet.models import ScrapingTarget, ScrapedContent, ScrapingLog
            SCRAPER_AVAILABLE = True
            print("✅ 스크래퍼 모듈 로드 성공 (절대 경로)")
        except ImportError as e3:
            SCRAPER_AVAILABLE = False
            print(f"⚠️ 스크래퍼 모듈을 찾을 수 없습니다.")
            print(f"   오류 1: {e1}")
            print(f"   오류 2: {e2}")
            print(f"   오류 3: {e3}")
            print(f"   현재 경로: {os.getcwd()}")
            print(f"   sys.path: {sys.path[:3]}...")

# 설정
FIXED_CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', 'your-claude-api-key-here')
DB_PATHS = ['src/instance/nongbu_financial.db', 'instance/nongbu_financial.db', 'instance/nongbu_financial_clean.db', 'nongbu_financial.db']

# Flask 앱 생성
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'nongbu-claude-dashboard-secret-key-2024')

# 유틸리티 함수들
def get_db_connection():
    """데이터베이스 연결 - 개선된 버전"""
    try:
        for db_path in DB_PATHS:
            if os.path.exists(db_path):
                # WAL 모드와 타임아웃 설정으로 락 문제 해결
                conn = sqlite3.connect(db_path, timeout=30.0)
                conn.row_factory = sqlite3.Row
                
                # WAL 모드 설정 (Write-Ahead Logging)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                conn.execute("PRAGMA temp_store=MEMORY")
                
                return conn
        return None
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return None

def execute_db_query(query, params=None, fetch_one=False, fetch_all=False):
    """데이터베이스 쿼리 실행 헬퍼"""
    try:
        conn = get_db_connection()
        if not conn:
            return None
        
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.rowcount
            
        conn.commit()
        conn.close()
        return result
    except Exception as e:
        print(f"DB 쿼리 실패: {e}")
        return None

def create_response(success=True, data=None, error=None, **kwargs):
    """표준 응답 생성"""
    response = {'success': success}
    if data:
        response.update(data)
    if error:
        response['error'] = error
    response.update(kwargs)
    return jsonify(response)

def safe_file_operation(operation, default_response):
    """파일 작업 안전 실행"""
    try:
        return operation()
    except Exception:
        return default_response

# HTML 템플릿
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NongBu Claude 4 Sonnet Pro 시스템</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚀</text></svg>">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh; color: #333;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; }
        .header p { font-size: 1.1rem; opacity: 0.9; }
        
        .section { 
            background: white; padding: 30px; border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 20px; 
        }
        .status { padding: 15px; border-radius: 8px; margin: 15px 0; }
        .status-success { background: #d4edda; color: #155724; border-left: 4px solid #28a745; }
        .status-error { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
        
        .content-item { 
            padding: 20px; border-left: 4px solid #667eea; margin-bottom: 15px; 
            background: #f8f9ff; border-radius: 0 8px 8px 0;
        }
        .content-title { font-weight: bold; margin-bottom: 8px; color: #333; font-size: 1.1rem; }
        .content-meta { font-size: 0.9rem; color: #666; margin-bottom: 10px; }
        .content-summary { font-size: 0.9rem; color: #777; margin-bottom: 15px; line-height: 1.4; }
        
        .btn { 
            padding: 12px 24px; border: none; border-radius: 8px; font-size: 1rem; 
            font-weight: 600; cursor: pointer; transition: all 0.3s ease; margin: 5px;
            display: inline-block; text-decoration: none;
        }
        .btn-primary { background: #667eea; color: white; }
        .btn-primary:hover { background: #5a6fd8; }
        .btn-success { background: #48bb78; color: white; }
        .btn-success:hover { background: #38a169; }
        .btn-info { background: #4299e1; color: white; }
        .btn-info:hover { background: #3182ce; }
        .btn-danger { background: #dc3545; color: white; }
        .btn-danger:hover { background: #c82333; }
        .btn:disabled { background: #ccc; cursor: not-allowed; opacity: 0.6; }
        
        .loading { text-align: center; padding: 40px; color: #666; font-size: 1.1rem; }

        /* 스케줄러 토글 */
        .scheduler-section {
            display: flex; align-items: center; justify-content: center; gap: 15px;
            margin: 20px 0; padding: 20px; background: #f8f9ff; border-radius: 10px;
        }
        .switch { position: relative; display: inline-block; width: 60px; height: 34px; }
        .switch input { opacity: 0; width: 0; height: 0; }
        .slider {
            position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
            background-color: #ccc; transition: .4s; border-radius: 34px;
        }
        .slider:before {
            position: absolute; content: ""; height: 26px; width: 26px; left: 4px; bottom: 4px;
            background-color: white; transition: .4s; border-radius: 50%;
        }
        input:checked + .slider { background-color: #4CAF50; }
        input:checked + .slider:before { transform: translateX(26px); }
        .scheduler-status { font-size: 1.2rem; font-weight: bold; }
        .scheduler-status.active { color: #4CAF50; }
        .scheduler-status.inactive { color: #f44336; }

        /* 탭 시스템 */
        .tabs-container { 
            background: white; border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); margin-bottom: 20px; 
            overflow: hidden;
        }
        .tabs-header {
            display: flex; background: #f8f9fa; border-bottom: 2px solid #dee2e6;
        }
        .tab-button {
            flex: 1; padding: 20px; border: none; background: transparent;
            font-size: 1.1rem; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease; color: #666;
            border-bottom: 3px solid transparent;
        }
        .tab-button.active {
            background: white; color: #667eea; border-bottom-color: #667eea;
        }
        .tab-button:hover:not(.active) {
            background: #e9ecef; color: #495057;
        }
        .tab-content {
            display: none; padding: 30px;
        }
        .tab-content.active {
            display: block;
        }
        .tab-header {
            display: flex; justify-content: space-between; align-items: center; 
            margin-bottom: 20px;
        }
        .tab-header h2 {
            margin: 0; color: #333; font-size: 1.8rem;
        }

        /* 무한 스크롤 */
        .content-list {
            max-height: 600px; overflow-y: auto; padding-right: 10px;
        }
        .content-list::-webkit-scrollbar { width: 8px; }
        .content-list::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
        .content-list::-webkit-scrollbar-thumb { background: #667eea; border-radius: 10px; }
        .content-list::-webkit-scrollbar-thumb:hover { background: #5a6fd8; }

        /* 모달 스타일 */
        .modal {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.8); z-index: 1000; display: flex;
            align-items: center; justify-content: center; padding: 20px;
        }
        .modal-content {
            background: white; border-radius: 15px; padding: 30px;
            max-width: 90%; max-height: 90%; overflow-y: auto;
            position: relative; box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            min-width: 500px; width: 80%;
        }
        .modal-header {
            display: flex; justify-content: space-between; align-items: center; 
            margin-bottom: 20px; border-bottom: 2px solid #eee; padding-bottom: 15px;
        }
        .modal-title {
            margin: 0; color: #333; font-size: 1.5rem;
        }
        .modal-close {
            background: #dc3545; color: white; border: none; 
            border-radius: 50%; width: 35px; height: 35px; 
            font-size: 18px; cursor: pointer; font-weight: bold;
            transition: background 0.3s ease;
        }
        .modal-close:hover {
            background: #c82333;
        }
        .modal-body {
            white-space: pre-wrap; font-family: 'Malgun Gothic', sans-serif; 
            line-height: 1.6; color: #333; font-size: 14px;
            max-height: 60vh; overflow-y: auto; padding: 15px;
            background: #f8f9fa; border-radius: 8px; border: 1px solid #dee2e6;
        }

        /* 반응형 */
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 2rem; }
            .scheduler-section { flex-direction: column; gap: 10px; }
            .modal-content {
                min-width: 90%; width: 95%; padding: 20px;
            }
            .modal-title {
                font-size: 1.2rem;
            }
            .tab-button {
                padding: 15px; font-size: 1rem;
            }
            .tabs-header {
                flex-direction: column;
            }
            .tab-button {
                border-bottom: none; border-right: 3px solid transparent;
            }
            .tab-button.active {
                border-right-color: #667eea; border-bottom: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 NongBu Claude 4 Sonnet Pro 시스템</h1>
            <p>프로플랜으로 고품질 AI 콘텐츠 생성</p>
        </div>
        
        <!-- API 연결 상태 -->
        <div class="section">
            <h2>🔑 Claude API 연결 상태</h2>
            <div class="status status-success">
                ✅ <strong>Claude API 연결됨:</strong> 고정 API 키로 자동 연결되었습니다.
            </div>
        </div>
        
        <!-- 스케줄러 설정 -->
        <div class="section">
            <h2>⚙️ 자동 스크래핑 설정</h2>
            <div class="scheduler-section">
                <span class="scheduler-status" id="scheduler-status">🔄 상태 확인 중...</span>
                <label class="switch">
                    <input type="checkbox" id="scheduler-toggle" onchange="toggleScheduler()">
                    <span class="slider"></span>
                </label>
                <span style="font-size: 1rem; color: #666;">자동 스크래핑 ON/OFF</span>
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <button class="btn btn-info" onclick="manualCollection()">🔄 수동 수집 실행</button>
            </div>
        </div>
        
        <!-- 콘텐츠 탭 시스템 -->
        <div class="tabs-container">
            <div class="tabs-header">
                <button class="tab-button active" onclick="switchTab('scraped')">
                    📡 수집된 콘텐츠
                </button>
                <button class="tab-button" onclick="switchTab('generated')">
                    📝 생성된 콘텐츠
                </button>
        </div>
        
            <!-- 수집된 콘텐츠 탭 -->
            <div id="scraped-tab" class="tab-content active">
                <div class="tab-header">
            <h2>📡 수집된 콘텐츠</h2>
                    <button class="btn btn-danger" onclick="deleteContent('scraped')" style="font-size: 0.9rem;">
                        🗑️ 모든 콘텐츠 삭제
                    </button>
                </div>
            <div class="content-list" id="scraped-content-list">
                <div class="loading">콘텐츠를 불러오는 중...</div>
            </div>
        </div>
        
            <!-- 생성된 콘텐츠 탭 -->
            <div id="generated-tab" class="tab-content">
                <div class="tab-header">
                <h2>📝 생성된 콘텐츠</h2>
                    <button class="btn btn-danger" onclick="deleteContent('generated')" style="font-size: 0.9rem;">
                        🗑️ 모든 콘텐츠 삭제
                    </button>
            </div>
            <div class="content-list" id="generated-content-list">
                <div class="loading">콘텐츠를 불러오는 중...</div>
            </div>
            </div>
        </div>
    </div>

    <script>
        // 전역 변수
        const state = {
            scraped: { page: 1, loading: false, hasMore: true },
            generated: { page: 1, loading: false, hasMore: true },
            activeTab: 'scraped'
        };

        // 탭 전환 함수
        function switchTab(tabName) {
            // 모든 탭 버튼 비활성화
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // 모든 탭 콘텐츠 숨기기
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 선택된 탭 활성화
            event.target.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
            
            // 상태 업데이트
            state.activeTab = tabName;
            
            // 해당 탭의 콘텐츠 로드 (아직 로드되지 않았다면)
            if (tabName === 'scraped' && state.scraped.page === 1) {
                loadContent('scraped');
            } else if (tabName === 'generated' && state.generated.page === 1) {
                loadContent('generated');
            }
        }

        // API 호출 헬퍼
        async function apiCall(url, options = {}) {
            try {
                const response = await fetch(url, options);
                
                // HTTP 상태 코드 확인
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                return data;
            } catch (error) {
                console.error('API 호출 실패:', error);
                return { success: false, error: error.message };
            }
        }

        // 스케줄러 관련
        async function loadSchedulerStatus() {
            const data = await apiCall('/api/scheduler-info');
            const statusEl = document.getElementById('scheduler-status');
            const toggleEl = document.getElementById('scheduler-toggle');
                
                if (data.is_running) {
                statusEl.textContent = '🟢 실행중';
                statusEl.className = 'scheduler-status active';
                toggleEl.checked = true;
                } else {
                statusEl.textContent = '🔴 중지됨';
                statusEl.className = 'scheduler-status inactive';
                toggleEl.checked = false;
            }
        }

        async function toggleScheduler() {
            const toggle = document.getElementById('scheduler-toggle');
            const statusEl = document.getElementById('scheduler-status');
            
            statusEl.textContent = '⏳ 변경 중...';
                
            const result = await apiCall('/api/scheduler-toggle', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enable: toggle.checked })
                });
                
                if (result.success) {
                    if (toggle.checked) {
                    statusEl.textContent = '🟢 실행중';
                    statusEl.className = 'scheduler-status active';
                    } else {
                    statusEl.textContent = '🔴 중지됨';
                    statusEl.className = 'scheduler-status inactive';
                    }
                } else {
                    toggle.checked = !toggle.checked;
                statusEl.textContent = '❌ 변경 실패';
                alert('스케줄러 상태 변경 실패: ' + result.error);
            }
        }

        async function manualCollection() {
            const btn = event.target;
            const originalText = btn.innerHTML;
            
                btn.innerHTML = '⏳ 수집 중...';
                btn.disabled = true;
                
            try {
                const result = await apiCall('/api/manual-collection', { method: 'POST' });
                
                if (result.success) {
                    alert(`✅ 수집 완료!\\n새로운 콘텐츠: ${result.new_count}개`);
                    // 수집된 콘텐츠 새로고침
                    loadContent('scraped');
                    // 수집된 콘텐츠 탭으로 전환
                    switchToTab('scraped');
                } else {
                    alert('❌ 수집 실패: ' + (result.error || '알 수 없는 오류'));
                }
            } catch (error) {
                console.error('수동 수집 오류:', error);
                alert('❌ 수집 중 오류가 발생했습니다.');
            }
            
                btn.innerHTML = originalText;
                btn.disabled = false;
            }
        
        // 탭 전환 헬퍼 함수 (event 없이 호출 가능)
        function switchToTab(tabName) {
            // 모든 탭 버튼 비활성화
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // 모든 탭 콘텐츠 숨기기
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // 선택된 탭 활성화
            const buttons = document.querySelectorAll('.tab-button');
            if (tabName === 'scraped') {
                buttons[0].classList.add('active');
            } else if (tabName === 'generated') {
                buttons[1].classList.add('active');
            }
            
            document.getElementById(`${tabName}-tab`).classList.add('active');
            state.activeTab = tabName;
        }

        // 콘텐츠 로드
        async function loadContent(type, page = 1, append = false) {
            if (state[type].loading || (!state[type].hasMore && page > 1)) return;
            
            state[type].loading = true;
            const container = document.getElementById(`${type}-content-list`);
            
            if (!append) {
                container.innerHTML = '<div class="loading">콘텐츠를 불러오는 중...</div>';
            }
            
            const data = await apiCall(`/api/${type}-content-detailed?page=${page}&per_page=10`);
                
            if (!append) container.innerHTML = '';
                
                if (data.content && data.content.length > 0) {
                    data.content.forEach(item => {
                    const div = document.createElement('div');
                    div.className = 'content-item';
                    
                    if (type === 'scraped') {
                        div.innerHTML = `
                            <div class="content-title">${item.title}</div>
                            <div class="content-meta">
                                📅 ${new Date(item.created_at).toLocaleString('ko-KR')} | 
                                🌐 ${item.source} | 
                                🔗 <a href="${item.url}" target="_blank">원문 보기</a>
                            </div>
                            <div class="content-summary">${item.summary || '요약 없음'}</div>
                            <div style="text-align: right; margin-top: 10px;">
                                <button class="btn btn-info" onclick="viewScrapedContent(${item.id})">📖 본문 보기</button>
                                <button class="btn btn-success" onclick="generateContent(${item.id})">🤖 콘텐츠 생성</button>
                            </div>
                        `;
                    } else {
                        div.innerHTML = `
                            <div class="content-title">${item.title}</div>
                            <div class="content-meta">
                                📅 ${new Date(item.created_at).toLocaleString('ko-KR')} | 🤖 Claude 생성
                            </div>
                            <div class="content-summary">${item.summary || '요약 없음'}</div>
                            <div style="text-align: right; margin-top: 10px;">
                                <button class="btn btn-info" onclick="viewGeneratedContent(${item.id})">📖 전체 보기</button>
                                <button class="btn btn-success" onclick="saveMarkdown(${item.id})">💾 마크다운 저장</button>
                            </div>
                        `;
                    }
                    container.appendChild(div);
                    });
                    
                state[type].hasMore = data.has_next;
                state[type].page = page;
                } else {
                    if (!append) {
                    container.innerHTML = `<div class="loading">${type === 'scraped' ? '수집된' : '생성된'} 콘텐츠가 없습니다.</div>`;
                    }
                state[type].hasMore = false;
                }
            
            state[type].loading = false;
        }

        // 콘텐츠 삭제
        async function deleteContent(type) {
            const typeText = type === 'scraped' ? '수집된' : '생성된';
            if (!confirm(`모든 ${typeText} 콘텐츠를 삭제하시겠습니까?\\n\\n이 작업은 되돌릴 수 없습니다.`)) {
                return;
            }
            
            const result = await apiCall(`/api/delete-all-${type}-content`, { method: 'POST' });
            
            if (result.success) {
                alert(`✅ ${result.message}`);
                loadContent(type);
            } else {
                alert('❌ 삭제 실패: ' + result.error);
            }
        }

        // 스크래핑된 콘텐츠 전체 보기
        async function viewScrapedContent(contentId) {
            console.log('viewScrapedContent 호출됨, contentId:', contentId);
            
            try {
                const result = await apiCall(`/api/scraped-content/${contentId}`);
                console.log('API 결과:', result);
                
                if (result.success) {
                    // API 응답에서 데이터는 result 자체에 있음 (data 속성 안에 있지 않음)
                    console.log('콘텐츠 데이터:', result);
                    
                    const content = `제목: ${result.title || 'No Title'}

출처: ${result.source || 'Unknown'}
URL: ${result.url || 'N/A'}
수집 시간: ${result.scraped_at ? new Date(result.scraped_at).toLocaleString('ko-KR') : 'Unknown'}

===== 전체 본문 =====

${result.content || '내용 없음'}`;
                    
                    console.log('모달에 표시할 콘텐츠 길이:', content.length);
                    showModal('스크래핑된 콘텐츠 전체 보기', content);
                } else {
                    console.error('API 실패:', result.error);
                    alert('❌ 콘텐츠 로드 실패: ' + result.error);
                }
            } catch (error) {
                console.error('viewScrapedContent 에러:', error);
                alert('❌ 오류가 발생했습니다: ' + error.message);
            }
        }

        // 생성된 콘텐츠 전체 보기
        async function viewGeneratedContent(contentId) {
            const result = await apiCall(`/api/generated-content/${contentId}`);
            
            if (result.success) {
                // API 응답에서 데이터는 result 자체에 있음 (data 속성 안에 있지 않음)
                const content = `제목: ${result.title || 'No Title'}

생성 시간: ${result.created_at ? new Date(result.created_at).toLocaleString('ko-KR') : 'Unknown'}
AI 모델: Claude 3.5 Sonnet

===== 생성된 콘텐츠 =====

${result.content || '내용 없음'}`;
                
                showModal('AI 생성 콘텐츠 전체 보기', content);
            } else {
                alert('❌ 콘텐츠 로드 실패: ' + result.error);
            }
        }

        // 콘텐츠 생성 - 개별 콘텐츠에 대해서만 실행
        async function generateContent(scrapedId) {
            console.log('generateContent 호출됨, scrapedId:', scrapedId);
            
            if (!scrapedId || scrapedId <= 0) {
                alert('❌ 잘못된 콘텐츠 ID입니다.');
                return;
            }
            
            const btn = event.target;
            const originalText = btn.innerHTML;
            
            btn.innerHTML = '🤖 생성 중...';
                btn.disabled = true;
                
            try {
                const result = await apiCall('/api/generate-content', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scraped_id: scrapedId })
                });
                
                if (result.success) {
                    alert(`✅ 콘텐츠 생성 완료!\\n제목: ${result.title}`);
                    // 생성된 콘텐츠 탭으로 자동 전환
                    switchToTab('generated');
                    loadContent('generated');
                } else {
                    alert('❌ 콘텐츠 생성 실패: ' + (result.error || '알 수 없는 오류'));
                }
            } catch (error) {
                console.error('콘텐츠 생성 오류:', error);
                alert('❌ 콘텐츠 생성 중 오류가 발생했습니다.');
            }
            
                btn.innerHTML = originalText;
                btn.disabled = false;
        }

        // 마크다운 저장 (새로운 API 사용)
        async function saveContentMarkdown(contentId) {
            const btn = event.target;
            const originalText = btn.innerHTML;
            
                btn.innerHTML = '⏳ 저장 중...';
                btn.disabled = true;
                
            try {
                const result = await apiCall('/api/save-content-markdown', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content_id: contentId })
                });
                
                if (result.success) {
                    alert(`✅ 마크다운 저장 완료!\n파일: ${result.filename}`);
                } else {
                    alert('❌ 저장 실패: ' + result.error);
                }
            } catch (error) {
                console.error('마크다운 저장 오류:', error);
                alert('❌ 저장 중 오류가 발생했습니다: ' + error.message);
            }
            
                btn.innerHTML = originalText;
                btn.disabled = false;
            }

        // 마크다운 저장 (기존 함수 - 호환성 유지)
        async function saveMarkdown(generatedId) {
            await saveContentMarkdown(generatedId);
        }

        // 모달 표시 함수
        function showModal(title, content) {
            console.log('showModal 호출됨:', title);
            
            // 기존 모달 제거
            const existingModal = document.getElementById('content-modal');
            if (existingModal) {
                existingModal.remove();
            }
            
            // 새 모달 생성
            const modal = document.createElement('div');
            modal.id = 'content-modal';
            modal.className = 'modal';
            
            // 모달 콘텐츠 생성
            const modalContent = document.createElement('div');
            modalContent.className = 'modal-content';
            
            // 모달 헤더
            const modalHeader = document.createElement('div');
            modalHeader.className = 'modal-header';
            modalHeader.innerHTML = `
                <h2 class="modal-title">${title}</h2>
                <button class="modal-close" onclick="closeModal()">×</button>
            `;
            
            // 모달 바디
            const modalBody = document.createElement('div');
            modalBody.className = 'modal-body';
            modalBody.textContent = content;
            
            // 조립
            modalContent.appendChild(modalHeader);
            modalContent.appendChild(modalBody);
            modal.appendChild(modalContent);
            
            // 페이지에 추가
            document.body.appendChild(modal);
            console.log('모달이 DOM에 추가됨');
            
            // 모달 외부 클릭 시 닫기
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    closeModal();
            }
            });

            // ESC 키로 닫기
            document.addEventListener('keydown', function escHandler(e) {
                if (e.key === 'Escape') {
                    closeModal();
                    document.removeEventListener('keydown', escHandler);
                }
            });
        }

        // 모달 닫기 함수
        function closeModal() {
            console.log('closeModal 호출됨');
            const modal = document.getElementById('content-modal');
            if (modal) {
                modal.remove();
                console.log('모달이 제거됨');
            }
        }

        // 무한 스크롤 설정
        function setupInfiniteScroll() {
            ['scraped', 'generated'].forEach(type => {
                const list = document.getElementById(`${type}-content-list`);
                list.addEventListener('scroll', () => {
                    if (list.scrollTop + list.clientHeight >= list.scrollHeight - 10) {
                        if (state[type].hasMore && !state[type].loading) {
                            loadContent(type, state[type].page + 1, true);
                    }
                }
            });
            });
        }
            
        // 초기화
        document.addEventListener('DOMContentLoaded', () => {
            loadSchedulerStatus();
            loadContent('scraped'); // 첫 번째 탭(수집된 콘텐츠)만 초기 로드
            setupInfiniteScroll();
        });
    </script>
</body>
</html>
"""

# 라우트들
@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/scraped-content/<int:content_id>')
def api_get_scraped_content(content_id):
    """개별 스크래핑된 콘텐츠의 전체 내용 조회"""
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(success=False, error='데이터베이스 연결 실패')
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, url, scraped_at
            FROM scraped_contents
            WHERE id = ?
        """, (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return create_response(success=False, error='콘텐츠를 찾을 수 없습니다.')
        
        content_data = {
            'id': row[0],
            'title': row[1] or 'No Title',
            'content': row[2] or '',
            'url': row[3] or '',
            'source': 'Manual Collection',
            'scraped_at': row[4] or ''
        }
        
        return create_response(data=content_data)
    except Exception as e:
        print(f"콘텐츠 조회 API 오류: {e}")
        return create_response(success=False, error=str(e))

@app.route('/api/generate-content', methods=['POST'])
def api_generate_content():
    """스크래핑된 콘텐츠를 기반으로 Claude를 이용해 새로운 콘텐츠 생성"""
    try:
        data = request.get_json()
        scraped_id = data.get('scraped_id')
        
        # 스크래핑된 콘텐츠 조회
        conn = get_db_connection()
        if not conn:
            return create_response(success=False, error='데이터베이스 연결 실패')
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sc.title, sc.content, sc.url, st.name as source_name
            FROM scraped_contents sc
            LEFT JOIN scraping_targets st ON sc.target_id = st.id
            WHERE sc.id = ?
        """, (scraped_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return create_response(success=False, error='원본 콘텐츠를 찾을 수 없습니다.')
        
        original_title = row[0] or 'No Title'
        original_content = row[1] or ''
        original_url = row[2] or ''
        source_name = row[3] or 'Unknown'
        
        # Claude API를 이용해 콘텐츠 생성
        client = anthropic.Anthropic(api_key=FIXED_CLAUDE_API_KEY)
        
        # 고급 구조화된 금융 뉴스 템플릿 기반 프롬프트
        prompt = f"""당신은 한국 투자자를 위한 전문 금융 분석가입니다. 다음 영문 금융 뉴스를 바탕으로 한국 투자자 관점에서 실용적이고 전문적인 분석 콘텐츠를 작성해주세요.

=== 원본 정보 ===
제목: {original_title}
출처: {source_name}
URL: {original_url}
내용: {original_content[:2000]}

=== 작성 지침 ===
다음 구조화된 형식으로 한국어로 작성해주세요:

🇺🇸 [제목을 한국어로 번역하고 적절한 이모지 추가] 

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 **핵심 내용**

• [핵심 포인트 1 - 가장 중요한 수치/정보]
• [핵심 포인트 2 - 주요 변화나 발표 내용]  
• [핵심 포인트 3 - 관련 기업/섹터 영향]
• [핵심 포인트 4 - 시장 반응이나 전망]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚡ **배경 및 경위**

**주요 배경:**
[이 뉴스가 나오게 된 배경과 맥락을 2-3문장으로 설명]

**경위:**
[시간순으로 주요 흐름이나 발전 과정을 간단히 설명]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 **파급효과 & 의미**

**시장 영향:**
• [관련 주식/섹터에 미치는 직접적 영향]
• [한국 투자자가 주목해야 할 종목이나 ETF]
• [달러/원화 환율이나 한국 시장에 미치는 영향]

**투자 관점:**
• [단기적 관점에서의 투자 포인트]
• [중장기적 관점에서의 시사점]
• [리스크 요소와 기회 요소]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**한마디로:** [이 뉴스의 핵심을 한 문장으로 요약하며, 한국 투자자에게 주는 시사점 포함]

#미국투자 #금융뉴스 #투자정보 [원본 내용과 관련된 구체적 해시태그 3-5개 추가]

=== 중요 사항 ===
1. 모든 내용을 한국어로 작성
2. 구체적인 숫자나 퍼센트가 있으면 반드시 포함
3. 한국 투자자 관점에서 실용적인 정보 제공
4. 전문적이지만 이해하기 쉽게 작성
5. 투자 판단에 도움이 되는 구체적 인사이트 제공
6. 이모지를 적절히 활용하여 가독성 향상
7. 과장하지 말고 객관적으로 분석"""
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=3000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Claude API 응답에서 텍스트 추출
        generated_content = ""
        if message.content and len(message.content) > 0:
            content_block = message.content[0]
            if hasattr(content_block, 'text'):
                generated_content = content_block.text
            else:
                generated_content = str(content_block)
        
        generated_title = f"[분석] {original_title}"
        
        # 생성된 콘텐츠를 데이터베이스에 저장
        cursor.execute("""
            INSERT INTO generated_contents (title, content, created_at, scraped_content_id)
            VALUES (?, ?, ?, ?)
        """, (generated_title, generated_content, datetime.now().isoformat(), scraped_id))
        
        generated_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return create_response(data={
            'generated_id': generated_id,
            'title': generated_title,
            'content': generated_content,
            'original_title': original_title
        })
        
    except Exception as e:
        print(f"콘텐츠 생성 API 오류: {e}")
        return create_response(success=False, error=f'콘텐츠 생성 실패: {str(e)}')

@app.route('/api/generated-content/<int:content_id>')
def api_get_generated_content(content_id):
    """개별 생성된 콘텐츠의 전체 내용 조회"""
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(success=False, error='데이터베이스 연결 실패')
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, content, created_at
            FROM generated_contents
            WHERE id = ?
        """, (content_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return create_response(success=False, error='콘텐츠를 찾을 수 없습니다.')
        
        content_data = {
            'id': row[0],
            'title': row[1] or 'No Title',
            'content': row[2] or '',
            'created_at': row[3] or ''
        }
        
        return create_response(data=content_data)
    except Exception as e:
        print(f"생성된 콘텐츠 조회 API 오류: {e}")
        return create_response(success=False, error=str(e))

@app.route('/api/generated-content-detailed')
def api_generated_content_detailed():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page
    
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(data={
                'content': [], 'has_next': False, 'has_prev': False,
                'page': 1, 'pages': 0, 'total': 0
            })
        
        cursor = conn.cursor()
        
        # 총 개수 조회
        cursor.execute("SELECT COUNT(*) FROM generated_contents")
        total_row = cursor.fetchone()
        total = total_row[0] if total_row else 0
        
        # 생성된 콘텐츠 조회
        cursor.execute("""
            SELECT id, title, content, created_at
            FROM generated_contents
            ORDER BY created_at DESC 
            LIMIT ? OFFSET ?
        """, (per_page + 1, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return create_response(data={
                'content': [], 'has_next': False, 'has_prev': False,
                'page': 1, 'pages': 0, 'total': 0
            })
        
        has_next = len(rows) > per_page
        if has_next:
            rows = rows[:-1]
        
        content_list = []
        for row in rows:
            row_id = row[0] if len(row) > 0 else 0
            title = row[1] if len(row) > 1 else 'No Title'
            content = row[2] if len(row) > 2 else ''
            created_at = row[3] if len(row) > 3 else ''
            
            # 요약 생성 (첫 200자)
            summary = content[:200] + '...' if content and len(content) > 200 else (content or '')
            
            content_list.append({
                'id': row_id,
                'title': title or 'No Title',
                'summary': summary,
                'content_length': len(content) if content else 0,
                'created_at': created_at or '',
                'source': 'AI Generated'
            })
        
        return create_response(data={
            'content': content_list,
            'has_next': has_next,
            'has_prev': page > 1,
            'page': page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 0,
            'total': total
        })
    except Exception as e:
        print(f"생성된 콘텐츠 API 오류: {e}")
        return create_response(data={
            'content': [], 'has_next': False, 'has_prev': False,
            'page': 1, 'pages': 0, 'total': 0
        })

@app.route('/api/save-content-markdown', methods=['POST'])
def api_save_content_markdown():
    """개별 생성된 콘텐츠를 마크다운 파일로 저장"""
    try:
        data = request.get_json()
        content_id = data.get('content_id')
        
        result = execute_db_query(
            "SELECT title, content, created_at FROM generated_contents WHERE id = ?",
            (content_id,), fetch_one=True
        )
        
        if not result:
            return create_response(success=False, error='콘텐츠를 찾을 수 없습니다.')
        
        title = result[0] if isinstance(result, (tuple, list)) else result['title']
        content = result[1] if isinstance(result, (tuple, list)) else result['content']
        created_at = result[2] if isinstance(result, (tuple, list)) else result['created_at']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in (title or 'content') if c.isalnum() or c in (' ', '-', '_')).rstrip()[:50]
        filename = f"nongbu_{safe_title}_{timestamp}.md"
        
        markdown_content = f"""# {title or 'AI 생성 콘텐츠'}

**생성일시:** {created_at}
**AI 모델:** Claude 3.5 Sonnet
**시스템:** NongBu Financial AI

---

{content}

---

*본 콘텐츠는 NongBu Claude AI 시스템에 의해 자동 생성되었습니다.*
"""
        
        os.makedirs("saved_markdown", exist_ok=True)
        file_path = os.path.join("saved_markdown", filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return create_response(data={'filename': filename, 'file_path': file_path})
    except Exception as e:
        return create_response(success=False, error=f'마크다운 저장 실패: {str(e)}')

@app.route('/api/stats')
def api_stats():
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(data={'scraped': 0, 'generated': 0})
        
        cursor = conn.cursor()
        
        # 수집된 콘텐츠 수
        cursor.execute('SELECT COUNT(*) FROM scraped_contents')
        scraped_result = cursor.fetchone()
        scraped_num = scraped_result[0] if scraped_result else 0
        
        # generated_contents 테이블이 존재하는지 확인
        try:
            cursor.execute('SELECT COUNT(*) FROM generated_contents')
            generated_result = cursor.fetchone()
            generated_num = generated_result[0] if generated_result else 0
        except:
            generated_num = 0
        
        conn.close()
        
        return create_response(data={
            'scraped': scraped_num,
            'generated': generated_num
        })
    except Exception as e:
        print(f"통계 API 오류: {e}")
        return create_response(data={'scraped': 0, 'generated': 0})

@app.route('/api/scheduler-info')
def api_scheduler_info():
    def get_scheduler_info():
        with open("scheduler_info.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    
    info = safe_file_operation(get_scheduler_info, {
        'is_running': False, 'last_run': None, 'next_run': None, 'interval_minutes': 180
            })
    
    return jsonify(info)

@app.route('/api/scheduler-toggle', methods=['POST'])
def api_scheduler_toggle():
    data = request.get_json()
    enable = data.get('enable', False)
    
    def save_scheduler_info():
        scheduler_info = {
            'is_running': enable,
            'last_updated': datetime.now().isoformat(),
            'interval_minutes': 180
        }
        with open("scheduler_info.json", 'w', encoding='utf-8') as f:
            json.dump(scheduler_info, f, ensure_ascii=False, indent=2)
        return True

    success = safe_file_operation(save_scheduler_info, False)
    
    return create_response(
        success=success,
        is_running=enable,
        message=f"스케줄러가 {'활성화' if enable else '비활성화'}되었습니다."
    )

@app.route('/api/manual-collection', methods=['POST'])
def api_manual_collection():
    """수동 스크래핑 실행 - 고급 다중 기술 스크래핑"""
    try:
        print("🚀 고급 스크래핑 시스템으로 콘텐츠 수집 시작...")
        
        # 고급 스크래퍼 임포트 및 실행
        from advanced_scraper import AdvancedScraper
        
        scraper = AdvancedScraper(use_selenium=False)
        results = scraper.scrape_all_targets()
        scraper.close()
        
        if 'error' in results:
            return create_response(
                success=False,
                error=f'고급 스크래핑 실패: {results["error"]}',
                new_count=0
            )
        
        total_found = results['total_found']
        total_new = results['total_new']
        target_results = results['target_results']
        
        # 성공 메시지 생성
        success_targets = [r for r in target_results if r['status'] == 'success']
        failed_targets = [r for r in target_results if r['status'] == 'failed']
        
        message_parts = [f'고급 스크래핑 완료: 총 {total_new}개 새 콘텐츠 수집 (전체 {total_found}개 발견)']
        
        if success_targets:
            message_parts.append(f'성공: {len(success_targets)}개 사이트')
            for target in success_targets:
                if target['new'] > 0:
                    message_parts.append(f"  • {target['target']}: {target['new']}개 새 콘텐츠")
        
        if failed_targets:
            message_parts.append(f'실패: {len(failed_targets)}개 사이트')
            for target in failed_targets:
                error_msg = target.get('error', '알 수 없는 오류')[:100]
                message_parts.append(f"  • {target['target']}: {error_msg}")
        
        message = '\n'.join(message_parts)
        
        return create_response(
            success=True,
            message=message,
            new_count=total_new,
            total_found=total_found,
            results=target_results
        )
        
    except ImportError as e:
        print(f"고급 스크래퍼 임포트 실패: {e}")
        return create_response(
            success=False,
            error=f'고급 스크래퍼 모듈을 찾을 수 없습니다: {str(e)}',
            new_count=0
        )
    except Exception as e:
        print(f"고급 스크래핑 오류: {e}")
        return create_response(
            success=False,
            error=f'고급 스크래핑 실행 중 오류: {str(e)}',
            new_count=0
        )

@app.route('/api/scraped-content-detailed')
def api_scraped_content_detailed():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    offset = (page - 1) * per_page
    
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(data={
                'content': [], 'has_next': False, 'has_prev': False,
                'page': 1, 'pages': 0, 'total': 0
            })
        
        cursor = conn.cursor()
        
        # 총 콘텐츠 수 확인
        cursor.execute("SELECT COUNT(*) FROM scraped_contents")
        total_result = cursor.fetchone()
        total = total_result[0] if total_result else 0
        
        # 콘텐츠 목록 조회 (간단한 쿼리로 변경)
        cursor.execute("""
            SELECT id, title, content, url, scraped_at
            FROM scraped_contents
            ORDER BY scraped_at DESC 
            LIMIT ? OFFSET ?
        """, (per_page + 1, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return create_response(data={
                'content': [], 'has_next': False, 'has_prev': False,
                'page': 1, 'pages': 0, 'total': 0
            })
        
        has_next = len(rows) > per_page
        if has_next:
            rows = rows[:-1]
        
        content_list = []
        for row in rows:
            # 데이터베이스 Row 객체에서 안전하게 값 추출
            row_id = row[0] if len(row) > 0 else 0
            title = row[1] if len(row) > 1 else 'No Title'
            content = row[2] if len(row) > 2 else ''
            url = row[3] if len(row) > 3 else ''
            scraped_at = row[4] if len(row) > 4 else ''
            
            # 요약 생성 (첫 200자)
            summary = content[:200] + '...' if content and len(content) > 200 else (content or '')
            
            content_list.append({
                'id': row_id,
                'title': title or 'No Title',
                'url': url or '',
                'source': 'Manual Collection',
                'summary': summary,
                'content_length': len(content) if content else 0,
                'created_at': scraped_at or ''
            })
            
        return create_response(data={
            'content': content_list,
            'has_next': has_next,
            'has_prev': page > 1,
            'page': page,
            'pages': (total + per_page - 1) // per_page if total > 0 else 0,
            'total': total
        })
    except Exception as e:
        print(f"스크래핑 콘텐츠 API 오류: {e}")
        return create_response(data={
            'content': [], 'has_next': False, 'has_prev': False,
            'page': 1, 'pages': 0, 'total': 0
        })

@app.route('/api/save-markdown', methods=['POST'])
def api_save_markdown():
    data = request.get_json()
    generated_id = data.get('generated_id')
    
    result = execute_db_query(
        "SELECT title, content, created_at FROM generated_contents WHERE id = ?",
        (generated_id,), fetch_one=True
    )
    
    if not result:
        return create_response(success=False, error='콘텐츠를 찾을 수 없습니다.')
        
    title = result['title'] if hasattr(result, 'keys') else result[0]
    content = result['content'] if hasattr(result, 'keys') else result[1]
    created_at = result['created_at'] if hasattr(result, 'keys') else result[2]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    filename = f"nongbu_{safe_title}_{timestamp}.md"
    
    markdown_content = f"""# {title}

**생성일시:** {created_at}
**AI 모델:** Claude 3.5 Sonnet

---

{content}

---

*본 콘텐츠는 NongBu Claude AI 시스템에 의해 자동 생성되었습니다.*
"""
    
    try:
        os.makedirs("saved_markdown", exist_ok=True)
        file_path = os.path.join("saved_markdown", filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return create_response(data={'filename': filename, 'file_path': file_path})
    except Exception as e:
        return create_response(success=False, error=f'마크다운 저장 실패: {str(e)}')

@app.route('/api/delete-all-scraped-content', methods=['POST'])
def api_delete_scraped_content():
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(success=False, error='데이터베이스 연결 실패')
        
        cursor = conn.cursor()
        
        # 삭제할 개수 확인
        cursor.execute("SELECT COUNT(*) FROM scraped_contents")
        count_result = cursor.fetchone()
        deleted_count = count_result[0] if count_result else 0
        
        # 삭제 실행
        cursor.execute("DELETE FROM scraped_contents")
        conn.commit()
        conn.close()
        
        return create_response(data={
            'deleted_count': deleted_count,
            'message': f'모든 수집된 콘텐츠 삭제 완료: {deleted_count}개'
        })
    except Exception as e:
        print(f"수집된 콘텐츠 삭제 오류: {e}")
        return create_response(success=False, error=f'삭제 실패: {str(e)}')

@app.route('/api/delete-all-generated-content', methods=['POST'])
def api_delete_generated_content():
    try:
        conn = get_db_connection()
        if not conn:
            return create_response(success=False, error='데이터베이스 연결 실패')
        
        cursor = conn.cursor()
        
        # 삭제할 개수 확인
        cursor.execute("SELECT COUNT(*) FROM generated_contents")
        count_result = cursor.fetchone()
        deleted_count = count_result[0] if count_result else 0
        
        # 삭제 실행
        cursor.execute("DELETE FROM generated_contents")
        conn.commit()
        conn.close()
        
        return create_response(data={
                'deleted_count': deleted_count,
                'message': f'모든 생성된 콘텐츠 삭제 완료: {deleted_count}개'
            })
    except Exception as e:
        print(f"생성된 콘텐츠 삭제 오류: {e}")
        return create_response(success=False, error=f'삭제 실패: {str(e)}')

def find_free_port(start_port=8001):
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            continue
    return start_port

def main():
    port = find_free_port(8001)
    print("🚀 NongBu Claude 4 Sonnet Pro 대시보드 시작")
    print(f"🌐 URL: http://localhost:{port}")
    print("🔑 고정 API 키로 자동 연결")
    print("💎 스케줄러 토글 및 무한 스크롤 지원")
    print(f"📡 스크래퍼 모듈: {'✅ 사용 가능' if SCRAPER_AVAILABLE else '❌ 사용 불가'}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == '__main__':
    main() 