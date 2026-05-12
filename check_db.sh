#!/bin/bash
podman exec backend psql -U postgres -d quantdinger -c "
SELECT ec.id as cred_id, ec.name, ec.exchange_id, 
       ak.id as ak_id, ak.api_key, ak.key_name, ak.credential_id, ak.active 
FROM qd_exchange_credentials ec 
LEFT JOIN qd_api_keys ak ON ec.id = ak.credential_id 
ORDER BY ec.id DESC LIMIT 5;
"
