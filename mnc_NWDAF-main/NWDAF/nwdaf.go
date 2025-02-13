package main

import (
	// "fmt"
	"os"
	"os/signal"
	"syscall"

	"github.com/sirupsen/logrus"
	"github.com/urfave/cli"

	NativeContext "context"

	"github.com/free5gc/version"
	"nwdaf.com/context"
	"nwdaf.com/factory"
	"nwdaf.com/logger"
	"nwdaf.com/service"
)

// var NWDAF = &service.NWDAF{}
var NWDAF *service.NwdafApp

var appLog *logrus.Entry

func init() {
	appLog = logger.AppLog
}

func main() {
	app := cli.NewApp()
	app.Name = "nwdaf"
	appLog.Infoln(app.Name)
	appLog.Infoln("NWDAF version: ", version.GetVersion())
	app.Usage = "-free5gccfg common configuration file -nwdafcfg nwdaf configuration file"
	app.Action = action
	// app.Flags = NWDAF.GetCliCmd()
	app.Flags = []cli.Flag{
		cli.StringFlag{
			Name:  "config, c",
			Usage: "Load configuration from `FILE`",
		},
		cli.StringSliceFlag{
			Name:  "log, l",
			Usage: "Output NF log to `FILE`",
		},
	}
	if err := app.Run(os.Args); err != nil {
		appLog.Errorf("NWDAF Run error: %v", err)
		return
	}
}

func action(c *cli.Context) error {

	ctx, cancel := NativeContext.WithCancel(NativeContext.Background())
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	go func() {
		<-sigCh  // Wait for interrupt signal to gracefully shutdown
		cancel() // Notify each goroutine and wait them stopped
	}()

	cfg, err := factory.ReadConfig(c.String("config"))
	if err != nil {
		return err
	}
	factory.NwdafConfig = cfg

	context.InitNwdafContext(factory.NwdafConfig)

	// if err := NWDAF.Initialize(c); err != nil {
	// 	logger.CfgLog.Errorf("%+v", err)
	// 	return fmt.Errorf("Failed to initialize !!")
	// }
	nwdaf, err := service.NewApp(ctx, cfg)
	if err != nil {
		return err
	}
	NWDAF = nwdaf
	nwdaf.Start()

	return nil
}
