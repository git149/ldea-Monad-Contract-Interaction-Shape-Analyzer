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
    <div className="min-h-screen font-sans text-gray-300 selection:bg-monad-purple selection:text-white pb-20">
      {/* Background Texture */}
      <div className="fixed inset-0 z-0 pointer-events-none bg-grid-pattern opacity-[0.03]"></div>

      {/* Header */}
      <header className="relative z-10 border-b border-white/5 backdrop-blur-md sticky top-0">
        <div className="max-w-6xl mx-auto px-6 h-20 flex justify-between items-center">
          <div className="flex items-center gap-3 group cursor-default">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-monad-purple to-monad-purple-dark flex items-center justify-center shadow-lg shadow-monad-purple/20 group-hover:scale-105 transition-transform duration-300">
              <span className="text-white font-bold text-xl">M</span>
            </div>
            <div>
              <h1 className="text-lg font-bold text-white leading-none tracking-tight">
                Token Score
              </h1>
              <p className="text-xs text-monad-purple font-mono mt-0.5">Risk Analysis Protocol</p>
            </div>
          </div>
          <ConnectWallet />
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-12">
        {/* Hero / Input Section */}
        <div className={`transition-all duration-500 ease-out ${scoreData ? 'mb-12' : 'min-h-[60vh] flex flex-col justify-center mb-0'}`}>
          {!scoreData && (
            <div className="text-center mb-10 animate-fade-in">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
                Evaluate Token Risk on <span className="text-transparent bg-clip-text bg-gradient-to-r from-monad-purple to-purple-400">Monad</span>
              </h2>
              <p className="text-gray-400 text-lg max-w-2xl mx-auto">
                Comprehensive analysis of Holder distribution, Contract permissions, and User activity.
              </p>
            </div>
          )}
          
          <TokenInput onAnalyze={handleAnalyze} loading={loading} />
        </div>

        {/* Error Message */}
        {error && (
          <div className="max-w-2xl mx-auto mb-8 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400 flex items-center gap-3 animate-fade-in">
            <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {error}
          </div>
        )}

        {/* Loading State - Custom Loader */}
        {loading && !scoreData && (
          <div className="max-w-2xl mx-auto text-center py-12 animate-pulse">
            <div className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-monad-purple/20 border-t-monad-purple animate-spin"></div>
            <p className="text-monad-purple font-mono">Scanning Blockchain Data...</p>
          </div>
        )}

        {/* Results */}
        {scoreData && !loading && (
          <div className="animate-fade-in space-y-8">
            <ScoreDisplay data={scoreData} />
            
            <div className="border-t border-white/5 pt-8">
              <SubmitScore data={scoreData} />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 mt-auto">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-gray-600 text-sm">
            © 2026 Monad Token Score. Built on <span className="text-gray-400 hover:text-monad-purple transition-colors cursor-pointer">Monad Testnet</span>.
          </p>
          <div className="flex gap-6 text-sm text-gray-500 font-mono">
            <a href="#" className="hover:text-white transition-colors">Documentation</a>
            <a href="#" className="hover:text-white transition-colors">Explorer</a>
            <a href="#" className="hover:text-white transition-colors">Github</a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default App