# Electrum - lightweight Bitcoin client
# Copyright (C) 2012 thomasv@ecdsa.org
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import os
import threading

from . import util
from . import bitcoin
from . import constants
from .bitcoin import *

MAX_TARGET = 0x00000000FFFF0000000000000000000000000000000000000000000000000000


def get_block_header_offset(height):
    return height * constants.net.BPQ_HDR_SIZE


def get_block_header_size(height):
    #return get_block_header_offset(height+1)-get_block_header_offset(height)
    return constants.net.BPQ_HDR_SIZE


def get_header_len1(data, pos, height):
    return constants.net.BPQ_HDR_SIZE


def serialize_header(res, for_hash=False):

    nMajorVersion = res['majorversion']

    height = res.get('block_height')

    nonce = res.get('nonce')
    if not (isinstance(nonce, str) and len(nonce) == 64):
        raise Exception("Invalid header nonce: {}, height: {}".format(nonce, height))

    sol = res.get('sol')
    if not (isinstance(sol, str) and len(sol) == constants.net.SOL_LENGTH * 2 and sol[:2] == int_to_hex(constants.net.SOL_LENGTH-1, 1)):
        raise Exception("Invalid header sol: {}, height: {}".format(sol, height))

    if for_hash and nMajorVersion == 0:

        s = int_to_hex(res['version'], 4) \
            + rev_hex(res['prev_block_hash']) \
            + rev_hex(res['merkle_root']) \
            + int_to_hex(int(res['timestamp']), 4) \
            + int_to_hex(int(res['bits']), 4) \
            + nonce[:8]

        if len(s) // 2 != 80:
            raise Exception("Invalid header, height: {}".format(height))

    else:

        s = int_to_hex(nMajorVersion, 1) \
            + int_to_hex(res['version'], 4) \
            + rev_hex(res['prev_block_hash']) \
            + rev_hex(res['merkle_root']) \
            + rev_hex(res['witness_merkle_root']) \
            + int_to_hex(int(res['timestamp']), 4) \
            + int_to_hex(int(res['bits']), 4) \
            + nonce \
            + sol

        if len(s) // 2 != constants.net.BPQ_HDR_SIZE:
            raise Exception("Invalid header, height: {}".format(height))

    return s


def deserialize_header(s, height):
    if not s:
        raise Exception('Invalid header: {}'.format(s))

    hex_to_int = lambda s: int('0x' + bh2u(s[::-1]), 16)

    if len(s) != constants.net.BPQ_HDR_SIZE:
        raise Exception('Invalid header length: {}'.format(len(s)))

    nonce = s[109:141].hex()
    sol = s[141:141+constants.net.SOL_LENGTH].hex()

    h = {
        'block_height': height,

        'majorversion': hex_to_int(s[0:1]),
        'version': hex_to_int(s[1:5]),

        'prev_block_hash': hash_encode(s[5:37]),
        'merkle_root': hash_encode(s[37:69]),
        'witness_merkle_root': hash_encode(s[69:101]),

        'timestamp': hex_to_int(s[101:105]),
        'bits': hex_to_int(s[105:109]),

        'nonce': nonce,
        'sol': sol
    }

    return h

def hash_header(header):
    if header is None:
        return '0' * 64
    if header.get('prev_block_hash') is None:
        header['prev_block_hash'] = '00'*32

    hdr = serialize_header(header, True)
    return hash_encode(Hash(bfh(hdr)))


blockchains = {}

def read_blockchains(config):
    blockchains[0] = Blockchain(config, 0, None)
    fdir = os.path.join(util.get_headers_dir(config), 'forks')
    if not os.path.exists(fdir):
        os.mkdir(fdir)
    l = filter(lambda x: x.startswith('fork_'), os.listdir(fdir))
    l = sorted(l, key = lambda x: int(x.split('_')[1]))
    for filename in l:
        checkpoint = int(filename.split('_')[2])
        parent_id = int(filename.split('_')[1])
        b = Blockchain(config, checkpoint, parent_id)
        h = b.read_header(b.checkpoint)
        if b.parent().can_connect(h, check_height=False):
            blockchains[b.checkpoint] = b
        else:
            util.print_error("cannot connect", filename)
    return blockchains

def check_header(header):
    if type(header) is not dict:
        return False
    for b in blockchains.values():
        if b.check_header(header):
            return b
    return False

def can_connect(header):
    for b in blockchains.values():
        if b.can_connect(header):
            return b
    return False


