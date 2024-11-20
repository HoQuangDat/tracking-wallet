import requests
import json
import time
import os
import re
from web3 import Web3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve variables from the environment
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY')
BSCSCAN_API_KEY = os.getenv('BSCSCAN_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
PRIVATE_KEY_FOUNDATION_WALLET = os.getenv('PRIVATE_KEY_FOUNDATION_WALLET')
PRIVATE_KEY_POOL_WALLET = os.getenv('PRIVATE_KEY_POOL_WALLET')
PRIVATE_KEY_DEV_CHEAT_WALLET = os.getenv('PRIVATE_KEY_DEV_CHEAT_WALLET')
FOUNDATION_WALLET = os.getenv('FOUNDATION_WALLET')
POOL_WALLET = os.getenv('POOL_WALLET')
BNB_NODE_URL = os.getenv('BNB_NODE_URL')
DEV_CHEAT_WALLET = os.getenv('DEV_CHEAT_WALLET')
MANH_WALLET = os.getenv('MANH_WALLET')
TON_WALLET = os.getenv('TON_WALLET')
MARKETING_WALLET = os.getenv('MARKETING_WALLET')
AFF_WALLET = os.getenv('AFF_WALLET')
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
ECOSYSTEM_WALLET = os.getenv('ECOSYSTEM_WALLET')

web3 = Web3(Web3.HTTPProvider(BNB_NODE_URL))

transfer_status = {
    "foundation_to_dev": 0.0,
    "pool_to_dev": 0.0
}

wallet_names = {
    POOL_WALLET: "Ví Pool",
    AFF_WALLET: "Ví AFF",
    MARKETING_WALLET: "Ví Marketing",
    CONTRACT_ADDRESS: "Contract",
    ECOSYSTEM_WALLET: "Ví Ecosystem"
}

def get_wallet_transactions(wallet_address, blockchain):
    if blockchain == 'eth':
        url = f'https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={ETHERSCAN_API_KEY}'
    elif blockchain == 'bnb' and wallet_address != CONTRACT_ADDRESS:
        url = f'https://api.bscscan.com/api?module=account&action=txlistinternal&address={wallet_address}&sort=desc&apikey={BSCSCAN_API_KEY}'
    elif blockchain == 'bnb' and wallet_address == CONTRACT_ADDRESS:
        url = f'https://api.bscscan.com/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={BSCSCAN_API_KEY}'
    else:
        raise ValueError('Invalid blockchain specified')

    response = requests.get(url)
    data = json.loads(response.text)

    result = data.get('result', [])
    if not isinstance(result, list):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error fetching transactions for {wallet_address} on {blockchain.upper()} blockchain: {data}")
        return []

    return result


def send_telegram_notification(message, value, usd_value, tx_hash, blockchain):
    if blockchain == 'eth':
        etherscan_link = f'<a href="https://etherscan.io/tx/{tx_hash}"></a>'
    elif blockchain == 'bnb':
        etherscan_link = f'<a href="https://bscscan.com/tx/{tx_hash}"></a>'
    else:
        raise ValueError('Invalid blockchain specified')

    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    payload = {
        'chat_id': f'{TELEGRAM_CHAT_ID}',
        'text': f'{message}: {value:.6f} {blockchain.upper()} (${usd_value:.2f}) {etherscan_link}',
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=payload)
    # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Telegram notification sent with message: {message}, value: {value} {blockchain.upper()} (${usd_value:.2f})")
    return response


def send_transaction(private_key, from_wallet, to_wallet, amount):
    """Send a transaction on the Binance Smart Chain."""
    try:
        # Lấy nonce chính xác từ trạng thái "pending"
        nonce = web3.eth.get_transaction_count(from_wallet, "pending")
        gas_price = web3.eth.gas_price
        gas_limit = 21000
        estimated_gas_fee = gas_limit * gas_price / 10**18  # Phí gas ước tính bằng BNB

        # Kiểm tra nếu số tiền nhỏ hơn phí gas
        if amount <= estimated_gas_fee:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Transaction skipped: Amount ({amount} BNB) is less than gas fee ({estimated_gas_fee} BNB)")
            return None

        tx = {
            'nonce': nonce,
            'to': to_wallet,
            'value': web3.to_wei(amount, 'ether'),
            'gas': gas_limit,
            'gasPrice': gas_price,
        }

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        # Log giao dịch thành công
        # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Transaction sent. TX Hash: {tx_hash.hex()}")

        # Gửi thông báo Telegram
        # send_telegram_notification(
        #     message=f"Transaction Successful",
        #     value=amount,
        #     usd_value=amount * gas_price,  # Giá trị USD có thể cập nhật
        #     tx_hash=tx_hash.hex(),
        #     blockchain="bnb",
        # )

        return tx_hash.hex()
    except Exception as e:
        error_message = str(e)
        print(f"Failed to send transaction: {error_message}")

        # Xử lý lỗi nonce quá thấp
        if "nonce too low" in error_message:
            print("[Retrying] Nonce too low detected, retrying with updated nonce...")
            try:
                nonce += 1  # Tăng nonce lên và thử lại
                tx['nonce'] = nonce
                signed_tx = web3.eth.account.sign_transaction(tx, private_key)
                tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Transaction retried. TX Hash: {tx_hash.hex()}")
                return tx_hash.hex()
            except Exception as retry_error:
                print(f"Retry failed: {retry_error}")
        return None
    
def calculate_dev_cheat_total(dev_received, foundation_to_dev, pool_to_dev):
    """
    Tính tổng số tiền mà DEV_CHEAT_WALLET sẽ quản lý.
    :param dev_received: 10% từ contract gửi trước đó.
    :param foundation_to_dev: 5% dư từ FOUNDATION_WALLET.
    :param pool_to_dev: 12.5% dư từ POOL_WALLET.
    :return: Tổng số tiền DEV_CHEAT sẽ nhận (27.5%).
    """
    return dev_received + foundation_to_dev + pool_to_dev

def distribute_from_dev_wallet(dev_total_value):
    """
    Phân phối từ ví DEV_CHEAT theo tỷ lệ:
    - 12% cho ví A
    - 12% cho ví B
    - 2.5% cho ví C
    - Giữ lại 1% trong DEV_CHEAT_WALLET
    """
    # Tính toán số tiền cho từng ví
    a_share = dev_total_value * 0.12  # 12%
    b_share = dev_total_value * 0.12  # 12%
    c_share = dev_total_value * 0.025  # 2.5%
    remaining_share = dev_total_value * 0.01  # 1%

    # print(f"Distributing DEV_CHEAT funds: A={a_share} BNB, B={b_share} BNB, C={c_share} BNB, Remaining={remaining_share} BNB")

    # Chuyển tiền đến các ví
    send_transaction(PRIVATE_KEY_DEV_CHEAT_WALLET, DEV_CHEAT_WALLET, MANH_WALLET, a_share)
    send_transaction(PRIVATE_KEY_DEV_CHEAT_WALLET, DEV_CHEAT_WALLET, TON_WALLET, b_share)
    send_transaction(PRIVATE_KEY_DEV_CHEAT_WALLET, DEV_CHEAT_WALLET, MARKETING_WALLET, c_share)
    
    # tx_hash_a = send_transaction(PRIVATE_KEY_DEV_CHEAT_WALLET, DEV_CHEAT_WALLET, MANH_WALLET, a_share)
    # if tx_hash_a:
    #     print(f"Sent {a_share} BNB to MANH_WALLET ({MANH_WALLET}). TX Hash: {tx_hash_a}")

    # tx_hash_b = send_transaction(PRIVATE_KEY_DEV_CHEAT_WALLET, DEV_CHEAT_WALLET, TON_WALLET, b_share)
    # if tx_hash_b:
    #     print(f"Sent {b_share} BNB to TON_WALLET ({TON_WALLET}). TX Hash: {tx_hash_b}")

    # tx_hash_c = send_transaction(PRIVATE_KEY_DEV_CHEAT_WALLET, DEV_CHEAT_WALLET, MARKETING_WALLET, c_share)
    # if tx_hash_c:
    #     print(f"Sent {c_share} BNB to MARKETING_WALLET ({MARKETING_WALLET}). TX Hash: {tx_hash_c}")

    # print(f"Remaining {remaining_share} BNB kept in DEV_CHEAT_WALLET.")
    
def process_incoming_transaction(wallet_address, value, blockchain):
    """
    Xử lý giao dịch đến từ FOUNDATION_WALLET và POOL_WALLET.
    Chỉ phân phối tiền từ DEV_CHEAT khi cả hai ví đã chuyển tiền vào DEV_CHEAT.
    """
    global transfer_status

    if wallet_address.lower() == FOUNDATION_WALLET.lower() and blockchain == 'bnb':
        portion = 0.2  # Contract gửi 20%, dư 5% chuyển sang DEV_CHEAT
        foundation_to_dev = (value / portion) * 0.05  # Tính dư thừa 5% từ tổng giá trị gốc
        private_key = PRIVATE_KEY_FOUNDATION_WALLET

        # Chuyển dư thừa 5% từ FOUNDATION_WALLET sang DEV_CHEAT_WALLET
        tx_hash = send_transaction(private_key, FOUNDATION_WALLET, DEV_CHEAT_WALLET, foundation_to_dev)
        if tx_hash:
            # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Transferred {foundation_to_dev} BNB from FOUNDATION_WALLET to DEV_CHEAT_WALLET. TX Hash: {tx_hash}")
            transfer_status["foundation_to_dev"] = foundation_to_dev
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to transfer {foundation_to_dev} BNB from FOUNDATION_WALLET to DEV_CHEAT_WALLET.")
            return

    elif wallet_address.lower() == POOL_WALLET.lower() and blockchain == 'bnb':
        portion = 0.4  # Contract gửi 40%, dư 12.5% chuyển sang DEV_CHEAT
        pool_to_dev = (value / portion) * 0.125  # Tính dư thừa 12.5% từ tổng giá trị gốc
        private_key = PRIVATE_KEY_POOL_WALLET

        # Chuyển dư thừa 12.5% từ POOL_WALLET sang DEV_CHEAT_WALLET
        tx_hash = send_transaction(private_key, POOL_WALLET, DEV_CHEAT_WALLET, pool_to_dev)
        if tx_hash:
            # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Transferred {pool_to_dev} BNB from POOL_WALLET to DEV_CHEAT_WALLET. TX Hash: {tx_hash}")
            transfer_status["pool_to_dev"] = pool_to_dev
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Failed to transfer {pool_to_dev} BNB from POOL_WALLET to DEV_CHEAT_WALLET.")
            return

    else:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Skipping processing for wallet: {wallet_address}")
        return
    # print("CHECK transfer_status", transfer_status);
    # Kiểm tra nếu cả hai ví đã chuyển tiền vào DEV_CHEAT
    if transfer_status["foundation_to_dev"] > 0 and transfer_status["pool_to_dev"] > 0:
        # Tính tổng giá trị 10% mà contract đã gửi trước đó cho DEV_CHEAT
        dev_received_from_contract = ((transfer_status["foundation_to_dev"] / 0.05) * 0.1)

        # Tổng DEV_CHEAT sẽ nhận (17.5% từ 2 ví + 10% từ contract)
        total_dev_value = calculate_dev_cheat_total(
            dev_received_from_contract,
            transfer_status["foundation_to_dev"],
            transfer_status["pool_to_dev"]
        )

        # Log tổng giá trị
        # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Total Value in DEV_CHEAT (27.5%): {total_dev_value}")

        # Phân phối sau khi DEV_CHEAT nhận đủ tiền
        distribute_from_dev_wallet(total_dev_value)

        # Reset trạng thái sau khi phân phối
        transfer_status["foundation_to_dev"] = 0.0
        transfer_status["pool_to_dev"] = 0.0


def monitor_wallets():
    watched_wallets = set()
    file_path = "watched_wallets.txt"
    if not os.path.exists(file_path):
        open(file_path, 'w').close()

    latest_tx_hashes = {}
    latest_tx_hashes_path = "latest_tx_hashes.json"
    if os.path.exists(latest_tx_hashes_path):
        with open(latest_tx_hashes_path, "r") as f:
            latest_tx_hashes = json.load(f)

    last_run_time = 0
    last_run_time_path = "last_run_time.txt"
    if os.path.exists(last_run_time_path):
        with open(last_run_time_path, "r") as f:
            last_run_time = int(f.read())

    while True:
        try:
            # Fetch current ETH and BNB prices in USD from CoinGecko API
            eth_usd_price_url = 'https://api.coingecko.com/api/v3/simple/price?ids=ethereum%2Cbinancecoin&vs_currencies=usd'
            response = requests.get(eth_usd_price_url)
            data = json.loads(response.text)
            eth_usd_price = data['ethereum']['usd']
            bnb_usd_price = data['binancecoin']['usd']

            # Read from file
            with open(file_path, 'r') as f:
                watched_wallets = set(f.read().splitlines())

            for wallet in watched_wallets:
                blockchain, wallet_address = wallet.split(':')
                transactions = get_wallet_transactions(wallet_address, blockchain)
                for tx in transactions:
                    tx_hash = tx['hash']
                    tx_time = int(tx['timeStamp'])

                    if tx_hash not in latest_tx_hashes and tx_time > last_run_time:
                        if tx['to'].lower() == wallet_address.lower():
                            value = float(tx['value']) / 10**18  # Convert from wei to ETH or BNB
                            usd_value = value * (eth_usd_price if blockchain == 'eth' else bnb_usd_price)  # Calculate value in USD
                            wallet_name = wallet_names.get(wallet_address, "")
                            message = f'🚨 {wallet_name} ( {wallet_address} ) đã nhận được'
                            send_telegram_notification(message, value, usd_value, tx['hash'], blockchain)
                            # print("VALUEEEEEEEEEEEEEE", value)

                            # Process specific wallets
                            process_incoming_transaction(wallet_address, value, blockchain)

                        latest_tx_hashes[tx_hash] = int(tx['blockNumber'])

            # Save latest_tx_hashes to file
            with open(latest_tx_hashes_path, "w") as f:
                json.dump(latest_tx_hashes, f)

            # Update last_run_time
            last_run_time = int(time.time())
            with open(last_run_time_path, "w") as f:
                f.write(str(last_run_time))

            # Sleep for 1 minute
            time.sleep(60)
        except Exception as e:
            print(f'An error occurred: {e}')
            # Sleep for 10 seconds before trying again
            time.sleep(10)


# Set up the Telegram bot
from telegram.ext import Updater, CommandHandler

updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Define the command handlers
def start(update, context):
    message = """
👋 Welcome to the Ethereum and Binance Wallet Monitoring Bot!

Use /add <blockchain> <wallet_address> to add a new wallet to monitor.

Example: /add ETH 0x123456789abcdef

Use /remove <blockchain> <wallet_address> to stop monitoring a wallet.

Example: /remove ETH 0x123456789abcdef

Use /list <blockchain> to list all wallets being monitored for a specific blockchain.

Example: /list ETH or just /list
"""
    context.bot.send_message(chat_id=update.message.chat_id, text=message)


def add(update, context):
    if len(context.args) < 2:
        context.bot.send_message(chat_id=update.message.chat_id, text="Please provide a blockchain and wallet address to add.")
        return

    blockchain = context.args[0].lower()
    wallet_address = context.args[1]

    if blockchain == 'eth':
        if not re.match(r'^0x[a-fA-F0-9]{40}$', wallet_address):
            context.bot.send_message(chat_id=update.message.chat_id, text=f"{wallet_address} is not a valid Ethereum wallet address.")
            return
    elif blockchain == 'bnb':
        if not re.match(r'^0x[a-fA-F0-9]{40}$', wallet_address):
            context.bot.send_message(chat_id=update.message.chat_id, text=f"{wallet_address} is not a valid Binance Smart Chain wallet address.")
            return
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text=f"Invalid blockchain specified: {blockchain}")
        return

    with open("watched_wallets.txt", "a") as f:
        f.write(f"{blockchain}:{wallet_address}\n")

    message = f'Added {wallet_address} to the list of watched {blockchain.upper()} wallets.'
    context.bot.send_message(chat_id=update.message.chat_id, text=message)


