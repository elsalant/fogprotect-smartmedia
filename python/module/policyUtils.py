import pandas as pd
import json

TEST = False
VALID_RETURN = 200

class PolicyUtils():
    def __init__(self, logger):
        self.logger = logger

    def get_policies(self):
        #TODO
        policies = ""
        if TEST:
            cmDict = {'dict_item': [
                ('transformations',
                 [])]}
  #               [{'action': 'BlockResource', 'description': 'redact columns: [valueQuantity.value id]',
  #                 'columns': ['valueQuantity.value', 'id'], 'options': {'redactValue': 'XXXXX'}},
  #                {'action': 'ReturnIntent', 'description': 'return intent',
  #                 'columns': ['N/A'], 'intent': 'research'}]), ('assetID', 'sql-fhir/observation-json')]}
            policies = dict(cmDict['dict_item'])
        return policies

    def apply_policy(self, jsonDict):
        ## The use case does not have any policies on filtering the Kafka data.  The policies should no transformations
        policy = self.get_policies()
  #      df = pd.json_normalize(jsonDict)
        df = pd.DataFrame([jsonDict])
        if len(policy['transformations']) == 0:
            self.logger.warning(f'No actions found!')
            return (str(df.to_json()))
        self.logger.info(f'inside apply_policy. Length policies = ' + str(len(policy)) + ' type(policy) = ' + str(type(policy)))
        self.logger.info(f'policy = ' + str(policy))
        action = policy['transformations'][0]['action']
        if action == '':
            return (str(df.to_json()))
        self.logger.info(f'Action = ' + action)

    # Allow specifying a particular attribute for a given resource by specifying the in policy file the
    # the column name as <resource>.<column_name>
        dfToRows = []
        if action == 'DeleteColumn':
            try:
                for col in policy['transformations'][0]['columns']:
                    if '.' in col:
                        (resource, col) = col.split('.')
                        self.logger.info("resource, attribute specified: " + resource + ", " + col)
                        if (df['resourceType'][0]) != resource:
                            continue
                    df.drop(col, inplace=True, axis=1)
            except:
                self.logger.warning(f"No such column " + col + " to delete")
            for i in df.index:
                jsonList = [json.loads(x) for x in dfToRows]
            return (jsonList, VALID_RETURN)
        if action == 'RedactColumn':
            replacementStr = policy['transformations'][0]['options']['redactValue']
            for col in policy['transformations'][0]['columns']:
                if '.' in col:
    # We can either be passing something of the form:  resource.attribute, or attribute, where attribute
    # itself may contain a '.'.  Take the result of the first split and see if that is equal to resourceType to differentiate
                    (resourceCandidate, colCandidate) = col.split('.',1)
                    if resourceCandidate == df['resourceType'][0]:
                        col = colCandidate
                    self.logger.info(f"resource, attribute specified: " + resourceCandidate + ", " + col)
                try:
        # Replace won't replace floats or ints.  Instead, convert to column to be replaced to a string
        # before replacing
      #              df[col].replace(r'.+', replacementStr, regex=True, inplace=True)
                    df[col]= df[col].astype(str).str.replace(r'.+', replacementStr, regex=True)
                except:
                    self.logger.warning(f"No such column " + col + " to redact")
            for i in df.index:
     #           dfToRows = dfToRows + df.loc[i].to_json()
                dfToRows.append(df.loc[i].to_json())
            jsonList = [json.loads(x) for x in dfToRows]
            return (jsonList, VALID_RETURN)

        if action == 'BlockUser':
            return ('{"result": "User blocked by policy!!"}')

        if action == 'BlockResource':
            if df['resourceType'][0] in policy['transformations'][0]['columns']:
                return('{"result": "Resource blocked by policy!!"}')
            else:
                self.logger.error(f'Error in BlockResourced. resourceType =  ' + df['resourceType'][0] + \
                      ' policy[\'transformations\'][0][\'columns\'][0] = ' + df['resourceType'][0] in policy['transformations'][0]['columns'][0])
                return((str(df.to_json())))

        if action == 'AddColumn':
            # Need to get the status from the asset and use this instead of "UNSAFE"
            df['Status'] = 'UNSAFE'
            return('{"result": "Unsafe column added!"}')

        return('{"Unknown transformation": "'+ action + '"}')
