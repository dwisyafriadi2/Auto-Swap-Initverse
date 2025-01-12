# Auto swap Initverse token

This bot automatically swap token transactions and support multi account stored in the `private_keys.txt` file. Transactions are carried out randomly with the number of tokens specified by the user and can use a proxy for privacy. If no proxy is available, the bot will still run without it.

## Main Features

- Supports the use of proxies for each private key.
- Uses multi-threading for efficiency.
- Provides an option to run without a proxy if `proxy.txt` is empty.

## Requirements

- Python 3.8 or higher.
- Required Python modules (see below).

## Installation

1. **Clone the repository** or **Copy the code** and save it in a Python file named `gnit.py`.

2. **Create Configuration Files**:

   - **Create a `private_keys.txt` file** to store private keys. Example file contents:
     ```plaintext
     0xPRIVATEKEY1
     0xPRIVATEKEY2
     0xPRIVATEKEY3
     ```

   - **Create a `proxy.txt` file** to store a list of proxies (optional). Example file contents:
     ```plaintext
     http://username:password@proxy1:port
     http://username:password@proxy2:port
     ```

     If there are no proxies, leave this file empty.

3. **Install Required Python Modules**: Run the following command to install the necessary modules:
   ```bash
   pip install web3 rich requests eth-account

## Running the Bot

1. **Run the Bot**: Use the following command to run the bot:
   ```bash
   python gnit.py

## Join Telegram Channel
[Telegram Channel](https://t.me/dasarpemulung)

Credits @zamzamsalim
