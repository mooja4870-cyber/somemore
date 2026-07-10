# 🦉 SOMEMORE 공공데이터 자동 동기화 기술 설계서

**작성일**: 2026-06-05  
**목적**: 정부 기준 데이터를 매월/분기/연 자동 업데이트 → DAU 증대 + 신뢰도 강화  
**핵심**: "일회성 앱" → "지속적 재방문 앱" 전환

---

## 1️⃣ 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                    공공데이터 소스 (정부 API)                  │
│  (통계청, 한국은행, 국민연금공단, 한국감정평가협회 등)          │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
        ┌───────────────────────────────────────┐
        │     데이터 수집 서버 (백엔드)           │
        │  • 월 1일 자동 수집 (Cron job)        │
        │  • 데이터 파싱 & 검증                  │
        │  • 버전 관리 (히스토리 저장)           │
        └────────────┬────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   ┌────────────┐         ┌─────────────┐
   │  데이터    │         │ 사용자      │
   │  DB        │         │ 알림        │
   │ (버전별    │         │ 시스템      │
   │  저장)     │         │ (Push)      │
   └────────────┘         └─────────────┘
        │                        │
        └────────────┬───────────┘
                     ▼
        ┌───────────────────────────────────┐
        │   SOMEMORE 앱 (프론트엔드)         │
        │  • 최신 데이터 자동 로드            │
        │  • "데이터 업데이트됨" 알림 표시    │
        │  • 과거 버전 비교 기능              │
        └───────────────────────────────────┘
```

---

## 2️⃣ 수집 대상 & 데이터 소스

### **A. 월 1회 업데이트**

| # | 데이터 | 제공처 | API/방식 | 범위 | 사용 목적 |
|---|--------|--------|---------|------|----------|
| 1 | 소비자물가지수 | 통계청 | KOSIS API | 전국 | 물가상승률 (inflation) |
| 2 | 기준금리 | 한국은행 | 보도자료/크롤링 | - | 현금 수익률 (cashReturn) 참고 |
| 3 | 아파트 매매가격지수 | 한국감정평가협회 | 월간 발표 | 전국 | 부동산 상승률 (reGrowth) 참고 |

### **B. 분기 1회 (매년 3·6·9·12월)**

| # | 데이터 | 제공처 | 방식 | 사용 목적 |
|----|--------|--------|------|----------|
| 1 | 국민연금 인상률 | 국민연금공단 | 공식 공고 | "국민연금" 소득 항목 인상 |
| 2 | 고용통계 | 통계청 | 월간 발표 | 근로소득 평균 수익률 참고 |

### **C. 연 1회 (12월)**

| # | 데이터 | 제공처 | 방식 | 사용 목적 |
|----|--------|--------|------|----------|
| 1 | 생명표 (기대수명) | 통계청 | 연간 발표 | 시뮬레이션 기준 나이 범위 업데이트 |

---

## 3️⃣ 기술 스택 & 구현

### **백엔드**

```yaml
언어: Python 3.10+
프레임워크: FastAPI / Django
데이터베이스: PostgreSQL (+ Redis 캐시)
스케줄: APScheduler / Celery
알림: Firebase Cloud Messaging (FCM)

디렉토리 구조:
├── app/
│   ├── api/
│   │   └── public_data.py          # 공공데이터 API 엔드포인트
│   ├── services/
│   │   ├── data_collector.py       # 데이터 수집 (통계청, 한은 등)
│   │   ├── data_validator.py       # 데이터 검증
│   │   └── notification.py         # FCM 알림 발송
│   ├── models/
│   │   ├── public_data.py          # DB 모델
│   │   └── data_version.py         # 버전 관리 모델
│   └── tasks/
│       └── scheduled_tasks.py       # Cron job 정의
├── tests/
│   └── test_data_sync.py
└── config.py                        # 설정 (API 키 등)
```

---

## 4️⃣ 데이터 수집 흐름 (상세)

### **Step 1: 통계청 KOSIS API에서 물가지수 수집**

```python
# app/services/data_collector.py

import requests
from datetime import datetime
from models.public_data import InflationData

