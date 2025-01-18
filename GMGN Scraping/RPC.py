import requests
from datetime import datetime
import concurrent.futures
import time
import random

RPC_URL = "https://api.mainnet-beta.solana.com"

def make_request_with_retry(payload, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.post(RPC_URL, json=payload).json()
            if "result" in response:
                return response["result"]
            elif "error" in response and response["error"].get("code") == 429:
                wait_time = (2 ** attempt) + random.random()  # Exponential backoff with jitter
                print(f"\nRate limited. Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                continue
            else:
                print(f"\nError: {response.get('error', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"\nRequest error: {e}")
            time.sleep(1)
    return None

def fetch_signatures_for_program(program_id, limit=1000, before=None):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getSignaturesForAddress",
        "params": [
            program_id,
            {"limit": limit, "before": before}
        ]
    }
    return make_request_with_retry(payload)

def fetch_all_signatures(program_id, total_desired=5000):
    all_signatures = []
    before = None
    
    while len(all_signatures) < total_desired:
        batch = fetch_signatures_for_program(program_id, limit=100, before=before)  # Reduced batch size
        if not batch:
            break
            
        all_signatures.extend(batch)
        print(f"\rFetched {len(all_signatures)} signatures so far...", end="")
        
        before = batch[-1]["signature"]
        time.sleep(1)  # Increased delay between batches
    
    return all_signatures[:total_desired]

def fetch_transaction_details(signature):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTransaction",
        "params": [
            signature,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
        ]
    }
    return make_request_with_retry(payload)

def process_transaction(sig):
    tx_details = fetch_transaction_details(sig['signature'])
    if tx_details and "meta" in tx_details:
        pre_balances = tx_details["meta"].get("preBalances", [])
        post_balances = tx_details["meta"].get("postBalances", [])
        
        for pre, post in zip(pre_balances, post_balances):
            change = (post - pre) / 1e9
            if abs(change) > 35 and abs(change) < 43:
                timestamp = datetime.fromtimestamp(sig['blockTime'])
                return {
                    "timestamp": timestamp,
                    "amount": change,
                    "signature": sig['signature']
                }
    return None

# Your token address
program_id = "EjCdnqp7u6Y1WrK3mp2EA6Bu77jUnD45ceaZqwgTpump"

print("Fetching signatures...")
signatures = fetch_all_signatures(program_id, total_desired=5000)

if signatures:
    print(f"\nFound {len(signatures)} transactions. Analyzing transactions in parallel...")
    
    processed = 0
    matches = []
    
    # Reduced number of concurrent workers
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_sig = {executor.submit(process_transaction, sig): sig for sig in signatures}
        
        for future in concurrent.futures.as_completed(future_to_sig):
            processed += 1
            print(f"\rProcessed {processed}/{len(signatures)} transactions", end="")
            
            result = future.result()
            if result:
                matches.append(result)
                print(f"\nPotential match found!")
                print(f"Date: {result['timestamp']}")
                print(f"Amount: {result['amount']:.2f} SOL")
                print(f"Transaction: {result['signature']}")
                print("-" * 80)

    print(f"\n\nAnalysis complete. Found {len(matches)} potential matches.")