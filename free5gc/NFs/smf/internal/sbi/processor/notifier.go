package processor

import (
	"context"
	"fmt"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/gin-gonic/gin"

	"github.com/free5gc/openapi"
	"github.com/free5gc/openapi/Nsmf_EventExposure"
	"github.com/free5gc/openapi/models"
	smf_context "github.com/free5gc/smf/internal/context"
	"github.com/free5gc/smf/internal/logger"
)

func (p *Processor) HandleChargingNotification(
	c *gin.Context,
	chargingNotifyRequest models.ChargingNotifyRequest,
	smContextRef string,
) {
	logger.ChargingLog.Info("Handle Charging Notification")

	problemDetails := p.chargingNotificationProcedure(chargingNotifyRequest, smContextRef)
	if problemDetails == nil {
		c.Status(http.StatusNoContent)
		return
	}
	c.JSON(int(problemDetails.Status), problemDetails)
}

// While receive Charging Notification from CHF, SMF will send Charging Information to CHF and update UPF
// The Charging Notification will be sent when CHF found the changes of the quota file.
func (p *Processor) chargingNotificationProcedure(
	req models.ChargingNotifyRequest, smContextRef string,
) *models.ProblemDetails {
	if smContext := smf_context.GetSMContextByRef(smContextRef); smContext != nil {
		smContext.SMLock.Lock()
		defer smContext.SMLock.Unlock()
		upfUrrMap := make(map[string][]*smf_context.URR)
		for _, reauthorizeDetail := range req.ReauthorizationDetails {
			rg := reauthorizeDetail.RatingGroup
			logger.ChargingLog.Infof("Force update charging information for rating group %d", rg)
			for _, urr := range smContext.UrrUpfMap {
				chgInfo := smContext.ChargingInfo[urr.URRID]
				if chgInfo.RatingGroup == rg ||
					chgInfo.ChargingLevel == smf_context.PduSessionCharging {
					logger.ChargingLog.Tracef("Query URR (%d) for Rating Group (%d)", urr.URRID, rg)
					upfId := smContext.ChargingInfo[urr.URRID].UpfId
					upfUrrMap[upfId] = append(upfUrrMap[upfId], urr)
				}
			}
		}
		for upfId, urrList := range upfUrrMap {
			upf := smf_context.GetUpfById(upfId)
			if upf == nil {
				logger.ChargingLog.Warnf("Cound not find upf %s", upfId)
				continue
			}
			QueryReport(smContext, upf, urrList, models.TriggerType_FORCED_REAUTHORISATION)
		}
		p.ReportUsageAndUpdateQuota(smContext)
	} else {
		problemDetails := &models.ProblemDetails{
			Status: http.StatusNotFound,
			Cause:  CONTEXT_NOT_FOUND,
			Detail: fmt.Sprintf("SM Context [%s] Not Found ", smContextRef),
		}
		return problemDetails
	}

	return nil
}

func (p *Processor) HandleSMPolicyUpdateNotify(
	c *gin.Context,
	request models.SmPolicyNotification,
	smContextRef string,
) {
	logger.PduSessLog.Infoln("In HandleSMPolicyUpdateNotify")
	decision := request.SmPolicyDecision
	smContext := smf_context.GetSMContextByRef(smContextRef)

	if smContext == nil {
		logger.PduSessLog.Errorf("SMContext[%s] not found", smContextRef)
		c.Status(http.StatusBadRequest)
		return
	}

	smContext.SMLock.Lock()
	defer smContext.SMLock.Unlock()

	smContext.CheckState(smf_context.Active)
	// Wait till the state becomes Active again
	// TODO: implement waiting in concurrent architecture

	smContext.SetState(smf_context.ModificationPending)

	// Update SessionRule from decision
	if err := smContext.ApplySessionRules(decision); err != nil {
		// TODO: Fill the error body
		smContext.Log.Errorf("SMPolicyUpdateNotify err: %v", err)
		c.Status(http.StatusBadRequest)
		return
	}

	// TODO: Response data type -
	// [200 OK] UeCampingRep
	// [200 OK] array(PartialSuccessReport)
	// [400 Bad Request] ErrorReport
	if err := smContext.ApplyPccRules(decision); err != nil {
		smContext.Log.Errorf("apply sm policy decision error: %+v", err)
		// TODO: Fill the error body
		c.Status(http.StatusBadRequest)
		return
	}

	smContext.SendUpPathChgNotification("EARLY", SendUpPathChgEventExposureNotification)

	ActivateUPFSession(smContext, nil)

	smContext.SendUpPathChgNotification("LATE", SendUpPathChgEventExposureNotification)

	smContext.PostRemoveDataPath()

	c.Status(http.StatusNoContent)
}

func SendUpPathChgEventExposureNotification(
	uri string, notification *models.NsmfEventExposureNotification,
) {
	configuration := Nsmf_EventExposure.NewConfiguration()
	client := Nsmf_EventExposure.NewAPIClient(configuration)
	_, httpResponse, err := client.
		DefaultCallbackApi.
		SmfEventExposureNotification(context.Background(), uri, *notification)
	if err != nil {
		if httpResponse != nil {
			logger.PduSessLog.Warnf("SMF Event Exposure Notification Error[%s]", httpResponse.Status)
		} else {
			logger.PduSessLog.Warnf("SMF Event Exposure Notification Failed[%s]", err.Error())
		}
		return
	} else if httpResponse == nil {
		logger.PduSessLog.Warnln("SMF Event Exposure Notification Failed[HTTP Response is nil]")
		return
	}
	defer func() {
		if rspCloseErr := httpResponse.Body.Close(); rspCloseErr != nil {
			logger.PduSessLog.Errorf("SmfEventExposureNotification response body cannot close: %+v", rspCloseErr)
		}
	}()
	if httpResponse.StatusCode != http.StatusOK && httpResponse.StatusCode != http.StatusNoContent {
		logger.PduSessLog.Warnf("SMF Event Exposure Notification Failed")
	} else {
		logger.PduSessLog.Tracef("SMF Event Exposure Notification Success")
	}
}