class StatisticsKoreaCollector:
    """통계청 KOSIS API 클라이언트"""
    
    KOSIS_API_KEY = os.getenv("KOSIS_API_KEY")
    KOSIS_API_URL = "https://kosis.kr/api/rest/data"
    
    def fetch_inflation_rate(self):
        """
        최신 소비자물가지수 수집
        - API: KOSIS 통계청
        - 주기: 매월 6일경 발표
        """
        params = {
            'orgId': 'stat',
            'statCode': '114Y001',  # 소비자물가지수 코드
            'itemCode': 'ALL',      # 전체 품목
            'prdSe': 'M',           # 월별
            'startPrdDe': '202606', # YYYYMM
            'endPrdDe': datetime.now().strftime('%Y%m'),
            'apiKey': self.KOSIS_API_KEY
        }
        
        try:
            response = requests.get(self.KOSIS_API_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # 최신 월 데이터 추출
            latest_record = data['result']['data'][0]
            current_month = latest_record['PRD_DE']  # YYYYMM
            cpi_index = float(latest_record['DT_1'])  # 지수값
            
            # YoY 상승률 계산 (작년 같은 달 대비)
            yoy_rate = self._calculate_yoy_rate(cpi_index, current_month)
            
            return {
                'date': current_month,
                'cpi_index': cpi_index,
                'yoy_rate': yoy_rate,  # 예: 2.8
                'source': 'statistics_korea',
                'fetched_at': datetime.now()
            }
        except Exception as e:
            self._log_error(f"KOSIS API 오류: {e}")
            return None
    
    def _calculate_yoy_rate(self, current_cpi, current_month):
        """작년 같은 달 대비 % 계산"""
        # DB에서 작년 같은 달 CPI 조회 후 계산
        # (상세 구현 생략)
        pass
```

### **Step 2: 데이터 검증 & DB 저장**

```python
# app/services/data_validator.py

class DataValidator:
    """수집된 데이터 검증"""
    
    @staticmethod
    def validate_inflation(data):
        """물가지수 데이터 검증"""
        assert 0 <= data['yoy_rate'] <= 10, "물가상승률이 범위 초과"
        assert data['cpi_index'] > 0, "CPI 지수값 오류"
        return True
    
    @staticmethod
    def validate_pension_rate(data):
        """국민연금 인상률 검증"""
        assert 0 <= data['rate'] <= 10, "연금 인상률 범위 초과"
        return True

# app/services/data_collector.py에서 호출

from models.public_data import InflationData

def save_inflation_data(data):
    """데이터베이스에 저장 (버전 관리)"""
    if not DataValidator.validate_inflation(data):
        raise ValueError("데이터 검증 실패")
    
    # 기존 최신 버전이 있으면 'latest=False'로 설정
    InflationData.objects.filter(latest=True).update(latest=False)
    
    # 새 버전 저장
    inflation_record = InflationData(
        yoy_rate=data['yoy_rate'],
        cpi_index=data['cpi_index'],
        effective_date=data['date'],
        source='statistics_korea',
        latest=True,
        version_number=get_next_version()
    )
    inflation_record.save()
    
    return inflation_record.version_number
```

### **Step 3: 사용자에게 알림 발송**

```python
# app/services/notification.py

from firebase_admin import messaging

class NotificationService:
    """FCM을 통한 푸시 알림"""
    
    @staticmethod
    def notify_inflation_update(new_rate, previous_rate, user_tokens):
        """물가 업데이트 알림"""
        title = "📢 물가지수가 업데이트됐어요!"
        body = f"{previous_rate}% → {new_rate}% (매월 기준 상승률)"
        
        data = {
            'notification_type': 'inflation_update',
            'new_rate': str(new_rate),
            'action': 'open_simulator'  # 클릭 시 시뮬레이터로 이동
        }
        
        # 다중 발송 (배치)
        multicast_message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            tokens=user_tokens  # 모든 사용자 토큰 배열
        )
        
        response = messaging.send_multicast(multicast_message)
        return response
    
    @staticmethod
    def notify_pension_rate_update(new_rate, pension_type, user_tokens):
        """국민연금 인상률 알림"""
        title = "📢 2026년 국민연금 인상률이 확정됐어요!"
        body = f"연금이 {new_rate}% 인상됩니다"
        
        # 마찬가지로 FCM 발송
        pass
