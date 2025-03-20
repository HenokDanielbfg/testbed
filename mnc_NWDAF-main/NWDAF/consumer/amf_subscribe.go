package consumer

import (
	// "context"

	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	// "time"

	"github.com/free5gc/openapi/Namf_Communication"
	"github.com/free5gc/openapi/Namf_EventExposure"
	"github.com/free5gc/openapi/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/prometheus/client_golang/prometheus"
	nwdaf_context "nwdaf.com/context"
	"nwdaf.com/factory"
	"nwdaf.com/logger"
	// "nwdaf.com/service"
)

type SubscriptionCommandRequest struct {
	Action         string `json:"action"`                   // "subscribe" or "unsubscribe"
	Target         string `json:"target"`                   // "amf" or "smf"
	SubscriptionID string `json:"subscriptionId,omitempty"` // required for unsubscribe
}

// HandleSubscriptionCommand processes subscription/unsubscription commands sent via /nwdaf/command.
func HandleSubscriptionCommand(c *gin.Context) {
	log.Println("Received a subscription command")
	var req SubscriptionCommandRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request payload"})
		return
	}

	// Get the NWDAF context.
	ctx := nwdaf_context.NWDAF_Self()
	var responseMsg string
	// var err error
	// req.SubscriptionID = ctx.Subscriptions[req.Target]
	// Determine action and target.
	if req.Action == "subscribe" {
		if req.Target == "amf" {
			// Query NRF for AMF instances.
			amfInstances, queryErr := QueryNRFForNF(ctx, models.NfType_AMF)
			if queryErr != nil || len(amfInstances.NfInstances) == 0 {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query NRF for AMF"})
				return
			}
			// Subscribe to AMF events (e.g., UE status changes).
			subID, subErr := SubscribeToAMF_UEStatus(ctx, amfInstances.NfInstances[0])
			if subErr != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("AMF subscription failed: %v", subErr)})
				return
			}
			if subID == "already subscribed to the AMF" {
				c.JSON(http.StatusOK, gin.H{"message": "already subscribed to the AMF"})
				return
			}
			responseMsg = fmt.Sprintf("Subscribed to AMF events successfully. Subscription ID: %s", subID)
		} else if req.Target == "smf" {
			// Query NRF for SMF instances.
			smfInstances, queryErr := QueryNRFForNF(ctx, models.NfType_SMF)
			if queryErr != nil || len(smfInstances.NfInstances) == 0 {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query NRF for SMF"})
				return
			}
			// Subscribe to SMF events (e.g., PDU session events).
			subID, subErr := SubscribeToSMFEvents(ctx, smfInstances.NfInstances[0])
			if subErr != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("SMF subscription failed: %v", subErr)})
				return
			}
			if subID == "already subscribed to the SMF" {
				c.JSON(http.StatusOK, gin.H{"message": "already subscribed to the SMF"})
				return
			}
			responseMsg = fmt.Sprintf("Subscribed to SMF events successfully. Subscription ID: %s", subID)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid target; must be 'amf' or 'smf'"})
			return
		}
	} else if req.Action == "unsubscribe" {
		req.SubscriptionID = ctx.Subscriptions[req.Target]

		if req.SubscriptionID == "" {
			c.JSON(http.StatusBadRequest, gin.H{"error": "subscriptionId is required for unsubscription"})
			return
		}
		if req.Target == "amf" {
			// Query NRF for AMF instances.
			amfInstances, queryErr := QueryNRFForNF(ctx, models.NfType_AMF)
			if queryErr != nil || len(amfInstances.NfInstances) == 0 {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query NRF for AMF"})
				return
			}
			// Unsubscribe from AMF events.
			respd, err := UnsubscribeFromAMF_UEStatus(ctx, req.SubscriptionID, amfInstances.NfInstances[0])
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("AMF unsubscription failed: %v", err)})
				return
			}
			if respd != "" {
				c.JSON(http.StatusOK, gin.H{"message": "No existing subscription to the AMF"})
				return
			}
			responseMsg = fmt.Sprintf("Unsubscribed from AMF events successfully. Subscription ID: %s", req.SubscriptionID)
		} else if req.Target == "smf" {
			// Query NRF for SMF instances.
			smfInstances, queryErr := QueryNRFForNF(ctx, models.NfType_SMF)
			if queryErr != nil || len(smfInstances.NfInstances) == 0 {
				c.JSON(http.StatusInternalServerError, gin.H{"error": "failed to query NRF for SMF"})
				return
			}
			// Unsubscribe from SMF events.
			respd, err := UnsubscribeFromSMF_events(ctx, req.SubscriptionID, smfInstances.NfInstances[0])
			if err != nil {
				c.JSON(http.StatusInternalServerError, gin.H{"error": fmt.Sprintf("SMF unsubscription failed: %v", err)})
				return
			}
			if respd != "" {
				c.JSON(http.StatusOK, gin.H{"message": "No existing subscription to the AMF"})
				return
			}
			responseMsg = fmt.Sprintf("Unsubscribed from SMF events successfully. Subscription ID: %s", req.SubscriptionID)
		} else {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid target; must be 'amf' or 'smf'"})
			return
		}
	} else {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid action; must be 'subscribe' or 'unsubscribe'"})
		return
	}

	// Return a success response.
	logger.ConsumerLog.Infof("Subscription command processed: %s", responseMsg)
	c.JSON(http.StatusOK, gin.H{"message": responseMsg})
}

