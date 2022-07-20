from flask import Flask, request
from .kafka_utils import KafkaUtils
from .curl_utils import composeAndExecuteOPACurl, handleQuery
import yaml

import logging
import jwt
import json
import os

ACCESS_DENIED_CODE = 403
ERROR_CODE = 406
VALID_RETURN = 200

FLASK_PORT_NUM = 5559  # this application

FIXED_SCHEMA_ROLE = 'realm_access.roles'
FIXED_SCHEMA_ORG = 'realm_access.organization'

OPA_BLOCK_URL = os.getenv("OPA_URL") if os.getenv("OPA_URL") else '/v1/data/katalog/example/blockList'
OPA_FILTER_URL = os.getenv("OPA_URL") if os.getenv("OPA_URL") else '/v1/data/katalog/example/filters'

CM_PATH = '/etc/confmod/moduleconfig.yaml'  #k8s mount of configmap for general configuration parameters
CM_SITUATION_PATH = '/etc/conf/situationstatus.yaml'

TESTING=False
TESTING_SITUATION_STATUS = 'safe'

app = Flask(__name__)

def readConfig(CM_PATH):
    if not TESTING:
        try:
            with open(CM_PATH, 'r') as stream:
                cmReturn = yaml.safe_load(stream)
        except Exception as e:
            raise ValueError('Error reading from file! ' + CM_PATH)
    else:
        cmDict = {'MSG_TOPIC': 'sm', 'HEIR_KAFKA_HOST': 'kafka.fybrik-system:9092', 'VAULT_SECRET_PATH': None,
                  'SECRET_NSPACE': 'fybrik-system', 'SECRET_FNAME': 'credentials-els',
                  'S3_URL': 'http://s3.eu.cloud-object-storage.appdomain.cloud', 'SUBMITTER': 'EliotSalant',
                  'SAFE_METADATA_URL':'http://localhost/safe-metadata-URL/', 'SAFE_VIDEO_URL':'http://localhost/safe-video-URL/',
                  'UNSAFE_METADATA_URL':'http://localhost/unsafe-metadata-video-URL/', 'UNSAFE_VIDEO_URL':'http://localhost/unsafe-video-URL/'}
        return(cmDict)
    cmDict = cmReturn.get('data', [])
    logging.info(f'cmReturn = ', cmReturn)
    return(cmDict)


# Catch anything
@app.route('/<path:queryString>',methods=['GET', 'POST', 'PUT'])
def getAll(queryString=None):
    cmDict = readConfig(CM_PATH)
