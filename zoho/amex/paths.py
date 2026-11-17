"""Paths shared by the Amex scripts. Override with env vars if needed."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ZOHO = os.path.dirname(HERE)                       # repo/zoho
STMT_DIR = os.environ.get("AMEX_STMT_DIR", os.path.join(HERE, "statements"))   # s_<key>.txt statement text files
sys.path.insert(0, HERE)
sys.path.insert(0, ZOHO)                            # zoho_client.py
