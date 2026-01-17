import type { ScoreData, RiskTag, TopHolder, DangerousFunction } from '../App'

interface Props {
  data: ScoreData
}

const riskConfig: Record<string, { color: string; bg: string; label: string }> = {
  low_risk: { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30', label: '低风险' },
  medium_risk: { color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/30', label: '中等风险' },
  high_risk: { color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30', label: '高风险' },
  extreme_risk: { color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/30', label: '极高风险' },
}

const tagTypeConfig: Record<string, { color: string; bg: string; icon: string }> = {
  success: { color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/30', icon: '✓' },
  warning: { color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/30', icon: '!' },
  danger: { color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/30', icon: '✕' },
}

export default function ScoreDisplay({ data }: Props) {
  const { overview, scores, risk_tags } = data
  const risk = riskConfig[overview.risk_level] || { color: 'text-gray-400', bg: 'bg-gray-800 border-gray-600', label: '未知' }

  return (
    <div className="space-y-6">
      {/* 总分概览卡片 */}
      <div className="card-monad">
        <div className={`p-6 rounded-xl border ${risk.bg} mb-6`}>
          <div className="flex justify-between items-center">
            <div>
              <p className="text-gray-500 text-sm mb-1">综合评分</p>
              <div className="flex items-baseline gap-1">
                <span className={`text-5xl font-bold ${risk.color}`}>
                  {Math.round(overview.total_score)}
                </span>
                <span className="text-xl text-gray-600">/100</span>
              </div>
            </div>
            <div className="text-right">
              <p className="text-gray-500 text-sm mb-1">风险等级</p>
              <p className={`text-2xl font-bold ${risk.color}`}>
                {overview.risk_label_cn || risk.label}
              </p>
            </div>
          </div>

          {/* 总分进度条 */}
          <div className="mt-4 h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full progress-monad rounded-full transition-all duration-500"
              style={{ width: `${overview.total_score}%` }}
            />
          </div>
        </div>

        {/* 风险标签 */}
        {risk_tags && risk_tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            {risk_tags.map((tag) => (
              <RiskTagBadge key={tag.key} tag={tag} />
            ))}
          </div>
        )}

        {/* 分项评分概览 */}
        <div className="grid grid-cols-3 gap-4">
          <ScoreItem
            label={scores.eoa.name_cn || "用户活跃度"}
            score={scores.eoa.score}
            maxScore={scores.eoa.max_score}
            icon="👤"
            riskLevel={scores.eoa.risk_level}
          />
          <ScoreItem
            label={scores.holder.name_cn || "持仓分布"}
            score={scores.holder.score}
            maxScore={scores.holder.max_score}
            icon="📊"
            riskLevel={scores.holder.risk_level}
          />
          <ScoreItem
            label={scores.permission.name_cn || "合约安全"}
            score={scores.permission.score}
            maxScore={scores.permission.max_score}
            icon="🔒"
            riskLevel={scores.permission.risk_level}
          />
        </div>

        {/* 代币地址 */}
        <div className="mt-6 pt-4 border-t border-gray-800">
          <p className="text-sm text-gray-500">
            代币地址:
            <a
              href={`https://monad.socialscan.io/token/${data.token_address}`}
              target="_blank"
              rel="noopener noreferrer"
              className="ml-2 text-[#836EF9] hover:underline font-mono"
            >
              {data.token_address.slice(0, 10)}...{data.token_address.slice(-8)}
            </a>
          </p>
        </div>
      </div>

      {/* EOA 分析详情 */}
      <EOADetails scores={scores.eoa} dataSource={data.data_sources?.eoa} />

      {/* 持仓分布详情 */}
      <HolderDetails scores={scores.holder} dataSource={data.data_sources?.holder} />

      {/* 合约权限详情 */}
      <PermissionDetails scores={scores.permission} dataSource={data.data_sources?.permission} />
    </div>
  )
}

// 风险标签组件
function RiskTagBadge({ tag }: { tag: RiskTag }) {
  const config = tagTypeConfig[tag.type] || tagTypeConfig.warning
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border ${config.bg} ${config.color}`}>
      <span className="text-xs">{config.icon}</span>
      {tag.label_cn || tag.label}
    </span>
  )
}

// 分数项组件
function ScoreItem({ label, score, maxScore, icon, riskLevel }: {
  label: string;
  score: number;
  maxScore: number;
  icon: string;
  riskLevel?: string;
}) {
  const percentage = (score / maxScore) * 100
  const levelConfig = riskConfig[riskLevel || ''] || { color: 'text-white' }

  return (
    <div className="bg-[#1a1a1a] rounded-xl p-4 border border-gray-800/50">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <p className="text-sm text-gray-400">{label}</p>
      </div>
      <p className={`text-2xl font-bold mb-2 ${levelConfig.color}`}>
        {Math.round(score)}
        <span className="text-sm text-gray-500 font-normal">/{maxScore}</span>
      </p>
      <div className="h-1.5 bg-gray-800 rounded-full overflow-hidden">
        <div
          className="h-full progress-monad rounded-full transition-all duration-500"
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

// EOA 分析详情组件
function EOADetails({ scores, dataSource }: { scores: ScoreData['scores']['eoa']; dataSource?: string }) {
  const { metrics } = scores

  return (
    <div className="card-monad">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">👤</span>
          <h3 className="text-lg font-semibold text-white">{scores.name_cn || "用户活跃度分析"}</h3>
        </div>
        <span className="text-[#836EF9] font-bold">{Math.round(scores.score)}/{scores.max_score}</span>
      </div>
      <p className="text-gray-400 text-sm mb-4">{scores.description_cn || scores.description}</p>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <MetricCard label="独立 EOA 数量" value={metrics.unique_eoa_count?.toLocaleString() || '0'} />
        <MetricCard label="EOA 占比" value={`${metrics.eoa_percentage?.toFixed(1) || 0}%`} />
        <MetricCard label="分析地址数" value={metrics.total_addresses?.toLocaleString() || '0'} />
      </div>

      {dataSource && (
        <div className="text-xs text-gray-500 pt-3 border-t border-gray-800">
          数据来源: {dataSource.toUpperCase()}
        </div>
      )}
    </div>
  )
}

// 持仓分布详情组件
function HolderDetails({ scores, dataSource }: { scores: ScoreData['scores']['holder']; dataSource?: string }) {
  const { metrics } = scores

  return (
    <div className="card-monad">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">📊</span>
          <h3 className="text-lg font-semibold text-white">{scores.name_cn || "持仓分布分析"}</h3>
        </div>
        <span className="text-[#836EF9] font-bold">{Math.round(scores.score)}/{scores.max_score}</span>
      </div>
      <p className="text-gray-400 text-sm mb-4">{scores.description_cn || scores.description}</p>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <MetricCard label="总持有者数" value={metrics.total_holders?.toLocaleString() || '0'} />
        <MetricCard label="Top10 占比" value={`${metrics.top10_percentage?.toFixed(2) || 0}%`} highlight={metrics.top10_percentage > 50} />
      </div>

      {/* Top 10 持有者表格 */}
      {metrics.top10_holders && metrics.top10_holders.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Top 10 持有者</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-800">
                  <th className="pb-2 pr-4">#</th>
                  <th className="pb-2 pr-4">地址</th>
                  <th className="pb-2 text-right">占比</th>
                </tr>
              </thead>
              <tbody>
                {metrics.top10_holders.map((holder: TopHolder) => (
                  <tr key={holder.rank} className="border-b border-gray-800/50">
                    <td className="py-2 pr-4 text-gray-400">{holder.rank}</td>
                    <td className="py-2 pr-4">
                      <a
                        href={`https://monad.socialscan.io/address/${holder.address}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[#836EF9] hover:underline font-mono"
                      >
                        {holder.address_short}
                      </a>
                    </td>
                    <td className="py-2 text-right text-gray-300">{holder.percentage?.toFixed(2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {dataSource && (
        <div className="text-xs text-gray-500 pt-3 border-t border-gray-800 mt-4">
          数据来源: {dataSource.toUpperCase()}
        </div>
      )}
    </div>
  )
}

// 合约权限详情组件
function PermissionDetails({ scores, dataSource }: { scores: ScoreData['scores']['permission']; dataSource?: string }) {
  const { metrics } = scores

  return (
    <div className="card-monad">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔒</span>
          <h3 className="text-lg font-semibold text-white">{scores.name_cn || "合约安全分析"}</h3>
        </div>
        <span className="text-[#836EF9] font-bold">{Math.round(scores.score)}/{scores.max_score}</span>
      </div>
      <p className="text-gray-400 text-sm mb-4">{scores.description_cn || scores.description}</p>

      {/* 状态检查 */}
      <div className="space-y-2 mb-4">
        <StatusItem
          label="Owner 权限"
          value={metrics.has_owner ? "有 Owner" : "无 Owner"}
          isGood={!metrics.has_owner}
          subValue={metrics.owner_address ? `${metrics.owner_address.slice(0, 10)}...${metrics.owner_address.slice(-8)}` : undefined}
        />
        <StatusItem
          label="Owner 已放弃"
          value={metrics.is_renounced ? "已放弃" : "未放弃"}
          isGood={metrics.is_renounced}
        />
        <StatusItem
          label="多签地址"
          value={metrics.is_multisig ? "是" : "否"}
          isGood={metrics.is_multisig}
        />
        <StatusItem
          label="代理合约"
          value={metrics.is_proxy ? "是" : "否"}
          isGood={!metrics.is_proxy}
        />
      </div>

      {/* 危险函数 */}
      {metrics.dangerous_functions && metrics.dangerous_functions.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-red-400 mb-3">危险函数 ({metrics.dangerous_functions.length})</h4>
          <div className="space-y-2">
            {metrics.dangerous_functions.map((func: DangerousFunction, idx: number) => (
              <div key={idx} className="flex items-center gap-2 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
                <span className="text-red-400">⚠</span>
                <span className="text-gray-400">{func.category}:</span>
                <code className="text-red-300 font-mono">{func.signature}</code>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 风险摘要 */}
      {metrics.risk_summary && metrics.risk_summary.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-cyan-400 mb-3">风险提示</h4>
          <ul className="space-y-1">
            {metrics.risk_summary.map((item: string, idx: number) => (
              <li key={idx} className="text-sm text-gray-400 flex items-start gap-2">
                <span className="text-cyan-400">•</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {dataSource && (
        <div className="text-xs text-gray-500 pt-3 border-t border-gray-800 mt-4">
          数据来源: {dataSource.toUpperCase()}
        </div>
      )}
    </div>
  )
}

// 指标卡片组件
function MetricCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="bg-[#1a1a1a] rounded-lg p-3 border border-gray-800/50">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-xl font-bold ${highlight ? 'text-purple-400' : 'text-white'}`}>{value}</p>
    </div>
  )
}

// 状态项组件
function StatusItem({ label, value, isGood, subValue }: { label: string; value: string; isGood: boolean; subValue?: string }) {
  return (
    <div className="flex items-center justify-between py-2 px-3 bg-[#1a1a1a] rounded-lg">
      <span className="text-sm text-gray-400">{label}</span>
      <div className="text-right">
        <span className={`text-sm font-medium ${isGood ? 'text-green-400' : 'text-red-400'}`}>
          {isGood ? '✓' : '✕'} {value}
        </span>
        {subValue && (
          <p className="text-xs text-gray-500 mt-0.5 font-mono">{subValue}</p>
        )}
      </div>
    </div>
  )
}
