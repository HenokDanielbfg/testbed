package callback

import (
	// "bytes"
	"context"
	// "encoding/json"
	// "fmt"
	"log"

	// "crypto/tls"
	// "net"
	"net/http"
	"net/url"
	"reflect"
	"strings"
	"time"

	// "time"

	amf_context "github.com/free5gc/amf/internal/context"
	"github.com/free5gc/amf/internal/logger"
	"github.com/free5gc/openapi"

	// "golang.org/x/net/http2"

	"github.com/free5gc/openapi/Namf_Communication"
	"github.com/free5gc/openapi/Namf_EventExposure"
	"github.com/free5gc/openapi/models"
)

func SendEventNotification(amfUe *amf_context.AmfUe, eventType models.AmfEventType, status ...bool) {
	amfSelf := amf_context.GetSelf()
	amfSelf.EventSubscriptions.Range(func(key, value interface{}) bool {

		subscriptionData := value.(*amf_context.AMFContextEventSubscription).EventSubscription

		configuration := Namf_EventExposure.NewConfiguration()
		configuration.SetBasePath(subscriptionData.EventNotifyUri)
		client := Namf_EventExposure.NewAPIClient(configuration)
		log.Println(client)
		// if subscriptionData.SubsChangeNotifyCorrelationId != "" {
		// 	notification.SubsChangeNotifyCorrelationId = subscriptionData.SubsChangeNotifyCorrelationId
		// }

		for _, eventlist := range *subscriptionData.EventList {

			if eventlist.Type == eventType {
				log.Printf("event type happened: %s", eventlist.Type)
				amfEventNotification := models.AmfEventNotification{
					NotifyCorrelationId: subscriptionData.NotifyCorrelationId,
					ReportList:          []models.AmfEventReport{ // <- wrap the single struct in a slice

					},
				}

				eventReport := models.AmfEventReport{
					Type:      eventType,
					TimeStamp: &time.Time{},
					AnyUe:     true,
					Supi:      amfUe.Supi,
					Gpsi:      amfUe.Gpsi,
					Pei:       amfUe.Pei,
				}

				switch eventType {
				case models.AmfEventType_REGISTRATION_STATE_REPORT:
					uecount := 0

					// Iterate over the sync.Map and count the entries
					amfSelf.UePool.Range(func(key, value interface{}) bool {
						uecount++
						return true // Continue iterating
					})
					log.Printf("ACTIVE UES: %d", uecount)
					eventReport.State = &models.AmfEventState{
						Active: status[0],
					}
					eventReport.Location = &amfUe.Location
					if status[0] {
						eventReport.NumberOfUes = int32(uecount)
					} else {
						eventReport.NumberOfUes = int32(uecount) - 1
					}
					// eventReport.AccessTypeList = []models.AccessType{amfUe.AmPolicyAssociation.Request.AccessType}

				case models.AmfEventType_LOCATION_REPORT:
					eventReport.Location = &amfUe.Location

				case models.AmfEventType_PRESENCE_IN_AOI_REPORT:
					// Implement presence in area of interest logic
					// This might require additional parameters and logic

				case models.AmfEventType_TIMEZONE_REPORT:
					eventReport.Timezone = amfUe.TimeZone

				case models.AmfEventType_ACCESS_TYPE_REPORT:
					eventReport.AccessTypeList = []models.AccessType{amfUe.AmPolicyAssociation.Request.AccessType}

				case models.AmfEventType_CONNECTIVITY_STATE_REPORT:
					eventReport.CmInfoList = amfUe.GetCmInfo()

				case models.AmfEventType_REACHABILITY_REPORT:
					eventReport.Reachability = amfUe.Reachability

				case models.AmfEventType_UES_IN_AREA_REPORT:
					// Implement UEs in area report logic
					// This might require additional parameters and logic

				default:
					logger.CallbackLog.Warnf("Unsupported event type: %v", eventType)
					return false
				}

				amfEventNotification.ReportList = append(amfEventNotification.ReportList, eventReport)

				var (
					localVarHttpMethod   = strings.ToUpper("Post")
					localVarPostBody     interface{}
					localVarFormFileName string
					localVarFileName     string
					localVarFileBytes    []byte
				)

				// create path and map variables
				localVarPath := subscriptionData.EventNotifyUri
				localVarHeaderParams := make(map[string]string)
				localVarQueryParams := url.Values{}
				localVarFormParams := url.Values{}

				localVarHttpContentTypes := []string{"application/json"}
				localVarHeaderParams["Content-Type"] = localVarHttpContentTypes[0] // use the first content type specified in 'consumes'
				localVarPostBody = &amfEventNotification
				// to determine the Accept header
				localVarHttpHeaderAccepts := []string{"application/problem+json"}
				localVarHttpHeaderAccept := openapi.SelectHeaderAccept(localVarHttpHeaderAccepts)
				if localVarHttpHeaderAccept != "" {
					localVarHeaderParams["Accept"] = localVarHttpHeaderAccept
				}

				r, err := openapi.PrepareRequest(context.Background(), configuration, localVarPath, localVarHttpMethod, localVarPostBody, localVarHeaderParams, localVarQueryParams, localVarFormParams, localVarFormFileName, localVarFileName, localVarFileBytes)
				if err != nil {
					logger.CommLog.Info("Preparing request error")
					return false
				} else {
					logger.CommLog.Infof("Prepared request successfully")
				}
				client1 := &http.Client{
					Timeout: time.Second * 10, // Set a 10 second timeout
				}

				/////////////////////////////////////////////////////////
				logger.ProducerLog.Infof("[AMF] Send Amf Event Notify to %s", subscriptionData.EventNotifyUri)
				httpResponse, err := client1.Do(r)

				if err != nil {
					if httpResponse == nil {
						HttpLog.Errorln(err.Error())

					} else if err.Error() != httpResponse.Status {
						HttpLog.Errorln(err.Error())

					}
					return false
				}
				if httpResponse != nil {
					defer httpResponse.Body.Close()
				}

			}
		}

		return true
	})
}

