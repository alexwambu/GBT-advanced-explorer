from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from web3 import Web3
import os, requests

app = FastAPI(title="GBTNetwork Explorer")

# === RPC Configuration ===
PRIMARY_RPC = os.getenv("RPC_URL", "https://gbtnetwork-1989.created.app")
LOCAL_RPC = "http://localhost:9636"

def check_rpc(url):
    """Test if an RPC endpoint returns valid JSON-RPC response"""
    try:
        r = requests.post(url, json={
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }, timeout=5)
        r.raise_for_status()
        data = r.json()
        if "result" in data:
            return True
    except Exception as e:
        print(f"⚠️ RPC test failed for {url}: {e}")
    return False

# Choose working RPC
if check_rpc(PRIMARY_RPC):
    RPC_URL = PRIMARY_RPC
    print("✅ Connected to Public RPC:", RPC_URL)
elif check_rpc(LOCAL_RPC):
    RPC_URL = LOCAL_RPC
    print("✅ Connected to Local RPC:", RPC_URL)
else:
    RPC_URL = None
    print("❌ No valid RPC endpoint found!")

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(RPC_URL)) if RPC_URL else None

# === Global Error Handler ===
@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    )

# === Routes ===
@app.get("/", response_class=JSONResponse)
async def home():
    if not w3 or not w3.is_connected():
        return {"status": "offline", "error": "RPC connection failed"}
    latest_block = w3.eth.block_number
    chain_id = w3.eth.chain_id
    return {
        "status": "GBT Explorer Online",
        "rpc": RPC_URL,
        "chain_id": chain_id,
        "latest_block": latest_block
    }

@app.get("/block/{block_number}", response_class=JSONResponse)
async def get_block(block_number: int):
    if not w3 or not w3.is_connected():
        return {"error": "Not connected to RPC"}
    try:
        block = w3.eth.get_block(block_number)
        return {
            "blockNumber": block.number,
            "hash": block.hash.hex(),
            "timestamp": block.timestamp,
            "tx_count": len(block.transactions)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/tx/{tx_hash}", response_class=JSONResponse)
async def get_transaction(tx_hash: str):
    if not w3 or not w3.is_connected():
        return {"error": "Not connected to RPC"}
    try:
        tx = w3.eth.get_transaction(tx_hash)
        return {
            "from": tx['from'],
            "to": tx['to'],
            "value": w3.from_wei(tx['value'], 'ether'),
            "gas": tx['gas'],
            "hash": tx['hash'].hex()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/token", response_class=JSONResponse)
async def token_info():
    if not w3 or not w3.is_connected():
        return {"error": "Not connected to RPC"}
    try:
        token_address = Web3.to_checksum_address("0x742d35Cc891c4F8ECa9B7a0A0f7f4e5e5C5D5E5A")
        abi = [
            {"constant": True, "inputs": [], "name": "name", "outputs": [{"name":"","type":"string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name":"","type":"string"}], "type": "function"},
            {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name":"","type":"uint8"}], "type": "function"}
        ]
        contract = w3.eth.contract(address=token_address, abi=abi)
        name = contract.functions.name().call()
        symbol = contract.functions.symbol().call()
        decimals = contract.functions.decimals().call()
        return {"token": name, "symbol": symbol, "decimals": decimals}
    except Exception as e:
        return {"error": str(e)}

@app.get("/ui", response_class=HTMLResponse)
async def serve_ui():
    try:
        with open("explorer.html", "r") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h3>Explorer UI not found.</h3>")
