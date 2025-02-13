package service

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"

	// "github.com/free5gc/openapi/models"
	"github.com/free5gc/openapi/models"
	"nef.com/consumer"
	nef_context "nef.com/context"
	"nef.com/factory"
)

type NefApp struct {
	nefCtx *nef_context.NEFContext
	cfg    *factory.Config
	server *http.Server
	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

func NewApp(ctx context.Context, cfg *factory.Config) (*NefApp, error) {
	// nef := &NefApp{
	// 	cfg: cfg,
	// }
	server := &http.Server{
		Addr: fmt.Sprintf("%s:%d", cfg.Configuration.Sbi.RegisterIPv4, cfg.Configuration.Sbi.Port),
		// Addr: ":8081",
	}

	nef := &NefApp{
		cfg:    cfg,
		server: server,
		ctx:    ctx,
	}
	// nef.server = server
	// nef.ctx, nef.cancel = context.WithCancel(context.Background())
	return nef, nil
}

func (a *NefApp) Start() {
	a.setupServiceHandlers()

	if a.server == nil {
		log.Fatal("Server is nil")
	}

	a.nefCtx = nef_context.NEF_Self()
	log.Printf("NEF context: %+v\n", a.nefCtx)
	var profile models.NfProfile

	profile = consumer.BuildNFInstance(a.nefCtx)
	// if profile == nil {
	// 	log.Fatal("Failed to build NEF Profile")
	// }

	go func() {
		log.Printf("Starting NEF server on %s\n", a.server.Addr)
		if err := a.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Could not listen on %s: %v\n", a.server.Addr, err)
		}
	}()

	// Register with NRF
	consumer.SendRegisterNFInstance(a.nefCtx.NrfUri, a.nefCtx.NfId, profile)

	// Wait for interrupt signal to gracefully shut down the server
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	<-sigCh

	a.Terminate()
}

func (a *NefApp) Terminate() {
	consumer.SendDeregisterNFInstance()
	log.Println("Shutting down NEF...")
	if err := a.server.Shutdown(a.ctx); err != nil {
		log.Printf("HTTP server Shutdown: %v", err)
	}
	a.cancel()
	a.wg.Wait()
}

func (a *NefApp) setupServiceHandlers() {
	mux := http.NewServeMux()
	mux.HandleFunc("/nef-info", a.handleNefInfo)
	// Add more handlers for NEF-specific endpoints
	a.server.Handler = mux
}

func (a *NefApp) handleNefInfo(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	// Implement NEF info response
}

// Add more NEF-specific methods here, such as:
// - HandleAPIExposure
// - ManageSubscriptions
// - ProcessNetworkEvents
// etc.
