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
FIXED_SCHEMA_ORG = 'organization'
FIXED_SCHEMA_USER = 'name'
FIXED_PREFERRED_NAME = 'preferred_username'

KAFKA_DENY_TOPIC = os.getenv("KAFKA_DENY_TOPIC") if os.getenv("KAFKA_TOPIC") else "blocked-access"
KAFKA_ALLOW_TOPIC = os.getenv("KAFKA_ALLOW_TOPIC") if os.getenv("KAFKA_TOPIC") else "granted-access"

CM_PATH = '/etc/confmod/moduleconfig.yaml'  #k8s mount of configmap for general configuration parameters
CM_SITUATION_PATH = '/etc/conf/situationstatus.yaml'

TESTING=False
TESTING_SITUATION_STATUS = 'safe'

app = Flask(__name__)
logger = logging.getLogger('flask_utils.py')
logger.setLevel(logging.DEBUG)
logger.info('setting log level to DEBUG')

kafkaUtils = KafkaUtils()

def readConfig(CM_PATH):
    if not TESTING:
        try:
            with open(CM_PATH, 'r') as stream:
                cmReturn = yaml.safe_load(stream)
        except Exception as e:
            raise ValueError('Error reading from file! ' + CM_PATH)
    else:
        cmReturn = {'MSG_TOPIC': 'sm', 'HEIR_KAFKA_HOST': 'kafka.fybrik-system:9092', 'VAULT_SECRET_PATH': None,
                  'SECRET_NSPACE': 'fybrik-system', 'SECRET_FNAME': 'credentials-els',
                  'S3_URL': 'http://s3.eu.cloud-object-storage.appdomain.cloud', 'SUBMITTER': 'EliotSalant',
                  'SAFE_METADATA_URL':'http://localhost/safe-metadata-URL/', 'SAFE_VIDEO_URL':'http://localhost/safe-video-URL/',
                  'UNSAFE_METADATA_URL':'http://localhost/unsafe-metadata-video-URL/', 'UNSAFE_VIDEO_URL':'http://localhost/unsafe-video-URL/'}
    return(cmReturn)

# Catch anything
@app.route('/<path:queryString>',methods=['GET', 'POST', 'PUT'])
def getAll(queryString=None):
    # Ignore liveness requests
    splitRequest = request.url.split('/')
    resourceType = splitRequest[-1].lower()
    if resourceType == 'liveness':   # used for Kubernetes/Helm liveness testing
        return("I'm alive", VALID_RETURN)
    cmDict = readConfig(CM_PATH)
