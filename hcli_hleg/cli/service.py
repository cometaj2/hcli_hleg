import io
import json
import sys
import os
import re
import time
import inspect
import logger
import refresher as r
import threading
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from collections import OrderedDict

logging = logger.Logger()
logging.setLevel(logger.INFO)


class Service:
    controller = None
    scheduler = None
    jogger = None
    refresher = None
    root = os.path.dirname(inspect.getfile(lambda: None))

    def __init__(self):
        global scheduler

        scheduler = BackgroundScheduler()
        self.refresher = r.Refresher()
        process = self.schedule(self.refresh_data)
        scheduler.start()

        return

    def ls(self):
        return self.refresher.ls()

    # we schedule immediate single instance job executions.
    def schedule(self, function):
        return scheduler.add_job(function, 'date', run_date=datetime.now(), max_instances=1)

    # we run the refresher singleton in the background to refresh legislature information
    def refresh_data(self):
        with self.refresher.lock:
            while True:
                if not self.refresher.is_running:
                    self.refresher.refresh()

                time.sleep(86400)

# we kick off the background service immediately to avoid having to wait for the first request to come through.
Service()
