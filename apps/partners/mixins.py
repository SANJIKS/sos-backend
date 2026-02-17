class BuildFullUrlToImage:
    """
    Mixin class for building complete URLs to image resources.
    Can be used with models or views that need to construct full image URLs.
    """

    def get_full_url_to_image(self, image_path):
        """
        Builds a complete URL for an image by combining request's base URL with image path.

        Args:
            image_path (str | FieldFile | StorageFile | None): Relative path or file object

        Returns:
            str | None: Complete URL to the image, original absolute URL, or None if not available
        """
        if not image_path:
            return None

        path = getattr(image_path, 'url', image_path)

        if not path:
            return None

        if isinstance(path, str) and (path.startswith('http://') or path.startswith('https://')):
            return path

        request = getattr(self, 'request', None)
        if not request:
            context = getattr(self, 'context', None)
            if isinstance(context, dict):
                request = context.get('request')

        if not request:
            return path

        return request.build_absolute_uri(path)