# Support JWT token for OAuth 2.1
    noJWT = True
    payloadEncrypted = request.headers.get('Authorization')
    organization = 'Not defined'
    role = 'Not defined'
    user = 'Not defined'
    if (payloadEncrypted == None):
        logger.debug("----> payloadEncrypted = None !!")
    if (payloadEncrypted != None):
        noJWT = False
        roleKey = os.getenv("SCHEMA_ROLE") if os.getenv("SCHEMA_ROLE") else FIXED_SCHEMA_ROLE
        try:
            role = decryptJWT(payloadEncrypted, roleKey)
            # Role will be returned as a list.  To make life simple in the policy, assume that only
            # first element is the real role.  Maybe fix this one day...
            if type(role) is list:
                role = role[0]
        except:
            logger.error("Error: no role in JWT!")
            role = 'ERROR NO ROLE!'
        userKey = os.getenv("SCHEMA_USER") if os.getenv("SCHEMA_USER") else FIXED_SCHEMA_USER
        preferredUserNameKey = FIXED_PREFERRED_NAME
        try:
            user = decryptJWT(payloadEncrypted, preferredUserNameKey)
        except:
            logger.error("No preferred_username in JWT!  Trying \'name\'")
            try:
                user = decryptJWT(payloadEncrypted, userKey)
            except:
                logger.error("Error: no user in JWT!")
                user = 'ERROR NO USER!'
        try:
            sub = decryptJWT(payloadEncrypted, 'sub')
        except:
            logger.error("No sub in JWT!")
            sub = 'MISSING SUB!'
        organizationKey = os.getenv("SCHEMA_ORG") if os.getenv("SCHEMA_ORG") else FIXED_SCHEMA_ORG
        try:
            organization = decryptJWT(payloadEncrypted, organizationKey)
        except:
            logger.error("Error: no organization in JWT!")
            organization = 'ERROR NO organizationKey!'
    if (noJWT):
        role = request.headers.get('role')   # testing only
    if (role == None):
        role = 'ERROR NO ROLE!'
    if (organization == None):
        organization = 'NO ORGANIZATION'
    logger.debug('-> role = ' + str(role) + " organization = " + str(organization) + " user = " + str(user))
    # The environment variable, SITUATION_STATUS, is created from a config map and can be externally changed.
    # The value of this env determines to which URL to write to
    situationStatus, unsafeEntityName, unsafeOrganization = getSituationStatus()
    logger.debug('After getSituationStatus, situationStatus = ' + situationStatus + ', \
        unsafeEntityName = ' + unsafeEntityName + ' unsafeOrganization = ' + unsafeOrganization)
    if (not TESTING):
    # Determine if the requester has access to this URL.  If the requested endpoint shows up in opaDict, then return 500
        opaDict = composeAndExecuteOPACurl(role, queryString, request.method, situationStatus, user, unsafeEntityName, organization)
        logger.info('After call to OPA, opaDict = ' + str(opaDict))
        try:
            if len(opaDict['result']) == 0:
                jString = \
                          "{\"user\": \"" + str(user) +  "\"" \
                          ", \"sub\": \"" + str(sub) + "\"" + \
                          ", \"role\": \"" + str(role) + "\"" + \
                          ", \"org\": \"" + str(organization) + "\"" + \
                          ", \"URL\": \"" + request.url + "\"" + \
                          ", \"method\": \"" + request.method + "\"" + \
                          ", \"reason\": \"" + "No restrictions by default" + "\"}"
                kafkaUtils.writeToKafka(jString, KAFKA_ALLOW_TOPIC)
            else:
                for resultDict in opaDict['result']:
                    blockURL = resultDict['action']
                    logger.debug('blockURL = ' + str(blockURL))
                    jString = \
                              "{\"user\": \"" + str(user) +  "\"" \
                              ", \"sub\": \"" + str(sub) + "\"" + \
                              ", \"role\": \"" + str(role) + "\"" + \
                              ", \"org\": \"" + str(organization) + "\"" + \
                              ", \"URL\": \"" + request.url + "\"" + \
                              ", \"method\": \"" + request.method + "\"" + \
                              ", \"reason\": \"" + resultDict['name'] + "\"}"
                    if blockURL == "BlockURL" or blockURL == "BlockUser" or blockURL == "BlockRole" or blockURL == 'BlockResource':
                        kafkaUtils.writeToKafka(jString, KAFKA_DENY_TOPIC)
                        return ("Access denied!", ACCESS_DENIED_CODE)
                    else:
                        kafkaUtils.writeToKafka(jString, KAFKA_ALLOW_TOPIC)
        except:
            logger.debug('OOps - opaDict does not return a result ' + str(opaDict))
            jString = \
                "{\"user\": \"" + str(user) + "\"" + \
                ", \"sub\": \"" + str(sub) + "\"" + \
                ", \"role\": \"" + str(role) + "\"" + \
                ", \"org\": \"" + str(organization) + "\"" + \
                ", \"URL\": \"" + request.url + "\"" + \
                ", \"method\": \"" + request.method + "\"" + \
                ", \"reason\": " + '"No rules found"}'
            kafkaUtils.writeToKafka(jString, KAFKA_ALLOW_TOPIC)
    # Go out to the destination URL based on the situation state
    # Assuming URL ends either in 'video' or 'metadata'
    splitRequest = request.url.split('/')
    resourceType = splitRequest[-1]