```

---

## 5️⃣ Cron Job 스케줄 정의

```python
# app/tasks/scheduled_tasks.py

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

def setup_scheduler():
    """모든 정기 작업 스케줄 설정"""
    scheduler = BackgroundScheduler()
    
    # 매월 1일 10:00 (통계청 물가지수 발표 확인 후 수집)
    scheduler.add_job(
        func=collect_inflation_data_task,
        trigger="cron",
        day=1,
        hour=10,
        minute=0,
        id='monthly_inflation_sync',
        name='월 물가지수 동기화'
    )
    
    # 매월 10일 (기준금리, 부동산지수 수집)
    scheduler.add_job(
        func=collect_market_rates_task,
        trigger="cron",
        day=10,
        hour=11,
        id='monthly_market_rates_sync'
    )
    
    # 매년 12월 15일 (국민연금 인상률 발표 후)
    scheduler.add_job(
        func=collect_pension_rate_task,
        trigger="cron",
        month=12,
        day=15,
        hour=14,
        id='annual_pension_rate_sync'
    )
    
    # 매년 2월 (통계청 생명표 발표 후)
    scheduler.add_job(
        func=collect_life_table_task,
        trigger="cron",
        month=2,
        day=28,
        hour=15,
        id='annual_life_table_sync'
    )
    
    scheduler.start()
    return scheduler

# 각 작업 함수
async def collect_inflation_data_task():
    """월 물가지수 수집 작업"""
    collector = StatisticsKoreaCollector()
    data = collector.fetch_inflation_rate()
    
    if data:
        version = save_inflation_data(data)
        
        # 모든 사용자에게 알림
        all_user_tokens = get_all_fcm_tokens()
        NotificationService.notify_inflation_update(
            new_rate=data['yoy_rate'],
            previous_rate=get_previous_inflation_rate(),
            user_tokens=all_user_tokens
        )
        
        log(f"물가지수 업데이트 완료: v{version}")
    else:
        log("물가지수 수집 실패 (재시도 예정)")
```

---

## 6️⃣ 프론트엔드 연동

### **A. 시뮬레이터 로드 시 최신 데이터 자동 적용**

```javascript
// sim_v8.html 초기화 로직

async function bootstrap() {
  // 1. 서버에서 최신 공공데이터 조회
  const latestData = await fetch('/api/public-data/latest').then(r => r.json());
  
  // 2. 기본값 업데이트
  state.inflation = latestData.inflation_rate;      // 2.8
  state.reGrowth = latestData.realEstate_growth;    // 1.8
  state.cashReturn = latestData.interest_rate;      // 3.2
  
  // 3. 데이터 버전 정보 표시
  state.dataVersion = latestData.version;
  state.dataLastUpdated = latestData.updated_at;
  
  renderLevel1();
}
```

### **B. "데이터 업데이트됨" 배너 표시**

```html
<!-- 페이지 상단에 배너 -->
<div id="dataUpdateBanner" style="display: none;">
  <div class="banner-content">
    <span class="banner-icon">📢</span>
    <span class="banner-text">
      최신 통계청 물가지수 반영됨 (2.8% → 2.9%) 
      <a href="#" onclick="location.reload()">지금 다시 계산하기</a>
    </span>
  </div>
</div>

<script>
// 알림 수신 (Firebase Cloud Messaging)
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.ready.then(registration => {
    messaging.onMessage((payload) => {
      if (payload.data.notification_type === 'inflation_update') {
        showDataUpdateBanner(payload.data);
      }
    });
  });
}

function showDataUpdateBanner(data) {
  const banner = document.getElementById('dataUpdateBanner');
  banner.innerHTML = `
    <div class="banner-content">
      <span class="banner-icon">📢</span>
      <span class="banner-text">
        물가지수가 업데이트됐어요! 
        시뮬레이션이 자동으로 재계산되었습니다.
      </span>
      <button onclick="location.reload()" style="margin-left: 10px;">확인</button>
    </div>
  `;
  banner.style.display = 'block';
}
</script>
```

### **C. 버전 비교 기능**

```javascript
// 결과 화면에 "데이터 버전 비교" 섹션 추가

