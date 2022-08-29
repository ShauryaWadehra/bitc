import asyncio
import logging
import struct
from asyncio import Queue
from concurrent.futures import CancelledError
import bitstring

REQUEST_SIZE = 2**14

class ProtocolError(BaseException):
    pass

class PeerConnection:
    """
    used to download and upload pieces.

    The peer connection will consume one available peer from the given 
    queue.Based on the peer details the PeerConnection will try to open 
    a connection and perform a BitTorrent handshake.

    After a successful handshake, the PeerConnection will be in a *choked*
    state, not allowed to request any data from the remote peer. 
    
    After sending an interested message the PeerConnection will be waiting 
    to get *unchoked*. Once the remote peer unchoked us, we can start 
    requesting pieces. The PeerConnection will continue to request pieces 
    for as long as there are pieces left to request, or until the remote 
    peer disconnects.
    
    If the connection with a remote peer drops, the PeerConnection will 
    consume the next available peer from off the queue and try to connect 
    to that one instead.
    """
    def __init__(self, queue: Queue, info_hash, peer_id, piece_manager, on_block_cb=None):
        """
        contructs a PeerConnection and add it to the asyncio event -loop

        queue-> async Queue containing available peers
        info_hash -> we know
        peer_id->identify ourselves
        piece_manager-> determine which pieces to request
        on_block_cb-> callback when block recived
        """
        self.my_state = []
        self.peer_state = []
        self.queue = queue
        self.info_hash = info_hash
        self.peer_id = peer_id
        self.remote_id = None
        self.writer = None
        self.reader = None
        self.piece_manager = piece_manager
        self.on_block_cb = on_block_cb
        self.future = asyncio.ensure_future(self._start())