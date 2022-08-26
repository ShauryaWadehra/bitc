from collections import OrderedDict

"""
The b'...' notation allows the bytes to be specified with ASCII 
characters instead of hex numbers.
"""
START_INT = b'i'

START_LIST = b'l'

STRING_SEP = b':'

START_DICT = b'd'

TOKEN_END = b'e'


class Encoder:
    """
    for int -> 4 -> 'i4e'
    for string -> hello -> '5:hello'
    for list -> 'l(encode each item)e'
    for dict -> 'd(for each (encode key,encode value))e'
    """
    def __init__(self, data):
        self._data = data

    def encode(self) -> bytes:
       
        return self.encode_next(self._data)

    def encode_next(self, data):
        if type(data) == str:
            return self._encode_string(data)
        elif type(data) == int:
            return self._encode_int(data)
        elif type(data) == list:
            return self._encode_list(data)
        elif type(data) == dict or type(data) == OrderedDict:
            return self._encode_dict(data)
        elif type(data) == bytes:
            return self._encode_bytes(data)
        else:
            return None

    def _encode_int(self, value):
        return str.encode('i' + str(value) + 'e')

    def _encode_string(self, value: str):
        return str.encode(str(len(value)) + ':' + value)

    def _encode_bytes(self, value: str):
        return bytearray() + str.encode(str(len(value))) + b':' + value

    def _encode_list(self, data):
        return bytearray('l', 'utf-8') + b''.join([self.encode_next(item) for item in data]) + b'e'

    def _encode_dict(self, data: dict) -> bytes:
        result = bytearray('d', 'utf-8')
        for k, v in data.items():
            key = self.encode(k)
            value = self.encode(v)
            if key and value:
                result += key
                result += value
            else:
                raise RuntimeError('Bad dictionary')
        result += b'e'
        return result


class Decoder:
    def __init__(self, data: bytes):
        if not isinstance(data, bytes):
            raise TypeError('Argument "data" must be of type bytes')
        self._data = data
        self._index = 0

    def decode(self):

        c = self._peek()
        if c is None:
            raise EOFError('Unexpected end-of-file')
        elif c == START_INT:
            self._consume()  
            return self._decode_int()
        elif c == START_LIST:
            self._consume()  
            return self._decode_list()
        elif c == START_DICT:
            self._consume()  
            return self._decode_dict()
        elif c == TOKEN_END:
            return None
        elif c in b'01234567899':
            return self._decode_string()
        else:
            raise RuntimeError('Invalid token read at {0}'.format(
                str(self._index)))

    def _peek(self):

        if self._index + 1 >= len(self._data):
            return None
        return self._data[self._index:self._index + 1]

    def _consume(self) -> bytes:

        self._index += 1

    def _read(self, length: int) -> bytes:

        if self._index + length > len(self._data):
            raise IndexError('Cannot read {0} bytes from current position {1}'
                             .format(str(length), str(self._index)))
        res = self._data[self._index:self._index+length]
        self._index += length
        return res

    def _read_until(self, token: bytes) -> bytes:

        try:
            occurrence = self._data.index(token, self._index)
            result = self._data[self._index:occurrence]
            self._index = occurrence + 1
            return result
        except ValueError:
            raise RuntimeError('Unable to find token {0}'.format(
                str(token)))

    def _decode_int(self):
        return int(self._read_until(TOKEN_END))

    def _decode_list(self):
        res = []
        while self._data[self._index: self._index + 1] != TOKEN_END:
            res.append(self.decode())
        self._consume()
        return res

    def _decode_dict(self):
        res = OrderedDict()
        while self._data[self._index: self._index + 1] != TOKEN_END:
            key = self.decode()
            obj = self.decode()
            res[key] = obj
        self._consume()
        return res

    def _decode_string(self):
        bytes_to_read = int(self._read_until(STRING_SEP))
        data = self._read(bytes_to_read)
        return data
