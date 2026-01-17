# Token Score Frontend Design Document

## 1. Overview

This document outlines the frontend design for the Token Risk Scoring System. The frontend displays comprehensive token analysis data from the Nansen-powered backend API.

## 2. API Response Structure

The `/api/analyze` endpoint returns rich data that needs to be displayed:

```json
{
  "token_address": "0x...",
  "timestamp": "2025-01-16T...",
  "analysis_mode": "fast",
  "data_sources": {
    "eoa": "nansen",
    "holder": "nansen",
    "permission": "blockpi"
  },
  "overview": {
    "total_score": 75,
    "max_score": 100,
    "risk_level": "medium_risk",
    "risk_label": "Medium Risk",
    "risk_label_cn": "中等风险",
    "risk_color": "#eab308",
    "risk_bg_color": "#fef9c3"
  },
  "risk_tags": [
    {
      "key": "ORGANIC_GROWTH",
      "label": "Organic Growth",
      "label_cn": "真实用户增长",
      "type": "success",
      "category": "activity"
    }
  ],
  "scores": {
    "eoa": {
      "score": 40,
      "max_score": 40,
      "metrics": {
        "unique_eoa_count": 903,
        "total_addresses": 1000,
        "eoa_percentage": 90.3
      }
    },
    "holder": {
      "score": 30,
      "max_score": 30,
      "metrics": {
        "total_holders": 1000,
        "top10_percentage": 45.2,
        "top10_holders": [
          {
            "rank": 1,
            "address": "0x...",
            "address_short": "0x1234...abcd",
            "percentage": 12.5
          }
        ]
      }
    },
    "permission": {
      "score": 5,
      "max_score": 30,
      "metrics": {
        "has_owner": true,
        "owner_address": "0x...",
        "is_renounced": false,
        "is_multisig": false,
        "is_proxy": true,
        "dangerous_functions": [
          {"category": "MINTING", "signature": "mint(address,uint256)"}
        ],
        "risk_summary": ["Owner can mint tokens"]
      }
    }
  }
}
```

## 3. Component Architecture

```
App.tsx
├── Header
│   ├── Logo
│   └── ConnectWallet
├── Main Content
│   ├── TokenInput
│   ├── Loading State
│   ├── Error State
│   └── Results Section
│       ├── ScoreOverview (总分概览)
│       ├── RiskTags (风险标签)
│       ├── ScoreBreakdown (分项评分)
│       │   ├── EOAMetrics
│       │   ├── HolderMetrics
│       │   │   └── HolderTable (Top10 持有者)
│       │   └── PermissionMetrics
│       │       └── DangerousFunctions
│       └── SubmitScore
└── Footer
```

## 4. UI Design Specifications

### 4.1 Color Scheme (Monad Theme)

```css
/* Primary Colors */
--monad-purple: #836EF9
--monad-purple-light: #9D8BFA
--monad-purple-dark: #6B5BD4

/* Risk Level Colors */
--risk-low: #22c55e (green)
--risk-medium: #eab308 (yellow)
--risk-high: #f97316 (orange)
--risk-extreme: #ef4444 (red)

/* Tag Type Colors */
--tag-success: green (border + bg)
--tag-warning: yellow (border + bg)
--tag-danger: red (border + bg)
```

### 4.2 Score Overview Card

```
┌─────────────────────────────────────────────────────┐
│  综合评分                           风险等级        │
│  ┌───────────┐                    ┌──────────┐     │
│  │    75     │                    │ 中等风险  │     │
│  │   /100    │                    └──────────┘     │
│  └───────────┘                                     │
│  ████████████████████░░░░░░░░░░ 75%               │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐          │
│  │真实用户增长│ │持仓分散  │ │ 跑路风险  │          │
│  │  success │ │ success │ │  danger  │          │
│  └──────────┘ └──────────┘ └───────────┘          │
└─────────────────────────────────────────────────────┘
```

### 4.3 Score Breakdown Cards

#### 4.3.1 EOA Analysis Card
```
┌─────────────────────────────────────────────────────┐
│ 👤 用户活跃度                            40/40     │
│ ────────────────────────────────────────────────── │
│ 独立EOA分析，检测虚假活跃                          │
│                                                     │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│ │ 独立EOA数量  │ │ EOA占比     │ │ 分析地址数   │   │
│ │    903     │ │   90.3%    │ │   1,000    │   │
│ └─────────────┘ └─────────────┘ └─────────────┘   │
│                                                     │
│ 数据来源: Nansen                                   │
└─────────────────────────────────────────────────────┘
```

