# rize.py

Script to analyze reserved instance utilization.

This is a fork of https://github.com/manos/AWS-Reserved-Instances-Optimizer but with all the handling for costs stripped out to keep it dead simple; for my purposes all I care about is the count of instances I'm missing.

# Identifies:
* Count of reservations that aren't being used
* Running instances that aren't reserved

## Prerequisites
You'll need to install `boto` and `texttable` into a virtualenv:
```
virtualenv env
source env/bin/activate
pip install boto texttable
```

Then configure `boto` with your AWS key:
```
cat <<EOF > ~/.boto
[Credentials]
aws_access_key_id = foo
aws_secret_access_key = bar
EOF
```

## Running:
Run with defaults:
```
./rize.py
```

Exclude instances with security group matching -e <regex>:
```
./rize.py -e '^ElasticMap.*'
```

Run in us-west-2:
```
./rize.py -r us-west-2
```

List all reserved instances and exit:
```
./rize.py -l
```

Operate only on VPC instances/reservations:
```
./rize.py --vpc
```
