package consumer

import (
	"encoding/json"
	"fmt"

	// "log"
	"net/http"

	"github.com/free5gc/openapi/Nsmf_EventExposure"
	"github.com/free5gc/openapi/models"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/prometheus/client_golang/prometheus"
	nwdaf_context "nwdaf.com/context"
	"nwdaf.com/factory"
	"nwdaf.com/logger"
)

var (
	ActivePduSession = prometheus.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "active_pdu_sessions",
			Help: "active PDU sessions",
		},
		[]string{"State"},
	)
	PduSessionTotal = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "total_pdu_session_events",
			Help: "total number of PDU session events",
		},
		[]string{"supi", "PDU_ID", "Est_or_Rel"},
	)
)

func SubscribeToSMFEvents(nwdafCtx *nwdaf_context.NWDAFContext, profile models.NfProfile) (string, error) {
	// check if already subscribed
	if nwdafCtx.Subscriptions["smf"] != "" {
		return "already subscribed to the SMF", nil
	}
	// Load dynamic subscription config
	config, err := factory.LoadSubscriptionConfig("nwdaf_subscriptions.yaml")
	if err != nil {
		return "", err
	}

	smfEvents := config.Subscriptions.SMF_SUB.Events
	var eventList []models.EventSubscription

	// Map string events to SmfEvent types
	for _, event := range smfEvents {
		eventList = append(eventList, models.EventSubscription{Event: models.SmfEvent(event)})
	}
	notifyURI := fmt.Sprintf("http%s/nnwdaf-smfEvents", nwdafCtx.GetIPv4Uri())
	if len(profile.Ipv4Addresses) == 0 {
		return "", fmt.Errorf("no valid SMF profile found")
	}

	notifyId := uuid.New().String()
	logger.ConsumerLog.Infof("Notify ID is: %s", notifyId)

	smfAddress := fmt.Sprintf("http://%s:8000", profile.Ipv4Addresses[0]) // Adjust port as needed
	configuration := Nsmf_EventExposure.NewConfiguration()
	logger.ConsumerLog.Infof("SMF IP address at: %s", smfAddress)
	configuration.SetBasePath(smfAddress)
	client := Nsmf_EventExposure.NewAPIClient(configuration)

	subscriptionData := models.NsmfEventExposure{
		// EventSubs: []models.EventSubscription{
		// 	{Event: models.SmfEvent_AC_TY_CH},
		// 	{Event: models.SmfEvent_UP_PATH_CH},
		// 	{Event: models.SmfEvent_PDU_SES_REL},
		// 	{Event: models.SmfEvent_PLMN_CH},
		// 	{Event: models.SmfEvent_PDU_SES_EST},
		// 	// {Event: models.SmfEvent_UE_IP_CH},
		// 	// {Event: models.SmfEvent},
		// 	// {Event: models.SmfEvent_COMM_FAIL},
		// 	// {Event: models.SmfEvent_QFI_ALLOC},
		// 	// {Event: models.SmfEvent_QOS_MON},
		// },
		EventSubs: eventList,
		NotifUri:  notifyURI,
		NotifId:   notifyId,
		AnyUeInd:  true,
	}

	ctx, _, err := nwdafCtx.GetTokenCtx(models.ServiceName_NSMF_EVENT_EXPOSURE, models.NfType_SMF)
	if err != nil {
		return "", err
	}
	resp, httpResp, err := client.DefaultApi.SubscriptionsPost(ctx, subscriptionData)
	if err != nil {
		logger.ConsumerLog.Errorf("SMF subscription failed: %v", err)
		return "", err
	}
	defer httpResp.Body.Close()

	if httpResp.StatusCode != http.StatusCreated {
		logger.ConsumerLog.Errorf("SMF subscription failed with status: %d", httpResp.StatusCode)
		return "", fmt.Errorf("unexpected status code: %d", httpResp.StatusCode)
	}
	nwdafCtx.Subscriptions["smf"] = resp.SubId
	logger.ConsumerLog.Infof("SMF subscription successful. Subscription ID: %s", resp.SubId)
	return resp.SubId, nil
}