func SendAmfStatusChangeNotify(amfStatus string, guamiList []models.Guami) {
	amfSelf := amf_context.GetSelf()

	amfSelf.AMFStatusSubscriptions.Range(func(key, value interface{}) bool {
		subscriptionData := value.(models.SubscriptionData)

		configuration := Namf_Communication.NewConfiguration()

		// client := Namf_Communication.NewAPIClient(configuration)
		amfStatusNotification := models.AmfStatusChangeNotification{}
		amfStatusInfo := models.AmfStatusInfo{}

		for _, guami := range guamiList {
			for _, subGumi := range subscriptionData.GuamiList {
				if reflect.DeepEqual(guami, subGumi) {
					// AMF status is available
					amfStatusInfo.GuamiList = append(amfStatusInfo.GuamiList, guami)
				}
			}
		}

		amfStatusInfo = models.AmfStatusInfo{
			StatusChange:     (models.StatusChange)(amfStatus),
			TargetAmfRemoval: "",
			TargetAmfFailure: "",
		}

		amfStatusNotification.AmfStatusInfoList = append(amfStatusNotification.AmfStatusInfoList, amfStatusInfo)
		uri := subscriptionData.AmfStatusUri

		//////////////////////////////////////////////////////

		var (
			localVarHttpMethod   = strings.ToUpper("Post")
			localVarPostBody     interface{}
			localVarFormFileName string
			localVarFileName     string
			localVarFileBytes    []byte
		)

		// create path and map variables
		localVarPath := uri
		localVarHeaderParams := make(map[string]string)
		localVarQueryParams := url.Values{}
		localVarFormParams := url.Values{}

		localVarHttpContentTypes := []string{"application/json"}
		localVarHeaderParams["Content-Type"] = localVarHttpContentTypes[0] // use the first content type specified in 'consumes'
		localVarPostBody = &amfStatusNotification
		// to determine the Accept header
		localVarHttpHeaderAccepts := []string{"application/problem+json"}
		localVarHttpHeaderAccept := openapi.SelectHeaderAccept(localVarHttpHeaderAccepts)
		if localVarHttpHeaderAccept != "" {
			localVarHeaderParams["Accept"] = localVarHttpHeaderAccept
		}

		r, err := openapi.PrepareRequest(context.Background(), configuration, localVarPath, localVarHttpMethod, localVarPostBody, localVarHeaderParams, localVarQueryParams, localVarFormParams, localVarFormFileName, localVarFileName, localVarFileBytes)
		if err != nil {
			logger.CommLog.Info("Preparing request error")
			return false
		} else {
			logger.CommLog.Infof("Prepared request successfully")
		}
		client1 := &http.Client{
			Timeout: time.Second * 10, // Set a 10 second timeout
		}

		/////////////////////////////////////////////////////////
		logger.ProducerLog.Infof("[AMF] Send Amf Status Change Notify to %s", uri)
		httpResponse, err := client1.Do(r)
		// httpResponse, err := client.AmfStatusChangeCallbackDocumentApiServiceCallbackDocumentApi.
		// 	AmfStatusChangeNotify(context.Background(), uri, amfStatusNotification)
		if err != nil {
			if httpResponse == nil {
				HttpLog.Errorln(err.Error())
			} else if err.Error() != httpResponse.Status {
				HttpLog.Errorln(err.Error())
			}
		}
		if httpResponse != nil {
			defer httpResponse.Body.Close()
		}
		return true
	})
}
