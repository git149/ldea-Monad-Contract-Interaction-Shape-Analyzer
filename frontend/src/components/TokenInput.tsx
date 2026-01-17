import { useState } from 'react'

interface Props {
  onAnalyze: (address: string) => void
  loading: boolean
}

export default function TokenInput({ onAnalyze, loading }: Props) {
  const [address, setAddress] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (address.trim()) {
      onAnalyze(address.trim())
    }
  }

  // Basic address validation
  const isValidAddress = /^0x[a-fA-F0-9]{40}$/.test(address)
  const isEmpty = address.trim().length === 0

  return (
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative group">
        <div className={`absolute -inset-0.5 bg-gradient-to-r from-monad-purple to-purple-600 rounded-xl opacity-20 group-hover:opacity-40 transition duration-500 blur ${loading ? 'opacity-50 animate-pulse' : ''}`}></div>
        <div className="relative flex items-center bg-monad-surface rounded-xl p-1.5 border border-monad-border shadow-2xl">
          <div className="pl-4 pr-2 text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          </div>
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Search Token Address (0x...)"
            className="flex-1 bg-transparent border-none text-white placeholder-gray-600 font-mono text-base focus:ring-0 px-2 py-3"
            spellCheck={false}
          />
          <button
            type="submit"
            disabled={!isValidAddress || loading}
            className={`px-6 py-2.5 rounded-lg font-medium transition-all duration-200 ${
              isValidAddress && !loading
                ? 'bg-monad-purple text-white shadow-lg shadow-monad-purple/20 hover:bg-monad-purple-dark'
                : 'bg-monad-surface-light text-gray-600 cursor-not-allowed'
            }`}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Analyzing
              </span>
            ) : (
              'Analyze'
            )}
          </button>
        </div>
      </form>
      
      {/* Helper text / Error */}
      <div className="h-6 mt-2 px-1">
        {address && !isValidAddress && !isEmpty && (
          <p className="text-red-400 text-xs flex items-center gap-1 animate-fade-in">
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            Invalid Contract Address format
          </p>
        )}
      </div>
    </div>
  )
}