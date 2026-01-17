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
    <div className="w-full max-w-3xl">
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex items-center bg-[#12121a] rounded-full border border-white/10 p-1.5 shadow-xl">
          {/* Search Icon */}
          <div className="pl-4 pr-2 text-gray-500">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>

          {/* Input */}
          <input
            type="text"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="0x754704bc059f8c67012fed69bc8a327a5aafb603"
            className="flex-1 bg-transparent border-none text-white placeholder-gray-600 font-mono text-sm focus:ring-0 focus:outline-none px-2 py-3"
            spellCheck={false}
          />

          {/* Shield Button */}
          <button
            type="submit"
            disabled={!isValidAddress || loading}
            className={`flex items-center gap-2 px-6 py-2.5 rounded-full font-medium transition-all duration-200 ${
              isValidAddress && !loading
                ? 'bg-monad-purple text-white hover:bg-monad-purple-dark shadow-lg shadow-monad-purple/30'
                : 'bg-gray-800 text-gray-500 cursor-not-allowed'
            }`}
          >
            {loading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Analyzing...</span>
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Shield  护盾</span>
              </>
            )}
          </button>
        </div>
      </form>

      {/* Error Message */}
      <div className="h-6 mt-2 px-4">
        {address && !isValidAddress && !isEmpty && (
          <p className="text-red-400 text-xs flex items-center gap-1">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Invalid Contract Address format
          </p>
        )}
      </div>
    </div>
  )
}