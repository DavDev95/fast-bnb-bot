"""On-chain constants for BNB Smart Chain (mainnet, chain id 56)."""

CHAIN_ID = 56

# PancakeSwap V2 router.
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"

# Wrapped BNB.
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"

# Minimal ERC-20 ABI (only what the bot needs).
ERC20_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
     "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
     "type": "function"},
    {"constant": True, "inputs": [], "name": "decimals",
     "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
    {"constant": True, "inputs": [], "name": "symbol",
     "outputs": [{"name": "", "type": "string"}], "type": "function"},
    {"constant": True,
     "inputs": [{"name": "_owner", "type": "address"},
                {"name": "_spender", "type": "address"}],
     "name": "allowance", "outputs": [{"name": "", "type": "uint256"}],
     "type": "function"},
    {"constant": False,
     "inputs": [{"name": "_spender", "type": "address"},
                {"name": "_value", "type": "uint256"}],
     "name": "approve", "outputs": [{"name": "", "type": "bool"}],
     "type": "function"},
]

# Minimal PancakeSwap V2 router ABI (read price + swap).
ROUTER_ABI = [
    {"inputs": [{"name": "amountIn", "type": "uint256"},
                {"name": "path", "type": "address[]"}],
     "name": "getAmountsOut",
     "outputs": [{"name": "amounts", "type": "uint256[]"}],
     "stateMutability": "view", "type": "function"},
    {"inputs": [{"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMin", "type": "uint256"},
                {"name": "path", "type": "address[]"},
                {"name": "to", "type": "address"},
                {"name": "deadline", "type": "uint256"}],
     "name": "swapExactTokensForTokens",
     "outputs": [{"name": "amounts", "type": "uint256[]"}],
     "stateMutability": "nonpayable", "type": "function"},
    {"inputs": [{"name": "amountOutMin", "type": "uint256"},
                {"name": "path", "type": "address[]"},
                {"name": "to", "type": "address"},
                {"name": "deadline", "type": "uint256"}],
     "name": "swapExactETHForTokens",
     "outputs": [{"name": "amounts", "type": "uint256[]"}],
     "stateMutability": "payable", "type": "function"},
    {"inputs": [{"name": "amountIn", "type": "uint256"},
                {"name": "amountOutMin", "type": "uint256"},
                {"name": "path", "type": "address[]"},
                {"name": "to", "type": "address"},
                {"name": "deadline", "type": "uint256"}],
     "name": "swapExactTokensForETH",
     "outputs": [{"name": "amounts", "type": "uint256[]"}],
     "stateMutability": "nonpayable", "type": "function"},
]