# Support JWT token for OAuth 2.1
    noJWT = True
    payloadEncrypted = request.headers.get('Authorization')
    organization = None
    role = None
    if (payloadEncrypted != None):
        noJWT = False
        roleKey = os.getenv("SCHEMA_ROLE") if os.getenv("SCHEMA_ROLE") else FIXED_SCHEMA_ROLE
        organizationKey = os.getenv("SCHEMA_ORG") if os.getenv("SCHEMA_ORG") else FIXED_SCHEMA_ORG
        try:
            role = decryptJWT(payloadEncrypted, roleKey)
        except:
            logging.error("Error: no role in JWT!")
            role = 'ERROR NO ROLE!'
        organization = decryptJWT(payloadEncrypted, organizationKey)
    if (noJWT):
        role = request.headers.get('role')   # testing only
    if (role == None):
        role = 'ERROR NO ROLE!'
    if (organization == None):
        organization = 'NO ORGANIZATION'
    logging.debug('role = ', role, " organization = ", organization)
    if (not TESTING):
    # Determine if the requester has access to this URL.  If the requested endpoint shows up in blockDict, then return 500
        blockDict = composeAndExecuteOPACurl(role, OPA_BLOCK_URL, queryString)
        for resultDict in blockDict['result']:
            blockURL = resultDict['action']
            jString = "\role\": " + role + \
                      ", \"org\": " + organization + \
                      ", \"URL\": " + request.url + \
                      ", \"method\": " + request.method + \
                      "\"Reason\": " + resultDict['name']
            if blockURL == "BlockURL":
                KafkaUtils.logToKafka(jString, KafkaUtils.KAFKA_DENY_TOPIC)
                return ("Access denied!", ACCESS_DENIED_CODE)
            else:
                KafkaUtils.logToKafka(jString, KafkaUtils.KAFKA_ALLOW_TOPIC)

    # Get the filter constraints from OPA
        filterDict = composeAndExecuteOPACurl(role, OPA_FILTER_URL, queryString)   # queryString not needed here
        logging.debug('filterDict = ' + str(filterDict))

    # Go out to the destination URL based on the situation state
    # Assuming URL ends either in 'video' or 'metadata'
    splitRequest = request.url.split('/')
    resourceType = splitRequest[-1].lower()

    if resourceType == 'video':
        safeURLName = cmDict['SAFE_VIDEO_URL']
        unsafeURLName = cmDict['UNSAFE_VIDEO_URL']
    elif resourceType == 'metadata':
        safeURLName = cmDict['SAFE_VIDEO_URL']
        unsafeURLName = cmDict['UNSAFE_VIDEO_URL']
    elif resourceType == 'liveness':   # used for Kubernetes/Helm liveness testing
        return("I'm alive", VALID_RETURN)
    else:
        raise Exception('URL needs to end in "video" or "metadata" - not in '+resourceType)

    logging.info(' safeURLName = ' + str(safeURLName) + ' unsafeURLName = ' + str(unsafeURLName))

    # The environment variable, SITUATION_STATUS, is created from a config map and can be externally changed.
    # The value of this env determines to which URL to write to
    situationStatus = getSituationStatus()
    logging.debug('situationStatus = ' + situationStatus)
    if situationStatus.lower() == 'safe':
        destinationURL = safeURLName
    elif situationStatus.lower() == 'unsafe':
        destinationURL = unsafeURLName
    else:
        raise Exception('situationStatus = ' + situationStatus)

    logging.debug("destinationURL= ", destinationURL, "request.method = " + request.method)
    returnHeaders = ''
    ans, returnHeaders = handleQuery(destinationURL, queryString, request.headers, request.method, request.form, request.args)

    if (ans is None):
        return ("No results returned", VALID_RETURN)

    filteredLine = ''
 # The input can actually be a list, a string (JSON), or interpreted by Python to be a dict
    processing = True
    listIndex = 0
    while processing:
        processing = False
        if (type(ans) is str):
            if (returnHeaders['Content-Type'] == 'video/mp4'):  # this check might not be necessary - type should return as bytes in this case
                logging.debug("binary data found")
                return ans, VALID_RETURN
            try:
                jsonDict = json.loads(ans)
            except:
               logging.debug("Non-JSON string received! ans = " + ans)
               return('Non-JSON string received!',ERROR_CODE)
        elif (type(ans) is dict):
                jsonDict = ans
        elif (type(ans) is bytes):
            logging.debug("Binary bytes received!")
            return ans, VALID_RETURN
        elif (type(ans) is list):
            if (type(ans[listIndex]) is not dict):
                logging.debug("--> WARNING: list of " + str(type(ans[listIndex])) + " - not filtering")
                return(str(ans).replace('\'', '\"' ), VALID_RETURN)
            jsonDict = ans[listIndex]
            listIndex += 1
            if listIndex < len(ans):
                processing = True
        else:
            logging.debug("WARNING: Too complicated - not filtering")
            return (json.dumps(ans), VALID_RETURN)
  #  for line in ans:
        for resultDict in filterDict['result']:
            action = resultDict['action']
            # Handle the filtering here
            if (action == 'Deny'):
                return ('{"action":"Deny","name":"Deny by default"}', ACCESS_DENIED_CODE)
            if (action == 'Allow'):
                return (json.dumps(ans), VALID_RETURN)
            # Note: can have both "RedactColumn" and "BlockColumn" actions in line
            if (action == 'RedactColumn' or action == 'BlockColumn'):
                columns = resultDict['columns']
                for keySearch in columns:
                    recurse(jsonDict, keySearch.split('.'), action)
            if (action == 'Filter'):
                filterPred = resultDict['filterPredicate']

        filteredLine += json.dumps(jsonDict)
        logging.debug("filteredLine", filteredLine)
    return (filteredLine, VALID_RETURN)

def getSituationStatus():
    if not TESTING:
        try:
            with open(CM_SITUATION_PATH, 'r') as stream:
                cmReturn = yaml.safe_load(stream)
                cmDict = cmReturn.get('data', [])
                situationStatus = cmDict['situation-status']
        except Exception as e:
            errorStr = 'Error reading from file! ' + CM_SITUATION_PATH
            raise ValueError(errorStr)
    else:
        situationStatus = TESTING_SITUATION_STATUS

    return(situationStatus)

def decryptJWT(encryptedToken, flatKey):
# String with "Bearer <token>".  Strip out "Bearer"...
    prefix = 'Bearer'
    assert encryptedToken.startswith(prefix), '\"Bearer\" not found in token' + encryptedToken
    strippedToken = encryptedToken[len(prefix):].strip()
    decodedJWT = jwt.api_jwt.decode(strippedToken, options={"verify_signature": False})
    logging.debug('decodedJWT = ', decodedJWT)
 #   flatKey = os.getenv("SCHEMA_ROLE") if os.getenv("SCHEMA_ROLE") else FIXED_SCHEMA_ROLE
# We might have an nested key in JWT (dict within dict).  In that case, flatKey will express the hierarchy and so we
# will interatively chunk through it.
    decodedKey = None
    while type(decodedJWT) is dict:
        for s in flatKey.split('.'):
            if s in decodedJWT:
                decodedJWT = decodedJWT[s]
                decodedKey = decodedJWT
            else:
                logging.debug("warning: " + s + " not found in decodedKey!")
                return decodedKey
    return decodedKey

def recurse(jDict, keySearch, action):
    try:
        i = keySearch.pop(0)
    except:
        logging.debug("Error on keySearch.pop, keySearch = " + str(keySearch))
        return(jDict)
    while i in jDict:
        last = jDict[i]
        if not keySearch:
            if action == 'RedactColumn':
                jDict[i] = 'XXX'
            else:
                del jDict[i]
            return(jDict)
        else:
            recurse(jDict[i], keySearch, action)
            return(jDict)

def startServer():
    app.run(port=FLASK_PORT_NUM, host='0.0.0.0')