async function showVersionHistory() {
  const history = await fetch('/api/public-data/history').then(r => r.json());
  
  // history = [
  //   { date: '2026-06-01', inflation: 2.8, version: 'v5' },
  //   { date: '2026-05-01', inflation: 2.7, version: 'v4' },
  //   { date: '2026-04-01', inflation: 2.6, version: 'v3' },
  // ]
  
  const html = `
    <div class="data-version-comparison">
      <h3>📊 데이터 버전별 시뮬레이션 비교</h3>
      <table>
        <tr>
          <th>버전</th>
          <th>발효일</th>
          <th>물가상승률</th>
          <th>90세 예상자산</th>
          <th>변화</th>
        </tr>
        ${history.map((v, i) => `
          <tr>
            <td>${v.version}</td>
            <td>${v.date}</td>
            <td>${v.inflation}%</td>
            <td>${v.projected_asset}억</td>
            <td>${i > 0 ? `${(v.projected_asset - history[i-1].projected_asset) > 0 ? '+' : ''}${(v.projected_asset - history[i-1].projected_asset) * 10}만원` : '-'}</td>
          </tr>
        `).join('')}
      </table>
    </div>
  `;
  
  return html;
}
```

---

## 7️⃣ 데이터베이스 스키마

```sql
-- 공공데이터 버전 관리
CREATE TABLE public_data_versions (
  id SERIAL PRIMARY KEY,
  version_number VARCHAR(10) UNIQUE,  -- v1, v2, v3...
  created_at TIMESTAMP DEFAULT NOW(),
  note TEXT  -- "2026년 6월 물가지수 반영"
);