func HandleSMFEvents(c *gin.Context) {
	if c.Request.Method != http.MethodPost {
		http.Error(c.Writer, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var smfEventNotification models.NsmfEventExposureNotification

	// Decode the incoming JSON request into the AmfEventNotification struct
	err := json.NewDecoder(c.Request.Body).Decode(&smfEventNotification)
	if err != nil {
		http.Error(c.Writer, "Invalid request body", http.StatusBadRequest)
		return
	}
	logger.ConsumerLog.Infof("received SMF event notification %s", c.Request.Body)

	// Iterate through the ReportList to process each event report
	for _, eventReport := range smfEventNotification.EventNotifs {
		// log.Printf("Processing event report: %+v", eventReport)

		switch eventReport.Event {
		case models.SmfEvent_AC_TY_CH:
			logger.ConsumerLog.Infof("Handling Access type change report: Access type: %s", eventReport.AccType)

		case models.SmfEvent_PDU_SES_EST:
			logger.ConsumerLog.Infof("Handling PDU session ESTABLISHMENT report for UE Supi: %s ,pdu sesion id %d", eventReport.Supi, eventReport.PduSeId)
			ActivePduSession.WithLabelValues("active").Inc()
			PduSessionTotal.WithLabelValues(eventReport.Supi, fmt.Sprintf("%d", eventReport.PduSeId), "Established").Inc()
		case models.SmfEvent_PDU_SES_REL:
			logger.ConsumerLog.Infof("Handling PDU session RELEASE report for UE Supi: %s ,pdu sesion id %d", eventReport.Supi, eventReport.PduSeId)
			ActivePduSession.WithLabelValues("active").Dec()
			PduSessionTotal.WithLabelValues(eventReport.Supi, fmt.Sprintf("%d", eventReport.PduSeId), "Release").Inc()

		case models.SmfEvent_PLMN_CH:
			logger.ConsumerLog.Infof("Handling PLMN change report: PLMN Mcc id: %s", eventReport.PlmnId.Mcc)

		case models.SmfEvent_UP_PATH_CH:
			logger.ConsumerLog.Infof("Handling UP path change report: ")
		default:
			logger.ConsumerLog.Infof("Received unsupported event type: %v", eventReport.Event)
			http.Error(c.Writer, "Unsupported event type", http.StatusNotImplemented)
			return
		}
	}

	c.Writer.WriteHeader(http.StatusOK)
}

func UnsubscribeFromSMF_events(nwdafCtx *nwdaf_context.NWDAFContext, subscriptionId string, smfProfile models.NfProfile) (string, error) {

	// check if there is no subscription
	if nwdafCtx.Subscriptions["smf"] == "" {
		return "no subscription to SMF", nil
	}
	subscriptionId = nwdafCtx.Subscriptions["smf"]
	if subscriptionId == "" {
		return "", fmt.Errorf("invalid subscription ID")
	}

	if len(smfProfile.Ipv4Addresses) == 0 {
		return "", fmt.Errorf("no valid AMF address found")
	}
	if subscriptionId == "" {
		return "", fmt.Errorf("invalid subscription ID")
	}

	amfAddress := fmt.Sprintf("http://%s:8000", smfProfile.Ipv4Addresses[0]) // Adjust port if needed
	configuration := Nsmf_EventExposure.NewConfiguration()
	configuration.SetBasePath(amfAddress)

	client := Nsmf_EventExposure.NewAPIClient(configuration)

	ctx, _, err := nwdafCtx.GetTokenCtx(models.ServiceName_NSMF_EVENT_EXPOSURE, models.NfType_SMF)
	if err != nil {
		return "", fmt.Errorf("failed to get token context: %v", err)
	}

	httpResp, err := client.DefaultApi.SubscriptionsSubIdDelete(ctx, subscriptionId)
	if err != nil {
		return "", fmt.Errorf("SMF unsubscription failed: %v", err)
	}

	// defer httpResp.Body.Close()

	if httpResp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("unexpected status code on unsubscribe: %d", httpResp.StatusCode)
	}
	delete(nwdafCtx.Subscriptions, "smf")
	logger.ConsumerLog.Infof("Successfully unsubscribed from SMF events. Subscription ID was: %s", subscriptionId)
	return "", nil
}