#### 4.3.2 Holder Distribution Card
```
┌─────────────────────────────────────────────────────┐
│ 📊 持仓分布                              30/30     │
│ ────────────────────────────────────────────────── │
│ Top持有者集中度分析，评估抛压风险                   │
│                                                     │
│ ┌─────────────┐ ┌─────────────┐                   │
│ │ 总持有者数   │ │ Top10占比   │                   │
│ │   1,000    │ │   45.2%    │                   │
│ └─────────────┘ └─────────────┘                   │
│                                                     │
│ Top 10 持有者:                                     │
│ ┌───┬────────────────┬───────────┬──────────────┐ │
│ │ # │ 地址           │ 占比      │ 标签         │ │
│ ├───┼────────────────┼───────────┼──────────────┤ │
│ │ 1 │ 0x1234...abcd  │ 12.50%   │ Smart Money  │ │
│ │ 2 │ 0x5678...efgh  │  8.30%   │              │ │
│ │...│ ...            │ ...      │ ...          │ │
│ └───┴────────────────┴───────────┴──────────────┘ │
│                                                     │
│ 数据来源: Nansen                                   │
└─────────────────────────────────────────────────────┘
```

#### 4.3.3 Contract Safety Card
```
┌─────────────────────────────────────────────────────┐
│ 🔒 合约安全                               5/30     │
│ ────────────────────────────────────────────────── │
│ 合约权限分析，检测Rug Pull风险                      │
│                                                     │
│ 状态检查:                                          │
│ ┌─────────────────────────────────────────────────┐│
│ │ ❌ 有Owner权限   Owner: 0x1234...abcd          ││
│ │ ❌ Owner未放弃   (Renounced: No)               ││
│ │ ❌ 非多签地址    (Multisig: No)                ││
│ │ ⚠️ 代理合约     (Proxy: Yes)                  ││
│ └─────────────────────────────────────────────────┘│
│                                                     │
│ 危险函数:                                          │
│ ┌───────────────────────────────────────────────┐ │
│ │ ⚠️ MINTING: mint(address,uint256)             │ │
│ │ ⚠️ BLACKLIST: blacklist(address)              │ │
│ │ ⚠️ PAUSING: pause()                           │ │
│ └───────────────────────────────────────────────┘ │
│                                                     │
│ 风险摘要:                                          │
│ • Owner can mint unlimited tokens                  │
│ • Contract can be paused by owner                  │
│                                                     │
│ 数据来源: BlockPi RPC                              │
└─────────────────────────────────────────────────────┘
```

## 5. Component Specifications

### 5.1 ScoreOverview Component

**Props:**
```typescript
interface ScoreOverviewProps {
  overview: {
    total_score: number
    max_score: number
    risk_level: string
    risk_label_cn: string
    risk_color: string
  }
  risk_tags: RiskTag[]
}
```

**Features:**
- Large score display with risk-based color
- Progress bar showing score percentage
- Risk level badge
- Risk tags as colored badges

### 5.2 RiskTags Component

**Props:**
```typescript
interface RiskTagsProps {
  tags: RiskTag[]
}
```

**Display Logic:**
- `type: "success"` → Green badge with checkmark
- `type: "warning"` → Yellow badge with warning icon
- `type: "danger"` → Red badge with X icon

### 5.3 ScoreCard Component (Reusable)

**Props:**
```typescript
interface ScoreCardProps {
  icon: string
  title: string
  description: string
  score: number
  maxScore: number
  riskLevel: string
  dataSource: string
  children: React.ReactNode // For metrics content
}
```

### 5.4 HolderTable Component

**Props:**
```typescript
interface HolderTableProps {
  holders: TopHolder[]
  totalHolders: number
  top10Percentage: number
}
```

**Features:**
- Sortable table
- Address truncation with copy button
- Link to block explorer
- Percentage bars
- Smart Money / Bot labels (from Nansen)

### 5.5 PermissionDetails Component

**Props:**
```typescript
interface PermissionDetailsProps {
  metrics: {
    has_owner: boolean
    owner_address: string | null
    is_renounced: boolean
    is_multisig: boolean
    is_proxy: boolean
    dangerous_functions: DangerousFunction[]
    risk_summary: string[]
  }
}
```

**Features:**
- Status indicators (checkmark/X icons)
- Dangerous functions list with categories
- Risk summary bullet points
- Owner address link (if exists)

## 6. Responsive Design

### Breakpoints:
- Mobile: < 640px (single column)
- Tablet: 640px - 1024px (2 columns)
- Desktop: > 1024px (3 columns for score cards)

### Mobile Adaptations:
- Collapsible score detail sections
- Horizontal scroll for holder table
- Stacked risk tags

## 7. Interactions

