from typing import List
from pathlib import Path
from zlib import decompress
from re import sub
from math import sqrt, pow

_WHITE_SPACE = {0x00, 0x09, 0x0A, 0x0C, 0x0D, 0x20}
_DELIMITERS = {0x28, 0x29, 0x3C, 0x3E, 0x5B, 0x5D, 0x7B, 0x7D, 0x2F, 0x25}
_NAME_CHARS = set(range(0x21, 0x7F)) - _WHITE_SPACE - _DELIMITERS
_DIGITS = {0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39}
_NUMBER_CHARS = {0x2B, 0x2D, 0x2E} | _DIGITS
_HEX_DIGITS = {0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66} | _DIGITS

_CUSTOM_FONTS = {
    b'AAGAPI+txexs': {
        b'RANGE': {1: [(b'\x02', b'\x02')]},
        b'MAX_LEN': 1,
        b'MAPPING': {1: {b'\x02': 'Σ'}},
        b'WIDTHS': [0.808],
        b'AVG_WIDTH': 0.808,
        b'FIRST_CHAR': 2,
        b'ASCENT': 0,
        b'DESCENT': -0.72,
        b'WEIGHT': 400
    },
    b'WinAnsiEncoding': {
        b'RANGE': {1: [
            (b'\x00', b'\x80'),
            (b'\x82', b'\x8c'),
            (b'\x8e', b'\x8e'),
            (b'\x91', b'\x9c'),
            (b'\x9e', b'\xff'),
        ]},
        b'MAX_LEN': 1,
        b'MAPPING': {1: dict([(bytes([c]), bytes([c]).decode(encoding = "cp1252")) \
            for c in range(0, 0x100) if c not in [0x81, 0x8d, 0x8f, 0x90, 0x9d]])}
    },
    b'Helvetica': {
        b'RANGE': {1: [
            (b'\x00', b'\x80'),
            (b'\x82', b'\x8c'),
            (b'\x8e', b'\x8e'),
            (b'\x91', b'\x9c'),
            (b'\x9e', b'\xff'),
        ]},
        b'MAX_LEN': 1,
        b'MAPPING': {1: dict([(bytes([c]), bytes([c]).decode(encoding = "cp1252")) \
            for c in range(0, 0x100) if c not in [0x81, 0x8d, 0x8f, 0x90, 0x9d]])},
        b'WIDTHS': [],
        b'AVG_WIDTH': 0.667,
        b'FIRST_CHAR': 0,
        b'ASCENT': 0.71,
        b'DESCENT': -0.242,
        b'WEIGHT': 400
    },
    b'Helvetica-Bold': {
        b'RANGE': {1: [
            (b'\x00', b'\x80'),
            (b'\x82', b'\x8c'),
            (b'\x8e', b'\x8e'),
            (b'\x91', b'\x9c'),
            (b'\x9e', b'\xff'),
        ]},
        b'MAX_LEN': 1,
        b'MAPPING': {1: dict([(bytes([c]), bytes([c]).decode(encoding = "cp1252")) \
            for c in range(0, 0x100) if c not in [0x81, 0x8d, 0x8f, 0x90, 0x9d]])},
        b'WIDTHS': [],
        b'AVG_WIDTH': 0.667,
        b'FIRST_CHAR': 0,
        b'ASCENT': 0.71,
        b'DESCENT': -0.242,
        b'WEIGHT': 700
    },
    b'NONE': {
        b'RANGE': dict(),
        b'MAX_LEN': 0,
        b'MAPPING': dict(),
        b'WIDTHS': [],
        b'AVG_WIDTH': 0.667,
        b'FIRST_CHAR': 0,
        b'ASCENT': 0.71,
        b'DESCENT': -0.242,
        b'WEIGHT': 400
    }
}
_CUSTOM_FONTS[b'Times-Roman'] = _CUSTOM_FONTS[b'Helvetica']

def _decode_font_bytes(data : bytes, font : dict) -> str:
    start = 0
    value = list()

    while start < len(data):
        byte_count = 0
        for byte_len in range(1, font[b'MAX_LEN'] + 1):
            if not byte_len in font[b'RANGE']: continue
            for byte_range in font[b'RANGE'][byte_len]:
                if all(byte_range[0][b] <= data[start + b] <= byte_range[1][b] for b in range(0, byte_len)):
                    byte_count = byte_len
                    break

            if byte_count > 0: break

        if byte_count == 0:
            value.append((" ", font[b'AVG_WIDTH']))
            start += 1
        elif not data[start : start + byte_count] in font[b'MAPPING'][byte_count]:
            try:
                value.append((font[b'MAPPING'][byte_count].decode(encoding = "utf-8"), font[b'AVG_WIDTH']))
            except:
                value.append((" ", font[b'AVG_WIDTH']))
        elif 0 <= (idx := int.from_bytes(data[start : start + byte_count], "big") - font[b'FIRST_CHAR']) < len(font[b'WIDTHS']) \
            and font[b'WIDTHS'][idx] != 0:
            value.append((font[b'MAPPING'][byte_count][data[start : start + byte_count]], \
                font[b'WIDTHS'][idx]))
        else:
            value.append((font[b'MAPPING'][byte_count][data[start : start + byte_count]], \
                font[b'AVG_WIDTH']))
        start += byte_count

    return value

def _byte_strip(data : bytes) -> bytes:
    a, b = 0, len(data) - 1
    while data[a] in _WHITE_SPACE: a += 1
    while data[b] in _WHITE_SPACE: b -= 1

    return data[a : b + 1]

def _read_name(data : bytes, start : int) -> (bytes, int):
    assert data[start] == 0x2F, "Expected solidus at start of name!"
    start += 1

    real_name = bytearray()
    while data[start] in _NAME_CHARS:
        if data[start] != 0x23:
            real_name.append(data[start])
            start += 1
        elif data[start + 1] == 0x23:
            real_name.append(0x25)
            start += 2
        else:
            real_name.append(int(data[start + 1: start + 3].decode(), base = 16))
            start += 3

    return bytes(real_name), start

def _read_array(data : bytes, start : int) -> ([object], int):
    assert data[start] == 0x5B, "Expected keyword [ at start of array!"
    start += 1

    array = []
    while True:
        while data[start] in _WHITE_SPACE: start += 1
        if data[start] == 0x5D: break

        obj, start = _read_value(data, start)
        array.append(obj)
    
    return array, start + 1

def _read_byte_string(data : bytes, start : int) -> (bytearray, int):
    assert data[start] == 0x3C, "Expected keyword < at start of bytestring!"
    start += 1

    array = bytearray()
    while True:
        if data[start] == 0x3E: 
            break
        elif data[start] in _HEX_DIGITS:
            array.append(data[start])
            start += 1
        elif data[start] in _WHITE_SPACE: 
            start += 1
        else:
            raise ValueError("Unsupported byte in bytestring!")

    if len(array) & 0b1: array.append(0x30)

    bytestr = bytearray()
    for a in range(0, len(array), 2):
        bytestr.append(int(array[a: a + 2].decode(), base = 16))

    return bytes(bytestr), start + 1

def _read_literal_string(data : bytes, start : int) -> (bytearray, int):
    assert data[start] == 0x28, "Expected ( at start of literal string!"
    start += 1
    depth = 0

    string = bytearray()
    while True:
        if data[start] == 0x28:
            string.append(0x28)
            start += 1
            depth += 1
        elif data[start] == 0x29:
            if depth == 0: break
            string.append(0x29)
            start += 1
            depth -= 1
        elif data[start] == 0x5C:
            if data[start + 1] == 0x6E:
                string.append(0x0A)
                start += 2
            elif data[start + 1] == 0x72:
                string.append(0x0D)
                start += 2
            elif data[start + 1] == 0x74:
                string.append(0x09)
                start += 2
            elif data[start + 1] == 0x62:
                string.append(0x08)
                start += 2
            elif data[start + 1] == 0x66:
                string.append(0x0C)
                start += 2
            elif data[start + 1] == 0x28:
                string.append(0x28)
                start += 2
            elif data[start + 1] == 0x29:
                string.append(0x29)
                start += 2
            elif data[start + 1] == 0x5C:
                string.append(0x5C)
                start += 2
            elif data[start + 1] == 0x0D:
                if data[start + 2] == 0x0A: start += 3
                else: start += 2
            elif data[start + 1] == 0x0A:
                start += 2
            elif data[start + 1] in _DIGITS:
                if data[start + 2] in _DIGITS:
                    if data[start + 3] in _DIGITS:
                        string.append(int(data[start + 1: start + 4].decode(), base = 8))
                        start += 4
                    else:
                        string.append(int(data[start + 1: start + 3].decode(), base = 8))
                        start += 3
                else:
                    string.append(int(data[start + 1: start + 2].decode(), base = 8))
                    start += 2
            else:
                start += 1
        elif data[start] == 0x0D:
            if data[start + 1] == 0x0A: start += 2
            else: start += 1
            string.append(0x0A)
        else:
            string.append(data[start])
            start += 1

    return bytes(string), start + 1

def _read_number(data : bytes, start : int, single : bool = False) -> (object, int):
    a, b, tmp = start, 0, 0

    if data[start] in _DIGITS:
        while data[a] in _DIGITS: a += 1
        if data[a] == 0x2E:
            a += 1
            while data[a] in _DIGITS: a += 1
            return float(data[start : a].decode()), a
        tmp = int(data[start : a].decode())
        if single or data[a] not in _WHITE_SPACE: return tmp, a
        b = a
        while data[a] in _WHITE_SPACE: a += 1
        if data[a] not in _DIGITS: return tmp, b
        start = a
        while data[a] in _DIGITS: a += 1
        if data[a] not in _WHITE_SPACE: return tmp, b
        tmp = (tmp, int(data[start : a].decode()))
        while data[a] in _WHITE_SPACE: a += 1
        if data[a] == 0x52: return tmp, a + 1
        else: return tmp[0], b
    elif data[start] in _NUMBER_CHARS:
        if data[start] == 0x2B or data[start] == 0x2D: start += 1
        while data[start] in _DIGITS: start += 1
        if data[start] == 0x2E: start += 1
        while data[start] in _DIGITS: start += 1
        if a - start == 1 or a - start == 2 and data[start - 1] == 0x2E: raise ValueError("Unsupported number format!")
        return float(data[a : start].decode()) if 0x2E in data[a : start] else int(data[a : start].decode()), start
    else:
        raise ValueError("Unsupported value in number!")

