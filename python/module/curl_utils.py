import urllib.parse as urlparse
import requests
import os
import re
import curlify
import logging

OPA_SERVER = os.getenv("OPA_SERVER") if os.getenv("OPA_SERVER") else 'localhost'

OPA_PORT = os.getenv("OPA_SERVICE_PORT") if os.getenv("OPA_SERVICE_PORT") else 8181
OPA_FILTER_URL = os.getenv("OPA_URL") if os.getenv("OPA_URL") else '/v1/data/katalog/example/filters'
OPA_BLOCK_URL = os.getenv("OPA_URL") if os.getenv("OPA_URL") else '/v1/data/katalog/example/blockList'
OPA_HEADER = {"Content-Type": "application/json"}
ASSET_NAMESPACE = os.getenv("ASSET_NAMESPACE") if os.getenv("ASSET_NAMESPACE") else 'default'

def composeAndExecuteOPACurl(role, queryURL, passedURL):
    # The assumption is that the if there are query parameters (queryString), then this is prefixed by a "?"

    parsedURL = urlparse.urlparse(passedURL)
#    asset = parsedURL.path[1:]
    asset = parsedURL[1]+parsedURL[2]
    # If we have passed parameters, asset will end in a '/' which needs to be stripped off
    if (asset[-1] == '/'):
        asset = asset[:-1]
    logging.debug("asset = " + asset)
    assetName = asset.replace('/', '.').replace('_','-')
 ## TBD - role is being put into the header as a string - it should go in as a list for Rego.  What we are doing
 ## now requires the Rego to do a substring search, rather than search in a list

    opa_query_body = '{ \"input\": { \
\"request\": { \
\"operation\": \"READ\", \
\"role\": \"' + str(role) + '\", \
\"asset\": { \
\"namespace\": \"' + ASSET_NAMESPACE + '\", \
\"name\": \"' + assetName + '\" \
}  \
}  \
}  \
}'

    urlString = 'http://' + OPA_SERVER + ":" + str(OPA_PORT) + queryURL
    logging.debug('urlString = ' + urlString + " assetName = " + assetName + " opa_query_body " + opa_query_body)

    r = requests.post(urlString, data=opa_query_body, headers=OPA_HEADER)

    if (r is None):  # should never happen
        raise Exception("No values returned from OPA! for " + urlString + " data " + opa_query_body)
    try:
        returnString = r.json()
    except Exception as e:
        logging.debug("r.json fails - " + urlString + " data " + opa_query_body)
        raise Exception("No values returned from OPA! for " + urlString + " data " + opa_query_body)

    logging.debug('returnString = ' + str(returnString))
    return (returnString)

def forwardQuery(destinationURL, request, queryString):
    # Go out to the actual destination webserver
    logging.debug("queryGatewayURL= ", destinationURL, "request.method = " + request.method)
    returnCode = handleQuery(destinationURL, queryString, request.headers, request.method, request.form,
                                     request.args)
    return (returnCode)

def handleQuery(queryGatewayURL, queryString, passedHeaders, method, values, args):
    #  print("querystring = " + queryString)
    queryStringsLessBlanks = re.sub(' +', ' ', queryString)

    curlString = queryGatewayURL + urlparse.unquote_plus(queryStringsLessBlanks)
    #   curlString = queryGatewayURL + str(base64.b64encode(queryStringsLessBlanks.encode('utf-8')))
#    if 'Host' in passedHeaders:  # avoid issues with istio gateways
#      passedHeaders.pop('Host')
    logging.debug("curlCommands: curlString = ", curlString)
    try:
      if (method == 'POST'):
        r = requests.post(curlString, headers=passedHeaders, data=values, params=args)
      else:
        r = requests.get(curlString, headers = passedHeaders, data=values, params=args)
    except Exception as e:
      logging.debug("Exception in handleQuery, curlString = " + curlString + ", method = " + method  + " passedHeaders = " + str(passedHeaders)  + " values = " + str(values))
      logging.debug(e.message, e.args)

    logging.debug("curl request = " + curlify.to_curl(r.request))
    return(r.status_code)

def decodeQuery(queryString):
    return(urlparse.unquote_plus(queryString))