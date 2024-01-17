import io
import sys
import logger
import threading
import time
import requests
import certifi
import xmltodict
import json

from hcli_hleg import config

logging = logger.Logger()


# Singleton Refresher
class Refresher:
    instance = None
    is_running = False
    lock = None
    terminate = None
    session = None

    def __new__(self):
        if self.instance is None:

            self.instance = super().__new__(self)
            self.lock = threading.Lock()
            self.exception_event = threading.Event()
            self.session = requests.Session()

            if config.ssl_verify == "verify":
                self.session.verify = certifi.where()
            elif config.ssl_verify == "skip":
                self.session.verify = False

            self.terminate = False

        return self.instance

    # background refresh process that periodically aggregates legislature information.
    def refresh(self):
        self.is_running = True
        self.terminate = False

        try:
            #gac = "https://wslwebservices.leg.wa.gov/CommitteeService.asmx/GetActiveCommittees"
            #logging.info("Requesting committee information...")
            #r = requests.get(gac, data=None, stream=True, verify=self.session.verify)
            #committees = self.output(r, committees)

            glby = "https://wslwebservices.leg.wa.gov/LegislationService.asmx/GetLegislationByYear?year=2024"
            logging.info("Requesting legislations for the current year...")
            r = requests.get(glby, data=None, stream=True, verify=self.session.verify)
            legislations = self.output(r)

        except TerminationException as e:
            self.abort()
        except Exception as e:
            logging.error(e)
            self.abort()
        finally:
            self.terminate = False
            self.is_running = False

        return

    def check_termination(self):
        if self.terminate:
            raise TerminationException("Terminated.")

    def abort(self):
        self.is_running = False
        self.terminate = False

    def get_dictionary(self, response, dictionary):
        if response.status_code >= 400:
            code = response.status_code
            logging.info(code, requests.status_codes._codes[code][0])
            logging.info(response.headers)
            logging.info(response.content)
        else:
            #cleanup = json.dumps(xmltodict.parse(response.content.decode()), indent=4)
            #logging.info(cleanup)
            return xmltodict.parse(response.content.decode())

        return None

class TerminationException(Exception):
    pass
