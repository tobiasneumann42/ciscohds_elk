# ciscohds_elk
Scripts used with Cisco Spark HDS and ELK stack

author  Tobias Neumann, tneumann(at)cisco.com

the configuration files and scripts in this repository are intented to be used with a lab excercise for 
Cisco Spark Hybrid Data Security(HDS) in conjunction with ELK for logging. 

All information in this repository is provided as is. Cisco Systems does not provide any support or 
warranty for the content. Use at your own risk.

/tmp/patterns/ciscokms      - includes sample patterns to parse messages send by Cisco HDS nodes to ELK
/tmp/scripts/spark_proc.py  - sample script that allows admins of Cisco HDS deployments to enrich the
                              logging information with human readable userIDs. This script requires refresh
                              and access token information.
                            
