import requests
from web3 import Web3
from eth_account import Account
import time
import sys
import os
import json
import logging
import threading


# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
NETWORKS = {
    "InitVerse": {
        "rpc_url": "https://rpc-testnet.inichain.com",
        "chain_id": 7234,
        "contract_address": "0x4ccB784744969D9B63C15cF07E622DDA65A88Ee7",
    }
}

TOKENS = {
    "USDT": "0xcF259Bca0315C6D32e877793B6a10e97e7647FdE",
    "INI": "0xfbECae21C91446f9c7b87E4e5869926998f99ffe",
}

def print_banner():
    banner = """
\033[95m                _  _
\033[92m             .-. || |               .-.
\033[91m            |   || |_              | | |   
\033[93m .--.  .---.| |_||( )  .--.  .---. | |_|_ .--.
\033[94m( (\\]/ .-. ||  _| |/ ( (\\]/ .-. \\|  _  [ \\]
\033[96m '.'.| | | || |   (   '.'.| | | || | | || |_
\033[92m[\\__) ) '-' || |_   \\   [\\__) ) '-' || | | || |_
\033[91m '--'  '---'|___|    '--'  '---'|___||___[___]
\033[93m    DASAR PEMULUNG - GETTING RICH TOGETHER!\033[0m
    """
    print(banner)

# Load proxies from proxy.txt
def load_proxies():
    proxies = []
    try:
        with open("proxy.txt", "r") as file:
            proxies = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.warning("Proxy file not found. Running without proxies.")
    return proxies

PROXIES = load_proxies()

# Load private keys from private_keys.txt
def load_private_keys():
    private_keys = []
    try:
        with open("private_keys.txt", "r") as file:
            private_keys = [line.strip() for line in file.readlines() if line.strip()]
    except FileNotFoundError:
        logger.error("Private keys file not found. Exiting.")
        sys.exit(1)
    return private_keys

PRIVATE_KEYS = load_private_keys()

# Load ABIs
def load_abi(name):
    with open(f"./{name}.json", "r") as f:
        return json.load(f)

ERC20_ABI = load_abi("ERC20_ABI")
ROUTER_ABI = load_abi("ROUTER_ABI")

# Get web3 provider with proxy support
def get_web3_provider(proxy=None):
    if proxy:
        return Web3(Web3.HTTPProvider(NETWORKS["InitVerse"]["rpc_url"], request_kwargs={"proxies": {"http": proxy, "https": proxy}}))
    return Web3(Web3.HTTPProvider(NETWORKS["InitVerse"]["rpc_url"]))

def get_user_info(address):
    return fetch_data(
        f"https://candyapi.inichain.com/airdrop/v1/user/userInfo?address={address}"
    )

def verify_user_before_swap(address):
    logger.info(f"\033[96mAddress:\033[0m {address}")  # Cyan

    user_info = get_user_info(address)
    if not user_info:
        print("\033[91mCannot retrieve user info. Exiting.\033[0m")  # Red
        sys.exit(1)

    task_status = fetch_data(
        f"https://candyapi.inichain.com/airdrop/v1/user/UserTaskStatus?address={address}"
    )
    if not task_status:
        print("\033[91mCannot retrieve task status. Exiting.\033[0m")  # Red
        sys.exit(1)

    daily_tasks = task_status.get("data", {}).get("dailyTaskInfo", [])
    if not daily_tasks:
        print("\033[91mNo daily tasks found. Exiting.\033[0m")  # Red
        return False

    # Bypass the task availability check
    logger.info("\033[92mBypassing swap task check. Proceeding...\033[0m")  # Green
    return True

def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Request failed: {e}")
        return None

def save_tx_hash(tx_hash, source_network, swap_name):
    base_folder = "Tx_Hash"
    os.makedirs(base_folder, exist_ok=True)

    network_folder = os.path.join(base_folder, source_network.replace(" ", "-"))
    os.makedirs(network_folder, exist_ok=True)

    swap_file_path = os.path.join(
        network_folder, f'Tx_{swap_name.replace(" ", "-")}.txt'
    )

    with open(swap_file_path, "a") as file:
        file.write(f"{tx_hash}\n")

def get_transaction_status(tx_hash, w3):
    start_time = time.time()  # Waktu mulai
    logger.info("\033[96mWaiting for transaction ...\033[0m")  # Cyan
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    elapsed_time = time.time() - start_time  # Hitung waktu yang telah berlalu
    logger.info(
        f"\033[92mTransaction Success in {elapsed_time:.2f} seconds.\033[0m"
    )  # Green
    return receipt["status"]  # 1 for success, 0 for failure

