ELECTRUM_VERSION = '4.0.0'   # version of the client package
PROTOCOL_VERSION = '1.2'     # protocol version requested

# The hash of the mnemonic seed must begin with this
SEED_PREFIX      = '01'      # Standard wallet
SEED_PREFIX_2FA  = '101'     # Two-factor authentication
SEED_PREFIX_SW   = '100'     # Segwit wallet

SEED_PREFIX_BPQ_XMSS10 = '20'      # BPQ wallet XMSS-10 key
SEED_PREFIX_BPQ_XMSS16 = '21'      # BPQ wallet XMSS-16 key
SEED_PREFIX_BPQ_XMSS20 = '22'      # BPQ wallet XMSS-20 key

def seed_prefix(seed_type):

    if seed_type == 'bpq-xmss10':
        return SEED_PREFIX_BPQ_XMSS10
    elif seed_type == 'bpq-xmss16':
        return SEED_PREFIX_BPQ_XMSS16
    elif seed_type == 'bpq-xmss20':
        return SEED_PREFIX_BPQ_XMSS20

    elif seed_type == 'standard':
        return SEED_PREFIX
    elif seed_type == 'segwit':
        return SEED_PREFIX_SW
    elif seed_type == '2fa':
        return SEED_PREFIX_2FA
