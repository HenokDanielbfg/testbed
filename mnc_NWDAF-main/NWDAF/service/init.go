package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"sync"
	"syscall"

	"github.com/free5gc/openapi/Nnrf_NFDiscovery"
	"github.com/free5gc/openapi/models"
	"github.com/gin-gonic/gin"

	// "github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"golang.org/x/net/http2"
	"nwdaf.com/consumer"
	nwdaf_context "nwdaf.com/context"
	"nwdaf.com/factory"
	"nwdaf.com/producer"
	// "github.com/prometheus/client_golang/prometheus/promhttp"
)

type NwdafApp struct {
	nwdafCtx *nwdaf_context.NWDAFContext
	cfg      *factory.Config
	// nwdaf  *NWDAF
	server *http.Server
	ctx    context.Context
	cancel context.CancelFunc
	wg     sync.WaitGroup
}

type Config struct {
	Info          *NfInstanceInfo
	Configuration *NwdafInfo
	ServingAreas  []string
}

type Server struct {
	httpServer *http.Server
	router     *gin.Engine
}

type NfInstanceInfo struct {
	NfInstanceId string
	NfType       string
	NfStatus     string
}

type NwdafInfo struct {
	EventIds []string
}

type NWDAF struct {
	NfInstanceInfo *NfInstanceInfo
	NwdafInfo      *NwdafInfo
	ServingAreas   []string
}

type AMFEvent struct {
	EventType string `json:"eventType"`
	Timestamp int64  `json:"timestamp"`
	Data      string `json:"data"`
}

// SMFEvent represents the structure of SMF events
type SMFEvent struct {
	EventType string `json:"eventType"`
	Timestamp int64  `json:"timestamp"`
	Data      string `json:"data"`
}

func NewApp(ctx context.Context, cfg *factory.Config) (*NwdafApp, error) {
	// nwdaf := &NWDAF{
	// 	NfInstanceInfo: cfg.NWDAFCon,
	// 	NwdafInfo:      cfg.Configuration,
	// 	ServingAreas:   cfg.ServingAreas,
	// }
	server := &http.Server{
		Addr: fmt.Sprintf("%s:%d", cfg.Configuration.Sbi.RegisterIPv4, cfg.Configuration.Sbi.Port),

		// ReadTimeout:    10 * time.Second,
		// WriteTimeout:   10 * time.Second,
		// IdleTimeout:    60 * time.Second,
		// MaxHeaderBytes: 1 << 20, // 1 MB
	}

	http2.ConfigureServer(server, &http2.Server{})

	nwdaf := &NwdafApp{
		cfg:    cfg,
		server: server,
		ctx:    ctx,
	}
	// nwdaf.SetLogEnable(cfg.GetLogEnable())
	// nwdaf.SetLogLevel(cfg.GetLogLevel())
	// nwdaf.SetReportCaller(cfg.GetLogReportCaller())

	return nwdaf, nil
}

func (a *NwdafApp) Start() {
	a.setupServiceHandlers()

	if a.server == nil {
		log.Fatal("Server is nil")
	}
	a.nwdafCtx = nwdaf_context.NWDAF_Self()
	fmt.Printf("Sending Nwdaf context for building: %+v\n", a.nwdafCtx)

	var profile models.NfProfile
	// if profileTmp := consumer.BuildNFInstance(a.nwdafCtx)!= nil {
	// 	logger.InitLog.Error("Build AMF Profile Error")
	// } else {
	// 	profile = profileTmp
	// }
	profile = consumer.BuildNFInstance(a.nwdafCtx)

	go func() {
		log.Printf("Starting NWDAF server on address %s", a.server.Addr)
		if err := a.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Could not listen on :8001: %v\n", err)
		}
	}()

	consumer.SendRegisterNFInstance(a.nwdafCtx.NrfUri, a.nwdafCtx.NfInstanceID, profile)
	amfInstances, err := QueryNRFForNF(a.nwdafCtx, models.NfType_AMF)
	if err != nil {
		log.Fatalf("Error querying NRF for AMF: %v", err)
	}
	// log.Print(amfInstances.NfInstances[0].Ipv4Addresses)
	smfInstances, err := QueryNRFForNF(a.nwdafCtx, models.NfType_SMF)
	if err != nil {
		log.Fatalf("Error querying NRF for SMF: %v", err)
	}

	consumer.SubscribeToAMFStatusChange(a.nwdafCtx, amfInstances.NfInstances)
	AmfsubId, err := consumer.SubscribeToAMF_UEStatus(a.nwdafCtx, amfInstances.NfInstances[0])
	if err != nil {
		log.Fatalf("Error subscribing to amf event: %v", err)
	} else {
		log.Printf("AMF event subscription Id is: %s", AmfsubId)
	}

	SmfsubId, err := consumer.SubscribeToSMFEvents(a.nwdafCtx, smfInstances.NfInstances[0])
	if err != nil {
		log.Fatalf("Error subscribing to smf event: %v", err)
	} else {
		log.Printf("SMF event subscription Id is: %s", SmfsubId)
	}

	// a.wg.Add(1)
	// go a.listenShutdownEvent()
	// Wait for interrupt signal to gracefully shut down the server
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, os.Interrupt, syscall.SIGTERM)
	<-sigCh

	consumer.UnsubscribeFromAMF_UEStatus(a.nwdafCtx, AmfsubId, amfInstances.NfInstances[0])
	consumer.UnsubscribeFromSMF_events(a.nwdafCtx, SmfsubId, smfInstances.NfInstances[0])
	consumer.SendDeregisterNFInstance()

	a.Terminate()
}