func SendEventNotification(smContext *smf_context.SMContext, eventType models.SmfEvent) {
	smfSelf := smf_context.GetSelf()

	// for _, sub := range smfSelf.SmfSubs.SubscriptionsList {
	smfSelf.EventSubscriptions.Range(func(key, value interface{}) bool {

		subscriptionData := value.(*models.NsmfEventExposure)

		// configuration := Nsmf_EventExposure.NewConfiguration()
		// configuration.SetBasePath(subscriptionData.NotifUri)
		// client := Nsmf_EventExposure.NewAPIClient(configuration)
		// log.Println(client)

		for _, eventlist := range subscriptionData.EventSubs {

			if eventlist.Event == eventType {
				logger.SBILog.Printf("event type happened: %s", eventlist.Event)
				configuration := Nsmf_EventExposure.NewConfiguration()
				configuration.SetBasePath(subscriptionData.NotifUri)
				client := Nsmf_EventExposure.NewAPIClient(configuration)
				logger.SBILog.Println(client)
				smfEventNotification := models.NsmfEventExposureNotification{
					NotifId:     subscriptionData.NotifId,
					EventNotifs: []models.EventNotification{ // <- wrap the single struct in a slice

					},
				}

				eventReport := models.EventNotification{
					Event:     eventType,
					TimeStamp: &time.Time{},
					Supi:      smContext.Supi,
				}

				switch eventType {
				// case models.SmfEvent_AC_TY_CH:
				// 	// eventReport.AccType = "...", // New access type
				// 	eventReport.PduSeId = " ", // PDU Session ID
				// 	eventReport.PlmnId = "...", // If changing networks
				case models.SmfEvent_PDU_SES_REL:
					eventReport.PduSeId = smContext.PDUSessionID
					// eventReport.ReIpv4Addr = "...",     // If IPv4 was used
				case models.SmfEvent_PDU_SES_EST:
					eventReport.PduSeId = smContext.PDUSessionID
					// eventReport.ReIpv4Addr = "...",     // If IPv4 was used
					// case models.SmfEvent_PLMN_CH:
					// 	eventReport.PlmnId = "...", // New PLMN ID
					// 	eventReport.PduSeId = "..."
					// case models.SmfEvent_UP_PATH_CH:
					// 	eventReport.SourceDnai = "...", // Original DNAI
					// 	eventReport.TargetDnai = "...", // New DNAI
					// 	eventReport.DnaiChgType = "...",
					// 	eventReport.SourceUeIpv4Addr = "...", // If IPv4 is used
					// 	eventReport.TargetUeIpv4Addr = "...", // If IPv4 is used
					// 	eventReport.PduSeId = "..."

					// default:
					// 	logger.SBILog.Warnf("Unsupported event type: %v", eventType)
					// 	return
				}

				smfEventNotification.EventNotifs = append(smfEventNotification.EventNotifs, eventReport)

				var (
					localVarHttpMethod   = strings.ToUpper("Post")
					localVarPostBody     interface{}
					localVarFormFileName string
					localVarFileName     string
					localVarFileBytes    []byte
				)

				// create path and map variables
				localVarPath := subscriptionData.NotifUri
				localVarHeaderParams := make(map[string]string)
				localVarQueryParams := url.Values{}
				localVarFormParams := url.Values{}

				localVarHttpContentTypes := []string{"application/json"}
				localVarHeaderParams["Content-Type"] = localVarHttpContentTypes[0] // use the first content type specified in 'consumes'
				localVarPostBody = &smfEventNotification
				// to determine the Accept header
				localVarHttpHeaderAccepts := []string{"application/problem+json"}
				localVarHttpHeaderAccept := openapi.SelectHeaderAccept(localVarHttpHeaderAccepts)
				if localVarHttpHeaderAccept != "" {
					localVarHeaderParams["Accept"] = localVarHttpHeaderAccept
				}

				r, err := openapi.PrepareRequest(context.Background(), configuration, localVarPath, localVarHttpMethod, localVarPostBody, localVarHeaderParams, localVarQueryParams, localVarFormParams, localVarFormFileName, localVarFileName, localVarFileBytes)
				if err != nil {
					logger.SBILog.Info("Preparing request error")
					// return false
				} else {
					logger.SBILog.Infof("Prepared request successfully")
				}
				client1 := &http.Client{
					Timeout: time.Second * 10, // Set a 10 second timeout
				}

				/////////////////////////////////////////////////////////
				logger.SBILog.Infof("[SMF] Send Smf Event Notify to %s", subscriptionData.NotifUri)
				httpResponse, err := client1.Do(r)

				if err != nil {
					if httpResponse == nil {
						logger.SBILog.Errorln(err.Error())

					} else if err.Error() != httpResponse.Status {
						logger.SBILog.Errorln(err.Error())

					}
					// return false
				}
				if httpResponse != nil {
					defer httpResponse.Body.Close()
				}

			}
		}

		return true
	})
}