def _read_value(data : bytes, start : int) -> (object, int):
    a, tmp = start, 0
    
    if data[start] == 0x74:
        if data[start : start + 4] == b'true': return True, start + 4
        else: raise ValueError("Expected keyword true as value!")
    elif data[start] == 0x66:
        if data[start : start + 5] == b'false': return False, start + 5
        else: raise ValueError("Expected keyword false as value!")
    elif data[start] == 0x6E:
        if data[start : start + 4] == b'null': return None, start + 4
        else: raise ValueError("Expected keyword null as value!")
    elif data[start] in _NUMBER_CHARS:
        return _read_number(data, start)
    elif data[start] == 0x5B:
        return _read_array(data, start)
    elif data[start : start + 2] == b'<<':
        return _read_dictionary(data, start)
    elif data[start] == 0x3C:
        return _read_byte_string(data, start)
    elif data[start] == 0x2F:
        return _read_name(data, start)
    elif data[start] == 0x28:
        return _read_literal_string(data, start)

    else:
        raise ValueError("Unsupported data value!")

def _read_dictionary(data : bytes, start : int) -> (dict, int):
    assert data[start : start + 2] == b'<<', "Expected keyword << at start of dictionary!"
    start += 2
    dictionary = dict()

    while True:
        while data[start] in _WHITE_SPACE: start += 1
        if data[start : start + 2] == b'>>': 
            break

        key, start = _read_name(data, start)
        while data[start] in _WHITE_SPACE: start += 1
        value, start = _read_value(data, start)
        dictionary[key] = value

    return dictionary, start + 2

def _test_for_obj(data : bytes, start : int) -> bool:
    if not data[start] in _DIGITS: return False
    while data[start] in _DIGITS: start += 1
    if not data[start] in _WHITE_SPACE: return False
    while data[start] in _WHITE_SPACE: start += 1
    if not data[start] in _DIGITS: return False
    while data[start] in _DIGITS: start += 1
    if not data[start] in _WHITE_SPACE: return False
    while data[start] in _WHITE_SPACE: start += 1
    return data[start : start + 3] == b'obj'

def _read_object(data : bytes, start : int) -> (dict, int):
    obj = dict()

    if not data[start] in _DIGITS: raise ValueError("Expected an id at the start of object!")
    a = start
    while data[start] in _DIGITS: start += 1
    tmp = int(data[a : start].decode())
    if not data[start] in _WHITE_SPACE: raise ValueError("Expected an id at the start of object!")
    while data[start] in _WHITE_SPACE: start += 1
    if not data[start] in _DIGITS: raise ValueError("Expected an id at the start of object!")
    a = start
    while data[start] in _DIGITS: start += 1
    obj[b'KEY'] = (tmp, int(data[a : start].decode()))
    if not data[start] in _WHITE_SPACE: raise ValueError("Expected an id at the start of object!")
    while data[start] in _WHITE_SPACE: start += 1
    if not data[start : start + 3] == b'obj': raise ValueError("Expected keyword obj at start of object!")
    start += 3
    while data[start] in _WHITE_SPACE: start += 1

    obj_value, start = _read_value(data, start)
    obj[b'VALUE'] = obj_value
    while data[start] in _WHITE_SPACE: start += 1
    if data[start : start + 6] == b'endobj': return obj, start + 6

    if not data[start : start + 6] == b'stream': raise ValueError("Unknown keyword in object!")
    if not b'Length' in obj_value: raise ValueError("Missing stream length in object!")
    start += 6

    if data[start] == 0x0D and data[start + 1] == 0x0A: start += 2
    elif data[start] == 0x0A: start += 1

    obj[b'STREAM'] = data[start : start + obj_value[b'Length']]
    start += obj_value[b'Length']

    while data[start] in _WHITE_SPACE: start += 1
    if not data[start : start + 9] == b'endstream': raise ValueError("Expected keyword endstream at end of stream!")
    start += 9
    while data[start] in _WHITE_SPACE: start += 1
    if not data[start : start + 6] == b'endobj': raise ValueError("Expected keyword endobj at end of stream!")

    if not b'Filter' in obj_value: return obj, start + 6

    return _uncompress(obj), start + 6

def _seek_object_definition(data : bytes, start : int, key : (int, int)) -> int:
    data = data[max(0, start - 511) : start + 512]
    start, a = 0, 0
    while start < len(data):
        while data[start : start + 4] != b' obj': start += 1
        a = start - 1
        while data[a] in _DIGITS: a -= 1
        if key[1] != _read_number(data, a + 1, single = True)[0]: 
            start += 1
            continue
        while data[a] in _WHITE_SPACE: a -= 1
        while data[a] in _DIGITS: a -= 1
        if key[0] != _read_number(data, a + 1, single = True)[0]: 
            start += 1
            continue

        return a + 1
    
    raise ValueError("Unable to find supplied key!")

def _load_object(data : bytes, xref : dict, key : (int, int)) -> object:
    if not key in xref: raise KeyError("Key missing in xref!")

    ref = xref[key]
    if type(ref) != dict or ref.get(b'TYPE', None) not in [b'REF', b'STREAM_REF']: 
        return ref

    if ref[b'TYPE'] == b'REF':
        while data[ref[b'POS']] in _WHITE_SPACE: ref[b'POS'] += 1
        if not _test_for_obj(data, ref[b'POS']):
            ref[b'POS'] = _seek_object_definition(data, ref[b'POS'], key)
        obj, _ = _read_object(data, ref[b'POS'])
    else:
        object_stream = _load_object(data, xref, ref[b'POS'])
        if not object_stream[b'VALUE'][b'Type'] == b'ObjStm': raise ValueError("Expected stream of type object stream!")
        if b'Extends' in object_stream[b'VALUE']: raise NotImplementedError("Extended streams not yet implemented!")
        
        start = 0
        stream = object_stream[b'STREAM']

        while ref[b'INDEX'] > 0:
            while stream[start] in _WHITE_SPACE: start += 1
            while stream[start] in _DIGITS: start += 1
            while stream[start] in _WHITE_SPACE: start += 1
            while stream[start] in _DIGITS: start += 1
            ref[b'INDEX'] -= 1
        
        while stream[start] in _WHITE_SPACE: start += 1
        idx, start = _read_number(stream, start, single = True)
        if idx != key[0]: raise ValueError("Index value is not matching key in object stream!")
        while stream[start] in _WHITE_SPACE: start += 1
        start, _ = _read_number(stream, start, single = True)

        start += object_stream[b'VALUE'][b'First']
        obj = {
            b'KEY': key,
            b'VALUE': _read_value(stream, start)[0]
        }

    xref[key] = obj
    return obj