def approve_token_if_needed(account, token_contract, router_address, w3):
    allowance = token_contract.functions.allowance(
        account.address, router_address
    ).call()
    balance = token_contract.functions.balanceOf(account.address).call()

    if allowance < balance:
        nonce = w3.eth.get_transaction_count(account.address)
        approval_txn = token_contract.functions.approve(
            router_address, balance
        ).build_transaction(
            {
                "from": account.address,
                "gas": 100000,
                "gasPrice": w3.to_wei("2", "gwei"),
                "nonce": nonce,
            }
        )

        signed_approval_txn = w3.eth.account.sign_transaction(
            approval_txn, private_key=account.key
        )
        approval_tx_hash = w3.eth.send_raw_transaction(
            signed_approval_txn.raw_transaction
        )
        logger.info(
            f"\033[96mApproval Tx Hash:\033[0m {w3.to_hex(approval_tx_hash)}"
        )  # Cyan

        # Wait for approval to be mined and confirm success
        approval_status = get_transaction_status(approval_tx_hash, w3)
        if approval_status != 1:
            logger.error("\033[91mApproval failed. Exiting.\033[0m")  # Red
            sys.exit(1)

def perform_swap(w3, account, router_contract, path, amount_in, is_eth_to_token):
    try:
        nonce = w3.eth.get_transaction_count(account.address)
        deadline = int(time.time()) + 10000

        if is_eth_to_token:
            txn = router_contract.functions.swapExactETHForTokens(
                0, path, account.address, deadline
            ).build_transaction(
                {
                    "from": account.address,
                    "value": amount_in,
                    "gas": 200000,
                    "gasPrice": w3.to_wei("2", "gwei"),
                    "nonce": nonce,
                }
            )
        else:
            balance = (
                w3.eth.contract(address=path[0], abi=ERC20_ABI)
                .functions.balanceOf(account.address)
                .call()
            )
            txn = router_contract.functions.swapExactTokensForETH(
                balance, 0, path, account.address, deadline
            ).build_transaction(
                {
                    "from": account.address,
                    "gas": 200000,
                    "gasPrice": w3.to_wei("2", "gwei"),
                    "nonce": nonce,
                }
            )

        signed_txn = w3.eth.account.sign_transaction(txn, private_key=account.key)
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        logger.info(f"\033[92mTransaction Hash:\033[0m {w3.to_hex(tx_hash)}")  # Green

        status = get_transaction_status(tx_hash, w3)
        return status == 1
    except Exception as e:
        logger.error(f"Error during swap: {e}")
        return False

def run_swap_loop(account, proxy=None, swap_amount_eth=0.2):
    w3 = get_web3_provider(proxy)
    router_address = "0x4ccB784744969D9B63C15cF07E622DDA65A88Ee7"
    router_contract = w3.eth.contract(
        address=Web3.to_checksum_address(router_address), abi=ROUTER_ABI
    )

    token_contract = w3.eth.contract(
        address=Web3.to_checksum_address(TOKENS["USDT"]), abi=ERC20_ABI
    )

    paths = {
        "eth_to_usdt": [TOKENS["INI"], TOKENS["USDT"]],
        "usdt_to_eth": [TOKENS["USDT"], TOKENS["INI"]],
    }

    while True:
        try:
            logger.info(f"Starting swaps for account: {account.address} with proxy: {proxy}")

            # Swap ETH to USDT
            if perform_swap(
                w3,
                account,
                router_contract,
                paths["eth_to_usdt"],
                w3.to_wei(swap_amount_eth, "ether"),
                True,
            ):
                logger.info(f"INI to USDT swap successful for {account.address}")
            else:
                logger.error(f"INI to USDT swap failed for {account.address}")

            # Swap USDT to ETH
            approve_token_if_needed(account, token_contract, router_address, w3)
            if perform_swap(w3, account, router_contract, paths["usdt_to_eth"], 0, False):
                logger.info(f"USDT to INI swap successful for {account.address}")
            else:
                logger.error(f"USDT to INI swap failed for {account.address}")

            time.sleep(300)  # Wait for 10 minutes

        except Exception as e:
            logger.error(f"Error in swap loop for {account.address}: {e}")
def get_swap_amount():
    try:
        amount = float(input("Enter the amount of ETH to swap to USDT (in ETH): ").strip())
        return amount
    except ValueError:
        logger.error("Invalid input. Please enter a numeric value.")
        sys.exit(1)

def main():
    try:
        os.system("clear") if os.name == "posix" else os.system("cls")
        print_banner()

        # Get swap amount from user
        swap_amount_eth = get_swap_amount()

        threads = []
        for i, private_key in enumerate(PRIVATE_KEYS):
            proxy = PROXIES[i % len(PROXIES)] if PROXIES else None
            account = Account.from_key(private_key)

            if not verify_user_before_swap(account.address):
                logger.error(f"Verification failed for {account.address}")
                continue

            thread = threading.Thread(target=run_swap_loop, args=(account, proxy, swap_amount_eth))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

    except KeyboardInterrupt:
        logger.info("Operation interrupted by user.")
        sys.exit()
if __name__ == "__main__":
    main()
