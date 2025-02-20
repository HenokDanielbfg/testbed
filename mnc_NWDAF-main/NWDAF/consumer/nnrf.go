package consumer

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/free5gc/openapi"
	"github.com/free5gc/openapi/Nnrf_NFDiscovery"
	"github.com/free5gc/openapi/Nnrf_NFManagement"
	"github.com/free5gc/openapi/models"
	nwdaf_context "nwdaf.com/context"
	"nwdaf.com/factory"
	"nwdaf.com/logger"
)

func BuildNFInstance(context *nwdaf_context.NWDAFContext) models.NfProfile {
	var profile models.NfProfile
	config := factory.NwdafConfig
	profile.NfInstanceId = context.NfInstanceID
	// profile.NfInstanceId = "29652ae3-eaaa-4e52-8736-f6c385fe4297"

	profile.NfType = models.NfType_NWDAF
	profile.NfStatus = models.NfStatus_REGISTERED
	version := config.Info.Version
	tmpVersion := strings.Split(version, ".")
	versionUri := "v" + tmpVersion[0]
	apiPrefix := fmt.Sprintf("%s://%s:%d", context.UriScheme, context.RegisterIPv4, context.SBIPort)
	services := []models.NfService{
		{
			ServiceInstanceId: "analytics",
			ServiceName:       "nnwdaf-analyticsinfo",
			Versions: &[]models.NfServiceVersion{
				{
					ApiFullVersion:  version,
					ApiVersionInUri: versionUri,
				},
			},
			Scheme:          context.UriScheme,
			NfServiceStatus: models.NfServiceStatus_REGISTERED,
			ApiPrefix:       apiPrefix,
			IpEndPoints: &[]models.IpEndPoint{
				{
					Ipv4Address: context.RegisterIPv4,
					Transport:   models.TransportProtocol_TCP,
					Port:        int32(context.SBIPort),
				},
			},
		},
	}
	profile.NfServices = &services

	profile.HeartBeatTimer = 60
	PlmnList := []models.PlmnId{
		{Mcc: "208", Mnc: "93"},
	}
	SNssais := []models.Snssai{
		{Sst: 1, Sd: "010203"},
	}
	profile.PlmnList = &PlmnList
	profile.SNssais = &SNssais

	log.Println("Successfully built nwdaf instance")
	// log.Println(profile.NfInstanceId)

	return profile
}

func SendRegisterNFInstance(nrfUri, nfInstanceId string, profile models.NfProfile) (string, string, error) {
	// Set client and set url
	configuration := Nnrf_NFManagement.NewConfiguration()
	configuration.SetBasePath(nrfUri)
	client := Nnrf_NFManagement.NewAPIClient(configuration)
	var resouceNrfUri string
	var retrieveNfInstanceId string

	for {
		_, res, err := client.NFInstanceIDDocumentApi.RegisterNFInstance(context.TODO(), nfInstanceId, profile)
		if err != nil || res == nil {
			// TODO : add log
			fmt.Printf("Sending NF Profile for Registration: %+v\n", profile)
			fmt.Println(fmt.Errorf("NWDAF register to NRF Error[%s]", err.Error()))
			time.Sleep(2 * time.Second)
			// continue
		}
		defer func() {
			if rspCloseErr := res.Body.Close(); rspCloseErr != nil {
				logger.ConsumerLog.Errorf("RegisterNFInstance response body cannot close: %+v", rspCloseErr)
			}
		}()

		status := res.StatusCode
		if status == http.StatusOK {
			// NFUpdate
			return resouceNrfUri, retrieveNfInstanceId, err
		} else if status == http.StatusCreated {
			// NFRegister
			log.Println("Successfully registered nwdaf instance")

			resourceUri := res.Header.Get("Location")
			resouceNrfUri = resourceUri[:strings.Index(resourceUri, "/nnrf-nfm/")]
			retrieveNfInstanceId = resourceUri[strings.LastIndex(resourceUri, "/")+1:]
			return resouceNrfUri, retrieveNfInstanceId, err
		} else {
			fmt.Println("handler returned wrong status code", status)
			fmt.Println("NRF return wrong status code", status)
		}
	}
}

func SendDeregisterNFInstance() (problemDetails *models.ProblemDetails, err error) {
	logger.ConsumerLog.Infof("Send Deregister NFInstance")

	nwdafSelf := nwdaf_context.NWDAF_Self()
	// Set client and set url
	configuration := Nnrf_NFManagement.NewConfiguration()
	configuration.SetBasePath(nwdafSelf.NrfUri)
	client := Nnrf_NFManagement.NewAPIClient(configuration)
	ctx, _, err := nwdafSelf.GetTokenCtx(models.ServiceName_NNRF_DISC, models.NfType_NRF)
	if err != nil {
		return nil, err
	}

	var res *http.Response
	log.Println(nwdafSelf.NfInstanceID)
	res, err = client.NFInstanceIDDocumentApi.DeregisterNFInstance(ctx, nwdafSelf.NfInstanceID)
	if err == nil {
		log.Println("NWDAF deregistered successfully")
		return
	} else if res != nil {
		log.Println(res.StatusCode)
		defer func() {
			if rspCloseErr := res.Body.Close(); rspCloseErr != nil {
				logger.ConsumerLog.Errorf("DeregisterNFInstance response body cannot close: %+v", rspCloseErr)
			}
		}()

		if res.Status != err.Error() {
			return
		}
		problem := err.(openapi.GenericOpenAPIError).Model().(models.ProblemDetails)
		problemDetails = &problem
	} else {
		err = openapi.ReportError("server no response")
	}
	return
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
