# pylint:disable=E0401
"""
Implement cameras as subclass of BaseCamera class. Camera specific code should
be contained to these classes.
"""
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
        Extract additional metadata from emails' body, subject line, etc.
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
            exif = self.get_exif(image) # NOTE: we only really need to do this for cuddelinks at the moment.
            print(f'exif: {exif}')
            new_tags = self.prep_new_tags(existing_exif=exif)
            print(f'new_tags: {new_tags}')
            helpers.enrich_exif(image, new_tags)
            yield image


class RidgetecCamera(BaseCamera):
    """
    Implements RidgeTec camera emails.
    """
    name = 'RidgeTec'

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

    def evaluate_make(self):
        return 'cuddelink' in self.email['From']

    def get_images(self):
        return helpers.save_attached_images(self.email)

    def prep_new_tags(self, existing_exif=None):
        print(f'prep_new_tags - Cuddeback - existing_exif: {existing_exif}')
        ret = {}
        existing_exif = [{}] if not existing_exif else existing_exif
        print(f'prep_new_tags - Cuddeback - existing_exif: {existing_exif}')
        user_comments = existing_exif[0].get('EXIF:UserComment', '').split(',')
        print(f'prep_new_tags - Cuddeback - user_comments: {user_comments}')
        cam_id = None
        for comment in user_comments:
            key, value = comment.split('=')
            if key == 'ID':
                cam_id = value
                break
        if cam_id:
            ret['SerialNumber'] = cam_id
        return ret

    def get_exif(self, image):
        return helpers.get_exif(image)