class Blockchain(util.PrintError):
    """
    Manages blockchain headers and their verification
    """

    def __init__(self, config, checkpoint, parent_id):
        self.config = config
        self.catch_up = None # interface catching up
        self.checkpoint = checkpoint
        self.checkpoints = constants.net.CHECKPOINTS
        self.parent_id = parent_id
        self.lock = threading.Lock()
        with self.lock:
            self.update_size()

    def parent(self):
        return blockchains[self.parent_id]

    def get_max_child(self):
        children = list(filter(lambda y: y.parent_id==self.checkpoint, blockchains.values()))
        return max([x.checkpoint for x in children]) if children else None

    def get_checkpoint(self):
        mc = self.get_max_child()
        return mc if mc is not None else self.checkpoint

    def get_branch_size(self):
        return self.height() - self.get_checkpoint() + 1

    def get_name(self):
        return self.get_hash(self.get_checkpoint()).lstrip('00')[0:10]

    def check_header(self, header):
        header_hash = hash_header(header)
        height = header.get('block_height')
        return header_hash == self.get_hash(height)

    def fork(parent, header):
        checkpoint = header.get('block_height')
        self = Blockchain(parent.config, checkpoint, parent.checkpoint)
        open(self.path(), 'w+').close()
        self.save_header(header)
        return self

    def height(self):
        return self.checkpoint + self.size() - 1

    def size(self):
        with self.lock:
            return self._size

    def update_size(self):
        p = self.path()
        if not os.path.exists(p):
            self._size = 0
            return

        fsize = os.path.getsize(p)

        self._size = fsize // constants.net.BPQ_HDR_SIZE

    def verify_header(self, header, prev_hash, target):
        _hash = hash_header(header)
        if prev_hash != header.get('prev_block_hash'):
            raise Exception("prev hash mismatch: %s vs %s" % (prev_hash, header.get('prev_block_hash')))

        #TODO: fix BPQ target
        return
        
        if constants.net.TESTNET:
            return
        bits = self.target_to_bits(target)
        if bits != header.get('bits'):
            raise Exception("bits mismatch: %s vs %s" % (bits, header.get('bits')))
        if int('0x' + _hash, 16) > target:
            raise Exception("insufficient proof of work: %s vs target %s" % (int('0x' + _hash, 16), target))

    def verify_chunk(self, index, data):

        prev_hash = self.get_hash(index * 2016 - 1)
        target = self.get_target(index-1)

        data_len = len(data)
        pos = 0
        height = index * 2016
        while pos < data_len:
            header_len = get_block_header_size(height)
            raw_header = data[pos:pos + header_len]
            header = deserialize_header(raw_header, height)

            h1 = raw_header.hex()
            h2 = serialize_header(header)
            assert(h1 == h2)

            self.verify_header(header, prev_hash, target)
            prev_hash = hash_header(header)
            height += 1
            pos += header_len
        return

    def path(self):
        d = util.get_headers_dir(self.config)
        filename = 'blockchain_headers' if self.parent_id is None else os.path.join('forks', 'fork_%d_%d'%(self.parent_id, self.checkpoint))
        return os.path.join(d, filename)

    def save_chunk(self, index, chunk):
        filename = self.path()
        d = get_block_header_offset(index * 2016) - get_block_header_offset(self.checkpoint)
        if d < 0:
            chunk = chunk[-d:]
            d = 0
        truncate = index >= len(self.checkpoints)
        self.write(chunk, d, truncate)
        self.swap_with_parent()

    def swap_with_parent(self):
        if self.parent_id is None:
            return
        parent_branch_size = self.parent().height() - self.checkpoint + 1
        if parent_branch_size >= self.size():
            return
        self.print_error("swap", self.checkpoint, self.parent_id)
        parent_id = self.parent_id
        checkpoint = self.checkpoint
        parent = self.parent()
        with open(self.path(), 'rb') as f:
            my_data = f.read()

        parrent_offs = get_block_header_offset(checkpoint) - get_block_header_offset(parent.checkpoint)
        with open(parent.path(), 'rb') as f:
            size = get_block_header_offset(self.parent().height()+1) - get_block_header_offset(self.checkpoint)
            f.seek(parrent_offs) # (checkpoint - parent.checkpoint)*80
            parent_data = f.read(size) #parent_branch_size*80)
        self.write(parent_data, 0)
        parent.write(my_data, parrent_offs) #(checkpoint - parent.checkpoint)*80)
        # store file path
        for b in blockchains.values():
            b.old_path = b.path()
        # swap parameters
        self.parent_id = parent.parent_id; parent.parent_id = parent_id
        self.checkpoint = parent.checkpoint; parent.checkpoint = checkpoint
        self._size = parent._size; parent._size = parent_branch_size
        # move files
        for b in blockchains.values():
            if b in [self, parent]: continue
            if b.old_path != b.path():
                self.print_error("renaming", b.old_path, b.path())
                os.rename(b.old_path, b.path())
        # update pointers
        blockchains[self.checkpoint] = self
        blockchains[parent.checkpoint] = parent

    def write(self, data, offset, truncate=True):
        filename = self.path()
        with self.lock:
            with open(filename, 'rb+') as f:
                my_size = get_block_header_offset(self.checkpoint+self._size) - get_block_header_offset(self.checkpoint)
                if truncate and offset != my_size: #self._size*80:
                    f.seek(offset)
                    f.truncate()
                f.seek(offset)
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            self.update_size()

    def save_header(self, header):
        height = header.get('block_height')
        delta = height - self.checkpoint
        data = bfh(serialize_header(header))
        assert delta == self.size()
        assert len(data) == get_block_header_size(height)
        offs = get_block_header_offset(height) - get_block_header_offset(self.checkpoint)
        self.write(data, offs)
        self.swap_with_parent()

    def read_header(self, height):
        assert self.parent_id != self.checkpoint
        if height < 0:
            return
        if height < self.checkpoint:
            return self.parent().read_header(height)
        if height > self.height():
            return
        hdr_size = get_block_header_size(height)
        delta = height - self.checkpoint
        name = self.path()
        if os.path.exists(name):
            with open(name, 'rb') as f:
                offs = get_block_header_offset(height) - get_block_header_offset(self.checkpoint)
                f.seek(offs)
                h = f.read(hdr_size)
                if len(h) < hdr_size:
                    raise Exception('Expected to read a full header. This was only {} bytes'.format(len(h)))
        elif not os.path.exists(util.get_headers_dir(self.config)):
            raise Exception('Electrum datadir does not exist. Was it deleted while running?')
        else:
            raise Exception('Cannot find headers file but datadir is there. Should be at {}'.format(name))
        if h == all(x == 0 for x in h): #bytes([0])*hdr_size:
            return None
        return deserialize_header(h, height)

    def get_hash(self, height):
        if height == -1:
            return '0000000000000000000000000000000000000000000000000000000000000000'
        elif height == 0:
            return constants.net.GENESIS
        elif height < len(self.checkpoints) * 2016:
            assert (height+1) % 2016 == 0, height
            index = height // 2016
            h, t = self.checkpoints[index]
            return h
        else:
            return hash_header(self.read_header(height))

    def get_target(self, index):

        #TODO: fix BPQ target
        return

        # compute target from chunk x, used in chunk x+1
        if constants.net.TESTNET:
            return 0
        if index == -1:
            return MAX_TARGET
        if index < len(self.checkpoints):
            h, t = self.checkpoints[index]
            return t
        # new target
        first = self.read_header(index * 2016)
        last = self.read_header(index * 2016 + 2015)
        bits = last.get('bits')
        target = self.bits_to_target(bits)
        nActualTimespan = last.get('timestamp') - first.get('timestamp')
        nTargetTimespan = 14 * 24 * 60 * 60
        nActualTimespan = max(nActualTimespan, nTargetTimespan // 4)
        nActualTimespan = min(nActualTimespan, nTargetTimespan * 4)
        new_target = min(MAX_TARGET, (target * nActualTimespan) // nTargetTimespan)
        return new_target

    def bits_to_target(self, bits):
        bitsN = (bits >> 24) & 0xff
        if not (bitsN >= 0x03 and bitsN <= 0x1d):
            raise Exception("First part of bits should be in [0x03, 0x1d]")
        bitsBase = bits & 0xffffff
        if not (bitsBase >= 0x8000 and bitsBase <= 0x7fffff):
            raise Exception("Second part of bits should be in [0x8000, 0x7fffff]")
        return bitsBase << (8 * (bitsN-3))

    def target_to_bits(self, target):
        c = ("%064x" % target)[2:]
        while c[:2] == '00' and len(c) > 6:
            c = c[2:]
        bitsN, bitsBase = len(c) // 2, int('0x' + c[:6], 16)
        if bitsBase >= 0x800000:
            bitsN += 1
            bitsBase >>= 8
        return bitsN << 24 | bitsBase

    def can_connect(self, header, check_height=True):
        if header is None:
            return False
        height = header['block_height']
        if check_height and self.height() != height - 1:
            #self.print_error("cannot connect at height", height)
            return False
        if height == 0:
            return hash_header(header) == constants.net.GENESIS
        try:
            prev_hash = self.get_hash(height - 1)
        except:
            return False
        if prev_hash != header.get('prev_block_hash'):
            return False
        target = self.get_target(height // 2016 - 1)
        try:
            self.verify_header(header, prev_hash, target)
        except BaseException as e:
            return False
        return True

    def connect_chunk(self, idx, hexdata):
        try:
            data = bfh(hexdata)
            self.verify_chunk(idx, data)
            self.print_error("validated chunk %d" % idx)
            self.save_chunk(idx, data)
            return True
        except BaseException as e:
            self.print_error('verify_chunk %d failed'%idx, str(e))
            return False

    def get_checkpoints(self):
        # for each chunk, store the hash of the last block and the target after the chunk
        cp = []
        n = self.height() // 2016
        for index in range(n):
            h = self.get_hash((index+1) * 2016 -1)
            target = self.get_target(index)
            cp.append((h, target))
        return cp
