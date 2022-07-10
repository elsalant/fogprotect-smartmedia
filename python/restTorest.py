import yaml
import logging

import module.flask_utils as flaskUtils

ACCESS_DENIED_CODE = 403
ERROR_CODE = 406
VALID_RETURN = 200

TEST = True   # allows testing outside of Fybrik/Kubernetes environment

FIXED_SCHEMA_ROLE = 'missing role'
FIXED_SCHEMA_ORG  = 'missing org'

#Kafka is used for logging requests
kafkaDisabled = False

logger = logging.getLogger(__name__)
cmDict = {}

def readConfig(CM_PATH):
    if not TEST:
        try:
            with open(CM_PATH, 'r') as stream:
                cmReturn = yaml.safe_load(stream)
        except Exception as e:
            raise ValueError('Error reading from file! ' + CM_PATH)
    else:
        cmDict = {'SAFE_URL':'safe-url', 'UNSAFE_URL':'unsafe-url'}
        return(cmDict)
    cmDict = cmReturn.get('data', [])
    logger.info(f'cmReturn = ', cmReturn)
    return(cmDict)

def main():
    global cmDict
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"starting module!!")

if __name__ == "__main__":
    main()
    flaskUtils.startServer()