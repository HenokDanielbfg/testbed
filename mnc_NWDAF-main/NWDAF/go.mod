module nwdaf.com

go 1.14

replace nwdaf.com/logger => ../logger

replace nwdaf.com/service => ../service

replace nwdaf.com/factory => ../factory

replace nwdaf.com/util => ../util

// replace nef.com => /home/henokbfg/Documents/mnc_NWDAF-main/NEF

// replace nef.com/server => ../server

replace nwdaf.com/consumer => ../consumer
replace nwdaf.com/producer => ../producer


replace nwdaf.com/context => ../context

require (
	github.com/antonfisher/nested-logrus-formatter v1.3.0
	github.com/free5gc/logger_conf v1.0.0
	github.com/free5gc/logger_util v1.0.0
	github.com/free5gc/openapi v1.0.8
	github.com/free5gc/version v1.0.0
	github.com/gin-gonic/gin v1.10.0 // indirect
	github.com/google/uuid v1.3.0
	github.com/prometheus/client_golang v1.20.5
	github.com/sirupsen/logrus v1.9.3
	github.com/urfave/cli v1.22.4
	golang.org/x/net v0.26.0 // indirect
	gopkg.in/yaml.v2 v2.4.0
	// nef.com v0.0.0 // indirect
)