def predictor(data, predictor, colors, bits, columns) -> bytes:
    if colors != 1: raise NotImplementedError("Prediction color value not yet implemented!")
    if bits != 8: raise NotImplementedError("Prediction bits value not yet implemented!")

    if predictor == 1:
        return data
    elif predictor == 2:
        raise NotImplementedError("TIFF predictor not yet implemented!")
    else:
        data += bytes(columns)
        data_rows = []
        for i in range(0, len(data), columns + 1):
            data_rows.append((data[i], (bytearray(data[i + 1 : i + columns + 1]))))
        data_rows.pop()

        data = bytearray()
        if predictor == 10:
            for _, line in data_rows:
                data.extend(line)
            return bytes(data)
        elif predictor == 11:
            for _, line in data_rows:
                prior = 0
                for value in line:
                    prior = (prior + value) % 256
                    data.append(value)
            return bytes(data)
        elif predictor == 12:
            up = bytearray(columns)
            for _, line in data_rows:
                for i in range(columns):
                    up[i] = (up[i] + line[i]) % 256
                    data.append(up[i])
            return bytes(data)
        elif predictor == 13:
            up = bytearray(columns)
            for _, line in data_rows:
                prior = 0
                for i in range(columns):
                    up[i] = (line[i] + (prior + up[i]) // 2) % 256
                    prior = up[i]
                    data.append(up[i])
            return bytes(data)
        else:
            raise NotImplementedError(f"PNG predictor {predictor} not yet implemented!")

def _flate_decode(obj : dict, parms : dict) -> dict:
    obj[b'STREAM'] = decompress(obj[b'STREAM'], wbits = 0)

    if parms != None:
        obj[b'STREAM'] = predictor(obj[b'STREAM'], parms.get(b'Predictor', 1), parms.get(b'Colors', 1), \
            parms.get(b'BitsPerComponent', 8), parms.get(b'Columns', 1))
    return obj

def _uncompress(obj : dict) -> dict:
    if obj.get(b'VALUE', dict()).get(b'Subtype') == b'Image':
        return obj

    if not b'VALUE' in obj or not b'STREAM' in obj: raise ValueError("object not in required format during uncompression!")
    if not b'Filter' in obj[b'VALUE']: raise ValueError("Missing keyword Filter in object value!")

    if type(obj[b'VALUE'][b'Filter']) != list: obj[b'VALUE'][b'Filter'] = [obj[b'VALUE'][b'Filter']] 
    if not b'DecodeParms' in obj[b'VALUE']: obj[b'VALUE'][b'DecodeParms'] = [None] * len(obj[b'VALUE'][b'Filter'])
    elif type(obj[b'VALUE'][b'DecodeParms']) != list: obj[b'VALUE'][b'DecodeParms'] = [obj[b'VALUE'][b'DecodeParms']]

    while obj[b'VALUE'][b'Filter']:
        parms = obj[b'VALUE'][b'DecodeParms'].pop(0)
        match obj[b'VALUE'][b'Filter'].pop(0):
            case b'FlateDecode':
                obj = _flate_decode(obj, parms)
            case v:
                raise NotImplementedError(f"Filtertype {v} not yet implemented")

    obj[b'VALUE'].pop(b'Filter')
    obj[b'VALUE'].pop(b'DecodeParms')

    return obj

def _load_properties(data : bytes, xref : dict, page : dict) -> dict:
    props = dict()

    for prop_name, resource in page.get(b'Resources', dict()).get(b'Properties', dict()).items():
        _load_object(data, xref, resource)
        props[prop_name] = resource
    
    return props

def _load_graphic_states(data : bytes, xref : dict, page : dict) -> dict:
    states = dict()

    for state_name, resource in page.get(b'Resources', dict()).get(b'ExtGState', dict()).items():
        _load_object(data, xref, resource)
        states[state_name] = resource
    
    return states

def _load_font_decodes(data : bytes, xref : dict, resources : dict) -> dict:
    fonts = dict()
    res = resources.get(b'Font', dict())
    if type(res) == tuple:
        res = _load_object(data, xref, res)[b'VALUE']

    for font_name, resource in res.items():
        font_obj = _load_object(data, xref, resource)
        if font_obj.get(b'FONT', None) != None:
            fonts[font_name] = resource
            continue

        if font_obj[b'VALUE'].get(b'BaseFont', None) in {b'Helvetica', b'Helvetica-Bold', b'Times-Roman'}:
            font_obj[b'FONT'] = _CUSTOM_FONTS[font_obj[b'VALUE'][b'BaseFont']]
            fonts[font_name] = resource
            continue

        if font_obj[b'VALUE'][b'Subtype'] == b'Type3':
            if not b'ToUnicode' in font_obj[b'VALUE']:
                font_obj[b'FONT'] = _CUSTOM_FONTS[b'NONE']
                fonts[font_name] = resource
                continue
            else:
                raise NotImplementedError("Type3 font with unicode encoding not yet implemented!")

        if font_obj[b'VALUE'][b'Subtype'] not in {b'Type1', b'TrueType', b'Type0'}: 
            raise NotImplementedError(f"{font_obj[b'VALUE'][b'Subtype']} Font not yet implemented!")

        if font_obj[b'VALUE'][b'Subtype'] == b'Type0':
            descendants = font_obj[b'VALUE'][b'DescendantFonts']
            if type(descendants) == tuple:
                descendants = _load_object(data, xref, descendants)[b'VALUE']
            cid_font = _load_object(data, xref, descendants[0])
            if not b'FontDescriptor' in cid_font[b'VALUE']: raise NotImplementedError("Type 0 fonts without cid font descriptors not yet implemented")
            font_desc = _load_object(data, xref, cid_font[b'VALUE'][b'FontDescriptor'])

            if not b'W' in cid_font[b'VALUE']: raise NotImplementedError("Type 0 fonts without font width not yet implemented")

            w = cid_font[b'VALUE'][b'W']
            if type(w) == tuple:
                w = _load_object(data, xref, w)[b'VALUE']

            if w:
                w = w.copy()

                a, b = w.pop(0), w.pop(0)
                if type(b) != list:
                    c = w.pop(0)
                    start = a
                    end = b
                    widths = [c] * (b - a + 1)
                else:
                    start = a
                    end = a + len(b) - 1
                    widths = b
                
                while w:
                    a, b = w.pop(0), w.pop(0)
                    if type(b) != list:
                        c = w.pop(0)
                        if a < start and b > end:
                            start = a
                            end = b
                            widths = [c] * (b - a + 1)
                        elif a < start:
                            widths = [0] * (start - a) + widths
                            start = a
                            for i in range(a, b + 1): widths[i - start] = c
                        elif b > end:
                            widths = widths + [0] * (b - end)
                            end = b
                            for i in range(a, b + 1): widths[i - start] = c
                        else:
                            for i in range(a, b + 1): widths[i - start] = c
                    else:
                        c = a + len(b) - 1
                        if a < start and c > end:
                            start = a
                            end = c
                            widths = b
                        elif a < start:
                            widths = [0] * (start - a) + widths
                            start = a
                            for i in range(0, len(b)): widths[i] = b[i]
                        elif c > end:
                            widths = widths + [0] * (c - end)
                            end = c
                            for i in range(0, len(b)): widths[i + a - start] = b[i]
                        else:
                            for i in range(0, len(b)): widths[i + a - start] = b[i]

                font_obj[b'VALUE'][b'Widths'] = widths
                font_obj[b'VALUE'][b'FirstChar'] = start
            else:
                font_obj[b'VALUE'][b'Widths'] = []
                font_obj[b'VALUE'][b'FirstChar'] = 0

            if b'DW' in cid_font[b'VALUE']:
                font_desc[b'VALUE'][b'AvgWidth'] = cid_font[b'VALUE'][b'DW']
        else:
            font_desc = _load_object(data, xref, font_obj[b'VALUE'][b'FontDescriptor'])
        
        widths = font_obj[b'VALUE'].get(b'Widths', None)
        if widths == None: raise NotImplementedError("Font without widths not yet implemented!")
        elif type(widths) == tuple:
            widths = _load_object(data, xref, widths)[b'VALUE']
        font_obj[b'VALUE'][b'Widths'] = [w / 1000 for w in widths]

        if not b'FontWeight' in font_desc[b'VALUE']:
            if font_desc[b'VALUE'].get(b'StemV', 0) == 0: font_desc[b'VALUE'][b'FontWeight'] = 400
            else: font_desc[b'VALUE'][b'FontWeight'] = 700 if font_desc[b'VALUE'][b'StemV'] > 100 else 400

        if not b'Ascent' in font_desc[b'VALUE'] or not b'Descent' in font_desc[b'VALUE']: 
            raise NotImplementedError("Font without height values not yet implemented!")
        font_desc[b'VALUE'][b'Ascent'] = font_desc[b'VALUE'][b'Ascent'] / 1000 if font_desc[b'VALUE'][b'Ascent'] else 0.71
        font_desc[b'VALUE'][b'Descent'] = font_desc[b'VALUE'][b'Descent'] / 1000 if font_desc[b'VALUE'][b'Descent'] else -0.242

        encoding = font_obj[b'VALUE'].get(b'Encoding', None)
        if type(encoding) != dict and encoding != None and encoding in _CUSTOM_FONTS:
            font = _CUSTOM_FONTS[encoding].copy()
            font[b'WIDTHS'] = font_obj[b'VALUE'][b'Widths']
            font[b'FIRST_CHAR'] = font_obj[b'VALUE'][b'FirstChar']
            font[b'ASCENT'] = font_desc[b'VALUE'][b'Ascent']
            font[b'DESCENT'] = font_desc[b'VALUE'][b'Descent']
            font[b'WEIGHT'] = font_desc[b'VALUE'][b'FontWeight']

            font_obj[b'FONT'] = font
            fonts[font_name] = resource
            continue

        if not b'ToUnicode' in font_obj[b'VALUE']:
            font = _CUSTOM_FONTS.get(font_obj[b'VALUE'][b'BaseFont'], None)
            if font == None: font = _CUSTOM_FONTS[b'Times-Roman']

            font_obj[b'FONT'] = font
            fonts[font_name] = resource
            continue

        c_map = _load_object(data, xref, font_obj[b'VALUE'][b'ToUnicode'])[b'STREAM']
        start = 0
        stack = []

        stack = []
        code_space_ranges = dict()
        code_space_mappings = dict()
        max_code_len = 0

        while c_map[start : start + 9] != b'begincmap': start += 1
        start += 9
        while True:
            if c_map[start] in _WHITE_SPACE: start += 1

            elif c_map[start : start + 3] == b'def':
                stack.clear()
                start += 3
            elif c_map[start : start + 19] == b'begincodespacerange':
                start += 19
                for _ in range(stack.pop()):
                    while c_map[start] in _WHITE_SPACE: start += 1
                    a, start = _read_byte_string(c_map, start)
                    while c_map[start] in _WHITE_SPACE: start += 1
                    b, start = _read_byte_string(c_map, start)
                    code_space_ranges.setdefault(len(b), []).append((a, b))
                    if len(b) > max_code_len: max_code_len = len(b)
                while c_map[start] in _WHITE_SPACE: start += 1
                if c_map[start : start + 17] != b'endcodespacerange': raise ValueError("Expected keyword endcodespacerange at end of codespacerange!")
                start += 17
            elif c_map[start : start + 11] == b'beginbfchar':
                start += 11
                for _ in range(stack.pop()):
                    while c_map[start] in _WHITE_SPACE: start += 1
                    a, start = _read_byte_string(c_map, start)
                    while c_map[start] in _WHITE_SPACE: start += 1
                    b, start = _read_byte_string(c_map, start)
                    code_space_mappings.setdefault(len(a), dict())[a] = b.decode("UTF-16BE")
                while c_map[start] in _WHITE_SPACE: start += 1
                if c_map[start : start + 9] != b'endbfchar': raise ValueError("Expected keyword endbfchar at end of bfchar!")
                start += 9
            elif c_map[start : start + 12] == b'beginbfrange':
                start += 12
                for _ in range(stack.pop()):
                    while c_map[start] in _WHITE_SPACE: start += 1
                    a, start = _read_byte_string(c_map, start)
                    a = int.from_bytes(a, "big")
                    while c_map[start] in _WHITE_SPACE: start += 1
                    b, start = _read_byte_string(c_map, start)
                    while c_map[start] in _WHITE_SPACE: start += 1
                    if c_map[start] == 0x5B:
                        c, start = _read_array(c_map, start)
                        for i in range(len(c)):
                            code_space_mappings.setdefault(len(b), dict())[(a + i).to_bytes(len(b), "big")] = c[i].decode("UTF-16BE")
                    else:
                        c, start = _read_byte_string(c_map, start)
                        len_c = len(c)
                        c = int.from_bytes(c, "big")
                        for i in range(0, int.from_bytes(b, "big") - a + 1):
                            code_space_mappings.setdefault(len(b), dict())[(a + i).to_bytes(len(b), "big")] = \
                                (c + i).to_bytes(len_c, "big").decode("UTF-16BE")

                while c_map[start] in _WHITE_SPACE: start += 1
                if c_map[start : start + 10] != b'endbfrange': raise ValueError("Expected keyword endbfrange at end of bfrange!")
                start += 10
            elif c_map[start : start + 7] == b'endcmap':
                break 

            elif c_map[start] == 0x2f:
                obj, start = _read_name(c_map, start)
                stack.append(obj)
            elif c_map[start : start + 2] == b'<<':
                obj, start = _read_dictionary(c_map, start)
                stack.append(obj)
            elif c_map[start] in _DIGITS:
                obj, start = _read_number(c_map, start, single = True)
                stack.append(obj)

            else:
                raise ValueError("Unrecognized symbol in unicode map!")
        
        font = {
            b'RANGE': code_space_ranges,
            b'MAX_LEN': max_code_len,
            b'MAPPING': code_space_mappings,
            b'WIDTHS': font_obj[b'VALUE'][b'Widths'],
            b'AVG_WIDTH': font_desc[b'VALUE'].get(b'AvgWidth', 667) / 1000,
            b'FIRST_CHAR': font_obj[b'VALUE'][b'FirstChar'],
            b'ASCENT': font_desc[b'VALUE'][b'Ascent'],
            b'DESCENT': font_desc[b'VALUE'][b'Descent'],
            b'WEIGHT': font_desc[b'VALUE'][b'FontWeight']
        }

        font_obj[b'FONT'] = font
        fonts[font_name] = resource

    return fonts

def _generate_sections(bbox: [float], width : float, height: float, lines : [dict]) -> [dict]:
    # Split page by line seperators
    horizontals = list()
    verticals = list()

    for line in lines:
        (a_x, a_y), (b_x, b_y), (c_x, c_y), _ = line[b'BBox']
        del line[b'BBox']
        if (c_x - a_x) + (b_y - a_y) < 3: continue

        line[b'Start'] = (a_x, a_y)
        line[b'Used'] = False

        if c_x - a_x > b_y - a_y:
            line[b'End'] = (c_x, c_y)
            horizontals.append(line)
        else:
            line[b'End'] = (b_x, b_y)
            verticals.append(line)

    sections = [{
        b'Height': height,
        b'Width': width,
        b'Start': (bbox[0], bbox[1]),
        b'End': (bbox[2], bbox[3]),
        b'InStart': (bbox[0] + 0.2 * width, bbox[1] + 0.2 * height),
        b'InEnd': (bbox[2] - 0.2 * width, bbox[3] - 0.2 * height)
    }]

    change = True
    while change:
        change = False

        for line in horizontals:
            if line[b'Used']: continue

            for section in sections:
                if not section[b'Start'][1] <= line[b'Start'][1] <= section[b'End'][1]:
                    continue

                if not line[b'Start'][0] <= section[b'InStart'][0]:
                    continue
                if not line[b'End'][0] >= section[b'InEnd'][0]:
                    continue

                new_height = section[b'End'][1] - line[b'Start'][1]
                sections.append({
                    b'Height': new_height,
                    b'Width': section[b'Width'],
                    b'Start': (section[b'Start'][0], line[b'Start'][1]),
                    b'End': section[b'End'],
                    b'InStart': (section[b'InStart'][0], line[b'Start'][1] + 0.2 * new_height),
                    b'InEnd': (section[b'InEnd'][0], section[b'End'][1] - 0.2 * new_height)
                })
                section[b'Height'] -= new_height
                section[b'End'] = (section[b'End'][0], line[b'Start'][1])
                section[b'InStart'] = (section[b'InStart'][0], section[b'Start'][1] + 0.2 * section[b'Height'])
                section[b'InEnd'] = (section[b'InEnd'][0], section[b'End'][1] - 0.2 * section[b'Height'])

                for v_line in verticals:
                    if v_line[b'Used']: continue

                    if not line[b'Start'][0] <= v_line[b'Start'][0] <= line[b'End'][0]: 
                        continue
                    if not v_line[b'Start'][1] <= line[b'Start'][1] <= v_line[b'End'][1]:
                        continue

                    verticals.append({
                        b'Start': (v_line[b'Start'][0], line[b'Start'][1] + 0.1),
                        b'End': v_line[b'End'],
                        b'Used': False,
                        b'Stroke': v_line[b'Stroke']
                    })
                    v_line[b'End'] = (v_line[b'End'][0], line[b'Start'][1] - 0.1)

                change = True
                line[b'Used'] = True
                break

        for line in verticals:
            if line[b'Used']: continue

            for section in sections:
                if not section[b'Start'][0] <= line[b'Start'][0] <= section[b'End'][0]:
                    continue

                if not line[b'Start'][1] <= section[b'InStart'][1]:
                    continue
                if not line[b'End'][1] >= section[b'InEnd'][1]:
                    continue

                new_width = section[b'End'][0] - line[b'Start'][0]
                sections.append({
                    b'Height': section[b'Height'],
                    b'Width': new_width,
                    b'Start': (line[b'Start'][0], section[b'Start'][1]),
                    b'End': section[b'End'],
                    b'InStart': (line[b'Start'][0] + 0.2 * new_width, section[b'InStart'][1]),
                    b'InEnd': (section[b'End'][0] - 0.2 * new_width, section[b'InEnd'][1])
                })
                section[b'Width'] -= new_width
                section[b'End'] = (line[b'Start'][0], section[b'End'][1])
                section[b'InStart'] = (section[b'Start'][0] + 0.2 * section[b'Width'], section[b'InStart'][1])
                section[b'InEnd'] = (section[b'End'][0] - 0.2 * section[b'Width'], section[b'InEnd'][1])

                for h_line in horizontals:
                    if h_line[b'Used']: continue

                    if not h_line[b'Start'][0] <= line[b'Start'][0] <= h_line[b'End'][0]: 
                        continue
                    if not line[b'Start'][1] <= h_line[b'Start'][1] <= line[b'End'][1]:
                        continue

                    horizontals.append({
                        b'Start': (line[b'Start'][0] + 0.1, h_line[b'Start'][1]),
                        b'End': h_line[b'End'],
                        b'Used': False,
                        b'Stroke': h_line[b'Stroke']
                    })
                    h_line[b'End'] = (line[b'Start'][0] - 0.1, h_line[b'End'][1])

                change = True
                line[b'Used'] = True
                break

    return sections

def _apply_transform(point : (float, float), transform : (float, float, float, float, float, float)) -> (float, float):
    x, y = point
    a, b, c, d, e, f = transform

    return(x * a + y * c + e, x * b + y * d + f)

def _interprete_page_text(texts : [dict]) -> dict:
    texts.sort(key = lambda t: (-t[b'Start'][1], t[b'Start'][0]))
    
    text_dict = dict()
    for idx, text in enumerate(texts):
        (a_x, a_y), (b_x, b_y), (c_x, c_y), _ = text[b'BBox']
        ab_x, ab_y, ac_x, ac_y = a_x - b_x, a_y - b_y, a_x - c_x, a_y - c_y

        width = sqrt(pow(ac_x, 2) + pow(ac_y, 2))

        div = 1 / width
        a = -ac_x * div
        c = -ac_y * div
        e = (a_x * ac_x + a_y * ac_y) * div
        b = -c
        d = a
        f = (-a_x * ac_y + a_y * ac_x) * div
        inv_div = 1 / (d * a - c * b)

        text[b'Width'] = width
        text[b'Right'] = (-ac_x / width, -ac_y / width)
        text[b'Size'] = sqrt(pow(ab_x * ac_y, 2) + pow(ab_y * ac_x, 2)) / width
        text[b'FontSize'] = text[b'Size']
        text[b'Up'] = (-text[b'Right'][1], text[b'Right'][0])
        text[b'Transform'] = (a, b, c, d, e, f)
        text[b'InvTransform'] = (d * inv_div, -b * inv_div, -c * inv_div, a * inv_div, (c * f - d * e) * inv_div, (b * e - a * f) * inv_div)
        text[b'ParagraphPoint'] = (text[b'Start'][0] + text[b'Up'][0] * text[b'Size'] * 1.2, text[b'Start'][1] + text[b'Up'][1] * text[b'Size'] * 1.2)
        text[b'InlinePoint'] = (text[b'Start'][0] - text[b'Right'][0] * text[b'Size'] * 0.8, text[b'Start'][1] - text[b'Right'][1] * text[b'Size'] * 0.8)
        text[b'Id'] = idx
        text[b'Ids'] = {idx}
        text[b'Text'] = text[b'Text'].replace("*", "\*").replace("|", "\|")

        text_dict[idx] = text
    
    # Check for text left
    for text in texts:
        text[b'Leads'] = set()
        text[b'MaxDist'] = -999999

        for lead in texts:
            if text == lead: continue

            # Check for text order:
            x, y = _apply_transform(text[b'BBox'][0], lead[b'Transform'])
            if not 0 < x or not -text[b'Size'] <= y <= lead[b'Size'] + 0.1:
                continue

            # Check text direction
            angle = text[b'Right'][0] * lead[b'Right'][0] + text[b'Right'][1] * lead[b'Right'][1]
            if not 0.99 <= angle:
                continue

            # Check exact distance
            d_x, _ = _apply_transform(lead[b'BBox'][2], text[b'Transform'])
            d_x /= text[b'Size']
            if not d_x <= 0.1:
                continue

            if d_x > -15:
                if text[b'MaxDist'] < -15:
                    text[b'Leads'] = [lead[b'Id']]
                else:
                    text[b'Leads'].append(lead[b'Id'])
                text[b'MaxDist'] = d_x
            else:
                if text[b'MaxDist'] < d_x:
                    text[b'Leads'] = [lead[b'Id']]
                    text[b'MaxDist'] = d_x

    text_nexts = dict()
    for text in texts:
        text_stack = text[b'Leads'].copy()
        text[b'Leads'] = set()
        while text_stack:
            lead = text_stack.pop(0)
            if lead in text[b'Leads']: continue
            text_stack.extend(text_dict[lead][b'Leads'])
            text_nexts.setdefault(lead, set()).add(text[b'Id'])
            text[b'Leads'].add(lead)

    text_leads = dict()
    for text in texts:
        next_ids = text_nexts.get(text[b'Id'], None)
        if next_ids == None: continue

        for next_id in next_ids:
            if any(text[b'Leads'].issubset(text_dict[other][b'Leads']) and text[b'Id'] in text_dict[other][b'Leads'] \
                for other in text_dict[next_id][b'Leads'] if other != text[b'Id']):
                continue

            text_leads.setdefault(next_id, set()).add(text[b'Id'])

    def lead_sorter(lead : dict, transform : ()) -> (float, float):
        x, y = _apply_transform(lead[b'Start'], transform)
        return (y, -x)

    text_nexts = dict()
    for key, values in text_leads.items():
        for value in values:
            if value not in text_nexts:
                text_nexts[value] = key
            else:
                text_nexts[value] = sorted([text_dict[key], text_dict[text_nexts[value]]], key = lambda l: lead_sorter(l, text_dict[key][b'Transform']))[1][b'Id']

    text_queue = texts.copy()
    while text_queue:
        text = text_queue.pop(0)

        leads = text_leads.get(text[b'Id'], None)
        if leads == None: continue

        if any(lead in text_leads for lead in leads):
            text_queue.append(text)
            continue

        leads = [text_dict[lead] for lead in leads]
        leads.sort(key = lambda l: lead_sorter(l, text[b'Transform']))

        for lead in leads:
            if not text_nexts[lead[b'Id']] == text[b'Id']: continue

            if text[b'IsBold'] and not lead[b'IsBold']:
                text[b'Text'] = "**" + text[b'Text'] + "**"
                text[b'IsBold'] = False
            elif not text[b'IsBold'] and lead[b'IsBold']:
                lead[b'Text'] = "**" + lead[b'Text'] + "**"
            
            d_x, d_y = _apply_transform(lead[b'BBox'][2], text[b'Transform'])
            if d_x < -0.15 and lead[b'Text'][-1] != ' ' and text[b'Text'][0] != ' ':
                lead[b'Text'] += ' '
            if d_y > 0.4 * text[b'Size']:
                lead[b'Text'] += '/'
            text[b'Text'] = lead[b'Text'] + text[b'Text']

            pos_1 = _apply_transform(lead[b'BBox'][1], lead[b'Transform'])
            pos_2 = _apply_transform(text[b'BBox'][2], lead[b'Transform'])
            pos_3 = _apply_transform(text[b'BBox'][3], lead[b'Transform'])

            x_low, x_high = 0, max(pos_2[0], pos_3[0])
            y_low, y_high = min(0, pos_2[1]), max(pos_1[1], pos_3[1])

            text[b'BBox'] = [
                _apply_transform((0, y_low), lead[b'InvTransform']),
                _apply_transform((0, y_high), lead[b'InvTransform']),
                _apply_transform((x_high, y_low), lead[b'InvTransform']),
                _apply_transform((x_high, y_high), lead[b'InvTransform'])
            ]

            a, b, c, d, e, f = lead[b'Transform']
            e -= x_low
            f -= y_low
            text[b'Transform'] = (a, b, c, d, e, f)
            a, b, c, d, e, f = lead[b'InvTransform']
            e += a * x_low + c * y_low
            f += b * x_low + d * y_low
            text[b'InvTransform'] = (a, b, c, d, e, f) 

            text[b'Width'] = x_high - x_low
            text[b'Size'] = y_high - y_low
            text[b'FontSize'] = min(text[b'FontSize'], lead[b'FontSize'])
            text[b'ParagraphPoint'] = (text[b'Start'][0] + text[b'Up'][0] * text[b'Size'] * 1.2, \
                text[b'Start'][1] + text[b'Up'][1] * text[b'Size'] * 1.2)
            
            texts.remove(lead)
        
        del text_leads[text[b'Id']]

    ## Check for text above
    for text in texts:
        del text[b'Leads']
        text[b'Lead'] = None
        text[b'LeadDist'] = None

        for lead in texts:
            if text == lead: continue

            # Check approx position
            x, y = _apply_transform(text[b'ParagraphPoint'], lead[b'Transform'])
            if not -2 * lead[b'Size'] <= x <= lead[b'Width'] + 0.1 or not -0.1 <= y <= lead[b'Size'] + 0.1:
                continue

            # Check text direction
            angle = text[b'Right'][0] * lead[b'Right'][0] + text[b'Right'][1] * lead[b'Right'][1]
            if not 0.99 <= angle:
                continue

            # Check exact distance
            left, d_y = _apply_transform(text[b'BBox'][1], lead[b'Transform'])
            d_y /= text[b'Size']
            if not d_y <= 0.4:
                continue

            # Check text size infit
            if not -2 * lead[b'Size'] <= left:
                continue
            right, _ = _apply_transform(text[b'BBox'][3], lead[b'Transform'])
            if not right <= lead[b'Width'] + 5 * lead[b'Size']:
                continue

            if text[b'Lead'] == None:
                text[b'Lead'] = lead[b'Id']
                text[b'LeadDist'] = d_y
                text_leads.setdefault(lead[b'Id'], set()).add(text[b'Id'])
            elif text[b'LeadDist'] < d_y:
                text_leads[text[b'Lead']].remove(text[b'Id'])
                text[b'Lead'] = lead[b'Id']
                text[b'LeadDist'] = d_y
                text_leads.setdefault(lead[b'Id'], set()).add(text[b'Id'])

    # Merge texts
    text_queue = [text[b'Id'] for text in texts]
    while text_queue:
        text = text_queue.pop(0)
        text_elem = text_dict[text]
        next_texts = text_leads.get(text, None)

        if not next_texts: continue
        
        for next_text in sorted(next_texts, key = lambda l: lead_sorter(text_dict[l], text_elem[b'Transform'])):
            next_text = list(next_texts)[0]
            if text_leads.get(next_text, None): continue

            next_text_elem = text_dict[next_text]
            if text_elem[b'IsBold'] and not next_text_elem[b'IsBold']:
                text_elem[b'Text'] = "**" + text_elem[b'Text'] + "**"
                text_elem[b'IsBold'] = False
            elif not text_elem[b'IsBold'] and next_text_elem[b'IsBold']:
                next_text_elem[b'Text'] = "**" + next_text_elem[b'Text'] + "**" 

            if next_text_elem[b'Text'][0] != ' ' and text_elem[b'Text'][-1] != ' ': text_elem[b'Text'] += ' '
            if text_elem[b'Text'][-2:] == "- ": text_elem[b'Text'] = text_elem[b'Text'][:-2]
            elif text_elem[b'Text'][-4:] in ["- **", "-** "] and next_text_elem[b'Text'][:2] == "**":
                text_elem[b'Text'] = text_elem[b'Text'][:-4]
                next_text_elem[b'Text'] = next_text_elem[b'Text'][2:]
            
            text_elem[b'Text'] += next_text_elem[b'Text']

            pos_0 = _apply_transform(next_text_elem[b'BBox'][0], text_elem[b'Transform'])
            pos_1 = _apply_transform(text_elem[b'BBox'][1], text_elem[b'Transform'])
            pos_2 = _apply_transform(next_text_elem[b'BBox'][2], text_elem[b'Transform'])
            pos_3 = _apply_transform(text_elem[b'BBox'][3], text_elem[b'Transform'])

            x_low, x_high = min(0, min(pos_0[0], pos_1[0])), max(pos_2[0], pos_3[0])
            y_low, y_high = min(pos_0[1], pos_2[1]), max(pos_1[1], pos_3[1])

            text_elem[b'BBox'] = [
                _apply_transform((x_low, y_low), text_elem[b'InvTransform']),
                _apply_transform((x_low, y_high), text_elem[b'InvTransform']),
                _apply_transform((x_high, y_low), text_elem[b'InvTransform']),
                _apply_transform((x_high, y_high), text_elem[b'InvTransform'])
            ]

            a, b, c, d, e, f = text_elem[b'Transform']
            e -= x_low
            f -= y_low
            text_elem[b'Transform'] = (a, b, c, d, e, f)

            a, b, c, d, e, f = text_elem[b'InvTransform']
            e += a * x_low + c * y_low
            f += b * x_low + d * y_low
            text_elem[b'InvTransform'] = (a, b, c, d, e, f) 

            text_elem[b'FontSize'] = min(text_elem[b'FontSize'], next_text_elem[b'FontSize'])
            text_elem[b'Width'] = x_high - x_low
            text_elem[b'Transform'] = (a, b, c, d, e, f)

            text_leads[text].remove(next_text)
            if text_elem[b'Lead']:
                text_queue.append(text_elem[b'Lead'])
            texts.remove(next_text_elem)

    # Get majority direction
    dirs = {
        b"Up": 0,
        b"Right": 0,
        b"Down": 0,
        b"Left": 0,
    }
    for text in texts:
        if abs(text[b'Up'][0]) < abs(text[b'Up'][1]):
            if text[b'Up'][1] > 0: dirs[b'Up'] += len(text[b'Text'])
            else: dirs[b'Down'] += len(text[b'Text'])
        else:
            if text[b'Up'][0] > 0: dirs[b'Right'] += len(text[b'Text'])
            else: dirs[b'Left'] += len(text[b'Text'])
    
    if dirs[b'Up'] >= dirs[b'Right'] and dirs[b'Up'] >= dirs[b'Down'] and dirs[b'Up'] >= dirs[b'Left']:
        orient = lambda x, y: (-y, x)
        orientation = b'Up'
    elif dirs[b'Right'] >= dirs[b'Down'] and dirs[b'Right'] >= dirs[b'Left']:
        orient = lambda x, y: (-x, -y)
        orientation = b'Right'
    elif dirs[b'Down'] >= dirs[b'Left']:
        orient = lambda x, y: (y, -x)
        orientation = b'Down'
    else:
        orient = lambda x, y: (x, y)
        orientation = b'Left'
    
    # Merge all texts according to normal reading order
    texts.sort(key = lambda t: orient(*t[b'Start']))
    page_text = [{
        b'Text': "**" + texts[0][b'Text'] + "**" if texts[0][b'IsBold'] else texts[0][b'Text'],
        b'FontSize': int(texts[0][b'FontSize'] * 4 * (1 + int(texts[0][b'IsBold']) * 0.2))  
    }]
    for idx in range(1, len(texts)):
        text = texts[idx]

        d_x = text[b'Start'][0] - texts[idx - 1][b'Start'][0]
        if abs(d_x) > text[b'Size']: page_text.append({b'Text': '\n', b'FontSize': -1})

        d_y = text[b'BBox'][1][1] - texts[idx - 1][b'BBox'][0][1]
        page_text.append({b'Text': '\n' * min(2, max(1, int(abs(d_y) / text[b'Size'] / 0.65))), b'FontSize': -1})
        page_text.append({
            b'Text': "**" + text[b'Text'] + "**" if text[b'IsBold'] else text[b'Text'],
            b'FontSize': int(text[b'FontSize'] * 4 * (1 + int(text[b'IsBold']) * 0.2))
        })

    return {b'Text': page_text, b'Orientation': orientation}

_CONTENT_STREAM_TOKENS = {
    b'(': (b'(', 0),
    b'/': (b'/', 0),

    b'B': (b'S', 1),
    b'BDC': (b'None', 3),
    b'BMC': (b'None', 3),
    b'BT': (b'BT', 2),
    b'CS': (b'None', 2),
    b'Do': (b'None', 2),
    b'ET': (b'ET', 2),
    b'EMC': (b'None', 3),
    b'G': (b'None', 1),
    b'J': (b'None', 1),
    b'K': (b'None', 1),
    b'M': (b'None', 1),
    b'Q': (b'Q', 1),
    b'RG': (b'None', 2),
    b'S': (b'S', 1),
    b'SC': (b'None', 2),
    b'Tc': (b'Tc', 2),
    b'Td': (b'Td', 2),
    b'TD': (b'TD', 2),
    b'Tf': (b'Tf', 2),
    b'TJ': (b'TJ', 2),
    b'Tj': (b'TJ', 2),
    b'TL': (b'TL', 2),
    b'Tm': (b'Tm', 2),
    b'Tr': (b'Tr', 2),
    b'Tw': (b'Tw', 2),
    b'Tz': (b'Tz', 2),
    b'T*': (b'T*', 2),
    b'W': (b'None', 1),
    b'W*': (b'None', 2),

    b'[': (b'[', 0),
    b'<<': (b'<<', 0),
    b'<': (b'<', 0),

    b'c': (b'c', 1),
    b'cm': (b'cm', 2),
    b'cs': (b'None', 2),
    b'd': (b'None', 1),
    b'f': (b'None', 1),
    b'f*': (b'None', 2),
    b'g': (b'None', 1),
    b'gs': (b'gs', 2),
    b'h': (b'h', 1),
    b'i': (b'None', 1),
    b'j': (b'None', 1),
    b'k': (b'None', 1),
    b'l': (b'l', 1),
    b'm': (b'm', 1),
    b'n': (b'None', 1),
    b'q': (b'q', 1),
    b're': (b're', 2),
    b'rg': (b'None', 2),
    b'ri': (b'None', 2),
    b's': (b'S', 1),
    b'sc': (b'None', 2),
    b'scn': (b'None', 3),
    b'v': (b'v', 1),
    b'w': (b'w', 1),
    b'y': (b'y', 1),
}
for ws in _WHITE_SPACE: _CONTENT_STREAM_TOKENS[ws.to_bytes(1, "big")] = (b' ', 1)
for nb in _NUMBER_CHARS: _CONTENT_STREAM_TOKENS[nb.to_bytes(1, "big")] = (b'0', 0)

def _get_text_from_content_stream(raw_data : bytes, data : bytes, xref : dict, resources : dict):
    start = 0
    stack = []
    graphics_state_stack = []
    path = []

    graphics_state = {
        b'CTM': (1, 0, 0, 1, 0, 0),
        b'w': 0
    }
    text_state = {
        b'Tf': None,
        b'Tfs': 0,
        b'TM': (1, 0, 0, 1, 0, 0),
        b'TLM': (1, 0, 0, 1, 0, 0),
        b'Tl': 0,
        b'Tr': True,
        b'Tc': 0,
        b'Tw': 0,
        b'Th': 1
    }
    marked_property = None

    texts = []
    lines = []

    while start < len(data):
        for i in range(3, 0, -1):
            token, offset = _CONTENT_STREAM_TOKENS.get(data[start : start + i], (None, 0))
            if token != None: break
        
        match token:
            case b' ': pass
            case b'None': stack.clear()

            case b'q':
                graphics_state_stack.append(graphics_state.copy())
            case b'Q':
                graphics_state = graphics_state_stack.pop()
            case b'gs':
                gs = resources[b'Graphic_states'][stack.pop()]
                if type(gs) == tuple: gs = _load_object(raw_data, xref, gs)[b'VALUE']
                if b'Font' in gs:
                    text_state[b'Tf'] = gs[b'FONT'][0]
                    text_state[b'Tfs'] = gs[b'FONT'][1]
            case b'cm':
                a, b, c, d, e, f = tuple(stack[-6:])
                g, h, i, j, k, l = graphics_state[b'CTM']
                
                graphics_state[b'CTM'] = (a*g + b*i, a*h + b*j, c*g + d*i, c*h + d*j, e*g + f*i + k, e*h + f*j + l)
                stack.clear()
            case b'w':
                graphics_state[b'w'] = stack.pop()
            
            case b'm':
                y, x = stack.pop(), stack.pop()
                p = _apply_transform((x, y), graphics_state[b'CTM'])
                path.append({
                    b'Points': [p],
                    b'Current': p,
                    b'Closed': False
                })
            case b'l':
                y, x = stack.pop(), stack.pop()
                p = _apply_transform((x, y), graphics_state[b'CTM'])
                path[-1][b'Points'].append(p)
                path[-1][b'Current'] = p
            case b'c':
                y_3, x_3 = stack.pop(), stack.pop()
                y_2, x_2 = stack.pop(), stack.pop()
                y_1, x_1 = stack.pop(), stack.pop()

                x_3, y_3 = _apply_transform((x_3, y_3), graphics_state[b'CTM'])
                x_2, y_2 = _apply_transform((x_2, y_2), graphics_state[b'CTM'])
                x_1, y_1 = _apply_transform((x_1, y_1), graphics_state[b'CTM'])
                x_0, y_0 = path[-1][b'Current']

                for t in range(1, 6):
                    t /= 5
                    x = pow(1 - t, 3) * x_0 + 3 * t * pow(1 - t, 2) * x_1 + 3 * pow(t, 2) * (1 - t) * x_2 + pow(t, 3) * x_3
                    y = pow(1 - t, 3) * y_0 + 3 * t * pow(1 - t, 2) * y_1 + 3 * pow(t, 2) * (1 - t) * y_2 + pow(t, 3) * y_3
                    path[-1][b'Points'].append((x, y))
                path[-1][b'Current'] = (x_3, y_3)
            case b'v':
                y_3, x_3 = stack.pop(), stack.pop()
                y_2, x_2 = stack.pop(), stack.pop()

                x_3, y_3 = _apply_transform((x_3, y_3), graphics_state[b'CTM'])
                x_2, y_2 = _apply_transform((x_2, y_2), graphics_state[b'CTM'])
                x_1, y_1 = path[-1][b'Current']
                x_0, y_0 = path[-1][b'Current']

                for t in range(1, 6):
                    t /= 5
                    x = pow(1 - t, 3) * x_0 + 3 * t * pow(1 - t, 2) * x_1 + 3 * pow(t, 2) * (1 - t) * x_2 + pow(t, 3) * x_3
                    y = pow(1 - t, 3) * y_0 + 3 * t * pow(1 - t, 2) * y_1 + 3 * pow(t, 2) * (1 - t) * y_2 + pow(t, 3) * y_3
                    path[-1][b'Points'].append((x, y))
                path[-1][b'Current'] = (x_3, y_3)
            case b'y':
                y_3, x_3 = stack.pop(), stack.pop()
                y_1, x_1 = stack.pop(), stack.pop()

                x_3, y_3 = _apply_transform((x_3, y_3), graphics_state[b'CTM'])
                x_2, y_2 = x_3, y_3
                x_1, y_1 = _apply_transform((x_1, y_1), graphics_state[b'CTM'])
                x_0, y_0 = path[-1][b'Current']

                for t in range(1, 6):
                    t /= 5
                    x = pow(1 - t, 3) * x_0 + 3 * t * pow(1 - t, 2) * x_1 + 3 * pow(t, 2) * (1 - t) * x_2 + pow(t, 3) * x_3
                    y = pow(1 - t, 3) * y_0 + 3 * t * pow(1 - t, 2) * y_1 + 3 * pow(t, 2) * (1 - t) * y_2 + pow(t, 3) * y_3
                    path[-1][b'Points'].append((x, y))
                path[-1][b'Current'] = (x_3, y_3)
            case b'h':
                path[-1][b'Points'].append(path[-1][b'Points'][0])
                path[-1][b'Current'] = path[-1][b'Points'][0]
                path[-1][b'Closed'] = True
                path.append({
                    b'Points': [],
                    b'Current': None,
                    b'Closed': False
                })
            case b're':
                height, width = stack.pop(), stack.pop()
                y, x = stack.pop(), stack.pop()

                path.append({
                    b'Points': [
                        _apply_transform((x, y), graphics_state[b'CTM']),
                        _apply_transform((x + width, y), graphics_state[b'CTM']),
                        _apply_transform((x + width, y + height), graphics_state[b'CTM']),
                        _apply_transform((x, y + height), graphics_state[b'CTM'])
                    ],
                    b'Current': None,
                    b'Closed': True
                })
                path.append({
                    b'Points': [],
                    b'Current': None,
                    b'Closed': False
                })
            case b'S':
                for subpath in path:
                    if subpath[b'Current'] == None or len(subpath[b'Points']) < 2: continue
                    min_x, max_x = subpath[b'Current'][0], subpath[b'Current'][0]
                    min_y, max_y = subpath[b'Current'][1], subpath[b'Current'][1]

                    for point in subpath[b'Points']:
                        min_x, max_x = min(min_x, point[0]), max(max_x, point[0])
                        min_y, max_y = min(min_y, point[1]), max(max_y, point[1])
                    
                    if max_x - min_x < 0.5 or max_y - min_y < 0.5:
                        lines.append({
                            b'BBox': [(min_x, min_y), (min_x, max_y), (max_x, min_y), (max_x, max_y)],
                            b'Stroke': graphics_state[b'w']
                        })
                path.clear()

            case b'BT':
                text_state[b'TM'] = (1, 0, 0, 1, 0, 0)
                text_state[b'TLM'] = (1, 0, 0, 1, 0, 0)
            case b'ET':
                pass
            case b'Tc':
                text_state[b'Tc'] = stack.pop()
            case b'Tz':
                text_state[b'Th'] = stack.pop()
            case b'Tw':
                text_state[b'Tw'] = stack.pop()
            case b'Tr':
                text_state[b'Tr'] = stack.pop() != 3
            case b'Tf':
                text_state[b'Tfs'] = stack.pop()
                text_state[b'Tf'] = resources[b'Fonts'][stack.pop()]
            case b'Tm':
                m = tuple(stack[-6:])
                text_state[b'TM'] = m
                text_state[b'TLM'] = m
                stack.clear()
            case b'Td':
                x, y = stack[-2:]
                a, b, c, d, e, f = text_state[b'TLM']
                e += x*a + y*b
                f += x*b + y*d
                text_state[b'TM'] = (a, b, c, d, e, f)
                text_state[b'TLM'] = (a, b, c, d, e, f)
                stack.clear()
            case b'TD':
                ty, tx = stack.pop(), stack.pop()
                text_state[b'Tl'] = -ty
                a, b, c, d, e, f = text_state[b'TLM']
                e += tx*a + ty*b
                f += tx*b + ty*d
                text_state[b'TM'] = (a, b, c, d, e, f)
                text_state[b'TLM'] = (a, b, c, d, e, f)
            case b'T*':
                a, b, c, d, e, f = text_state[b'TLM']
                e += -text_state[b'Tl']*b
                f += -text_state[b'Tl']*d
                text_state[b'TM'] = (a, b, c, d, e, f)
                text_state[b'TLM'] = (a, b, c, d, e, f)
            case b'TL':
                text_state[b'Tl'] = stack.pop()
            case b'TJ':
                if not text_state[b'Tr']:
                    stack.pop()
                else:
                    strings = stack.pop()
                    if type(strings) == bytes:
                        strings = [strings]
                    message = str()
                    font = xref[text_state[b'Tf']][b'FONT']

                    a, b, c, d, e, f = text_state[b'TM']
                    g, h, i, j, k, l = graphics_state[b'CTM']
                    text_start = (e*g + f*i + k, e*h + f*j + l)
                    y_vec = (c*g + d*i, c*h + d*j)

                    bbox = [(text_start[0] + font[b'DESCENT'] * text_state[b'Tfs'] * y_vec[0], text_start[1] + font[b'DESCENT'] * text_state[b'Tfs'] * y_vec[1])]
                    bbox.append((text_start[0] + font[b'ASCENT'] * text_state[b'Tfs'] * y_vec[0], text_start[1] + font[b'ASCENT'] * text_state[b'Tfs'] * y_vec[1]))

                    for string in strings:
                        if type(string) == bytes:
                            for char, width in _decode_font_bytes(string, font):
                                message += char
                                if text_state[b'Tc'] / text_state[b'Tfs'] >= 0.15: message += ' '

                                t_x = (width * text_state[b'Tfs'] + text_state[b'Tc']) * text_state[b'Th']
                                if char == ' ':
                                    t_x += text_state[b'Tw'] * text_state[b'Th']
                                t_y = 0
                                e += t_x*a + t_y*c
                                f += t_x*b + t_y*d
                        else:
                            width = -string / 1000
                            t_x = width * text_state[b'Tfs'] * text_state[b'Th']
                            if text_state[b'Tc'] / text_state[b'Tfs'] + width > 0.15: message += ' '
                            elif text_state[b'Tc'] / text_state[b'Tfs'] + width < 0.1: message = message.rstrip(' ')
                            t_y = 0
                            e += t_x*a + t_y*c
                            f += t_x*b + t_y*d

                    # Remove last Tc from position
                    if text_state[b'Tc'] * text_state[b'Th'] > 0.15: message = message.rstrip(' ')
                    t_x = -text_state[b'Tc'] * text_state[b'Th']
                    t_y = 0
                    e += t_x*a + t_y*c
                    f += t_x*b + t_y*d

                    text_state[b'TM'] = (a, b, c, d, e, f)
                    anchor = (e*g + f*i + k, e*h + f*j + l)

                    bbox.append((anchor[0] + font[b'DESCENT'] * text_state[b'Tfs'] * y_vec[0], anchor[1] + font[b'DESCENT'] * text_state[b'Tfs'] * y_vec[1]))
                    bbox.append((anchor[0] + font[b'ASCENT'] * text_state[b'Tfs'] * y_vec[0], anchor[1] + font[b'ASCENT'] * text_state[b'Tfs'] * y_vec[1]))

                    texts.append({
                        b'Text': message,
                        b'BBox': bbox,
                        b'Start': text_start,
                        b'IsBold': font[b'WEIGHT'] >= 600
                    })
            
            case b'/':
                mem, start = _read_name(data, start)
                stack.append(mem)
            case b'0':
                mem, start = _read_number(data, start, single = True)
                stack.append(mem)
            case b'[':
                mem, start = _read_array(data, start)
                stack.append(mem)
            case b'(':
                mem, start = _read_literal_string(data, start)
                stack.append(mem)
            case b'<<':
                mem, start = _read_dictionary(data, start)
                stack.append(mem)
            case b'<':
                mem, start = _read_byte_string(data, start)
                stack.append(mem)

            case _:
                start += 1
                continue
                raise NotImplementedError(f"Token {token} in {data[start : start + 5]} not yet implemented!")

        start += offset

    sections = _generate_sections(resources[b'BBox'], resources[b'Width'], resources[b'Height'], lines)

    for text in texts:
        x, y = text[b'Start']
        for section in sections:
            if not section[b'Start'][0] <= x <= section[b'End'][0]:
                continue
            if not section[b'Start'][1] <= y <= section[b'End'][1]:
                continue

            section.setdefault(b'Texts', []).append(text)
            break

    dirs = {
        b"Up": 0,
        b"Right": 0,
        b"Down": 0,
        b"Left": 0,
    }
    for section in sections:
        texts = section.get(b'Texts', None)
        if texts == None:
            section[b'Content'] = []
            continue

        del section[b'Texts']

        result = _interprete_page_text(texts)
        section[b'Content'] = result[b'Text']
        dirs[result[b'Orientation']] += 1

    if dirs[b'Up'] >= dirs[b'Right'] and dirs[b'Up'] >= dirs[b'Down'] and dirs[b'Up'] >= dirs[b'Left']:
        orient = lambda x, y: (-y, x)
    elif dirs[b'Right'] >= dirs[b'Down'] and dirs[b'Right'] >= dirs[b'Left']:
        orient = lambda x, y: (-x, -y)
    elif dirs[b'Down'] >= dirs[b'Left']:
        orient = lambda x, y: (y, -x)
    else:
        orient = lambda x, y: (x, y)

    rows = dict()
    for section in sections:
        section[b'Start'] = orient(*section[b'Start'])
        rows.setdefault(section[b'Start'][0], []).append(section)

    row_items = list(rows.items())
    row_items.sort(key = lambda r: r[0])

    page_result = []
    table_columns = 0
    table_preset = None
    for _, row in row_items:
        if len(row) == 1:
            if table_preset == None:
                page_result.extend(row[0][b'Content'])
            else:
                table_preset = None
                page_result.append({b'Text': '\n\n', b'FontSize': -1})
                page_result.extend(row[0][b'Content'])
        else:
            row.sort(key = lambda s: s[b'Start'])
            if table_preset != None and len(row) != table_columns:
                table_preset = None
                page_result.append({b'Text': '\n\n', b'FontSize': -1})
            if table_preset == None:
                table_columns = len(row)
                a = 0
                b = table_columns
                while not any(row[a][b'Content']) and a < table_columns: a += 1
                while not any(row[b - 1][b'Content']) and b > 1 == "": b -= 1
                if a >= b:
                    continue
                table_preset = (a, b)

                page_result.append({b'Text': '\n|', b'FontSize': -1})
                for section in row[a : b]:
                    for content in section[b'Content']:
                        content[b'Text'] = content[b'Text'].replace("\n", "<br>")
                        content[b'FontSize'] = -1
                        page_result.append(content)
                    page_result.append({b'Text': '|', b'FontSize': -1})

                page_result.append({b'Text': '\n|', b'FontSize': -1})
                for _ in range(b - a):
                    page_result.append({b'Text': '-------|', b'FontSize': -1})
            else:
                a, b = table_preset
                page_result.append({b'Text': '\n|', b'FontSize': -1})
                for section in row[a : b]:
                    for content in section[b'Content']:
                        content[b'Text'] = content[b'Text'].replace("\n", "<br>")
                        content[b'FontSize'] = -1
                        page_result.append(content)
                    page_result.append({b'Text': '|', b'FontSize': -1})

    return page_result

def _annotate_pages(pages : [[dict]]) -> [str]:
    if not any(p for p in pages): return [""]

    total_chars = 0
    font_sizes = dict()

    for page in pages:
        for text_block in page:
            if text_block[b'FontSize'] == -1: continue

            total_chars += len(text_block[b'Text'])
            font_sizes[text_block[b'FontSize']] = font_sizes.get(text_block[b'FontSize'], 0) + len(text_block[b'Text'])

    font_size_counts = list(font_sizes.items())
    font_size_counts.sort(key = lambda f: f[0])

    count_min = int(total_chars * 0.001)

    header_lvl = 4
    char_count = 0
    font_sizes[-1] = header_lvl

    for size, count in font_size_counts:
        if count > count_min and char_count > 0.5 * total_chars:
            header_lvl = max(header_lvl - 1, 1)
            total_chars -= char_count
            char_count = 0
        
        char_count += count
        font_sizes[size] = header_lvl

    final_pages = []
    for idx, page in enumerate(pages):
        final_page = ""

        for text_block in page:
            match font_sizes[text_block[b'FontSize']]:
                case 1:
                    final_page += "\n\n# " + text_block[b'Text'].lstrip(" ").rstrip(" \n") + "\n\n"
                case 2:
                    final_page += "\n\n## " + text_block[b'Text'].lstrip(" ").rstrip(" \n") + "\n\n"
                case 3:
                    final_page += "\n\n### " + text_block[b'Text'].lstrip(" ").rstrip(" \n") + "\n\n"
                case 4:
                    final_page += text_block[b'Text']

        final_page = sub("\n\n+", "\n\n", final_page).lstrip("\n").rstrip("\n")
        final_page = sub("\.\.\.+", "...", final_page)
        final_page = final_page.replace("** **", " ")
        final_page = final_page.replace("****", "")
        final_pages.append(final_page)

    return final_pages

def _read_xref_stream(data : bytes, start : int) -> (dict, dict):
    xref, trailer = dict(), None

    assert _test_for_obj(data, start), "Expected xref stream object!"

    xref_stream_obj, _ = _read_object(data, start)
    trailer = xref_stream_obj[b'VALUE']
    data_stream = xref_stream_obj[b'STREAM']
    stream_pointer = 0

    W = trailer[b'W']
    idx = trailer[b'Index'] if b'Index' in trailer else [0, trailer[b'Size']]
    current_idx = idx[0]

    while True:
        if idx[1] == 0:
            idx.pop(0)
            idx.pop(0)
            if not idx: break
            current_idx = idx[0]
        else:
            idx[1] -= 1
        
        f1 = int.from_bytes(data_stream[stream_pointer : (stream_pointer := stream_pointer + W[0])], "big")
        f2 = int.from_bytes(data_stream[stream_pointer : (stream_pointer := stream_pointer + W[1])], "big")
        f3 = int.from_bytes(data_stream[stream_pointer : (stream_pointer := stream_pointer + W[2])], "big")

        if f1 == 0:
            pass
        elif f1 == 1:
            xref[(current_idx, f3)] = {b'TYPE': b'REF', b'POS': f2}
        elif f1 == 2:
            xref[(current_idx, 0)] = {b'TYPE': b'STREAM_REF', b'POS': (f2, 0), b'INDEX': f3}
        else:
            raise ValueError("Unexpected f1 value in xref stream!")

        current_idx += 1
    
    prev = trailer.get(b'Prev', 0)
    if prev != 0:
        prev_xref, _ = _read_file_trailer(data, prev)

        for key, value in prev_xref.items():
            if not key in xref: xref[key] = value

    if b'Encrypt' in trailer: raise NotImplementedError("Encryption not yet implemented!")

    return xref, trailer

def _read_file_trailer(data : bytes, start : int) -> (dict, dict):
    if data[start : start + 4] != b'xref':
        return _read_xref_stream(data, start)

    xref, trailer = dict(), dict()

    start += 4
    while data[start] in _WHITE_SPACE: start += 1

    while data[start] in _DIGITS:
        current_idx, start = _read_number(data, start, single = True)
        assert data[start] == 0x20, "Expected space between numbers in xref!"
        count, start = _read_number(data, start + 1, single = True)

        while count > 0:
            while data[start] in _WHITE_SPACE: start += 1
            offset, start = _read_number(data, start, single = True)
            assert data[start] == 0x20, "Expected space between numbers in xref!"
            generation, start = _read_number(data, start + 1, single = True)
            assert data[start] == 0x20, "Expected space between numbers in xref!"
            if data[start + 1] == 0x6E:
                xref[(current_idx, generation)] = {b'TYPE': b'REF', b'POS': offset}

            start += 2
            current_idx += 1
            count -= 1 

    while data[start] in _WHITE_SPACE: start += 1
    assert data[start : start + 7] == b'trailer', "Expected keyword trailer after xref table!"
    start += 7
    while data[start] in _WHITE_SPACE: start += 1
    trailer, _ = _read_dictionary(data, start)

    xref_stm = trailer.get(b'XRefStm', None)
    if xref_stm != None:
        xref_stream_obj, _ = _read_object(data, xref_stm)
        data_stream = xref_stream_obj[b'STREAM']
        stream_pointer = 0

        W = xref_stream_obj[b'VALUE'][b'W']
        idx = xref_stream_obj[b'VALUE'][b'Index'] if b'Index' in xref_stream_obj[b'VALUE'] else [0, xref_stream_obj[b'VALUE'][b'Size']]
        current_idx = idx[0]

        while True:
            if idx[1] == 0:
                idx.pop(0)
                idx.pop(0)
                if not idx: break
                current_idx = idx[0]
            else:
                idx[1] -= 1
            
            f1 = int.from_bytes(data_stream[stream_pointer : (stream_pointer := stream_pointer + W[0])], "big")
            f2 = int.from_bytes(data_stream[stream_pointer : (stream_pointer := stream_pointer + W[1])], "big")
            f3 = int.from_bytes(data_stream[stream_pointer : (stream_pointer := stream_pointer + W[2])], "big")

            if f1 == 0:
                pass
            elif f1 == 1:
                xref[(current_idx, f3)] = {b'TYPE': b'REF', b'POS': f2}
            elif f1 == 2:
                xref[(current_idx, 0)] = {b'TYPE': b'STREAM_REF', b'POS': (f2, 0), b'INDEX': f3}
            else:
                raise ValueError("Unexpected f1 value in xref stream!")

            current_idx += 1

    prev = trailer.get(b'Prev', 0)
    if prev != 0:
        prev_xref, _ = _read_file_trailer(data, prev)

        for key, value in prev_xref.items():
            if not key in xref: xref[key] = value

    if b'Encrypt' in trailer: raise NotImplementedError("Encryption not yet implemented!")

    return xref, trailer

def load_xref_trailer(data : bytes, raw_pointer : int) -> (dict, dict):
    # Check for liniearized PDF Format:
    while data[raw_pointer] >= 0x80: raw_pointer += 1
    while data[raw_pointer] in _WHITE_SPACE: raw_pointer += 1
    if _test_for_obj(data, raw_pointer):
        linearized_header, raw_pointer = _read_object(data, raw_pointer)
        if b'Linearized' in linearized_header[b'VALUE'] and linearized_header[b'VALUE'].get(b'L', 0) == len(data) - 32:
            while data[raw_pointer] in _WHITE_SPACE: raw_pointer += 1
            return _read_file_trailer(data, raw_pointer)
    
    # Find XREF start
    raw_pointer = len(data) - 32
    while data[raw_pointer : raw_pointer + 5] != b'%%EOF': raw_pointer -= 1
    while data[raw_pointer : raw_pointer + 9] != b'startxref': raw_pointer -= 1
    raw_pointer += 9
    while data[raw_pointer] in _WHITE_SPACE: raw_pointer += 1
    XREF_Pos = _read_number(data, raw_pointer)[0]

    # Read file trailer
    return _read_file_trailer(data, XREF_Pos)

def parse_pdf(path : Path) -> List[str]:
    raw_data = []
    raw_pointer = 0

    with open(path, "rb") as ifile:
        raw_data = ifile.read() + b'\x00' * 32
    
    # Crop Beginning of file to first %
    while raw_data[raw_pointer] != 0x25: raw_pointer += 1
    raw_data = raw_data[raw_pointer:]

    # Check for pdf file header
    if raw_data[raw_pointer : raw_pointer + 5] != b'%PDF-': raise ValueError("file does not start with a PDF Tag!")
    raw_pointer += 11

    # Read file trailer
    XREF, TRAILER = load_xref_trailer(raw_data, raw_pointer)
    
    # Load root
    ROOT = _load_object(raw_data, XREF, TRAILER[b'Root'])[b'VALUE']
    if ROOT[b'Type'] != b'Catalog': raise ValueError("Root object must be of type Catalog!")

    PAGES = [_load_object(raw_data, XREF, ROOT[b'Pages'])[b'VALUE']]
    if not all(page[b'Type'] == b'Pages' for page in PAGES): raise ValueError("Pages object must be of type Pages!")

    tmp_pages = []
    while any(page.get(b'Type', None) == b'Pages' for page in PAGES):
        for page in PAGES:
            if page.get(b'Type', None) == b'Pages':
                new_pages = [_load_object(raw_data, XREF, kid)[b'VALUE'] for kid in page[b'Kids']]
                for new_page in new_pages:
                    if not b'Resources' in new_page:
                        new_page[b'Resources'] = page.get(b'Resources', dict())
                    if not b'MediaBox' in new_page:
                        new_page[b'MediaBox'] = page.get(b'MediaBox', [0, 0, 0, 0])
                tmp_pages.extend(new_pages)
            else:
                tmp_pages.append(page)
        
        PAGES = tmp_pages
        tmp_pages = []

    page_content = []
    for page in PAGES:
        page_resources = page.get(b'Resources', dict())
        if type(page_resources) == tuple:
            page_resources = _load_object(raw_data, XREF, page_resources)[b'VALUE']
        resources = {
            b'Fonts': _load_font_decodes(raw_data, XREF,page_resources),
            b'Graphic_states': page_resources.get(b'ExtGState', dict()),
            b'Properties': page_resources.get(b'Properties', dict()),
            b'XObjects': page_resources.get(b'XObject', dict()),
            b'BBox': page[b'MediaBox'],
            b'Width': page[b'MediaBox'][2] - page[b'MediaBox'][0],
            b'Height': page[b'MediaBox'][3] - page[b'MediaBox'][1]
        }
        if type(resources[b'Graphic_states']) == tuple: resources[b'Graphic_states'] = _load_object(raw_data, XREF, resources[b'Graphic_states'])[b'VALUE']

        if type(page[b'Contents']) != list:
            content = _load_object(raw_data, XREF, page[b'Contents'])[b'STREAM']
        else:
            content = b''.join(_load_object(raw_data, XREF, cont)[b'STREAM'] for cont in page[b'Contents'])

        page_content.append(_get_text_from_content_stream(raw_data, content, XREF, resources))
    
    return _annotate_pages(page_content)
