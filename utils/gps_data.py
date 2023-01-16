import os.path
from datetime import datetime, timezone
from constants.folders import location_records


def dd2dms(dd):
    dd = float(dd)
    mnt, sec = divmod(dd * 3600, 60)
    deg, mnt = divmod(mnt, 60)
    return round(deg * 100 + mnt + sec / 100, 4)


def ddm2dd(ddm):
    ddm = float(ddm)
    degrees = int(ddm // 100)
    minutes = (ddm % 100) / 60
    return round(degrees + minutes, 6)


def dd2ddm(dd):
    dd = float(dd)
    degrees = int(dd)
    minutes = (dd % 1) * 60
    return round(degrees * 100 + minutes, 4)


def dms2dd(dms):
    dms = float(dms)
    degrees = int(dms // 100)
    minutes = int(dms % 100) / 60
    seconds = (dms % 1) / 36
    return round(degrees + minutes + seconds, 6)


class GPSData:
    def __init__(self, gps_string):
        self.gps_string = gps_string.strip("\r\n").strip("$GPSACP: ")
        self.gps_data = self.gps_string.split(",")
        self.UTC = self.gps_data[0]  # UTC time
        self.lat = self.gps_data[1]  # latitude in ddmm.mmmm format
        self.lat_dir = ""  # N or S
        self.lng = self.gps_data[2]  # longitude in dddmm.mmmm format
        self.lng_dir = ""  # W or E
        self.hdop = self.gps_data[3]  # Horizontal Dilution of Precision
        self.altitude = self.gps_data[4]  # xxxx.x altitude in meters
        self.fix = self.gps_data[5]  # 0 or 1 = Invalid, 2 = 2D, 3 = 3D
        self.cog = self.gps_data[6]  # ddd.mm course over ground in degrees (ddd = 000 to 360) (mm = 00 to 59)
        self.spkm = self.gps_data[7]  # speed in km/h
        self.spkn = self.gps_data[8]  # speed in knots
        self.date = self.gps_data[9]  # ddmmmyy Date of fix
        self.nsat_gps = self.gps_data[10]  # Total number of GPS satellites in use (0-12)
        self.nsat_glonass = self.gps_data[11]  # Total number of GLONASS satellites in use (0-12)

        if self.fix == "2":
            self.fix2d = True
            self.fix3d = False
        elif self.fix == "3":
            self.fix2d = True
            self.fix3d = True
        else:
            self.fix2d = False
            self.fix3d = False

        if self.fix2d or self.fix3d:
            self.fix = int(self.fix)

            self.UTC_date = datetime.strptime(self.date + self.UTC, "%d%m%y%H%M%S.%f")
            self.local_date = self.UTC_date.replace(tzinfo=timezone.utc).astimezone(tz=None)
            self.local_date_str = self.local_date.strftime("%y%m%d-%H%M%S")

            self.lat_dir = self.lat[-1]
            self.lat = ddm2dd(self.lat[:-1])

            self.lng_dir = self.lng[-1]
            self.lng = ddm2dd(self.lng[:-1])

            self.gps_location = {"lat": self.lat, "lng": self.lng}

            self.altitude = float(self.altitude)
            self.hdop = float(self.hdop)
            self.cog = float(self.cog)
            self.spkm = float(self.spkm)
            self.spkn = float(self.spkn)
            self.nsat_gps = int(self.nsat_gps)
            self.nsat_glonass = int(self.nsat_glonass)

        self.save_to_file()

    def to_dict(self):
        return {"UTC": self.UTC, "latitude": self.lat, "longitude": self.lng, "hdop": self.hdop,
                "altitude": self.altitude, "fix": self.fix, "cog": self.cog, "spkm": self.spkm, "spkn": self.spkn,
                "date": self.date, "nsat_gps": self.nsat_gps, "nsat_glonass": self.nsat_glonass}

    def to_string(self):
        return self.gps_string

    def to_camera(self):
        return f"{self.lat}{self.lat_dir},{self.lng}{self.lng_dir},{self.cog},{self.spkm}kmh"

    def is_valid(self):
        return self.fix2d or self.fix3d

    def data_to_upload(self):
        return {"date": self.local_date.strftime("%Y-%m-%d %H:%M:%S"),
                "lat": str(self.lat),
                "lng": str(self.lng),
                "speed": str(self.spkm)}

    def save_to_file(self):
        if not os.path.isdir(location_records):
            os.mkdir(location_records)
        filename = location_records + datetime.now().strftime("%Y-%m-%d") + ".txt"
        with open(filename, "a") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')}: {self.gps_string}\n")