func SubscribeToAMFStatusChange(nwdafCtx *nwdaf_context.NWDAFContext, profile []models.NfProfile) error {
	// amfClient := createAMFClient(nwdafCtx)
	notifyURI := fmt.Sprintf("http%s/nnwdaf-amfStatus", nwdafCtx.GetIPv4Uri())
	log.Println(notifyURI)
	log.Println(profile[0].NfInstanceId)
	configuration := Namf_Communication.NewConfiguration()
	// configuration := Namf_EventExposure.NewConfiguration()
	baseURI := fmt.Sprintf("http://%s:8000", profile[0].Ipv4Addresses[0])
	log.Println(baseURI)
	configuration.SetBasePath(baseURI)
	// client := Namf_EventExposure.NewAPIClient(configuration)
	client := Namf_Communication.NewAPIClient(configuration)

	subs := models.SubscriptionData{
		GuamiList: []models.Guami{
			{
				PlmnId: &models.PlmnId{
					Mcc: "208",
					Mnc: "93",
				},
				AmfId: "cafe00",
			},
		},
		AmfStatusUri: notifyURI, // NWDAF's callback URI
	}

	// ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)

	// defer cancel()
	ctx, _, err := nwdafCtx.GetTokenCtx(models.ServiceName_NAMF_COMM, models.NfType_AMF)
	if err != nil {
		return nil
	}
	// resp, httpResp, err := client.SubscriptionsCollectionDocumentApi.CreateSubscription(ctx, sub)
	resp, httpResp, err := client.SubscriptionsCollectionDocumentApi.AMFStatusChangeSubscribe(ctx, subs)

	if err != nil {
		logger.ConsumerLog.Errorf("AMF subscription failed: %v", err)
		logger.ConsumerLog.Print(httpResp)
		return err
	}

	defer httpResp.Body.Close()

	if httpResp.StatusCode != http.StatusCreated {
		logger.ConsumerLog.Errorf("AMF subscription failed with status: %d", httpResp.StatusCode)
		return fmt.Errorf("unexpected status code: %d", httpResp.StatusCode)
	}

	logger.ConsumerLog.Infof("AMF subscription successful: %s", resp.AmfStatusUri)

	// Store the subscription ID for future use (e.g., unsubscribing)
	// nwdafCtx.StoreAMFSubscriptionID(resp.SubId)

	return nil
}

