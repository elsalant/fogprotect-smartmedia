import urllib.parse as urlparse
import requests
import os
import re
import curlify
import logging

logger = logging.getLogger('curl_utils.py')
logger.setLevel(logging.DEBUG)

TESTING = False
if TESTING:
    OPA_SERVER = 'localhost'
else:
    OPA_SERVER = 'opa.default'

OPA_PORT = os.getenv("OPA_SERVICE_PORT") if os.getenv("OPA_SERVICE_PORT") else 8181
OPA_ENDPT = os.getenv("OPA_URL") if os.getenv("OPA_URL") else '/v1/data/dataapi/authz/rule'
OPA_HEADER = {"Content-Type": "application/json"}
ASSET_NAMESPACE = os.getenv("ASSET_NAMESPACE") if os.getenv("ASSET_NAMESPACE") else 'default'


def composeAndExecuteOPACurl(role, passedURL, restType, situationStatus):
    parsedURL = urlparse.urlparse(passedURL)
    #    asset = parsedURL.path[1:]
    asset = parsedURL[1] + parsedURL[2]
    # If we have passed parameters, asset will end in a '/' which needs to be stripped off
    if (asset[-1] == '/'):
        asset = asset[:-1]
    assetName = asset.replace('/', '.').replace('_', '-')
    ## TBD - role is being put into the header as a string - it should go in as a list for Rego.  What we are doing
    ## now requires the Rego to do a substring search, rather than search in a list

    opa_query_body = '{ \"input\": { \
        \"request\": { \
        \"method\": \"' + restType + '\", \
        \"role\": \"' + str(role) + '\", \
        \"asset\": { \
        \"namespace\": \"' + ASSET_NAMESPACE + '\", \
        \"name\": \"' + assetName + '\", \
        \"situationStatus\": \"' + situationStatus + '\" \
        }  \
        }  \
        }  \
        }'

    urlString = 'http://' + OPA_SERVER + ":" + str(OPA_PORT) + OPA_ENDPT
    logger.debug('For OPA query: urlString = ' + urlString + " opa_query_body " + opa_query_body)

    r = requests.post(urlString, data=opa_query_body, headers=OPA_HEADER)

    if (r is None):  # should never happen
        raise Exception("No values returned from OPA! for " + urlString + " data " + opa_query_body)
    try:
        returnString = r.json()
    except Exception as e:
        logger.debug("r.json fails - " + urlString + " data " + opa_query_body)
        raise Exception("No values returned from OPA! for " + urlString + " data " + opa_query_body)

    logger.debug('returnString = ' + str(returnString))
    return (returnString)


def forwardQuery(destinationURL, request):
    # Go out to the actual destination webserver
    logger.debug("queryGatewayURL= " + destinationURL + " request.method = " + request.method)
    returnCode = handleQuery(destinationURL, request.headers, request.method, request.form,
                             request.args)
    return (returnCode)


def handleQuery(queryGatewayURL, passedHeaders, method, values, args):
    curlString = queryGatewayURL
    logger.debug("curlCommands: curlString = " + curlString)
    try:
        if (method == 'POST'):
            r = requests.post(curlString, headers=passedHeaders, data=values, params=args)
        else:
            r = requests.get(curlString, headers=passedHeaders, data=values, params=args)
    except Exception as e:
        logger.debug(
            "Exception in handleQuery, curlString = " + curlString + ", method = " + method + " passedHeaders = " + str(
                passedHeaders) + " values = " + str(values))
        raise ConnectionError('Error connecting ')
    logger.debug("curl request = " + curlify.to_curl(r.request))
    return (r.content, r.status_code)


def decodeQuery(queryString):
    return (urlparse.unquote_plus(queryString))
