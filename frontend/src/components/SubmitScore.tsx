import { useAccount, useWriteContract, useWaitForTransactionReceipt, useSimulateContract, useSwitchChain, useChainId } from 'wagmi'
import { SCORE_REGISTRY_ADDRESS, SCORE_REGISTRY_ABI, monadMainnet } from '../config/wagmi'
import type { ScoreData } from '../App'

interface Props {
  data: ScoreData
}

export default function SubmitScore({ data }: Props) {
  const { isConnected } = useAccount()
  const chainId = useChainId()
  const { switchChain, isPending: isSwitching } = useSwitchChain()

  const isWrongNetwork = chainId !== monadMainnet.id

  const { data: simulateData, error: simulateError } = useSimulateContract({
    address: SCORE_REGISTRY_ADDRESS,
    abi: SCORE_REGISTRY_ABI,
    functionName: 'submitScore',
    args: [
      data.submit_data.target as `0x${string}`,
      data.submit_data.totalScore,
      data.submit_data.eoaScore,
      data.submit_data.holderScore,
      data.submit_data.permissionScore,
      data.submit_data.riskLevel
    ],
    chainId: monadMainnet.id,
    query: {
      enabled: isConnected && !isWrongNetwork
    }
  })

  const { writeContract, data: hash, isPending, error: writeError } = useWriteContract()
  const { isLoading: isConfirming, isSuccess } = useWaitForTransactionReceipt({ hash })

  const estimatedGas = simulateData?.request?.gas
    ? (simulateData.request.gas * BigInt(120)) / BigInt(100)
    : BigInt(500000)

  const handleSubmit = () => {
    if (!simulateData?.request) return
    writeContract({
      ...simulateData.request,
      gas: estimatedGas
    })
  }

  const error = writeError || simulateError

  if (!isConnected) {
    return (
      <div className="card-monad flex flex-col items-center justify-center py-8 border-dashed border-gray-800">
        <div className="w-12 h-12 rounded-full bg-monad-purple/10 flex items-center justify-center mb-4 text-2xl text-monad-purple">
          🔗
        </div>
        <h3 className="text-lg font-medium text-white mb-2">Connect Wallet to Submit</h3>
        <p className="text-gray-500 text-sm text-center max-w-sm">
          Connect your wallet to record this score on the Monad Testnet permanently.
        </p>
      </div>
    )
  }

  return (
    <div className="card-monad relative overflow-hidden">
      {/* Background Decor */}
      <div className="absolute -right-10 -top-10 w-40 h-40 bg-monad-purple/5 rounded-full blur-3xl pointer-events-none"></div>

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 mb-6">
        <div>
           <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <span className="text-monad-purple">⚡</span>
            Submit Score On-Chain
          </h3>
          <p className="text-sm text-gray-500 mt-1">Immutable record on Monad Testnet</p>
        </div>
        
        {/* Gas Estimate */}
        <div className="flex items-center gap-4 text-xs font-mono bg-black/40 rounded-lg px-3 py-2 border border-white/5">
            <div className="flex flex-col">
                <span className="text-gray-500 uppercase tracking-wider">Est. Gas</span>
                <span className="text-gray-300">{Number(estimatedGas).toLocaleString()}</span>
            </div>
            <div className="h-6 w-px bg-white/10"></div>
            <div className="flex flex-col">
                <span className="text-gray-500 uppercase tracking-wider">Fee</span>
                <span className="text-monad-purple">~{(Number(estimatedGas) * 50 / 1e9).toFixed(4)} MON</span>
            </div>
        </div>
      </div>

      {/* Payload Preview */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2 mb-6 p-4 bg-black/20 rounded-lg border border-white/5 font-mono text-xs">
        <DataItem label="Total" value={data.submit_data.totalScore} highlight />
        <DataItem label="EOA" value={data.submit_data.eoaScore} />
        <DataItem label="Holder" value={data.submit_data.holderScore} />
        <DataItem label="Perms" value={data.submit_data.permissionScore} />
        <DataItem label="Risk" value={data.submit_data.riskLevel} />
        <div className="md:col-span-1 flex flex-col">
             <span className="text-gray-600 mb-1">Target</span>
             <span className="text-gray-400 truncate" title={data.submit_data.target}>{data.submit_data.target.slice(0, 6)}...</span>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mb-6 p-4 bg-risk-danger/10 border border-risk-danger/20 rounded-lg flex items-start gap-3 animate-fade-in">
          <svg className="w-5 h-5 text-risk-danger shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
          <div className="text-sm text-red-200 break-all">{error.message}</div>
        </div>
      )}

      {isSuccess && hash && (
        <div className="mb-6 p-4 bg-risk-safe/10 border border-risk-safe/20 rounded-lg flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-3">
             <div className="w-6 h-6 rounded-full bg-risk-safe/20 flex items-center justify-center text-risk-safe text-xs">✓</div>
             <span className="text-sm text-green-200">Transaction Confirmed!</span>
          </div>
          <a
            href={`https://monad.socialscan.io/tx/${hash}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs font-mono text-monad-purple hover:text-white transition-colors flex items-center gap-1"
          >
            View TX <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
          </a>
        </div>
      )}

      {/* Wrong Network Warning */}
      {isWrongNetwork && (
        <div className="mb-6 p-4 bg-cyan-500/10 border border-cyan-500/20 rounded-lg flex items-start gap-3 animate-fade-in">
          <svg className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="text-sm text-cyan-200">
            请切换到 Monad 网络 (Chain ID: {monadMainnet.id}) 以提交评分
          </div>
        </div>
      )}

      {/* Action Button */}
      {isWrongNetwork ? (
        <button
          onClick={() => switchChain({ chainId: monadMainnet.id })}
          disabled={isSwitching}
          className="w-full btn-monad h-12 text-base shadow-lg shadow-monad-purple/10 disabled:shadow-none"
        >
          {isSwitching ? (
            <span className="flex items-center gap-2 justify-center">
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              切换网络中...
            </span>
          ) : (
            '🔄 Switch to Monad Network'
          )}
        </button>
      ) : (
        <button
          onClick={handleSubmit}
          disabled={isPending || isConfirming || !simulateData?.request}
          className="w-full btn-monad h-12 text-base shadow-lg shadow-monad-purple/10 disabled:shadow-none"
        >
          {isPending ? (
              <span className="flex items-center gap-2 justify-center">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Waiting for Approval...
              </span>
          ) : isConfirming ? (
              <span className="flex items-center gap-2 justify-center">
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Confirming Transaction...
              </span>
          ) : (
              'Submit to Monad Chain'
          )}
        </button>
      )}
    </div>
  )
}

function DataItem({ label, value, highlight }: { label: string, value: number | string, highlight?: boolean }) {
    return (
        <div className="flex flex-col">
            <span className="text-gray-600 mb-1">{label}</span>
            <span className={`${highlight ? 'text-monad-purple font-bold' : 'text-gray-300'}`}>{value}</span>
        </div>
    )
}