func (a *NwdafApp) Terminate() {
	// consumer.SendDeregisterNFInstance()
	log.Println("Shutting down NWDAF...")
	if err := a.server.Shutdown(context.Background()); err != nil {
		log.Printf("HTTP server Shutdown: %v", err)
	}
}

func (a *NwdafApp) setupServiceHandlers() {
	router := gin.Default()

	// Create API group for version control
	v1 := router.Group("/nnwdaf-analyticsinfo/v1")
	{
		// Add middleware for this group
		// v1.Use(authMiddleware())

		// Define routes
		// v1.POST("/analytics", handleAnalyticsPost)
		v1.GET("/analytics", producer.HandleAnalyticsRequest)
	}
	router.Handle("POST", "/nnwdaf-amfStatus", consumer.HandleAMFStatus)
	router.Handle("POST", "/nnwdaf-amfEvents", consumer.HandleAMFEvents)
	router.Handle("POST", "/nnwdaf-smfEvents", consumer.HandleSMFEvents)

	router.Handle("GET", "/metrics", gin.WrapH(promhttp.Handler()))

	a.server.Handler = router
	// mux := http.NewServeMux()
	// mux.HandleFunc("/", a.handleNwdafInfo)
	// // mux.HandleFunc("/nnwdaf-analyticsinfo/v1/analytics", a.handleNwdafAnalytics)
	// mux.HandleFunc("/amf-status", a.handleAMFStatusEvent)
	// mux.HandleFunc("/amf-events", a.handleAMFEvents)
	// mux.Handle("/metrics", promhttp.Handler()) // Expose metrics on /metrics

	// a.server.Handler = mux
}

func (a *NwdafApp) handleNwdafInfo(w http.ResponseWriter, r *http.Request) {
	log.Println("you've reached the nwdaf server")
	fmt.Fprintf(w, "Hello, you've reached the nwdaf server!")
	w.Header().Set("Content-Type", "application/json")
	// json.NewEncoder(w).Encode(a.nwdaf)
}

func QueryNRFForNF(nwdafCtx *nwdaf_context.NWDAFContext, NFType models.NfType) (*models.SearchResult, error) {
	nrfUri := nwdafCtx.NrfUri

	configuration := Nnrf_NFDiscovery.NewConfiguration()
	configuration.SetBasePath(nrfUri)
	client := Nnrf_NFDiscovery.NewAPIClient(configuration)
	ctx, _, err := nwdafCtx.GetTokenCtx(models.ServiceName_NNRF_DISC, models.NfType_NRF)
	if err != nil {
		return nil, err
	}
	result, res, err := client.NFInstancesStoreApi.SearchNFInstances(ctx, NFType, models.NfType_NWDAF, nil)
	if res != nil && res.StatusCode == http.StatusTemporaryRedirect {
		return nil, fmt.Errorf("temporary Redirect For Non NRF Consumer")
	}
	if res == nil || res.Body == nil {
		return &result, err
	}
	defer func() {
		if res != nil {
			if bodyCloseErr := res.Body.Close(); bodyCloseErr != nil {
				err = fmt.Errorf("SearchNFInstances' response body cannot close: %+w", bodyCloseErr)
			}
		}
	}()
	return &result, err

}

