import { useState } from 'react'
import ConnectWallet from './components/ConnectWallet'
import TokenInput from './components/TokenInput'
import ScoreDisplay from './components/ScoreDisplay'
import SubmitScore from './components/SubmitScore'

// Top 持有者类型
export interface TopHolder {
  rank: number
  address: string
  address_short: string
  balance: number
  percentage: number
}

// 危险函数类型
export interface DangerousFunction {
  category: string
  signature: string
}

// 风险标签类型
export interface RiskTag {
  key: string
  label: string
  label_cn: string
  type: 'success' | 'warning' | 'danger'
  category: 'activity' | 'holder' | 'permission'
}

// 评分数据类型
export interface ScoreData {
  token_address: string
  timestamp: string
  analysis_mode: string
  data_sources: {
    eoa: string
    holder: string
    permission: string
  }
  overview: {
    total_score: number
    max_score: number
    risk_level: string
    risk_label: string
    risk_label_cn: string
    risk_color: string
    risk_bg_color: string
    risk_icon: string
  }
  risk_tags: RiskTag[]
  scores: {
    eoa: {
      name: string
      name_cn: string
      description: string
      description_cn: string
      score: number
      max_score: number
      weight: string
      risk_level: string
      metrics: {
        unique_eoa_count: number
        total_addresses: number
        eoa_percentage: number
        events_count: number
      }
    }
    holder: {
      name: string
      name_cn: string
      description: string
      description_cn: string
      score: number
      max_score: number
      weight: string
      risk_level: string
      metrics: {
        total_holders: number
        top10_percentage: number
        top10_holders: TopHolder[]
      }
    }
    permission: {
      name: string
      name_cn: string
      description: string
      description_cn: string
      score: number
      max_score: number
      weight: string
      risk_level: string
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
  }
  submit_data: {
    target: string
    totalScore: number
    eoaScore: number
    holderScore: number
    permissionScore: number
    riskLevel: number
  }
}

function App() {
  const [scoreData, setScoreData] = useState<ScoreData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleAnalyze = async (tokenAddress: string) => {
    setLoading(true)
    setError(null)
    setScoreData(null)

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token_address: tokenAddress })
      })

      if (!response.ok) {
        throw new Error('Analysis failed. Please check the contract address.')
      }

      const data = await response.json()
      setScoreData(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] font-sans text-gray-300">
      {/* Header */}
      <header className="border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-monad-purple to-purple-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Monad Shield</h1>
              <p className="text-xs text-gray-500">Interaction Analysis  交互分析</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <a href="https://github.com" target="_blank" rel="noopener noreferrer" className="text-gray-400 hover:text-white transition-colors">
              <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd" />
              </svg>
            </a>
            <ConnectWallet />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Search Bar */}
        <div className="flex justify-center mb-8">
          <TokenInput onAnalyze={handleAnalyze} loading={loading} />
        </div>

        {/* Error Message */}
        {error && (
          <div className="max-w-2xl mx-auto mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 flex items-center gap-3">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {error}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-20">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-monad-purple/20 border-t-monad-purple animate-spin"></div>
            <p className="text-monad-purple font-mono">Scanning Blockchain Data...</p>
          </div>
        )}

        {/* Results */}
        {scoreData && !loading && (
          <div className="space-y-6">
            <ScoreDisplay data={scoreData} />

            <div className="border-t border-white/5 pt-6">
              <SubmitScore data={scoreData} />
            </div>
          </div>
        )}

        {/* Empty State */}
        {!scoreData && !loading && !error && (
          <div className="text-center py-20">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gradient-to-br from-monad-purple/20 to-purple-600/20 flex items-center justify-center">
              <svg className="w-10 h-10 text-monad-purple" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-white mb-2">Token Risk Analysis</h2>
            <p className="text-gray-500 max-w-md mx-auto">
              Enter a token contract address to analyze its interaction patterns and risk profile
            </p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App