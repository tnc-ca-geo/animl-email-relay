"""
Some camera specific parsers put here in order to keep the camera implementation
code more readable.
"""
# standard library
import os
import re
from html import parser
from urllib.parse import urlparse


class RidgetecParser(parser.HTMLParser):
    """
    Extract metadata from RidgeTec HTML email.
    """

    def __init__(self):
        super().__init__()
        self.img_url = None
        self.filename = 'UNKNOWN_FILENAME.JPG'
        self.date_time_created = None
        self.timezone = None
        self.imei = None
        self.account_id = None

    def handle_starttag(self, tag, attrs):
        """
        Extract Attributes from start tags

        Args:
            tag(str): A certain tag from which to extract.
            attrs(list(str)): Attributes
        Returns:
            object
        """
        for attr in attrs:
            if attr[0] == 'src':
                self.img_url = attr[1]
            elif attr[0] == 'data-filename':
                self.filename = str(attr[1])
            elif attr[0] == 'data-date-time-created':
                self.date_time_created = attr[1]
            elif attr[0] == 'data-timezone':
                self.timezone = attr[1]
            elif attr[0] == 'data-imei':
                self.imei = str(attr[1])
            elif attr[0] == 'data-account-id':
                self.account_id = str(attr[1])


class SwiftParser():
    """
    Extract metadata from a Swift camera plain-text email body.

    Expected body format:
        Camera ID: <id>
        Pic was taken on Date & Time:(DD/MM/YYYY  HH:MM:SS)
    """

    CAMERA_ID_RE = re.compile(r'Camera\s*ID:\s*(.+?)\s*(?:\r?\n|$)')
    DATE_TIME_RE = re.compile(
        r'Pic was taken on Date & Time:\s*'
        r'\((\d{2})/(\d{2})/(\d{4})\s+(\d{2}:\d{2}:\d{2})\)')

    def __init__(self):
        self.camera_id = None
        self.date_time_created = None

    def feed(self, text):
        """
        Parse a plain-text email body.

        Args:
            text(str): The decoded plain-text body of a Swift email.
        """
        cam_match = self.CAMERA_ID_RE.search(text)
        if cam_match:
            self.camera_id = cam_match.group(1).strip()
        dt_match = self.DATE_TIME_RE.search(text)
        if dt_match:
            day, month, year, time = dt_match.groups()
            # ExifTool expects DateTimeOriginal as 'YYYY:MM:DD HH:MM:SS'
            self.date_time_created = f'{year}:{month}:{day} {time}'


class UOVisionParser(parser.HTMLParser):
    """
    Extract metadata from a UOVision / LinckEazi HTML email body.

    Expected body format (HTML):
        Date:DD.MM.YYYY<br>Time:HH:MM:SS<br>...
        <img src="https://msp-thumbnail.../FILENAME.jpg">
    """

    DATE_RE = re.compile(r'Date:(\d{2})\.(\d{2})\.(\d{4})')
    TIME_RE = re.compile(r'Time:(\d{2}:\d{2}:\d{2})')

    def __init__(self):
        super().__init__()
        self.img_url = None
        self.filename = 'UNKNOWN_FILENAME.JPG'
        self.date_time_created = None
        self._date = None
        self._time = None

    def handle_starttag(self, tag, attrs):
        if tag == 'img':
            for attr_name, attr_value in attrs:
                if attr_name == 'src':
                    self.img_url = attr_value
                    self.filename = os.path.basename(
                        urlparse(attr_value).path) or 'UNKNOWN_FILENAME.JPG'

    def handle_data(self, data):
        date_match = self.DATE_RE.search(data)
        if date_match:
            self._date = date_match.groups()  # (day, month, year)
        time_match = self.TIME_RE.search(data)
        if time_match:
            self._time = time_match.group(1)
        if self._date and self._time:
            day, month, year = self._date
            # ExifTool expects DateTimeOriginal as 'YYYY:MM:DD HH:MM:SS'
            self.date_time_created = f'{year}:{month}:{day} {self._time}'