def remove(update, context):
    if len(context.args) < 2:
        context.bot.send_message(chat_id=update.message.chat_id, text="Please provide a blockchain and wallet address to remove.\nUsage: /remove ETH 0x123456789abcdef")
        return

    blockchain = context.args[0].lower()
    wallet_address = context.args[1]
    temp_file = "watched_wallets_temp.txt"

    with open("watched_wallets.txt", "r") as f, open(temp_file, "w") as temp_f:
        for line in f:
            if line.strip() != f"{blockchain}:{wallet_address}":
                temp_f.write(line)

    os.replace(temp_file, "watched_wallets.txt")

    message = f'Removed {wallet_address} from the list of watched {blockchain.upper()} wallets.'
    context.bot.send_message(chat_id=update.message.chat_id, text=message)


def list_wallets(update, context):
    with open("watched_wallets.txt", "r") as f:
        wallets = [line.strip() for line in f.readlines()]

    if wallets:
        eth_wallets = [w.split(':')[1] for w in wallets if w.startswith('eth')]
        bnTON_WALLETs = [w.split(':')[1] for w in wallets if w.startswith('bnb')]

        message = "The following wallets are being monitored:\n"
        if eth_wallets:
            message += "\nEthereum Wallets:\n" + "\n".join(eth_wallets) + "\n"
        if bnTON_WALLETs:
            message += "\nBinance Smart Chain Wallets:\n" + "\n".join(bnTON_WALLETs)

        context.bot.send_message(chat_id=update.message.chat_id, text=message)
    else:
        context.bot.send_message(chat_id=update.message.chat_id, text="No wallets are currently being monitored.")


start_handler = CommandHandler('start', start)
add_handler = CommandHandler('add', add)
remove_handler = CommandHandler('remove', remove)
list_handler = CommandHandler('list', list_wallets)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(add_handler)
dispatcher.add_handler(remove_handler)
dispatcher.add_handler(list_handler)

updater.start_polling()
monitor_wallets()