-- 물가 데이터
CREATE TABLE inflation_data (
  id SERIAL PRIMARY KEY,
  version_id INT REFERENCES public_data_versions(id),
  yoy_rate DECIMAL(5, 2),      -- 2.8
  mom_rate DECIMAL(5, 2),      -- 월전월비
  cpi_index DECIMAL(7, 2),
  effective_date VARCHAR(6),   -- YYYYMM
  source VARCHAR(50),          -- 'statistics_korea'
  latest BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 국민연금 데이터
CREATE TABLE pension_rate_data (
  id SERIAL PRIMARY KEY,
  version_id INT REFERENCES public_data_versions(id),
  rate DECIMAL(5, 2),          -- 3.2
  effective_year INT,          -- 2026
  source VARCHAR(50),          -- 'national_pension_service'
  latest BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 부동산 가격지수
CREATE TABLE realEstate_index_data (
  id SERIAL PRIMARY KEY,
  version_id INT REFERENCES public_data_versions(id),
  yoy_growth_rate DECIMAL(5, 2),
  apartment_index DECIMAL(7, 2),
  effective_date VARCHAR(6),
  source VARCHAR(50),
  latest BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- 생명표
CREATE TABLE life_table_data (
  id SERIAL PRIMARY KEY,
  version_id INT REFERENCES public_data_versions(id),
  gender VARCHAR(10),          -- 'male', 'female'
  age INT,
  life_expectancy DECIMAL(4, 1),
  effective_year INT,
  source VARCHAR(50),          -- 'statistics_korea'
  latest BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- FCM 토큰 (알림 발송용)
CREATE TABLE user_fcm_tokens (
  id SERIAL PRIMARY KEY,
  user_id INT,
  fcm_token TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  last_used TIMESTAMP
);
```

---

## 8️⃣ API 엔드포인트

```
GET /api/public-data/latest
  → 최신 공공데이터 반환
  응답: { inflation_rate: 2.8, realEstate_growth: 1.8, ... }

GET /api/public-data/history
  → 버전별 데이터 히스토리 반환
  응답: [ {version: 'v5', date: '2026-06-01', ...}, ... ]

POST /api/fcm-token
  → 사용자 FCM 토큰 등록 (알림 수신 동의)
  요청: { token: "엄청_긴_FCM_토큰..." }

GET /api/public-data/sources
  → 모든 데이터 소스 및 마지막 업데이트 날짜
  응답: { inflation: {source: '통계청', last_updated: '2026-06-01', ...}, ... }
```

---

## 9️⃣ 구현 로드맵

### **Phase 1 (6주) — MVP (물가지수만)**

- [ ] 통계청 KOSIS API 연동
- [ ] 월 1일 자동 수집 Cron job
- [ ] DB 스키마 구축
- [ ] FCM 알림 시스템
- [ ] 프론트엔드: 최신 물가 자동 적용
- [ ] "데이터 업데이트됨" 배너

**예상 개발 시간**: 3~4주  
**테스트**: Mock 데이터로 Cron 작동 확인

### **Phase 2 (6주) — 확대 (국민연금, 부동산)**

- [ ] 국민연금공단 API 연동
- [ ] 한국감정평가협회 부동산지수 연동
- [ ] 버전별 비교 기능 UI
- [ ] 사용자 선호 데이터 소스 선택 기능

**예상 개발 시간**: 2~3주

### **Phase 3 (4주) — 고도화**

- [ ] 생명표 자동 업데이트
- [ ] 사용자 개인 알림 설정 (opt-in/opt-out)
- [ ] 데이터 업데이트 히스토리 그래프
- [ ] Analytics: 사용자가 "어떤 데이터 업데이트"로 재방문하는지 추적

**예상 개발 시간**: 2~3주

---

## 🔟 비용 추정

| 항목 | 월 비용 |
|------|--------|
| **API 비용** | - |
| 통계청 KOSIS API | 무료 (공공데이터) |
| 국민연금공단 | 무료 (공공 웹사이트) |
| 한국은행 | 무료 (공공데이터) |
| **인프라** | ~50~80만원 |
| AWS EC2 (Cron + 데이터 수집) | 3~5만원 |
| RDS PostgreSQL | 15~20만원 |
| Firebase (FCM 알림) | 무료~5만원 |
| **인건비** | ~3,000만원 (일회성) |
| 백엔드 개발 (4주) | ~2,000만원 |
| 프론트엔드 연동 (2주) | ~1,000만원 |

**총 초기 투자**: ~3,000만원  
**월간 운영 비용**: ~50~80만원

---

## 1️⃣1️⃣ 성과 지표 (KPI)

| KPI | 목표 | 측정 방법 |
|-----|------|---------|
| **DAU (일일활성사용자)** | 현 100 → 월말 500 | Google Analytics |
| **월간 재방문율** | 10% → 25% | Session tracking |
| **구독 전환율** | - → 5~10% | Revenue tracking |
| **데이터 업데이트 클릭율** | - → 30% | 배너 클릭 추적 |
| **푸시 알림 열람율** | - → 40% | FCM analytics |

---

## 1️⃣2️⃣ 위험 및 대응

| 위험 | 영향 | 대응 |
|------|------|------|
| **API 정책 변경** | 데이터 수집 불가 | 공공데이터 포탈 모니터링, 대체 API 준비 |
| **데이터 지연** | "업데이트됨" 알림 후 실제 미반영 | 데이터 유효성 검증, 재시도 로직 |
| **FCM 전달율 저하** | 사용자 알림 못 받음 | Firebase 대시보드 모니터링, 재발송 옵션 |
| **앱 성능 저하** | 데이터 로드 시간 증가 | 버전 데이터 캐싱, CDN 활용 |

---

## 결론

**이 설계의 핵심 가치:**

1. **"일회성" → "지속적" 전환**: 월 1회 이상 자동 업데이트 → 사용자 재방문 유도
2. **신뢰도 극대화**: "정부 최신 기준으로 매달 재계산합니다" → 경쟁사 대비 차별화
3. **수익화 기반 구축**: DAU ↑ → 구독, 프리미엄, 광고 모두 가능

**"한 번만 쓰는 앱" → "매달 들어오는 서비스"로 거듭나기**

---

**작성자**: Claude Opus 4.8  
**최종 업데이트**: 2026-06-05 09:12:12
