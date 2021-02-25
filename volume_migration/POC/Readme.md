## testcase 1:
### mongodb:
- 1x Deployment (mongo1-deployment)
- 1 PVC (mongo-pvc)
- 1 Service (Load Balancer, VPN required)
    
#### How to:
1. prepare testdata

``` 
cd datexis-k8s/utils/csi-migration/POC/
make clean
make pocdata 

```
2. check database:
- install compass (mongo client)
- connect via mongodb://cl-svc-243.ris.beuth-hochschule.de:27017/
- have a look at sync-db

3. run migration

``` 
cd datexis-k8s/utils/csi-migration/migration/
python3 csi-migration.py

```

## testcase 2:
### multiple pvc

#### How to:
- Deployment
- 2 PVCs
