"""
Some camera specific parsers put here in order to keep the camera implementation
code more readable.
"""
# standard library
from html import parser
from urllib.parse import urlparse


class RidgetecParser(parser.HTMLParser):
    """
    Extract metadata from RidgTec HTML email.
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
                url_parts = urlparse(attr[1])
                self.filename = url_parts.path.split('/')[-1]
            elif attr[0] == 'data-date-time-created':
                self.date_time_created = attr[1]
            elif attr[0] == 'data-timezone':
                self.timezone = attr[1]
            elif attr[0] == 'data-imei':
                self.imei = str(attr[1])
            elif attr[0] == 'data-account-id':
                self.account_id = str(attr[1])
