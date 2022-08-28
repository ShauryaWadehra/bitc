import aiohttp
import random
import logging
import socket
from struct import unpack
from urllib.parse import urlencode

from . import bencoder


class TrackerResponse:

    # handle response of tracker after successful connection to announce URL
    def __init__(self, response: dict):
        self.response = response

    @property
    def failure(self):

        # if failed, why, else none
        if b'failure reason' in self.response:
            return self.response[b'failure reason'].decode('utf-8')
        return None

    @property
    def interval(self) -> int:
        """
        specifies the interval in secs that client should wait bw 
        sending periodic req to tracker
        """
        return self.response.get(b'interval', 0)

    @property
    def complete(self) -> int:

        # seeders -> number of peers with entire file
        return self.response.get(b'complete', 0)

    @property
    def incomplete(self) -> int:

        # leechers -> number of peers without file
        return self.response.get(b'incomplete', 0)

    @property
    def peers(self):
        """
        2 types of responses-

        list of peers is a binary string with a length of multiple of
        6 bytes. Where each peer consist of a 4 byte IP address and a 2 
        byte port number

                                    OR

        list of tuples for each peer structured as (ip,port)
        """
        peers = self.response[b'peers']
        if type(peers) == list:
            logging.debug('Dictionary model peers are returned by tracker')
            raise NotImplementedError()
        else:
            logging.debug('Binary model peers are returned by tracker')

            # split string into strings of 6 bytes(4->ip,2->port)
            peers = [peers[i:i+6] for i in range(0, len(peers), 6)]
            """
            inet_ntoa converts an IP address, which is in 32-bit packed 
            format to the popular human readable dotted-quad string format.
            """
            return [(socket.inet_ntoa(peers[:4]), _decode_port(peers[4:]))]

    def __str__(self):
        return "incomplete: {incomplete}\n" \
               "complete: {complete}\n" \
               "interval: {interval}\n" \
               "peers: {peers}\n".format(
                   incomplete=self.incomplete,
                   complete=self.complete,
                   interval=self.interval,
                   peers=", ".join([x for (x, _) in self.peers]))       


class Tracker:
    def __init__(self,torrent):
        self.torrent = torrent
        self.peer_id = _calculate_peer_id()
        self.http_client = aiohttp.ClientSession()

    async def connect(self, first: bool = None, uploaded: int = 0, downloaded: int = 0):
        """
        first-> Whether or not this is the first announce call
        uploaded-> The total number of bytes uploaded
        downloaded-> The total number of bytes downloaded

        this function makes the announce call to the tracker to update 
        with our statistics as well as get a list of available peers to 
        connect to.

        If the call was successful, the list of peers will be updated as a
        result of calling this function.
        """

        #params we need to add to the HTTP GET request
        params = {
            'info_hash': self.torrent.info_hash,
            'peer_id': self.peer_id,
            'port': 6969,
            'uploaded': uploaded,
            'downloaded': downloaded,
            'left': self.torrent.total_size - downloaded,
            #either 0 or 1 indicating whether or not to return a compact 
            #peer list
            'compact': 1
        }
        if first:
            params['event'] = 'started'
        #urlencode -> encode a dict or sequence of two-element tuples 
        #into a URL query string.
        url = self.torrent.announce + '?' + urlencode(params)
        logging.info('Connecting to tracker at: ' + url)

        async with self.http_client.get(url) as response:
            if not response.status == 200:
                raise ConnectionError('unable to make connection to tracker: status code {}'.format(response.status))
            data = await response.read()
            self.raise_for_error(data)
            return TrackerResponse(bencoder.Decoder(data).decode())

    def close(self):
        self.http_client.close()

    def raise_for_error(self, tracker_response):
        """
        fix to detect errors by tracker even when the response has a status code of 200  
        """
        try:
            message = tracker_response.decode("utf-8")
            if "failure" in message:
                raise ConnectionError('Unable to connect to tracker: {}'.format(message))

        # a successful tracker response will have non-uncicode data, so it's a safe to bet ignore this exception.
        except UnicodeDecodeError:
            pass
                


def _decode_port(port):

    # converts a 32-bit packed binary port number to int
    # '>' -> big endian, 'H' -> unsigned short
    # unpack returns tuple
    return unpack(">H", port)[0]

def _calculate_peer_id():
    """
    peer_id is exactly 20 bytes long.
    Azureus-style uses the following encoding: '-', two characters for 
    client id, four ascii digits for version number, '-', followed by 
    random numbers. 
    """
    return '-PC0001-' + ''.join([str(random.randint(0, 9)) for _ in range(12)])