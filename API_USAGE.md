# Monad Contract Analyzer - HTTP API 使用文档

## 概述

这是一个 HTTP API 服务，用于分析 Monad 链上合约的交互形态。通过 API 密钥认证，外部用户可以提交合约地址进行分析。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并配置以下参数：

```bash
# Nansen API Key（必需）
NANSEN_API_KEY=your_nansen_api_key

# API 服务密钥（必需）
API_KEY=monad_analyzer_2026_secret_key_xyz789

# 服务器配置（可选）
PORT=5000
HOST=0.0.0.0
DEBUG=False
```

### 3. 启动服务

```bash
python api_server.py
```

服务将在 `http://0.0.0.0:5000` 启动。

## API 接口文档

### 基础信息

- **Base URL**: `http://localhost:5000`
- **认证方式**: HTTP Header `X-API-Key`
- **Content-Type**: `application/json`

### 接口列表

#### 1. 健康检查

**接口**: `GET /health`

**描述**: 检查服务是否正常运行

**认证**: 不需要

**示例**:

```bash
curl http://localhost:5000/health
```

**响应**:

```json
{
  "status": "healthy",
  "service": "Monad Contract Analyzer API"
}
```

---

#### 2. API 文档

**接口**: `GET /`

**描述**: 获取 API 使用文档

**认证**: 不需要

**示例**:

```bash
curl http://localhost:5000/
```

---

#### 3. 分析合约 (主要接口)

**接口**: `POST /api/analyze`

**描述**: 分析指定合约的交互形态

**认证**: 需要 API Key

**请求头**:

```
Content-Type: application/json
X-API-Key: your_api_key_here
```

**请求体**:

```json
{
  "contract_address": "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A",
  "limit": 500,
  "fetch_all": false
}
```

**参数说明**:

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| contract_address | string | 是 | - | 要分析的合约地址（必须以 0x 开头，42位） |
| limit | integer | 否 | 500 | 分析的地址数量上限 |
| fetch_all | boolean | 否 | false | 是否获取所有持有者（忽略 limit） |

**示例请求**:

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -H "X-API-Key: monad_analyzer_2026_secret_key_xyz789" \
  -d '{
    "contract_address": "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A",
    "limit": 500
  }'
```

**成功响应** (200):

```json
{
  "success": true,
  "data": {
    "token_address": "0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A",
    "health_score": 75,
    "total_addresses": 500,
    "total_interaction_volume": 1234567.89,
    "shape": "CONCENTRATED",
    "shape_description": "集中型（少数地址主导）",
    "risk_level": "MEDIUM",
    "concentration": {
      "top_1_percent": 15.5,
      "top_10_percent": 65.2
    },
    "bot_analysis": {
      "warning_level": "BOT_ACTIVE",
      "warning_description": "Bot 活跃",
      "bot_count_ratio": 12.5,
      "bot_volume_ratio": 25.3
    },
    "address_distribution": {
      "bot": 62,
      "dex": 15,
      "cex": 3,
      "smart_money": 45,
      "contract": 8,
      "eoa": 367
    },
    "eoa_ratio": 73.4,
    "top_interactors": [
      {
        "address": "0x1234...",
        "label": "Smart Trader",
        "balance": 100000.0,
        "total_interaction": 50000.0,
        "inflow": 30000.0,
        "outflow": 20000.0
      }
    ]
  },
  "report": "格式化的文本报告..."
}
```

**错误响应**:

**401 Unauthorized** - 缺少 API Key:

```json
{
  "success": false,
  "error": "Missing API Key",
  "message": "Please provide X-API-Key in request headers"
}
```

**403 Forbidden** - API Key 无效:

```json
{
  "success": false,
  "error": "Invalid API Key",
  "message": "The provided API key is not valid"
}
```

**400 Bad Request** - 缺少参数:

```json
{
  "success": false,
  "error": "Missing Parameter",
  "message": "contract_address is required"
}
```

**400 Bad Request** - 地址格式错误:

```json
{
  "success": false,
  "error": "Invalid Address",
  "message": "contract_address must be a valid Ethereum address (0x...)"
}
```

**500 Internal Server Error** - 分析失败:

```json
{
  "success": false,
  "error": "Analysis Failed",
  "message": "Failed to analyze contract. Please check the address and try again."
}
```

## 返回数据说明

### health_score (健康度评分)

- **范围**: 0-100
- **说明**: 综合评分，考虑集中度、Bot活动、EOA用户占比等因素
- **评分标准**:
  - 90-100: 非常健康
  - 75-89: 较健康
  - 60-74: 一般
  - 40-59: 需要注意
  - 0-39: 高风险

### shape (交互形态)

- `DISTRIBUTED`: 分散型（多地址低频）- 健康
- `MODERATE`: 适中（混合型）
- `CONCENTRATED`: 集中型（少数地址主导）
- `HIGHLY_CONCENTRATED`: 极度集中（少数地址高频）- 风险高

### risk_level (风险等级)

- `HEALTHY`: 健康
- `LOW`: 低风险
- `MEDIUM`: 中等风险
- `HIGH`: 高风险

### bot_warning (Bot 警告等级)

- `ORGANIC`: 有机交互（Bot 活动少）
- `BOT_ACTIVE`: Bot 活跃
- `BOT_DOMINATED`: Bot 主导（可能是刷量）

### address_distribution (地址分布)

统计各类型地址的数量：

- `bot`: Bot 地址
- `dex`: DEX/交易池地址
- `cex`: 中心化交易所地址
- `smart_money`: 聪明钱/专业交易者
- `contract`: 合约地址
- `eoa`: 普通用户地址（无标签 EOA）

## 使用场景示例

### Python 示例

```python
import requests