func SubscribeToAMF_UEStatus(nwdafCtx *nwdaf_context.NWDAFContext, profile models.NfProfile) (string, error) {

	// check if already subscribed
	if nwdafCtx.Subscriptions["amf"] != "" {
		return "already subscribed to the AMF", nil
	}
	// Load dynamic subscription config
	sub_config, err := factory.LoadSubscriptionConfig("nwdaf_subscriptions.yaml")
	amfEvents := sub_config.Subscriptions.AMF_SUB.Events
	var eventList []models.AmfEvent

	// Map string events to AmfEvent types
	for _, event := range amfEvents {
		eventList = append(eventList, models.AmfEvent{Type: models.AmfEventType(event), ImmediateFlag: true})
	}
	notifyURI := fmt.Sprintf("http%s/nnwdaf-amfEvents", nwdafCtx.GetIPv4Uri())
	if len(profile.Ipv4Addresses) == 0 || len(profile.Ipv4Addresses) == 0 {
		return "", fmt.Errorf("no valid AMF profile found")
	}
	notifyId := uuid.New().String()
	log.Println("notify id is: %s", notifyId)
	amfAddress := fmt.Sprintf("http://%s:8000", profile.Ipv4Addresses[0]) // Adjust as needed
	configuration := Namf_EventExposure.NewConfiguration()
	logger.ConsumerLog.Infof("AMF Ip address at: %s", amfAddress)

	configuration.SetBasePath(amfAddress)
	client := Namf_EventExposure.NewAPIClient(configuration)

	subscriptionData := models.AmfEventSubscription{
		// EventList: &[]models.AmfEvent{
		// 	{
		// 		Type:          models.AmfEventType_REGISTRATION_STATE_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_LOCATION_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_PRESENCE_IN_AOI_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_TIMEZONE_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_ACCESS_TYPE_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_CONNECTIVITY_STATE_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_REACHABILITY_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// 	{
		// 		Type:          models.AmfEventType_UES_IN_AREA_REPORT,
		// 		ImmediateFlag: true,
		// 	},
		// },
		EventList:      &eventList,
		EventNotifyUri: notifyURI,
		NfId:           profile.NfInstanceId,
		// NfId:                nwdafCtx.NfInstanceID,

		NotifyCorrelationId: notifyId,
		AnyUE:               true,
	}

	sub := models.AmfCreateEventSubscription{
		Subscription: &subscriptionData,
	}

	// ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	// defer cancel()
	ctx, _, err := nwdafCtx.GetTokenCtx(models.ServiceName_NAMF_EVTS, models.NfType_AMF)
	if err != nil {
		return "", err
	}
	// log.Println(ctx.Value())
	resp, httpResp, err := client.SubscriptionsCollectionDocumentApi.CreateSubscription(ctx, sub)
	if err != nil {
		logger.ConsumerLog.Errorf("AMF subscription failed: %v", err)
		return "", err
	}
	defer httpResp.Body.Close()

	if httpResp.StatusCode != http.StatusCreated {
		logger.ConsumerLog.Errorf("AMF subscription failed with status: %d", httpResp.StatusCode)
		return "", fmt.Errorf("unexpected status code: %d", httpResp.StatusCode)
	}
	nwdafCtx.Subscriptions["amf"] = resp.SubscriptionId
	logger.ConsumerLog.Infof("AMF subscription successful. Subscription ID: %s", resp.SubscriptionId)
	// Store the subscription ID for future use (e.g., unsubscribing)
	// nwdafCtx.StoreAMFSubscriptionID(resp.SubId)

	return resp.SubscriptionId, nil
}

func UnsubscribeFromAMF_UEStatus(nwdafCtx *nwdaf_context.NWDAFContext, subscriptionId string, amfProfile models.NfProfile) (string, error) {
	// check if there is no subscription
	if nwdafCtx.Subscriptions["amf"] == "" {
		return "no subscription to AMF", nil
	}

	subscriptionId = nwdafCtx.Subscriptions["amf"]

	if subscriptionId == "" {
		return "", fmt.Errorf("invalid subscription ID")
	}

	if len(amfProfile.Ipv4Addresses) == 0 {
		return "", fmt.Errorf("no valid AMF address found")
	}
	if subscriptionId == "" {
		return "", fmt.Errorf("invalid subscription ID")
	}

	amfAddress := fmt.Sprintf("http://%s:8000", amfProfile.Ipv4Addresses[0]) // Adjust port if needed
	configuration := Namf_EventExposure.NewConfiguration()
	configuration.SetBasePath(amfAddress)

	client := Namf_EventExposure.NewAPIClient(configuration)

	ctx, _, err := nwdafCtx.GetTokenCtx(models.ServiceName_NAMF_EVTS, models.NfType_AMF)
	if err != nil {
		return "", fmt.Errorf("failed to get token context: %v", err)
	}
	// defer cancel()

	// var httpResp *http.Response
	// func() {
	// 	defer func() {
	// 		if r := recover(); r != nil {
	// 			fmt.Errorf("Panic occurred in DeleteSubscription: %v", r)
	// 			err = fmt.Errorf("panic in DeleteSubscription: %v", r)
	// 		}
	// 	}()
	// 	httpResp, err = client.IndividualSubscriptionDocumentApi.DeleteSubscription(ctx, subscriptionId)
	// }()

	httpResp, err := client.IndividualSubscriptionDocumentApi.DeleteSubscription(ctx, subscriptionId)
	if err != nil {
		return "", fmt.Errorf("AMF unsubscription failed: %v", err)
	}
	// logger.ConsumerLog.Info("Successfully unsubscribed from AMF events%s", httpResp.StatusCode)

	// defer httpResp.Body.Close()

	if httpResp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("unexpected status code on unsubscribe: %d", httpResp.StatusCode)
	}
	delete(nwdafCtx.Subscriptions, "amf")
	logger.ConsumerLog.Infof("Successfully unsubscribed from AMF events. Subscription ID was: %s", subscriptionId)
	return "", nil
}