### 7.1 Loading States
- Skeleton loaders for each section
- Animated progress indicator
- Step-by-step progress: "Analyzing EOA..." → "Analyzing Holders..." → "Checking Permissions..."

### 7.2 Error Handling
- Per-section error states (allow partial results)
- Retry button for failed sections
- Clear error messages in Chinese

### 7.3 Animations
- Score counting animation (0 → final score)
- Progress bar fill animation
- Fade-in for result cards
- Risk tag appear animation (staggered)

## 8. Implementation Priority

### Phase 1 (Core Display)
1. Update TypeScript interfaces for full API response
2. Enhance ScoreDisplay with new overview layout
3. Add RiskTags component

### Phase 2 (Detailed Metrics)
4. Add EOA metrics display
5. Add HolderTable component
6. Add PermissionDetails component

### Phase 3 (Polish)
7. Add animations and transitions
8. Mobile responsive adjustments
9. Loading skeleton components

## 9. Files to Create/Modify

### New Files:
- `frontend/src/components/ScoreOverview.tsx`
- `frontend/src/components/RiskTags.tsx`
- `frontend/src/components/ScoreCard.tsx`
- `frontend/src/components/HolderTable.tsx`
- `frontend/src/components/PermissionDetails.tsx`
- `frontend/src/components/MetricItem.tsx`

### Modify:
- `frontend/src/App.tsx` - Update ScoreData interface
- `frontend/src/components/ScoreDisplay.tsx` - Restructure to use new components
- `frontend/src/index.css` - Add new utility classes

## 10. Sample Data for Testing

```typescript
const mockScoreData: ScoreData = {
  token_address: "0x754704bc059f8c67012fed69bc8a327a5aafb603",
  timestamp: "2025-01-16T12:00:00",
  analysis_mode: "fast",
  data_sources: {
    eoa: "nansen",
    holder: "nansen",
    permission: "blockpi"
  },
  overview: {
    total_score: 75,
    max_score: 100,
    risk_level: "medium_risk",
    risk_label: "Medium Risk",
    risk_label_cn: "中等风险",
    risk_color: "#eab308",
    risk_bg_color: "#fef9c3",
    risk_icon: "alert-triangle"
  },
  risk_tags: [
    { key: "ORGANIC_GROWTH", label: "Organic Growth", label_cn: "真实用户增长", type: "success", category: "activity" },
    { key: "DISTRIBUTED", label: "Well Distributed", label_cn: "持仓分散", type: "success", category: "holder" },
    { key: "RUG_RISK", label: "Rug Risk", label_cn: "跑路风险", type: "danger", category: "permission" }
  ],
  scores: {
    eoa: {
      name: "User Activity",
      name_cn: "用户活跃度",
      description: "Unique EOA analysis",
      description_cn: "独立EOA分析，检测虚假活跃",
      score: 40,
      max_score: 40,
      weight: "40%",
      risk_level: "low_risk",
      metrics: {
        unique_eoa_count: 903,
        total_addresses: 1000,
        eoa_percentage: 90.3,
        events_count: 1500
      }
    },
    holder: {
      name: "Holder Distribution",
      name_cn: "持仓分布",
      description: "Top holder concentration",
      description_cn: "Top持有者集中度分析",
      score: 30,
      max_score: 30,
      weight: "30%",
      risk_level: "low_risk",
      metrics: {
        total_holders: 1000,
        top10_percentage: 45.2,
        top10_holders: [
          { rank: 1, address: "0x1234567890abcdef", address_short: "0x1234...cdef", balance: 1000000, percentage: 12.5 },
          { rank: 2, address: "0xabcdef1234567890", address_short: "0xabcd...7890", balance: 800000, percentage: 10.0 }
        ]
      }
    },
    permission: {
      name: "Contract Safety",
      name_cn: "合约安全",
      description: "Permission analysis",
      description_cn: "合约权限分析",
      score: 5,
      max_score: 30,
      weight: "30%",
      risk_level: "high_risk",
      metrics: {
        has_owner: true,
        owner_address: "0x1234567890abcdef1234567890abcdef12345678",
        is_renounced: false,
        is_multisig: false,
        is_proxy: true,
        dangerous_functions: [
          { category: "MINTING", signature: "mint(address,uint256)" },
          { category: "BLACKLIST", signature: "blacklist(address)" }
        ],
        risk_summary: [
          "Owner can mint unlimited tokens",
          "Owner can blacklist addresses"
        ]
      }
    }
  },
  submit_data: {
    target: "0x754704bc059f8c67012fed69bc8a327a5aafb603",
    totalScore: 75,
    eoaScore: 40,
    holderScore: 30,
    permissionScore: 5,
    riskLevel: 1
  }
}
```
