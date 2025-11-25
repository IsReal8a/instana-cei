
import requests
import logging
import json

from utils import handle_api_error, get_api_headers, APIError

logger = logging.getLogger(__name__)


class InstanaAPI:
    """A wrapper for the Instana API."""

    def __init__(self, backend_config):
        self.base_url = backend_config['api_url'].rstrip('/')
        self.headers = get_api_headers(backend_config['api_token'])
        self.verify = not backend_config.get('allow_self_signed_certs', False)

    def _request(self, method, path, **kwargs):
        """Makes a request to the Instana API."""
        url = self.base_url + path
        try:
            response = requests.request(
                method, url, headers=self.headers, verify=self.verify, **kwargs
            )
            response.raise_for_status()  # Raise an exception for bad status codes
            return response.json()
        except requests.exceptions.HTTPError as e:
            handle_api_error(e.response, url)
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request to {url} failed: {e}")

    def get(self, path, **kwargs):
        """Makes a GET request."""
        return self._request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        """Makes a POST request."""
        return self._request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        """Makes a PUT request."""
        return self._request("PUT", path, **kwargs)
