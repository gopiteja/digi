import logging
import os



class Logging(logging.Logger):
    def __init__(self, **kwargs):
        log_levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }

        logging_config = {
            'level': log_levels['debug'],
            'format': '%(asctime)s - [%(traceID)s] - %(levelname)s - [%(tenantID)s] - %(message)s'
        }
        
        logging.basicConfig(**logging_config)

        logging.getLogger('kafka').disabled = True
        logging.getLogger('kafka.client').disabled = True
        logging.getLogger('kafka.cluster').disabled = True
        logging.getLogger('kafka.conn').disabled = True
        logging.getLogger('kafka.consumer.fetcher').disabled = True
        logging.getLogger('kafka.consumer.group').disabled = True
        logging.getLogger('kafka.consumer.subscription_state').disabled = True
        logging.getLogger('kafka.coordinator').disabled = True
        logging.getLogger('kafka.coordinator.consumer').disabled = True
        logging.getLogger('kafka.metrics.metrics').disabled = True
        logging.getLogger('kafka.producer.kafka').disabled = True
        logging.getLogger('kafka.producer.record_accumulator').disabled = True
        logging.getLogger('kafka.producer.sender').disabled = True
        logging.getLogger('matplotlib').disabled = True
        logging.getLogger('matplotlib.font_manager').disabled = True
        logging.getLogger('requests').disabled = True
        logging.getLogger('urllib3.connectionpool').disabled = True
        logging.getLogger('werkzeug').disabled = True

        self.extra = {
            'tenantID': None,
            'traceID': None
        }

        self.set_ids(**kwargs)

    def set_ids(self):
        tenant_id = None
        trace_id = None

        # logging.debug(f'Tenant ID: {tenant_id}', extra=self.extra)
        # logging.debug(f'Trace ID: {trace_id}', extra=self.extra)

        self.tenant_id = tenant_id
        self.trace_id = trace_id
        self.extra = {
            'tenantID': self.tenant_id,
            'traceID': self.trace_id
        }

    def basicConfig(self, *args, **kwargs):
        logging.basicConfig(**kwargs)

    def debug(self, msg, *args, **kwargs):
        self.set_ids()
        logging.debug(msg, extra=self.extra, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.set_ids()
        logging.info(msg, extra=self.extra, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.set_ids()
        logging.warning(msg, extra=self.extra, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.set_ids()
        logging.error(msg, extra=self.extra, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.set_ids()
        logging.critical(msg, extra=self.extra, *args, **kwargs)

    def exception(self, msg, *args, **kwargs):
        self.set_ids()
        logging.exception(msg, extra=self.extra, *args, **kwargs)

    def getLogger(self, name=None):
        return logging.getLogger(name=name)

    def disable(self, level):
        logging.disable(level)