// Error response structure for issues like 400, 404, etc.
type ProblemDetails struct {
	Status int    `json:"status"`
	Title  string `json:"title"`
	Detail string `json:"detail"`
}

func (a *NwdafApp) handleAMFStatusEvent(w http.ResponseWriter, r *http.Request) {
	log.Println("you've reached the nwdaf amf status server")

	if r.Method != http.MethodPost {
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(ProblemDetails{
			Status: 405,
			Title:  "Method Not Allowed",
			Detail: "Only POST method is allowed",
		})
		return
	}

	// Read the body of the request
	body, err := io.ReadAll(r.Body)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(ProblemDetails{
			Status: 500,
			Title:  "Internal Server Error",
			Detail: "Failed to read the request body",
		})
		return
	}
	defer r.Body.Close()

	// Unmarshal the request body into the notification structure
	var notification models.AmfStatusChangeNotification
	err = json.Unmarshal(body, &notification)
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(ProblemDetails{
			Status: 400,
			Title:  "Bad Request",
			Detail: "Invalid JSON format",
		})
		return
	}

	// Process the notification (e.g., store, log, or trigger other actions)
	log.Println("received amf status notification")
	// log.Printf("Received AMF Status Change: %s", notification.AmfStatusInfoList[0].StatusChange)

	// Respond with a 204 No Content to indicate successful processing
	w.WriteHeader(http.StatusNoContent)

}

// // Define Prometheus metrics
// var (
// 	RegistrationStateCounter = prometheus.NewCounterVec(
// 		prometheus.CounterOpts{
// 			Name: "amf_registration_state_events_total",
// 			Help: "Total number of AMF registration state events received",
// 		},
// 		[]string{"supi", "state"}, // Label by SUPI and active/inactive state
// 	)
// 	ActiveUEsGauge = prometheus.NewGaugeVec(
// 		prometheus.GaugeOpts{
// 			Name: "number_of_active_UEs",
// 			Help: "Tracks the number of active UEs",
// 		},
// 		[]string{"state"},
// 	)
// 	LocationGauge = prometheus.NewGaugeVec(
// 		prometheus.GaugeOpts{
// 			Name: "UE_location_report",
// 			Help: "Location report for each SUPI",
// 		},
// 		[]string{"supi", "tac", "NrCellId", "time"},
// 	)
// 	UEConnectivityGauge = prometheus.NewGaugeVec(
// 		prometheus.GaugeOpts{
// 			Name: "UE_connectivity_status",
// 			Help: "Connectivity status for each SUPI",
// 		},
// 		[]string{"supi", "CmState", "AccessType"}, // Reachability status
// 	)
// )

func init() {
	// Register the Prometheus metrics
	prometheus.MustRegister(consumer.RegistrationStateCounter)
	prometheus.MustRegister(consumer.LocationGauge)
	prometheus.MustRegister(consumer.UEConnectivityGauge)
	prometheus.MustRegister(consumer.ActiveUEsGauge)
	prometheus.MustRegister(consumer.RegistrationState)
	prometheus.MustRegister(consumer.ActivePduSession)
	prometheus.MustRegister(consumer.PduSessionTotal)

	log.Println("prometheus metrics registered")
}

// func (a *NwdafApp) handleAMFEvents(w http.ResponseWriter, r *http.Request) {
// 	if r.Method != http.MethodPost {
// 		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
// 		return
// 	}

// 	var amfEventNotification models.AmfEventNotification

// 	// Decode the incoming JSON request into the AmfEventNotification struct
// 	err := json.NewDecoder(r.Body).Decode(&amfEventNotification)
// 	if err != nil {
// 		http.Error(w, "Invalid request body", http.StatusBadRequest)
// 		return
// 	}

// 	// Log the received event notification
// 	log.Printf("Received AMF event notification: %+v", amfEventNotification)

// 	// Iterate through the ReportList to process each event report
// 	for _, eventReport := range amfEventNotification.ReportList {
// 		// log.Printf("Processing event report: %+v", eventReport)