#    if 'video' in resourceType:  # URL can either end in 'video' or 'video/<image>
#        safeURLName = cmDict['SAFE_VIDEO_URL']
#        unsafeURLName = cmDict['UNSAFE_VIDEO_URL']
#    elif resourceType == 'surveys':
#        safeURLName = cmDict['SAFE_VIDEO_URL']
#        unsafeURLName = cmDict['UNSAFE_VIDEO_URL']
#    elif resourceType == 'liveness':   # used for Kubernetes/Helm liveness testing
#        return("I'm alive", VALID_RETURN)
#    else:
#        raise Exception('URL needs to end in "video" or "survey" - not in '+resourceType)

    if request.method == 'GET':
        destinationURL = cmDict['BASE_URL']+request.path      #request.url
    else:  # Redirect on write operations
        if situationStatus.lower() == 'safe':
            destinationURL = cmDict['BASE_URL']+request.path
        elif 'unsafe' in situationStatus.lower():
            destinationURL = cmDict['BASE_URL']+request.path+'/quarantine'
        else:
            raise Exception('Error - bad situationStatus = ' + situationStatus)

    logger.debug("destinationURL= " + destinationURL + "  request.method = " + request.method + " queryString = " + queryString)
    returnHeaders = ''
    ans, returnStatus = handleQuery(destinationURL, request.headers, request.method, request.form, request.args)

    if (ans is None or returnStatus != VALID_RETURN):
        return ("No results returned", returnStatus)

    filteredLine = ''
 # The input can actually be a list, a string (JSON), or interpreted by Python to be a dict
    processing = True
    listIndex = 0
    while processing:
        processing = False
        if (type(ans) is str):
            try:
                jsonDict = json.loads(ans)
            except:
               logger.debug("Non-JSON string received! ans = " + ans)
               return('Non-JSON string received!',ERROR_CODE)
        elif (type(ans) is dict):
                jsonDict = ans
        elif (type(ans) is bytes):
            logger.debug("Binary bytes received!")
            return ans, VALID_RETURN
        elif (type(ans) is list):
            if (type(ans[listIndex]) is not dict):
                logger.debug("--> WARNING: list of " + str(type(ans[listIndex])) + " - not filtering")
                return(str(ans).replace('\'', '\"' ), VALID_RETURN)
            jsonDict = ans[listIndex]
            listIndex += 1
            if listIndex < len(ans):
                processing = True
        else:
            logger.debug("WARNING: Too complicated - not filtering")
            return (json.dumps(ans), VALID_RETURN)
  #  for line in ans:
        try:
            for resultDict in opaDict['result']:
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
        except:
            logger.debug('no redaction rules returned')
        filteredLine += json.dumps(jsonDict)
        logger.debug("filteredLine: " + filteredLine)
    return (filteredLine, VALID_RETURN)

def getSituationStatus():
    blockUser = 'N/A'
    blockedEntity = 'N/A'
    unsafeOrganization = 'N/A'
    if not TESTING:
        try:
            with open(CM_SITUATION_PATH, 'r') as stream:
                cmReturn = yaml.safe_load(stream)
 #               cmDict = cmReturn.get('data', [])
                situationStatus = cmReturn['situation-status']
                logger.info('situationStatus in getSituationStatus = ' + situationStatus)
                if situationStatus == 'unsafe-user':
                    blockedEntity = cmReturn['unsafeUserName']
                    logger.info('blockUser = ' + blockedEntity)
                if situationStatus == 'unsafe-role':
                    blockedEntity = cmReturn['unsafeRoleName']
                    try:
                        unsafeOrganization = cmReturn['unsafeOrganization']
                    except:
                        print("ERROR: No unsafeOrganization passed in unsafe role yaml!")
                        unsafeOrganization = 'ERROR - missing unsafe organization'
                    logger.info('blockRole = ' + str(blockedEntity))
                if situationStatus == 'organization-unsafe':
                    blockedEntity = 'ATC'
                    try:
                        unsafeOrganization = cmReturn['unsafeOrganization']
                    except:
                        print("ERROR: No unsafeOrganization passed in unsafe role yaml!")
                        unsafeOrganization = 'ATC'
                    logger.info('unsafeOrganization = ' + unsafeOrganization)
        except Exception as e:
            errorStr = 'Error reading from file! ' + CM_SITUATION_PATH
            raise ValueError(errorStr)
    else:
        situationStatus = TESTING_SITUATION_STATUS

    return(situationStatus, blockedEntity, unsafeOrganization)

def decryptJWT(encryptedToken, flatKey):
# String with "Bearer <token>".  Strip out "Bearer"...
    prefix = 'Bearer'
    assert encryptedToken.startswith(prefix), '\"Bearer\" not found in token' + encryptedToken
    strippedToken = encryptedToken[len(prefix):].strip()
 #   decodedJWT = jwt.api_jwt.decode(strippedToken, options={"verify_signature": False})
    decodedJWT = jwt.decode(strippedToken, options={"verify_signature": False})
#    logger.info(decodedJWT)

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
                logger.debug("warning: " + s + " not found in decodedKey!")
                return None
    return decodedKey

def recurse(jDict, keySearch, action):
    try:
        i = keySearch.pop(0)
    except:
        logger.debug("Error on keySearch.pop, keySearch = " + str(keySearch))
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