API_URL = "http://localhost:5000/api/analyze"
API_KEY = "monad_analyzer_2026_secret_key_xyz789"

def analyze_contract(contract_address):
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }

    payload = {
        "contract_address": contract_address,
        "limit": 500
    }

    response = requests.post(API_URL, json=payload, headers=headers)

    if response.status_code == 200:
        result = response.json()
        print(f"Health Score: {result['data']['health_score']}")
        print(f"Shape: {result['data']['shape_description']}")
        print(f"Risk Level: {result['data']['risk_level']}")
        return result
    else:
        print(f"Error: {response.json()}")
        return None

# 使用示例
result = analyze_contract("0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A")
```

### JavaScript 示例

```javascript
const API_URL = "http://localhost:5000/api/analyze";
const API_KEY = "monad_analyzer_2026_secret_key_xyz789";

async function analyzeContract(contractAddress) {
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify({
      contract_address: contractAddress,
      limit: 500
    })
  });

  const result = await response.json();

  if (result.success) {
    console.log(`Health Score: ${result.data.health_score}`);
    console.log(`Shape: ${result.data.shape_description}`);
    console.log(`Risk Level: ${result.data.risk_level}`);
    return result;
  } else {
    console.error(`Error: ${result.message}`);
    return null;
  }
}

// 使用示例
analyzeContract("0x3bd359C1119dA7Da1D913D1C4D2B7c461115433A");
```

## 部署建议

### 生产环境部署

1. **使用强密码**:
   ```bash
   # 生成随机 API Key
   openssl rand -hex 32
   ```

2. **使用 HTTPS**:
   - 配置反向代理（Nginx）
   - 使用 SSL 证书（Let's Encrypt）

3. **使用 Gunicorn**:
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 api_server:app
   ```

4. **配置防火墙**:
   ```bash
   # 仅允许特定 IP 访问
   sudo ufw allow from <trusted_ip> to any port 5000
   ```

5. **添加速率限制**:
   - 使用 Flask-Limiter
   - 配置 Nginx 限流

### Docker 部署

创建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "api_server.py"]
```

运行:

```bash
docker build -t monad-analyzer .
docker run -p 5000:5000 --env-file .env monad-analyzer
```

## 安全注意事项

1. **保护 API Key**: 不要将 `.env` 文件提交到版本控制
2. **使用 HTTPS**: 生产环境必须使用 HTTPS
3. **IP 白名单**: 限制可访问的 IP 地址
4. **速率限制**: 防止 API 滥用
5. **日志记录**: 记录所有 API 请求用于审计

## 常见问题

### Q: 如何更改 API Key?

A: 编辑 `.env` 文件中的 `API_KEY` 参数，然后重启服务。

### Q: 服务启动失败怎么办?

A: 检查：
1. `NANSEN_API_KEY` 是否已配置
2. 端口 5000 是否被占用
3. 依赖是否正确安装

### Q: 如何增加分析的地址数量?

A: 请求时设置更大的 `limit` 值，或将 `fetch_all` 设为 `true`。

### Q: API 返回 500 错误?

A: 检查：
1. 合约地址是否正确
2. Nansen API Key 是否有效
3. 网络连接是否正常

## 技术支持

如有问题，请查看：
- [README.md](README.md) - 项目概述
- [USAGE.md](USAGE.md) - 命令行工具使用说明
