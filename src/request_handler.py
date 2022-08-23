import logging
import requests


# create a class that can check the internet connection before sending requests
class RequestApi:
    @staticmethod
    def check_connection(url="https://cdn.atiknakit.com", timeout=5):
        try:
            requests.head(url, timeout=timeout)
            return True
        except requests.exceptions.ConnectionError:
            return False
        except requests.Timeout:
            return False

    @staticmethod
    def post(url, **kwargs):
        try:
            return requests.post(url=url, **kwargs)
        except requests.exceptions.ConnectionError:
            logging.warning("Connection Error while sending request to {}".format(url))
        except requests.Timeout:
            logging.warning("Timeout while posting to {}".format(url))
        except:
            logging.error("Error in post request to {}".format(url), exc_info=True)
        return requests.Response()

    @staticmethod
    def get(url, **kwargs):
        try:
            return requests.get(url=url, **kwargs)
        except requests.exceptions.ConnectionError:
            logging.warning("Connection error while getting from {}".format(url))
        except requests.Timeout:
            logging.warning("Timeout while getting from {}".format(url))
        except:
            logging.error("Error in get request to {}".format(url), exc_info=True)
        return requests.Response()
