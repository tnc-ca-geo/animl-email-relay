# pylint:disable=E0401
"""
Implement cameras as subclass of BaseCamera class. Camera specific code should
be contained to these classes.
"""
# standard library
import re
# project
import helpers
import parsers


class BaseCamera():
    """
    A base camera class defining an interface between generic and camera
    specific code assuming that all relevant information can be derrived from
    an email object.
    """
    name = 'other'

    def __init__(self, email):
        """
        Initialize camera parser class from an email.

        Args:
            email(an email object): As defined in standard library email module.
        """
        self.email = email
        self.metadata = self.get_additional_metadata()

    def __str__(self):
        """
        This will be returned when str() called with this class.
        """
        return self.name

    def evaluate_make(self):
        """
        Checks whether the email represents a message from the camera make
        that can be processed by thios class. True for base class as a fall
        back.

        Returns:
            bool
        """
        return True

    def get_additional_metadata(self):
        """
        Extract additional metadata from emails' bodies, subject lines, etc.
        """
        return {}

    def prep_new_tags(self, extra_data=None):
        """
        Format the new data that will be added to the images' exif
        """
        raise NotImplementedError('Not Implemented')

    def get_exif(self, image):
        """
        Wrapper around reading exif data. If we don't need to read
        existing data, we can just return an empty dict.

        Args:
            image(Image): An image
        Returns:
            dict
        """
        del image
        return {}

    def get_images(self):
        """
        Get images by downloading or extracting them from an email. The
        implementation must return a string that represents the temporary file.
        The filename, i.e. the last part of the path, will be the filename that
        will be used to store the image in the Animl ingestion S3 bucket.

        Returns:
            str
        """
        raise NotImplementedError('Camera make not implemented.')

    def images(self):
        """
        Process images.
        """
        for image in self.get_images():
            # NOTE: we only really need to get exif for cuddelinks at the moment
            # but we're currently reading it before and after updates for all
            # cameras for debugging purposes
            exif = self.get_exif(image)
            print(f'existing exif: {exif}')
            new_tags = self.prep_new_tags(existing_exif=exif)
            helpers.enrich_exif(image, new_tags)
            updated_exif = self.get_exif(image)
            print(f'updated exif: {updated_exif}')
            yield image


class RidgetecCamera(BaseCamera):
    """
    Implements RidgeTec camera emails.
    """
    name = 'RidgeTec'

    def get_exif(self, image):
        return helpers.get_exif(image)
    
    def evaluate_make(self):
        return 'ridgetec' in self.email['From']

    def get_additional_metadata(self):
        ridgetec_parser = parsers.RidgetecParser()
        ridgetec_parser.feed(self.email.as_string())
        return {
            field:getattr(ridgetec_parser, field) for field in
            ['filename', 'img_url', 'imei', 'date_time_created', 'account_id']}

    def prep_new_tags(self, existing_exif=None):
        return {
            # TODO: double check why we're setting Make. 
            # Do Ridgetecs not include makes in their exif?
            'Make': str(self),
            'SerialNumber': self.metadata.get('imei'),
            'DateTimeOriginal': self.metadata.get(
                'date_time_created', '').replace('-', ':'),
            'UserComment': f'AccountId={self.metadata.get("account_id")}'}

    def get_images(self):
        filename = self.metadata.get('filename')
        url = self.metadata.get('img_url')
        yield helpers.download_image(filename, url)


class CuddebackCamera(BaseCamera):
    """
    Implements Cuddelink camera emails.
    """
    name = 'CUDDEBACK'

    def get_exif(self, image):
        return helpers.get_exif(image)
    
    def evaluate_make(self):
        return 'cuddelink' in self.email['From']

    def get_images(self):
        return helpers.save_attached_images(self.email)

    def prep_new_tags(self, existing_exif=None):
        ret = {}
        existing_exif = [{}] if not existing_exif else existing_exif
        user_comments = existing_exif[0].get('EXIF:UserComment', '').split(',')
        cam_id = None
        for comment in user_comments:
            key, value = comment.split('=')
            if key == 'ID':
                cam_id = value
                break
        if cam_id:
            ret['SerialNumber'] = cam_id
        return ret
    

class SpartanCamera(BaseCamera):
    """
    Implements Spartan camera emails.
    """
    name = 'Spartan'

    def get_exif(self, image):
        return helpers.get_exif(image)
    
    def evaluate_make(self):
        return 'hcowireless' in self.email['From']
    
    def get_additional_metadata(self):
        subject_line = self.email['subject']
        print(f'subject line: {subject_line}')
        camera_id = subject_line.split('-')[-1]
        return {'camera_id': camera_id} if camera_id else {}

    def get_images(self):
        return helpers.save_attached_images(self.email)

    def prep_new_tags(self, existing_exif=None):
        return {'SerialNumber': self.metadata.get('camera_id')}


class SwiftCamera(BaseCamera):
    """
    Implements Swift camera emails.
    """
    name = 'Swift'
    # Serial number is embedded in the attachment filename in the subject
    # line, e.g. `... -SYPR0799.JPG`.
    SERIAL_RE = re.compile(r'-(SY[A-Z0-9]+)\.', re.IGNORECASE)

    def get_exif(self, image):
        return helpers.get_exif(image)

    def evaluate_make(self):
        return 'wuyuansys.net' in self.email['From']

    def get_additional_metadata(self):
        body_part = self.email.get_body(preferencelist=('plain',))
        try:
            body_text = body_part.get_content() if body_part else ''
        except (KeyError, AttributeError):
            body_text = ''
        swift_parser = parsers.SwiftParser()
        swift_parser.feed(body_text)
        subject = self.email['subject'] or ''
        serial_match = self.SERIAL_RE.search(subject)
        return {
            'camera_id': swift_parser.camera_id,
            'date_time_created': swift_parser.date_time_created,
            'serial_number': serial_match.group(1) if serial_match else None}

    def get_images(self):
        return helpers.save_attached_images(self.email)

    def prep_new_tags(self, existing_exif=None):
        existing_exif = [{}] if not existing_exif else existing_exif
        existing = existing_exif[0]
        camera_id = self.metadata.get('camera_id')
        candidates = {
            'Make': str(self),
            'SerialNumber': self.metadata.get('serial_number'),
            'DateTimeOriginal': self.metadata.get('date_time_created'),
            'UserComment': (
                f'CameraId={camera_id}' if camera_id else None)}
        # Always normalize Make to our own label; for the other tags preserve
        # any value the camera already wrote to the image's EXIF.
        always_overwrite = {'Make'}
        ret = {}
        for key, value in candidates.items():
            if not value:
                continue
            if key not in always_overwrite and existing.get(f'EXIF:{key}'):
                continue
            ret[key] = value
        return ret

