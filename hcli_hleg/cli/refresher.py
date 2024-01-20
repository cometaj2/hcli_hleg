import io
import sys
import logger
import threading
import time
import requests
import certifi
import xmltodict
import json
import traceback

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
            glby = "https://wslwebservices.leg.wa.gov/LegislationService.asmx/GetLegislationByYear?year=2024"
            logging.info("Requesting legislations for the current year...")
            response = requests.get(glby, data=None, stream=True, verify=self.session.verify)
            raw_legislation_data = self.get_dictionary(response)

            active_legislation_set = set()
            if raw_legislation_data is not None:
                for legislation in raw_legislation_data["ArrayOfLegislationInfo"]["LegislationInfo"]:
                    if legislation["Active"] == "true":
                        active_legislation_set.add(legislation["BillNumber"])

            active_legislations = sorted(list(active_legislation_set))

            all_hearings = []
            logging.info("Requesting legislation and hearing information for each active legislation...")
            for legislation in active_legislations:
                gl = "https://wslwebservices.leg.wa.gov/LegislationService.asmx/GetLegislation?biennium=2023-24&billNumber=" + legislation
                gh = "https://wslwebservices.leg.wa.gov/LegislationService.asmx/GetHearings?biennium=2023-24&billNumber=" + legislation
                response = requests.get(gl, data=None, stream=True, verify=self.session.verify)
                legislation_data = self.get_dictionary(response)
                response = requests.get(gh, data=None, stream=True, verify=self.session.verify)
                hearings_data = self.get_dictionary(response)

                if legislation_data is not None and hearings_data is not None:

                    legislation_data_type = legislation_data["ArrayOfLegislation"]["Legislation"]
                    legislation_data_corrected = legislation_data["ArrayOfLegislation"]["Legislation"]
                    if isinstance(legislation_data_type, list):
                        pass
                    elif isinstance(legislation_data_type, dict):
                        legislation_data_corrected = [legislation_data_corrected]
                    else:
                        logging.error("Unexpected data format for legislation.")

                    for legislation in legislation_data_corrected:
                        bill_id = legislation["BillId"]
                        logging.info("Processing " + bill_id + ".")

                        bill_number = legislation["BillNumber"]
                        agency = legislation["OriginalAgency"]

                        short_description = ''
                        if "ShortDescription" in legislation:
                            short_description = legislation["ShortDescription"]

                        long_description = legislation["LongDescription"]

                        if "Hearing" in hearings_data["ArrayOfHearing"]:
                            hearing_data_type = hearings_data["ArrayOfHearing"]["Hearing"]
                            hearing_data_corrected = hearings_data["ArrayOfHearing"]["Hearing"]
                            if isinstance(hearing_data_type, list):
                                pass
                            elif isinstance(hearing_data_type, dict):
                                hearing_data_corrected = [hearing_data_corrected]
                            else:
                                logging.error("Unexpected data format for hearing.")

                            for hearing in hearing_data_corrected:
                                if bill_id == hearing["BillId"]:
                                    hearing_type = hearing["HearingType"]
                                    hearing_type_description = hearing["HearingTypeDescription"]
                                    date = hearing["CommitteeMeeting"]["Date"]
                                    revised_date = hearing["CommitteeMeeting"]["RevisedDate"]

                                    committee_data_type = hearing["CommitteeMeeting"]["Committees"]["Committee"]
                                    committee_data_corrected = hearing["CommitteeMeeting"]["Committees"]["Committee"]
                                    if isinstance(committee_data_type, list):
                                        pass
                                    elif isinstance(committee_data_type, dict):
                                        committee_data_corrected = [committee_data_corrected]
                                    else:
                                        logging.error("Unexpected data format for committees.")

                                    committees = []
                                    for committee in committee_data_corrected:
                                        committee_id = committee["Id"]
                                        committee_longname = committee["LongName"]
                                        committees.append({
                                                              'committee_id' : committee_id,
                                                              'committee_longname' : committee_longname
                                        })

                                    all_hearings.append({
                                                            'bill_id': bill_id,
                                                            'short_description' : short_description,
                                                            'long_description' : long_description,
                                                            'agency' : agency,
                                                            'committees' : committees,
                                                            'date' : date,
                                                            'revised_date' : revised_date,
                                                            'hearing_type' : hearing_type,
                                                            'hearing_type_description' : hearing_type_description
                                    })
                else:
                    logging.error("Error retrieving some of the legislation or hearings data for legislation " + legislation)

            print(json.dumps(all_hearings, indent=4))

        except TerminationException as e:
            self.abort()
        except Exception as e:
            logging.error(e)
            traceback.print_exc()
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

    def get_dictionary(self, response):
        if response.status_code >= 400:
            code = response.status_code
            logging.info(code, requests.status_codes._codes[code][0])
            logging.info(response.headers)
            logging.info(response.content)
        else:
            return xmltodict.parse(response.content.decode())

        return None

class TerminationException(Exception):
    pass
