import logging
import requests


def check_connection(url="https://cdn.atiknakit.com", timeout=5):
    try:
        requests.head(url, timeout=timeout)
        return True
    except requests.exceptions.ConnectionError:
        pass
    except requests.Timeout:
        pass
    return False


def connect(host='http://google.com'):
    import urllib.request
    try:
        urllib.request.urlopen(host) #Python 3.x
        return True
    except:
        return False


def post(url, **kwargs):
    response = requests.Response()
    response.status_code = -1
    try:
        response = requests.post(url=url, **kwargs)  # TODO: show reason in error
    except requests.exceptions.ConnectionError:
        # logging.warning("Connection Error while sending request to {}".format(url))
        response.reason = "Connection Error while sending request to {}".format(url)
        response.status_code = -2
    except requests.Timeout:
        # logging.warning("Timeout while posting to {}".format(url))
        response.reason = "Timeout while posting to {}".format(url)
        response.status_code = -3
    except:
        logging.error("Error in post request to {}".format(url), exc_info=True)
    return response


def get(url, **kwargs):
    response = requests.Response()
    response.status_code = -1
    try:
        response = requests.get(url=url, **kwargs)
    except requests.exceptions.ConnectionError:
        # logging.warning("Connection error while getting from {}".format(url))
        response.reason = "Connection error while getting from {}".format(url)
        response.status_code = -2
    except requests.Timeout:
        # logging.warning("Timeout while getting from {}".format(url))
        response.reason = "Timeout while getting from {}".format(url)
        response.status_code = -3
    except requests.exceptions.ChunkedEncodingError:
        # logging.warning("Chunked Encoding Error while getting from {}".format(url))
        response.reason = "Chunked Encoding Error while getting from {}".format(url)
        response.status_code = -4
    except:
        logging.error("Error in get request to {}".format(url), exc_info=True)
    return response
