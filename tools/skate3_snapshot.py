"""Bounded reader for Skate3Recomp's Windows SK3GSNP1 memory snapshots."""
import bisect
import struct
from pathlib import Path


class Snapshot:
    def __init__(self, path):
        self.source = Path(path).open('rb')
        self.regions = []
        try:
            size = Path(path).stat().st_size
            if self.source.read(8) != b'SK3GSNP1':
                raise ValueError('Unsupported Skate memory snapshot header')
            while True:
                header = self.source.read(16)
                if len(header) != 16:
                    raise ValueError('Truncated memory snapshot header/terminator')
                address, count = struct.unpack('<QQ', header)
                if address == 0xFFFFFFFFFFFFFFFF:
                    if count or self.source.tell() != size:
                        raise ValueError('Invalid snapshot terminator/trailing data')
                    break
                if not count or address + count > 0x100001000 or count > size - self.source.tell():
                    raise ValueError('Invalid memory snapshot region')
                if self.regions and address < self.regions[-1][0] + self.regions[-1][1]:
                    raise ValueError('Overlapping or unordered snapshot regions')
                self.regions.append((address, count, self.source.tell()))
                self.source.seek(count, 1)
            self.starts = [r[0] for r in self.regions]
        except Exception:
            self.source.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.source.close()

    def read_guest(self, address, count):
        if not 0 <= address <= 0xFFFFFFFF or not 0 <= count <= 16 * 1024 * 1024:
            raise ValueError('Invalid guest buffer range')
        if address + count > 0x100000000 or address < 0xE0000000 < address + count:
            raise ValueError('Guest buffer crosses memory mapping boundary')
        # ReXGlue's physical guest mapping has an extra host page before E0000000.
        cursor = address + (0x1000 if address >= 0xE0000000 else 0)
        pieces = []
        while count:
            index = bisect.bisect_right(self.starts, cursor) - 1
            if index < 0:
                raise ValueError('Guest buffer missing from memory snapshot')
            start, length, offset = self.regions[index]
            available = start + length - cursor
            if available <= 0:
                raise ValueError('Guest buffer missing from memory snapshot')
            amount = min(available, count)
            self.source.seek(offset + cursor - start)
            data = self.source.read(amount)
            if len(data) != amount:
                raise ValueError('Truncated snapshot payload')
            pieces.append(data)
            cursor += amount
            count -= amount
        return b''.join(pieces)


def fingerprint(vb_address, ib_address, vb, ib):
    """Exact upstream ComputeItemFingerprint, including its nonstandard seed."""
    result = 1469598103934665603
    def mix(value):
        nonlocal result
        result = ((result ^ value) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    for value in [vb_address, ib_address, len(vb), len(ib) // 2]:
        mix(value)
    if len(vb) >= 8 and len(ib) >= 8:
        for k in range(16):
            vo = ((len(vb) - 8) * k // 15) & ~7
            io = ((len(ib) - 8) * k // 15) & ~7
            mix(struct.unpack_from('>Q', vb, vo)[0])
            mix(struct.unpack_from('>Q', ib, io)[0])
    return result
