import { http, createConfig } from 'wagmi'
import { defineChain } from 'viem'

// 定义 Monad 主网
export const monadMainnet = defineChain({
  id: 143,
  name: 'Monad Mainnet',
  nativeCurrency: {
    decimals: 18,
    name: 'Monad',
    symbol: 'MON',
  },
  rpcUrls: {
    default: {
      http: ['https://monad.blockpi.network/v1/rpc/3613459cff994323ab56a25c0df81712450ebf8b'],
    },
  },
  blockExplorers: {
    default: { name: 'Monad Explorer', url: 'https://monad.socialscan.io' },
  },
})

// wagmi 配置
export const config = createConfig({
  chains: [monadMainnet],
  transports: {
    [monadMainnet.id]: http(),
  },
})

// 合约地址
export const SCORE_REGISTRY_ADDRESS = '0x1F4eB0eeBbD97aae09f8f8d6Aaf84a71D8C0c3AA' as const

// 合约 ABI（只包含需要的函数）
export const SCORE_REGISTRY_ABI = [
  {
    inputs: [
      { name: 'target', type: 'address' },
      { name: 'totalScore', type: 'uint8' },
      { name: 'eoaScore', type: 'uint8' },
      { name: 'holderScore', type: 'uint8' },
      { name: 'permissionScore', type: 'uint8' },
      { name: 'riskLevel', type: 'uint8' }
    ],
    name: 'submitScore',
    outputs: [],
    stateMutability: 'nonpayable',
    type: 'function'
  },
  {
    inputs: [{ name: 'target', type: 'address' }],
    name: 'getLatestScore',
    outputs: [
      {
        components: [
          { name: 'totalScore', type: 'uint8' },
          { name: 'eoaScore', type: 'uint8' },
          { name: 'holderScore', type: 'uint8' },
          { name: 'permissionScore', type: 'uint8' },
          { name: 'riskLevel', type: 'uint8' },
          { name: 'timestamp', type: 'uint256' },
          { name: 'blockNumber', type: 'uint256' },
          { name: 'scorer', type: 'address' }
        ],
        type: 'tuple'
      }
    ],
    stateMutability: 'view',
    type: 'function'
  },
  {
    inputs: [{ name: 'target', type: 'address' }],
    name: 'hasBeenScored',
    outputs: [{ type: 'bool' }],
    stateMutability: 'view',
    type: 'function'
  },
  {
    inputs: [],
    name: 'getScoredProjectCount',
    outputs: [{ type: 'uint256' }],
    stateMutability: 'view',
    type: 'function'
  },
  {
    inputs: [],
    name: 'totalScoreCount',
    outputs: [{ type: 'uint256' }],
    stateMutability: 'view',
    type: 'function'
  }
] as const

// API 地址
export const API_BASE_URL = '/api'