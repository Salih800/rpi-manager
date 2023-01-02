class SizeConverter:
    def __init__(self, size: int = 0):
        """
        :param size:
        """
        self.bytes = size
        # self.kb = self.convert_to_kb(self.bytes)
        # self.mb = self.convert_to_mb(self.bytes)
        # self.gb = self.convert_to_gb(self.bytes)

    def __str__(self):
        return self.sizeof_fmt(self.bytes)

    def __add__(self, other):
        self.bytes += other.bytes
        return self

    def __sub__(self, other):
        self.bytes -= other.bytes
        return self

    def __mul__(self, other):
        self.bytes *= other.bytes
        return self

    def __truediv__(self, other):
        self.bytes /= other.bytes
        return self

    @staticmethod
    def sizeof_fmt(num, suffix="B"):
        for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
            if abs(num) < 1024.0:
                return f"{num:3.1f}{unit}{suffix}"
            num /= 1024.0
        return f"{num:.1f}Yi{suffix}"

    @staticmethod
    def convert_to_kb(size):
        return size / 1024

    @staticmethod
    def convert_to_mb(size):
        return size / 1024 ** 2

    @staticmethod
    def convert_to_gb(size):
        return size / 1024 ** 3

    @staticmethod
    def convert_to_tb(size):
        return size / 1024 ** 4

    @staticmethod
    def convert_to_pb(size):
        return size / 1024 ** 5

    @staticmethod
    def convert_to_eb(size):
        return size / 1024 ** 6

    @staticmethod
    def convert_to_zb(size):
        return size / 1024 ** 7
