#Grafana-tools

Grafana-tools contains the:
- container tests (**/tests**)
- service tests (**/tests**)
- script to reset the Grafana admin password (**/grafana_lib**)

##Launch container tests

The folder **tests_config** contains the configuration parameters needed to run the tests.

```
python -m pytest tests/test_grafana_container.py -vs --config-file tests_config/dev.json
```

The paremeter **-v** and **-s** are used to increase the verbosity. 

##Launch service test

```
python -m pytest tests/test_grafana_service.py -vs --grafana-config-file tests_config/grafana.json
```