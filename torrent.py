from fileinput import filename
from hashlib import sha1
from collections import namedtuple

from . import bencoder

TorrentFile = namedtuple('TorrentFile', ['name', 'length'])

class Torrent:
    """
    represent meta-data of torrent file
    this is essentially a wrapper around bencoder
    """
    def __init__(self,filename):
        self.filename = filename
        self.files = []

        with open(self.filename, 'rb') as f:
            meta_info = f.read()
            self.meta_info = bencoder.Decoder(meta_info).decode()
            info = bencoder.Encoder(self.meta_info).encode()
            """
            info hash is hash of info part of dict, hash used to 
            identify torrent
            """
            self.info_hash = sha1(info).digest()
            self._identify_files()
    
    def _identify_files(self):
        """
        Identifies files included in torrent
        """
        if self.multi_file:
            raise RuntimeError('Multi-file torrents not supported')
        self.files.append(
            TorrentFile(
                self.meta_info[b'info'][b'name'].decode('utf-8'),
                self.meta_info[b'info'][b'length']))

    @property
    def announce(self) -> str:
        """
        announce URL to the tracker.
        """
        return self.meta_info[b'announce'].decode('utf-8')

    @property
    def multi_file(self) -> bool:
        """
        multi file check
        """
        return b'files' in self.meta_info[b'info']

    @property
    def piece_length(self) -> int:
        """
        length in bytes for each piece
        """
        return self.meta_info[b'info'][b'piece length']

    @property
    def total_size(self) -> int:
        """
        The total size (in bytes) for all the files in this torrent. For a
        single file torrent this is the only file, for a multi-file torrent
        this is the sum of all files.
        """
        if self.multi_file:
            raise RuntimeError('Multi-file torrents not supported')
        return self.files[0].length

    @property
    def pieces(self):
        """
        split pieces to 20 byte hashes
        """
        data = self.meta_info[b'info'][b'pieces']
        pieces = []
        offset = 0
        length = len(data)

        while offset < length:
            pieces.append(data[offset:offset + 20])
            offset += 20
        return pieces

    @property
    def output_file(self):
        return self.meta_info[b'info'][b'name'].decode('utf-8')

    def __str__(self):
        return 'Filename: {0}\n' \
               'File length: {1}\n' \
               'Announce URL: {2}\n' \
               'Hash: {3}'.format(self.meta_info[b'info'][b'name'],
                                  self.meta_info[b'info'][b'length'],
                                  self.meta_info[b'announce'],
                                  self.info_hash)