// 		switch eventReport.Type {
// 		case models.AmfEventType_REGISTRATION_STATE_REPORT:
// 			log.Printf("Handling registration state report: SUPI: %s, Active: %v", eventReport.Supi, eventReport.State.Active)
// 			// Add your logic for handling registration state reports
// 			log.Printf("UE location is: %s", eventReport.Location)
// 			state := "inactive"
// 			if eventReport.State.Active {
// 				state = "active"
// 				ActiveUEsGauge.WithLabelValues("active").Inc()
// 			} else {
// 				ActiveUEsGauge.WithLabelValues("active").Dec()
// 			}
// 			RegistrationStateCounter.WithLabelValues(eventReport.Supi, state).Inc()

// 		case models.AmfEventType_LOCATION_REPORT:
// 			log.Printf("Handling location report: Location: %+v", eventReport.Location)
// 			// Add your logic for handling location reports
// 			// log.Print(eventReport.Supi)
// 			// log.Print(eventReport.Location.NrLocation.Tai.Tac)
// 			// log.Print(eventReport.Location.NrLocation.Ncgi.NrCellId)
// 			// log.Print(eventReport.Location.NrLocation.UeLocationTimestamp.String())
// 			// log.Print(eventReport.Location.NrLocation.GlobalGnbId.GNbId.GNBValue)
// 			LocationGauge.WithLabelValues(eventReport.Supi, eventReport.Location.NrLocation.Tai.Tac, eventReport.Location.NrLocation.Ncgi.NrCellId, eventReport.Location.NrLocation.UeLocationTimestamp.String())

// 		case models.AmfEventType_PRESENCE_IN_AOI_REPORT:
// 			log.Printf("Handling presence in AOI report")
// 			// Add your logic for handling presence in area of interest reports

// 		case models.AmfEventType_TIMEZONE_REPORT:
// 			log.Printf("Handling timezone report: Timezone: %s", eventReport.Timezone)
// 			// Add your logic for handling timezone reports

// 		case models.AmfEventType_ACCESS_TYPE_REPORT:
// 			log.Printf("Handling access type report: Access Types: %+v", eventReport.AccessTypeList)
// 			// Add your logic for handling access type reports

// 		case models.AmfEventType_CONNECTIVITY_STATE_REPORT:
// 			log.Printf("Handling connectivity state report: CM Info: %+v", eventReport.CmInfoList)
// 			// Add your logic for handling connectivity state reports
// 			if eventReport.CmInfoList[0].CmState == "CONNECTED" {
// 				UEConnectivityGauge.WithLabelValues(eventReport.Supi, fmt.Sprintf("%v", eventReport.CmInfoList[0].CmState), fmt.Sprintf("%v", eventReport.CmInfoList[0].AccessType))
// 			} else {
// 				UEConnectivityGauge.WithLabelValues(eventReport.Supi, fmt.Sprintf("%v", eventReport.CmInfoList[1].CmState), fmt.Sprintf("%v", eventReport.CmInfoList[1].AccessType))
// 			}

// 		case models.AmfEventType_REACHABILITY_REPORT:
// 			log.Printf("Handling reachability report: Reachability: %+v", eventReport.Reachability)
// 			// Add your logic for handling reachability reports

// 		case models.AmfEventType_UES_IN_AREA_REPORT:
// 			log.Printf("Handling UEs in area report")
// 			// Add your logic for handling UEs in area reports

// 		default:
// 			log.Printf("Received unsupported event type: %v", eventReport.Type)
// 			http.Error(w, "Unsupported event type", http.StatusNotImplemented)
// 			return
// 		}
// 	}

// 	// Respond with 200 OK if everything is processed successfully
// 	w.WriteHeader(http.StatusOK)
// }

func handleNwdafAnalytics(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello, you've reached the nwdaf's inference service!")

	param := r.URL.Query().Get("param")
	if param == "" {
		param = "default"
		log.Print("default param")

	}
	log.Printf(param)
	pythonScript := "pythonmodule/main.py"
	// name := "Alice"
	// jsonData := `{"nfService": "inference", "data": "42", "reqNFInstanceID": "nf123", "reqTime": "2024-10-23T14:07:07Z"}`

	// Create the command
	cmd := exec.Command("python3", pythonScript, param)

	// Capture the output
	// var out bytes.Buffer
	var out, errOut bytes.Buffer
	cmd.Stdout = &out
	// cmd.Stderr = &out
	cmd.Stderr = &errOut

	// Run the command
	err := cmd.Run()
	if err != nil {
		log.Fatalf("Error running Python script: %v\nError Output: %s", err, errOut.String())
	}

	// Print the output
	fmt.Println(out.String())

}