type ProblemDetails struct {
	Status int    `json:"status"`
	Title  string `json:"title"`
	Detail string `json:"detail"`
}

// Define Prometheus metrics
var (
	RegistrationState = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "amf_ue_registration_state",
			Help: "Current registration state of the UE (1 = active, 0 = inactive)",
		},
		[]string{"supi"}, // Label by SUPI
	)
	RegistrationStateCounter = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "amf_registration_state_events_total",
			Help: "Total number of AMF registration state events received",
		},
		[]string{"supi", "state"}, // Label by SUPI and active/inactive state
	)
	ActiveUEsGauge = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "active_UEs",
			Help: "Tracks the number of active UEs",
		},
		[]string{"state"},
	)
	LocationGauge = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "UE_location_report",
			Help: "Location report for each SUPI",
		},
		[]string{"supi", "tac", "NrCellId", "time"},
	)
	UEConnectivityGauge = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "UE_connectivity_status",
			Help: "Connectivity status for each SUPI",
		},
		[]string{"supi", "CmState", "AccessType"}, // Reachability status
	)
	UEcounter int = 0
)

// func init() {
// 	// Register the Prometheus metrics
// 	prometheus.MustRegister(RegistrationStateCounter)
// 	prometheus.MustRegister(LocationGauge)
// 	prometheus.MustRegister(UEConnectivityGauge)
// 	prometheus.MustRegister(ActiveUEsGauge)
// }

