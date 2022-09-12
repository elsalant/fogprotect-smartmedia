curl -X PUT \
-H 'content-type:text/plain' \
--data-binary @../misc/policy_smartmedia.rego \
http://localhost:8181/v1/policies/policy-smartmedia