func HandleAMFEvents(c *gin.Context) {
	if c.Request.Method != http.MethodPost {
		http.Error(c.Writer, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var amfEventNotification models.AmfEventNotification

	// Decode the incoming JSON request into the AmfEventNotification struct
	err := json.NewDecoder(c.Request.Body).Decode(&amfEventNotification)
	if err != nil {
		http.Error(c.Writer, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Log the received event notification
	logger.ConsumerLog.Infof("Received AMF event notification: %+v", amfEventNotification)

	// Iterate through the ReportList to process each event report
	for _, eventReport := range amfEventNotification.ReportList {
		// log.Printf("Processing event report: %+v", eventReport)

		switch eventReport.Type {
		case models.AmfEventType_REGISTRATION_STATE_REPORT:
			logger.ConsumerLog.Infof("Handling registration state report: SUPI: %s, Active: %v", eventReport.Supi, eventReport.State.Active)
			// Add your logic for handling registration state reports
			logger.ConsumerLog.Infof("UE location is: %s", eventReport.Location)
			UEcounter = UEcounter + 1
			log.Printf("CURRENT COUNT IS: %d", UEcounter)
			log.Printf("CURRENT UECOUNT from AMF IS: %d", eventReport.NumberOfUes)

			state := "inactive"
			if eventReport.State.Active {
				state = "active"
				// ActiveUEsGauge.WithLabelValues("active").Inc()
				ActiveUEsGauge.With(prometheus.Labels{"state": "current"}).Set(float64(eventReport.NumberOfUes))
				RegistrationState.WithLabelValues(eventReport.Supi).Set(1)
			} else {
				// ActiveUEsGauge.WithLabelValues("active").Dec()
				ActiveUEsGauge.With(prometheus.Labels{"state": "current"}).Set(float64(eventReport.NumberOfUes))
				RegistrationState.WithLabelValues(eventReport.Supi).Set(0)

			}
			RegistrationStateCounter.WithLabelValues(eventReport.Supi, state).Inc()

		case models.AmfEventType_LOCATION_REPORT:
			logger.ConsumerLog.Infof("Handling location report: Location: %+v", eventReport.Location.NrLocation.Ncgi.NrCellId)

			LocationGauge.WithLabelValues(eventReport.Supi, eventReport.Location.NrLocation.Tai.Tac, eventReport.Location.NrLocation.Ncgi.NrCellId, eventReport.Location.NrLocation.UeLocationTimestamp.String())

		case models.AmfEventType_PRESENCE_IN_AOI_REPORT:
			logger.ConsumerLog.Infof("Handling presence in AOI report")
			// Add your logic for handling presence in area of interest reports

		case models.AmfEventType_TIMEZONE_REPORT:
			logger.ConsumerLog.Infof("Handling timezone report: Timezone: %s", eventReport.Timezone)
			// Add your logic for handling timezone reports

		case models.AmfEventType_ACCESS_TYPE_REPORT:
			logger.ConsumerLog.Infof("Handling access type report: Access Types: %+v", eventReport.AccessTypeList)
			// Add your logic for handling access type reports

		case models.AmfEventType_CONNECTIVITY_STATE_REPORT:
			logger.ConsumerLog.Infof("Handling connectivity state report: CM Info: %+v", eventReport.CmInfoList)
			// Add your logic for handling connectivity state reports
			if eventReport.CmInfoList[0].CmState == "CONNECTED" {
				UEConnectivityGauge.WithLabelValues(eventReport.Supi, fmt.Sprintf("%v", eventReport.CmInfoList[0].CmState), fmt.Sprintf("%v", eventReport.CmInfoList[0].AccessType))
			} else {
				UEConnectivityGauge.WithLabelValues(eventReport.Supi, fmt.Sprintf("%v", eventReport.CmInfoList[1].CmState), fmt.Sprintf("%v", eventReport.CmInfoList[1].AccessType))
			}

		case models.AmfEventType_REACHABILITY_REPORT:
			logger.ConsumerLog.Infof("Handling reachability report: Reachability: %+v", eventReport.Reachability)
			// Add your logic for handling reachability reports

		case models.AmfEventType_UES_IN_AREA_REPORT:
			logger.ConsumerLog.Infof("Handling UEs in area report")
			// Add your logic for handling UEs in area reports

		default:
			logger.ConsumerLog.Infof("Received unsupported event type: %v", eventReport.Type)
			http.Error(c.Writer, "Unsupported event type", http.StatusNotImplemented)
			return
		}
	}

	// Respond with 200 OK if everything is processed successfully
	c.Writer.WriteHeader(http.StatusOK)
}

func HandleAMFStatus(c *gin.Context) {
	log.Println("you've reached the nwdaf amf status server")

	if c.Request.Method != http.MethodPost {
		c.Writer.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(c.Writer).Encode(ProblemDetails{
			Status: 405,
			Title:  "Method Not Allowed",
			Detail: "Only POST method is allowed",
		})
		return
	}

	// Read the body of the request
	body, err := io.ReadAll(c.Request.Body)
	if err != nil {
		c.Writer.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(c.Writer).Encode(ProblemDetails{
			Status: 500,
			Title:  "Internal Server Error",
			Detail: "Failed to read the request body",
		})
		return
	}
	defer c.Request.Body.Close()

	// Unmarshal the request body into the notification structure
	var notification models.AmfStatusChangeNotification
	err = json.Unmarshal(body, &notification)
	if err != nil {
		c.Writer.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(c.Writer).Encode(ProblemDetails{
			Status: 400,
			Title:  "Bad Request",
			Detail: "Invalid JSON format",
		})
		return
	}

	// Process the notification (e.g., store, log, or trigger other actions)
	logger.ConsumerLog.Infof("received amf status notification")
	logger.ConsumerLog.Infof("Received AMF Status Change: %s", notification.AmfStatusInfoList[0].StatusChange)

	// Respond with a 204 No Content to indicate successful processing
	c.Writer.WriteHeader(http.StatusNoContent)

}
